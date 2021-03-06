#!/usr/bin/python
# -*- encoding: utf-8 -*-

# uvozimo bottle.py
from bottle import *
#import sqlite3
import hashlib
import datetime

# povezava do datoteke baza
    #baza_datoteka = 'pohodnistvo.db' 

# uvozimo ustrezne podatke za povezavo
import auth_public as auth

# uvozimo psycopg2
import psycopg2, psycopg2.extensions, psycopg2.extras
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE) # se znebimo problemov s šumniki

import os

# privzete nastavitve
SERVER_PORT = os.environ.get('BOTTLE_PORT', 8080)
RELOADER = os.environ.get('BOTTLE_RELOADER', True)
ROOT = os.environ.get('BOTTLE_ROOT', '/')
DB_PORT = os.environ.get('POSTGRES_PORT', 5432)


# odkomentiraj, če želiš sporočila o napakah
    #debug(True)

######################################################################
#ERR in druge dobrote
@error(404)
def napaka404(error):
    return '<h1>Stran ne obstaja</h1><img src="https://upload.wikimedia.org/wikipedia/commons/d/d4/S%C3%B8ren_Kierkegaard_%281813-1855%29_-_%28cropped%29.jpg" style="width:300px;height:450px;" alt="Kierkegaard"><h2>Tudi Kierkegaard se je spraševal o obstoju, nisi edini</h2><a href="{{ROOT}}pohodnistvo", font-size:px>Nazaj na začetno stran.</a>'

@error(403)
def napaka403(error):
    return '<h1>Do te strani nimaš dostopa!</h1><a href="{{ROOT}}pohodnistvo", font-size:px>Nazaj na začetno stran.</a>'


def javiNapaka(napaka = None):
    sporocilo = request.get_cookie('napaka', secret=skrivnost)
    if napaka is None:
        response.delete_cookie('napaka')
    else:
        #path doloca za katere domene naj bo napaka, default je cela domena
        response.set_cookie('napaka', napaka, path="/", secret=skrivnost)
    return sporocilo

def javiNapaka2(napaka = None):
    sporocilo = request.get_cookie('napaka2', secret=skrivnost)
    if napaka is None:
        response.delete_cookie('napaka2')
    else:
        #path doloca za katere domene naj bo napaka, default je cela domena
        response.set_cookie('napaka2', napaka, path="/", secret=skrivnost)
    return sporocilo

skrivnost = "NekaVelikaDolgaSmesnaStvar"

def dostop():
    uporabnik = request.get_cookie("uporabnik", secret=skrivnost)
    
    #povezava na bazo ne deluje, oziroma bere bazo kot prazno? HELP pls
    if uporabnik:
        cur.execute("""
                    SELECT polozaj FROM oseba 
                    WHERE uporabnik = %s""", (uporabnik,))
        polozaj = cur.fetchone()
        return [uporabnik,polozaj[0]]
    redirect('{0}prijava'.format(ROOT))

######################################################################
# OSNOVNE STRANI

def rtemplate(*largs, **kwargs):
    """
    Izpis predloge s podajanjem spremenljivke ROOT z osnovnim URL-jem.
    """
    return template(ROOT=ROOT, *largs, **kwargs)

@get('/')
def osnovna_stran():
    #če prijavljen/registriran potem glavna_stran.html stran sicer prijava.html
    redirect('{0}pohodnistvo'.format(ROOT))

@get('/pohodnistvo')
def glavna_stran():
    user= dostop()
    return rtemplate('glavna_stran.html', 
                    naslov='Pohodništvo',
                    user=user)

@get('/o_projektu')
def o_projektu():
    uporabnik = request.get_cookie("uporabnik", secret=skrivnost)
    cur.execute("""SELECT polozaj FROM oseba 
                    WHERE uporabnik = %s""", (uporabnik,))
    polozaj = cur.fetchone()
    if polozaj:
        user = [uporabnik,polozaj[0]]
    else:
        user = None
    return rtemplate('o_projektu.html', naslov='O projektu', user=user)

######################################################################
# PRIJAVA / REGISTRACIJA

#zakodirajmo geslo
def hashGesla(s):
    m = hashlib.sha256()
    m.update(s.encode("utf-8"))
    return m.hexdigest()

@get('/registracija')
def registracija_get():
    user = request.get_cookie("uporabnik", secret=skrivnost)
    napaka = javiNapaka()
    return rtemplate('registracija.html', 
                    naslov='Registracija', 
                    napaka = napaka,
                    user=user)

@post('/registracija')
def registracija_post():
    #poberimo vnesene podatke
    identiteta = request.forms.identiteta
    uporabnik = request.forms.uporabnik
    geslo = request.forms.geslo
    iden = None

    try: 
        cur.execute("""
                    SELECT ime FROM oseba 
                    WHERE id = %s""", (identiteta,))
        iden = cur.fetchone()
    except:
        iden = None

    if iden is None:
        #id ne obstaja, ni član društva
        javiNapaka("Nisi (še) član društva, zato tvoj ID ne obstaja v bazi")
        redirect('{0}registracija_dodatna'.format(ROOT))
        return

    if len(geslo)<4:
        #dolzina gesla
        javiNapaka("Geslo prekratko. Dolžina gesla mora biti vsaj 5")
        redirect('{0}registracija'.format(ROOT))
        return

    cur.execute("""
                SELECT id FROM oseba 
                WHERE uporabnik = %s""", (uporabnik,))
    
    identiteta2 = cur.fetchone()
    if identiteta2 != None and identiteta != identiteta2:
        #enolicnost uporabnikov
        javiNapaka("To uporabniško ime je zasedeno")
        redirect('{0}registracija'.format(ROOT))
        return

    zgostitev = hashGesla(geslo)
    #brez str() ima lahko težave s tipom podatkov
    cur.execute("UPDATE oseba SET uporabnik = %s, geslo = %s, polozaj = %s WHERE id = %s", (str(uporabnik), str(zgostitev), 0, str(identiteta)))
    #dolocimo osebo ki uporablja brskalnik (z njo dolocimo cookie)
    response.set_cookie('uporabnik', uporabnik, secret=skrivnost)
    redirect('{0}pohodnistvo'.format(ROOT))


@get('/registracija_dodatna')
def registracija_dodatna_get():
    user = request.get_cookie("uporabnik", secret=skrivnost)
    javiNapaka()
    return rtemplate('registracija_dodatna.html', naslov='Registracija nove osebe',user=user)

@post('/registracija_dodatna')
def registracija_dodatna_post():
    #poberimo dodatne vnesene podatke
    identiteta = request.forms.identiteta
    ime = request.forms.ime
    priimek = request.forms.priimek
    starost = request.forms.starost
    spol = request.forms.spol
    drustvo = request.forms.drustva
    uporabnik = request.forms.uporabnik
    geslo = request.forms.geslo

    if len(identiteta)>4:
        #id je predolga
        javiNapaka(napaka="Identiteta predolga.")
        redirect('{0}registracija_dodatna'.format(ROOT))
        return

    cur.execute("SELECT id FROM oseba")
    identitete_veljavne = cur.fetchall()
    if identiteta in identitete_veljavne:
        #id je že zasedena
        javiNapaka(napaka="Izbrana identiteta je že zasedena")
        redirect('{0}registracija_dodatna'.format(ROOT))
        return

    if len(geslo)<4:
        #dolzina gesla
        javiNapaka(napaka="Geslo prekratko. Dolžina gesla mora biti vsaj 5")
        redirect('{0}registracija_dodatna'.format(ROOT))
        return

    cur.execute("SELECT uporabnik FROM oseba")
    identiteta_ze_registriranih= cur.fetchall()
    if  uporabnik in identiteta_ze_registriranih:
        #enolicnost uporabnikov
        javiNapaka(napaka="To uporabniško ime je zasedeno")
        redirect('{0}registracija_dodatna'.format(ROOT))
        return

    polozaj = 0
    zgostitev = hashGesla(geslo)
    #dodamo osebo v tabelo oseba
    cur.execute("""INSERT INTO oseba (id, ime, priimek, starost, spol, drustvo, uporabnik, geslo, polozaj) 
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (int(identiteta), str(ime), str(priimek), int(starost), str(spol), str(drustvo), str(uporabnik), str(zgostitev), str(polozaj)))
    #dolocimo osebo ki uporablja brskalnik (z njo dolocimo cookie)
    response.set_cookie('uporabnik', uporabnik, secret=skrivnost)
    redirect('{0}pohodnistvo'.format(ROOT))
    return 


@get('/prijava')
def prijava():
    
    napaka = javiNapaka()
    user = request.get_cookie("uporabnik", secret=skrivnost)

    return rtemplate('prijava.html', 
                    naslov='Prijava', 
                    napaka=napaka,
                    user=user)

@post('/prijava')
def prijava_post():
    #poberimo vnesene podatke
    uporabnik = request.forms.uporabnik
    geslo = request.forms.geslo
    
    hashGeslo = None
    try: 
        ukaz = ("SELECT geslo FROM oseba WHERE uporabnik = (%s)")
        cur.execute(ukaz, (uporabnik,))
        hashGeslo = cur.fetchone()
        hashGeslo = hashGeslo[0]
    except:
        hashGeslo = None
    if hashGeslo is None:
        javiNapaka('Niste še registrirani')
        redirect('{0}prijava'.format(ROOT))
        return
    if hashGesla(geslo) != hashGeslo:
        javiNapaka('Geslo ni pravilno')
        redirect('{0}prijava'.format(ROOT))
        return
    response.set_cookie('uporabnik', uporabnik, secret=skrivnost)
    redirect('{0}pohodnistvo'.format(ROOT))

@get('/odjava')
def odjava():
    response.delete_cookie('uporabnik')
    response.delete_cookie('identiteta')
    response.delete_cookie('napaka')
    response.delete_cookie('napaka2')
    redirect('{0}prijava'.format(ROOT))
    
######################################################################
# MOJE DRUŠTVO

@get('/moje_drustvo')
def moje_drustvo():
    user = dostop()
    uporabnik = str(user[0])
    

    cur.execute("""SELECT drustvo FROM oseba 
                WHERE uporabnik = %s""", (uporabnik,))
    drustvo = cur.fetchone()

    cur.execute("""SELECT id, ime, priimek, spol, starost 
                FROM oseba WHERE drustvo = %s 
                ORDER BY oseba.priimek""", (str(drustvo[0]),))
    osebe = cur.fetchall()

    polozaj = int(user[1])
    return rtemplate('moje_drustvo.html', 
                    naslov='Moje društvo',
                    osebe=osebe, 
                    polozaj = polozaj,
                    user = uporabnik)


@get('/osebe/dodaj_osebo_drustvo')
def dodaj_osebo_drustvo():
    user = dostop()
    if int(user[1]) > 0:
        redirect('{0}osebe/dodaj_osebo'.format(ROOT))
    else:
        raise HTTPError(403)

######################################################################
# OSEBE

@get('/osebe')
def osebe():
    user = dostop()
    if int(user[1])!=2:
        raise HTTPError(403)

    cur.execute("""
                SELECT id, ime, priimek, spol, starost, drustvo FROM oseba
                ORDER BY oseba.priimek""")
    osebe = cur.fetchall()

    return rtemplate('osebe.html', 
                     osebe=osebe, 
                     naslov='Pohodniki',
                     user=user[0])

@get('/osebe/dodaj_osebo')
def dodaj_osebo():
    user = dostop()
    if int(user[1])!=2:
        raise HTTPError(403)
    cur.execute("""
                SELECT drustva.ime FROM drustva
                ORDER BY drustva.ime""")
    drustvo = cur.fetchall()
    #naredimo list iz tuple
    drustvo = [x[0] for x in drustvo]

    return rtemplate('dodaj_osebo.html', 
                     drustvo=drustvo,
                     naslov='Dodaj osebo',
                     user=user[0])

@post('/osebe/dodaj_osebo')
def dodaj_osebo_post():
    ime = request.forms.get('ime')
    priimek = request.forms.get('priimek')
    spol = request.forms.get('spol')
    if spol == 'Male':
        pass
    else:
        spol = 'Female'
    starost = request.forms.get('starost')
    drustvo = request.forms.get('drustvo')
    
    cur.execute("""INSERT INTO oseba (ime, priimek, spol, starost, drustvo) 
                VALUES (%s, %s, %s, %s, %s)""", (ime, priimek, spol, starost, drustvo))
    redirect('{0}osebe'.format(ROOT))

@get('/osebe/uredi/<identiteta:int>')
def uredi_osebo(identiteta):
    user = dostop()
    response.set_cookie('identiteta',identiteta,secret=skrivnost)

    #jaz je ta, ki uporablja brskalnik
    cur.execute("""SELECT id FROM oseba 
                WHERE uporabnik = %s""", (str(user[0]),))
    jaz = cur.fetchone()

    if identiteta != jaz and int(user[1]) != 2:
        raise HTTPError(403)

    #poiscemo drustva
    cur.execute("""SELECT drustva.ime FROM drustva ORDER BY drustva.ime""")
    drustvo = cur.fetchall()
    #naredimo list iz tupla
    drustvo = list(drustvo)

    #bomo dali v naslov tab-a
    cur.execute("""SELECT ime, priimek 
                FROM oseba WHERE id = %s""", (str(identiteta),))
    ime = cur.fetchone()

    #oseba katere stran urejam
    cur.execute("""SELECT id, ime, priimek, spol, starost, drustvo 
                FROM oseba WHERE id = %s""", (identiteta,))
    oseba = cur.fetchone()

    return rtemplate('oseba-edit.html', 
                     oseba=oseba, 
                     drustvo=drustvo, 
                     naslov="Urejanje "+ime[0]+' '+ime[1],
                     user=user[0])

@post('/osebe/uredi/<identiteta:int>')
def uredi_osebo_post(identiteta):
    ime = request.forms.get('ime')
    priimek = request.forms.get('priimek')
    spol = request.forms.get('spol')
    starost = request.forms.get('starost')

    
    cur.execute("UPDATE oseba SET ime = %s, priimek = %s, spol = %s, starost = %s WHERE id = %s", 
                (str(ime), str(priimek), str(spol), int(starost), int(identiteta)))
    redirect('{0}moje_drustvo'.format(ROOT))


@post('/osebe/brisi/<identiteta:int>')
def brisi_osebo(identiteta):
    user = dostop()
    if int(user[1])!=2:
        raise HTTPError(403)

    cur.execute("DELETE FROM oseba WHERE id = %s", (identiteta,))
    redirect('{0}osebe'.format(ROOT))

@get('/osebe/<identiteta:int>')
def lastnosti_osebe(identiteta):
    user = dostop()
    #dolocim identiteto osebe, kjer bom brskal (admin ni nujno enak identiteti kjer ureja)
    response.set_cookie('identiteta',identiteta,secret=skrivnost)

    

    cur.execute("SELECT drustvo FROM oseba WHERE uporabnik = %s", (str(user[0]),))
    drustvo = cur.fetchone()
    cur.execute("SELECT drustvo FROM oseba WHERE id = %s", (identiteta,))
    drustvoID = cur.fetchone()

    if drustvo != drustvoID and int(user[1])!=2:
        raise HTTPError(403)

    cur.execute("""SELECT id, ime, priimek, spol, starost, drustvo 
                FROM oseba WHERE id = %s""", (identiteta,))
    oseba = cur.fetchone()

    #ta ki lahko dodaja hribe v tabelo obiskani za določenega posameznika je admin in oseba sama
    cur.execute("SELECT id FROM oseba WHERE uporabnik = %s", (str(user[0]),))
    jaz = cur.fetchone()

    #to preverim s spremenljivko dodaj, ki je true kadar lahko dodam
    dodaj = False
    if jaz[0] == int(identiteta) or user[1]==2:
        dodaj = True

    #najvisji osvojen vrh
    cur.execute("""
                SELECT visina, ime FROM gore WHERE 
                id IN (SELECT id_gore FROM obiskane 
                WHERE id_osebe = %s) ORDER BY visina""", (identiteta,))
    najvisji_osvojen_vrh = cur.fetchall()

    najvisja_gora = [0,None]
    if najvisji_osvojen_vrh != []:
        najvisji_osvojen_vrh = najvisji_osvojen_vrh[-1]
        if najvisji_osvojen_vrh[1] is not None and najvisji_osvojen_vrh[0] is not None:
            if najvisja_gora[0] <= najvisji_osvojen_vrh[0]:
                najvisja_gora = najvisji_osvojen_vrh

    #stevilo gora, na katerih je bil pohodnik
    cur.execute("""
                SELECT COUNT(id_gore) FROM obiskane
                WHERE id_osebe = %s""", (str(identiteta),))
    stevilo_osvojenih_gor = cur.fetchone()

    #vse gore na katerih je bil/bila
    cur.execute(""" 
                 SELECT ime, visina, gorovje, drzava, leto_pristopa FROM gore
                 JOIN obiskane ON id = id_gore
                 WHERE id_osebe = %s
                 ORDER BY ime
                 """, (str(identiteta), )) 
    vse_osvojene_gore = cur.fetchall() 

    return rtemplate('oseba-id.html',  
                     oseba=oseba, 
                     stevilo_osvojenih_gor=stevilo_osvojenih_gor[0],
                     najvisji_osvojen_vrh=najvisja_gora, 
                     vse_osvojene_gore=vse_osvojene_gore,
                     naslov='Pohodnik {0} {1}'.format(oseba[1], oseba[2]), 
                     identiteta=identiteta, 
                     dodaj=dodaj,
                     user=user[0])

@get('/osebe/dodaj goro')
def osvojena_gora():
    user=dostop()
    
    cur.execute("""SELECT id, prvi_pristop, ime, visina, gorovje, drzava 
                FROM gore ORDER BY ime""")
    gore = cur.fetchall()
    return rtemplate('dodaj_osvojeno_goro.html', 
                    gore=gore, 
                    naslov='Nov osvojen hrib',
                    user=user[0])

@post('/osebe/dodaj goro')
def osvojena_gora_post():
    
    #seznam gora
    gore = cur.execute("SELECT id FROM gore")
    gore = list(cur.fetchall())

    identiteta = request.get_cookie('identiteta', secret=skrivnost)

    #osvojene gore
    cur.execute("SELECT id_gore, leto_pristopa FROM obiskane WHERE id_osebe = %s",(identiteta,))
    prej_osvojene_vse = cur.fetchall()
    prej_osvojene = [i[0] for i in prej_osvojene_vse]
    osvojene = []

    time = datetime.datetime.now()

    #cursor nam vrne seznam tuplov [(int,), ...]
    for i in gore:
        #element gore je tuple oblike (integer,)
        i=i[0]
        #zapeljem se čez vse gore in pogledam, če je že osvojen
        j = request.forms.get(str(i))
        if j and int(j) not in prej_osvojene:
            leto = int(time.year)
            osvojene.append((int(j),leto))
    
    if prej_osvojene_vse != []:
        for i in prej_osvojene_vse:
            osvojene.append(i)
    #sčistim bazo že osvojenih za naš id in dodam osvojene in leto
    cur.execute("DELETE FROM obiskane WHERE id_osebe = %s", (identiteta,))
    for gora in osvojene:
        cur.execute("INSERT INTO obiskane (id_gore, id_osebe, leto_pristopa) VALUES (%s, %s, %s)",(int(gora[0]), str(identiteta), gora[1]))
    identiteta = str(identiteta)
    redirect('{0}osebe/{1}'.format(ROOT,identiteta))

@get('/osebe/brisi goro')
def brisi_goro():
    user=dostop()

    identiteta = request.get_cookie('identiteta', secret=skrivnost)

    cur.execute(""" 
                 SELECT id, prvi_pristop, ime, visina, gorovje, drzava  FROM gore
                 JOIN obiskane ON id = id_gore
                 WHERE id_osebe = %s
                 ORDER BY ime
                 """, (identiteta, )) 
    gore = cur.fetchall()
    return rtemplate('odstrani_osvojeno_goro.html', 
                    gore=gore, 
                    naslov='Zlagan dosežek',
                    user=user[0])

@post('/osebe/brisi goro')
def brisi_goro_post():

    identiteta = request.get_cookie('identiteta', secret=skrivnost)

    cur.execute("SELECT id_gore, leto_pristopa FROM obiskane WHERE id_osebe = %s",(identiteta,))
    j = cur.fetchall()


    for id_gore in j:
        #pogledamo katere id-je smo obkljukali
        i = request.forms.get(str(id_gore[0]))
        cur.execute("DELETE FROM obiskane WHERE id_osebe = %s and id_gore = %s", (identiteta, i, ))
    

    identiteta = str(identiteta)
    pot = '{0}osebe/{1}'.format(ROOT,identiteta)
    redirect(pot)
######################################################################
# GORE

@get('/gore')
def gore():
    cur.execute("""
                SELECT prvi_pristop, ime, visina, gorovje, drzava 
                FROM gore ORDER BY ime
                """)
    gore = cur.fetchall()

    uporabnik = request.get_cookie("uporabnik", secret=skrivnost)
    if uporabnik is not None:
        cur.execute("""
                        SELECT polozaj FROM oseba 
                        WHERE uporabnik = %s""", (uporabnik,))
        polozaj = (cur.fetchone())[0]
    else:
        polozaj = 0
    return rtemplate('gore.html', gore=gore, pravice=polozaj, naslov='Gore', user = uporabnik)

@get('/gore/dodaj goro')
def dodaj_goro():
    user=dostop()
    javiNapaka2()
    
    cur.execute("""
                SELECT gorovje.ime FROM gorovje
                ORDER BY gorovje.ime
                """)
    gorovje = cur.fetchall()
    #naredimo list iz tuple
    gorovje = [x[0] for x in gorovje]

    cur.execute("""
                SELECT drzave.ime FROM drzave
                ORDER BY drzave.ime
                """)
    drzave = cur.fetchall()
    drzave = [y[0] for y in drzave]

    napaka = request.get_cookie('napaka2',secret=skrivnost)

    return rtemplate('dodaj_goro.html', 
                    gorovje=gorovje, 
                    drzave=drzave, 
                    naslov='Dodaj goro',
                    user=user[0],
                    napaka=napaka)

@post('/gore/dodaj goro')
def dodaj_goro_post():
    ime = request.forms.get('ime_gore')
    visina = request.forms.get('visina')
    prvi_pristop = request.forms.get('prvi_pristop')
    drzava = request.forms.get('drzava')
    gorovje = request.forms.get('gorovje')

    if int(visina)>8886:
        javiNapaka2("Vnešena višina je nezemeljska!")
        redirect('{0}gore/dodaj goro'.format(ROOT))
        return

    time = datetime.datetime.now()
    leto = int(time.year)
    if int(prvi_pristop)>leto:
        javiNapaka2("To leto je v prihodnosti!")
        redirect('{0}gore/dodaj goro'.format(ROOT))
        return
    
    cur.execute("""INSERT INTO gore (prvi_pristop, ime, visina, gorovje, drzava)
        VALUES (%s, %s, %s, %s, %s)""",
         (int(prvi_pristop), str(ime), int(visina), str(gorovje), str(drzava)))
    redirect('{0}gore'.format(ROOT))

######################################################################
# DRUSTVA

@get('/drustva')
def drustva():
    user=dostop()
    
    cur.execute("""
                SELECT id, ime, leto_ustanovitve FROM drustva
                ORDER BY drustva.ime
                """)
    drustva = cur.fetchall()
    return rtemplate('drustva.html', 
                    drustva=drustva, 
                    naslov='Društva',
                    user=user[0])

@get('/drustva/<ime>')
def drustva_id(ime):
    user=dostop()
    
    cur.execute("""
                SELECT id, ime, leto_ustanovitve FROM drustva
                WHERE ime = %s""",(ime,))
    drustvo = cur.fetchone()

    cur.execute("""
                SELECT COUNT (oseba.drustvo) FROM oseba
	            WHERE oseba.drustvo = 
                (SELECT ime FROM drustva WHERE ime = %s)""",(ime,))
    stevilo_clanov_drustvo = cur.fetchone()

    cur.execute("""
                SELECT id, ime, priimek, spol, starost FROM oseba
	            WHERE oseba.drustvo = 
                (SELECT ime FROM drustva WHERE ime = %s)""",(ime,))
    clani_drustva = cur.fetchall()

    stevilo_vseh = 0
    najvisja_gora = [0,None]
    for clan in clani_drustva:
        identiteta = clan[0]
        #stevilo osvojenih gora za posameznika
        cur.execute("""
                    SELECT COUNT (id_gore) FROM obiskane 
                    WHERE id_osebe = %s""",(identiteta,))
        
        osvojenih_gora = cur.fetchone()
        stevilo_vseh += osvojenih_gora[0]

        #najvisja gora za posameznika
        cur.execute("""
                    SELECT visina, ime FROM gore WHERE 
                    id IN (SELECT id_gore FROM obiskane 
                    WHERE id_osebe = %s) ORDER BY visina""", (identiteta,))
        najvisji_osvojen_vrh = cur.fetchall()

        if najvisji_osvojen_vrh != []:
            najvisji_osvojen_vrh = najvisji_osvojen_vrh[-1]
            if najvisji_osvojen_vrh[1] is not None and najvisji_osvojen_vrh[0] is not None:
                if najvisja_gora[0] <= najvisji_osvojen_vrh[0]:
                    najvisja_gora = najvisji_osvojen_vrh

    #naredimo list iz tuple
    clani_drustva = [(x[1], x[2], x[3], x[4]) for x in clani_drustva]       

    
    return rtemplate('drustvo-id.html', 
                     drustvo=drustvo,
                     stevilo_clanov_drustvo=stevilo_clanov_drustvo[0],
                     clani_drustva=clani_drustva,
                     naslov='Društvo {0}'.format(ime), 
                     vse = stevilo_vseh, 
                     najvisja = najvisja_gora,
                     user=user[0])
        
######################################################################
# Za STATIC datoteke(slike)

# Mapa za statične vire (slike, css, ...)
static_dir = "./static"

@get('/static/<filename:path>')
def static(filename):
    return static_file(filename, root='static')

######################################################################
# Glavni program

#baza sqlite3 v tej mapi (pohodnistvo.db)
    #baza = sqlite3.connect(baza_datoteka, isolation_level=None)
    #baza.set_trace_callback(print) # izpis sql stavkov v terminal (za debugiranje pri razvoju)
    #

# priklopimo se na bazo na fmf
baza = psycopg2.connect(database=auth.db, host=auth.host, user=auth.user, password=auth.password, port=DB_PORT)
baza.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

cur = baza.cursor(cursor_factory=psycopg2.extras.DictCursor)

# zapoved upoštevanja omejitev FOREIGN KEY
#cur.execute("PRAGMA foreign_keys = ON;")

# poženemo strežnik na podanih vratih, npr. http://localhost:8080/
run(host='localhost', port=SERVER_PORT, reloader=RELOADER)