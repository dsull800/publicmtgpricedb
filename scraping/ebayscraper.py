from creds.credentials import host, port, dbname, user, password
import psycopg2
from itertools import chain
import numpy as np
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta
import re
import pytz

conn = psycopg2.connect(host=host, user=user,
                        password=password, database=dbname)

cur = conn.cursor()

cur.execute('''SELECT DISTINCT(name) FROM 
(SELECT DISTINCT(name) as name FROM public.cards WHERE name NOT ILIKE('%//%') 
 AND rarity IN('mythic','rare') 
 AND setcode IN(SELECT code FROM public.sets WHERE type IN ('expansion','core')
                and releasedate>=(SELECT releasedate FROM public.sets WHERE mcmname='Return to Ravnica')) 
 UNION SELECT DISTINCT(facename) FROM public.cards 
 WHERE name ILIKE('%//%') AND rarity IN('mythic','rare') 
 AND setcode IN(SELECT code FROM public.sets WHERE type IN ('expansion','core')
                and releasedate>=(SELECT releasedate FROM public.sets WHERE mcmname='Return to Ravnica'))) as baz 
                NATURAL JOIN (SELECT DISTINCT(pio.cardname) as name 
                              FROM ((SELECT DISTINCT(cardname) FROM tourninfo) 
                                    AS pio INNER JOIN (SELECT DISTINCT(cardname) FROM moderntourninfo) 
                                    AS mod ON pio.cardname=mod.cardname)) as boz''')

rows = cur.fetchall()
rows = set(rows)
usedusedrows = set()

cur.execute(
    """SELECT name,rarity FROM public.cards WHERE rarity IN('mythic','rare') AND setcode IN(SELECT code FROM public.sets WHERE type IN ('expansion','core') and releasedate>=(SELECT releasedate FROM public.sets WHERE mcmname='Return to Ravnica'))""")
cardraritys = cur.fetchall()
cardraritys = set(cardraritys)


def ebay_scrape(rows, usedusedrows):
    try:
        headers = requests.utils.default_headers()
        headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36',
        })

        xfun = lambda x: "x" + str(x)
        funx = lambda x: str(x) + "x"
        x_fun = lambda x: "×" + str(x)
        funx_ = lambda x: str(x) + "×"
        xspacefun = lambda x: "x " + str(x)
        funspacex = lambda x: str(x) + " x"
        funspacex_ = lambda x: str(x) + " ×"
        x_spacefun = lambda x: "× " + str(x)
        enclosedfun = lambda x: "(" + str(x) + ")"
        starfun = lambda x: f"*{x}*"

        titlequantities = list(chain.from_iterable((enclosedfun(x), x_fun(x), funx_(x), funspacex_(x), x_spacefun(x),
                                                    xfun(x), funx(x), xspacefun(x), funspacex(x), starfun(x)) for x in
                                                   range(8, 0, -1)))  # all lowercase
        # remember to add 1 x and x 1 to title quantities
        titlekeywords = ["time shifted", "timeshifted", "SDCC", "ugins fate", 'wall scroll',
                         "ugin's fate", "summer magic", "proxy", "not real", "stained glass",
                         'stained-glass', "borderless", "factory sealed", "godzilla", ' plus ', 'apocalyplse',
                         "showcase", "promo", "expedition", "masterpiece", "mythic edition", 'apocalypse',
                         "invocation", "invention", "extended art", "constellation", "altered", 'minature',
                         "full art", "secret lair", "stained glass", "miscut", "alternate art", 'alt art',
                         "anime", "poster", "signed", "painted", "custom", "alter", 'art card', 'art series',
                         'comic-con', 'comic con',
                         'world magic cup', 'ext art', 'ext. art', 'Alter', 'autograph', 'auto', 'extended', 'mystery',
                         '50%', 'box topper',
                         'boxtopper', 'signature spellbook', 'shirt', 'not tournament legal', 'damaged', 'generic',
                         'checklist',
                         'collection', 'assorted', 'odyssey', 'prerelease', 'pre-release', 'arena code', 'game day',
                         'extend art']  # altered art?

        titlelanguages = ['english', 'korean', 'japanese', 'chinese', 'russian', 'spanish']
        titleconditions = ['NM', 'LP', 'MP', 'HP', 'Mint', 'Lightly Played', 'Moderately Played', 'Heavily Played',
                           'Damage']
        Lottypes = ['lot ', ' lot ', ' lot', 'bundle ', ' bundle ', ' bundle']
        gradetypes = [' PSA ', ' Beckett ', ' BGS ', ' CGC ', 'grade']

        utc_now = pytz.utc.localize(datetime.utcnow())
        pst_now = utc_now.astimezone(pytz.timezone("US/Central"))
        yesterday = pst_now - timedelta(1)

        print(yesterday)

        rows = ((rows) - usedusedrows)

        list_rows = list(rows)

        # for cardname in list_rows:
        while len(list_rows) > 0:
            cardname = list_rows[0]

            conn = psycopg2.connect(host=host, user=user,
                                    password=password, database=dbname)
            cur = conn.cursor()

            if (cardname[0], 'rare') in cardraritys:
                rarity = 'rare'
            else:
                rarity = 'mythic'

            if cardname is None:
                print("NONE")
            else:
                cur.execute("""SELECT DISTINCT(printings) FROM public.cards WHERE name=%s""", (cardname))
                cardprintings = cur.fetchall()
                setlist = set()
                for printitem in cardprintings:
                    cardstring = printitem[0]
                    stringlist = cardstring.split(",")
                    setlist = setlist.union(set(stringlist))

                url = requests.get('https://www.ebay.com/sch/i.html?_nkw=' + cardname[
                    0] + ' mtg' + '&rt=nc&LH_Sold=1&LH_Complete=1&_ipg=200&_pgn=1',
                                   timeout=5)  # added this 05-06-2020 headers=headers

                rawtext = BeautifulSoup(url.text, 'html.parser')
                transactions = rawtext.find_all('div', attrs={"class": "s-item__info clearfix"})

                while len(transactions) == 0:
                    if len(list_rows) != 1:
                        cardname = list_rows[np.random.randint(0, len(list_rows) - 1)]
                    else:
                        cardname = list_rows[0]

                    url = requests.get('https://www.ebay.com/sch/i.html?_nkw=' + cardname[
                        0] + ' mtg' + '&rt=nc&LH_Sold=1&LH_Complete=1&_ipg=200&_pgn=1',
                                       timeout=5)  # added this 05-06-2020 headers=headers

                    rawtext = BeautifulSoup(url.text, 'html.parser')
                    transactions = rawtext.find_all('div', attrs={"class": "s-item__info clearfix"})

                if len(transactions) > 1:
                    print(cardname)
                    conn = psycopg2.connect(host=host, user=user,
                                            password=password, database=dbname)
                    cur = conn.cursor()

                    cur.execute('''SELECT MAX(carddate) FROm public.transactions WHERE cardname=%s''', (cardname))
                    max_carddate = cur.fetchall()
                    if max_carddate[0][0] is None:
                        newscrape = True
                        yesteryesterday = pst_now - timedelta(100)
                    else:
                        newscrape = False
                        yesteryesterday = datetime.strptime(max_carddate[0][0], '%Y-%m-%d') + timedelta(1)
                    for transaction in transactions[1:]:

                        transactionsetcode = None
                        price = None
                        title = None
                        carddate = None
                        IsFoil = None
                        saletype = None
                        cardquantity = None
                        cardspecial = None
                        cardlanguage = None
                        cardcondition = None
                        shipping = 0
                        possiblybad = False
                        isBanned = False
                        isLot = False
                        isboosterbox = None
                        isgraded = None
                        isemblem = None

                        price_div = transaction.find_all(attrs={"class": "s-item__title--tag"})
                        date_uncleaned = price_div[0].find_all('span', attrs={"class": "POSITIVE"})[0].getText()
                        date_cleaned = date_uncleaned[6:18]
                        carddate = datetime.strptime(date_cleaned, '%b %d, %Y').date()
                        print(carddate)

                        if yesteryesterday.date() > carddate:
                            if newscrape:
                                timed = timedelta(100)
                            else:
                                timed = timedelta(10)
                            if yesteryesterday.date() > carddate + timed:
                                continue
                            break

                        elif yesterday.date() >= carddate and yesteryesterday.date() <= carddate:

                            if transaction.find_all('div', attrs={"class": "s-item__title"})[0].string == None or len(
                                    transaction.find_all('div', attrs={"class": "s-item__title"})) == 0:
                                print("no title")
                                pass

                            else:
                                title = transaction.find_all('div', attrs={"class": "s-item__title"})[0].string

                                for setcode in setlist:
                                    setcode = setcode.strip()
                                    if title.lower().find(setcode.lower()) != -1 and cardname[0].lower().find(
                                            setcode.lower()) == -1:
                                        transactionsetcode = setcode

                                    else:
                                        cur.execute("""SELECT name,mcmname FROM public.sets WHERE code=%s""", [setcode])
                                        setname = cur.fetchall()
                                        if len(setname) == 0:
                                            pass
                                        else:
                                            if title.lower().find(setname[0][0].lower()) != -1:
                                                transactionsetcode = setcode
                                            if setname[0][1] != None and title.lower().find(
                                                    setname[0][1].lower()) != -1:
                                                transactionsetcode = setcode
                                                break

                                if title.lower().find(cardname[0].lower()) == -1:
                                    print("no cardname")
                                    pass
                                else:

                                    for lottype in Lottypes:
                                        if title.lower().find(lottype) != -1 and cardname[0].lower().find(
                                                lottype) == -1:
                                            isLot = True

                                    if title.lower().find("playset") != -1:
                                        cardquantity = 4

                                    for quantity in titlequantities:
                                        if title.lower().find(quantity.lower()) != -1:
                                            quant = re.findall("(\d+)", quantity)
                                            cardquantity = int(quant[0])
                                            break

                                    IsFoil = title.lower().find("foil") != -1 and cardname[0].lower().find("foil") == -1

                                    isemblem = title.lower().find("emblem") != -1 and cardname[0].lower().find(
                                        "emblem") == -1

                                    isboosterbox = title.lower().find("booster box") != -1 or title.lower().find(
                                        "boosterbox") != -1

                                    iscommanderdeck = title.lower().find("commander deck") != -1

                                    istoken = title.lower().find("token") != -1 and cardname[0].lower().find(
                                        "token") == -1

                                    for keyword in titlekeywords:
                                        if title.lower().find(keyword.lower()) != -1 and cardname[0].lower().find(
                                                keyword.lower()) == -1:
                                            cardspecial = keyword
                                            break

                                    for language in titlelanguages:
                                        if title.lower().find(language.lower()) != -1:
                                            cardlanguage = language
                                            break

                                    for condition in titleconditions:
                                        if title.lower().find(condition.lower()) != -1:
                                            cardcondition = condition
                                            break

                                    for gradetype in gradetypes:
                                        if title.lower().find(gradetype.lower()) != -1 and cardname[0].lower().find(
                                                gradetype.lower()) != -1:
                                            isgraded = True
                                            break

                                    if len(transaction.find_all('span', attrs={"class": "s-item__price"})) == 0:
                                        print("no price")
                                        pass

                                    else:
                                        intermedprice = transaction.find_all('span', attrs={"class": "s-item__price"})
                                        if len(intermedprice[0].find_all('span', attrs={
                                            "class": "STRIKETHROUGH POSITIVE ITALIC"})) == 1:
                                            saletype = 'strikethrough italic'
                                            price = float(re.sub(r'[^\d.]', '', intermedprice[0].find_all('span',
                                                                                                          attrs={
                                                                                                              "class": "STRIKETHROUGH POSITIVE ITALIC"})[
                                                0].string))
                                        elif len(intermedprice[0].find_all('span',
                                                                           attrs={"class": "POSITIVE ITALIC"})) == 1:
                                            saletype = 'italic'
                                            price = float(re.sub(r'[^\d.]', '', intermedprice[0].find_all('span',
                                                                                                          attrs={
                                                                                                              "class": "POSITIVE ITALIC"})[
                                                0].string))
                                        elif len(intermedprice[0].find_all('span', attrs={
                                            "class": "STRIKETHROUGH POSITIVE"})) == 1:
                                            saletype = 'BO accepted'
                                            price = float(re.sub(r'[^\d.]', '', intermedprice[0].find_all('span',
                                                                                                          attrs={
                                                                                                              "class": "STRIKETHROUGH POSITIVE"})[
                                                0].string))
                                        elif len(intermedprice[0].find_all('span', attrs={"class": "POSITIVE"})) == 1:
                                            saletype = 'normal'
                                            price = float(re.sub(r'[^\d.]', '', intermedprice[0].find_all('span',
                                                                                                          attrs={
                                                                                                              "class": "POSITIVE"})[
                                                0].string))

                                    if len(transaction.find_all('span', attrs={
                                        "class": "s-item__shipping s-item__logisticsCost"})) == 0:
                                        print("no shipping 1st")
                                        pass

                                    elif re.sub(r'[^\d.]', '', transaction.find_all('span', attrs={
                                        "class": "s-item__shipping s-item__logisticsCost"})[0].string) == '':
                                        print("no shipping 2nd")
                                        pass
                                    else:
                                        shipping = float(re.sub(r'[^\d.]', '', transaction.find_all('span', attrs={
                                            "class": "s-item__shipping s-item__logisticsCost"})[0].string))

                                    cur.execute("""INSERT INTO transactions (cardname,price,carddate,IsFoil,saletype,cardquantity,
                                    cardspecial,cardlanguage,cardcondition,title,possiblybad,isBanned,shipping,cardset,rarity,lotis,isboosterbox,isgraded,iscommanderdeck,istoken,isemblem) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                                                (cardname, price, carddate, IsFoil, saletype, cardquantity, cardspecial,
                                                 cardlanguage, cardcondition, title, possiblybad, isBanned, shipping,
                                                 transactionsetcode, rarity, isLot, isboosterbox, isgraded,
                                                 iscommanderdeck, istoken, isemblem))
                                    print('executed')

                        else:
                            pass

                    conn.commit()
                    cur.close()
                    conn.close()
                    usedusedrows.add(cardname)
                    list_rows.remove(cardname)
                    print('committed')
                else:
                    pass


    except Exception as e:
        print(e)
        import traceback
        print(traceback.format_exc())

        if conn.closed == 0:
            conn.close()
        else:
            pass
        ebay_scrape(rows, usedusedrows)


ebay_scrape(rows, usedusedrows)

cur.close()
conn.close()
