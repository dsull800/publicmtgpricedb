import sys
import os

sys.path.append(os.getcwd())
from creds.credentials import host, port, dbname, user, password
import argparse
import psycopg2
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta
import pytz
import time


def tourn_scraper(tourn_type):
    if tourn_type not in ['modern', 'pioneer', 'standard']:
        raise Exception('Arg must be mod, std or pio')

    keepalive_kwargs = {
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 5,
        "keepalives_count": 5,
    }
    conn = psycopg2.connect(host=host, user=user,
                            password=password, database=dbname, **keepalive_kwargs)

    cur = conn.cursor()

    headers = requests.utils.default_headers()
    headers.update({
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'no-cache',
        'cookie': 'type-preference=paper; _mtg_session=Yjgwakh1Z3BEQk91U2gxbFAyVkpUZytyelFwNkRYK011R3RjSnZURStKK0pjUVpWbm1pa1hGN0VnOCtnMkZGeU94Smg3WGRCMzVnZEFrS09oVWV4UlV1SklRMWw5UTVnMG1wbVN5ckFubGxmZVIycUc0M2JQNjVGRkt5ci9XR2JyS0RpMCtYc1Z5ZDVHdHJoMDNNbzdwSmduWEVaTUpuMEU4UUM5dWllRlZJcEFXdFFZNnc5czVMbXU3NlkzK1FiMlYzeElsSXJMQUk3L0MzV3dVMXEyMHN0YWlqcEd2NmhTZTFYem5RMlFJYz0tLUFQVTkxU0hnalppa3hyY25xQXB6dUE9PQ%3D%3D--7e02037e7a4d6d7f5f6d1e6c5f5ae377ce9a59df',
        'pragma': 'no-cache',
        'referer': 'http://localhost:8888/',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="90", "Google Chrome";v="90"',
        'sec-ch-ua-mobile': '?0',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36'

    })

    utc_now = pytz.utc.localize(datetime.utcnow())
    pst_now = utc_now.astimezone(pytz.timezone("America/Los_Angeles"))

    yester_now = pst_now - timedelta(days=14)

    start_date = yester_now.date()
    end_date = pst_now.date()

    for yesterdayindex in range((end_date - start_date).days + 1):

        yesterday = start_date + yesterdayindex * timedelta(days=1)

        print(yesterday)

        yesterweek = yesterday - timedelta(days=1)

        yesteryear = str(yesterday.year)

        yesday = str(yesterday.day)

        yestermonth = str(yesterday.month)

        yesweekmonth = str(yesterweek.month)

        yesweekday = str(yesterweek.day)

        yesweekyear = str(yesterweek.year)

        cur.execute(
            f'''SELECT DISTINCT tourntitle,entrydate FROM public.{tourn_type if tourn_type != 'pioneer' else ''}tourninfo WHERE entrydate=%s OR entrydate=%s''',
            (yesterweek.strftime('%Y-%m-%d'), yesterday.strftime('%Y-%m-%d')))
        intercollectedtourns = cur.fetchall()
        collectedtourns = set()
        for tourn in intercollectedtourns:
            collectedtourns.add(tourn)

        datedict = {}
        url = requests.get('''https://www.mtggoldfish.com/tournament_searches/create?commit=Search&page=''' + str(
            1) + '''&tournament_search%5Bdate_range%5D=''' + yesweekmonth + '''%2F''' + yesweekday + '''%2F''' + yesweekyear + '''+-+''' + yestermonth + '''%2F''' + yesday + '''%2F''' + yesteryear + f'''&tournament_search%5Bformat%5D={tourn_type}&tournament_search%5Bname%5D=&utf8=%E2%9C%93''')

        rawtext = BeautifulSoup(url.text, 'html.parser')

        table = rawtext.find_all('tr')

        if (len(table) == 0):
            pass
        else:

            for entry in table[1:]:

                linktocards = entry.find('a').get('href')
                entrydate = str(entry.find('td').contents[0])
                tourntitle = str(entry.find('a').contents[0])

                if (tourntitle, str(entrydate)) in collectedtourns:
                    print(tourntitle)
                else:

                    if entrydate not in datedict.keys():
                        datedict[entrydate] = {}

                    if tourntitle not in datedict[entrydate].keys():
                        datedict[entrydate][tourntitle] = {}

                    decklisturl = requests.get('https://www.mtggoldfish.com' + str(linktocards))
                    decktext = BeautifulSoup(decklisturl.text, 'html.parser')

                    deckstuff = decktext.find('table', attrs={'class': 'table-tournament'})
                    if deckstuff == None:
                        pass
                    else:
                        decklinks = deckstuff.find_all('a')

                        for deck in decklinks:
                            if str(deck.get('href')).lower().find('/deck/') != -1:
                                cardurl = requests.get('https://www.mtggoldfish.com' + str(deck.get('href')),
                                                       headers=headers)

                                cardtext = BeautifulSoup(cardurl.text, 'html.parser')
                                cardtext = cardtext.find_all('div', attrs={'id': 'tab-paper'})
                                cardquantsarr = cardtext[0].find_all('td', attrs={'class': 'text-right'})
                                cardquantsarr1 = []
                                for quant in cardquantsarr:
                                    try:
                                        cardquantsarr1.append(int(quant.contents[0]))
                                    except ValueError:
                                        pass

                                cardnamesintermed = cardtext[0].find_all('a', attrs={'rel': 'popover'})
                                allcardnames = [cardinfo.contents[0] for cardinfo in cardnamesintermed]
                                cardandquant = zip(allcardnames, cardquantsarr1)

                                for cardnames, cardquants in cardandquant:
                                    if cardnames in datedict[entrydate][tourntitle].keys():
                                        datedict[entrydate][tourntitle][cardnames] += cardquants
                                    else:
                                        datedict[entrydate][tourntitle][cardnames] = cardquants
                            time.sleep(1.5)

            conn = psycopg2.connect(host=host, user=user,
                                    password=password, database=dbname, **keepalive_kwargs)
            cur = conn.cursor()

            for datekeys in datedict.keys():
                for tournkeys in datedict[datekeys].keys():
                    for dictcards, dictquants in datedict[datekeys][tournkeys].items():
                        cur.execute(
                            f'''INSERT into {tourn_type if tourn_type != 'pioneer' else ''}tourninfo (cardname,entrydate,cardquant,tourntitle) VALUES (%s,%s,%s,%s)''',
                            (dictcards, datekeys, dictquants, tournkeys))
            conn.commit()
        time.sleep(1.5)

    cur.execute(
        f'''DELETE FROM public.{tourn_type if tourn_type != 'pioneer' else ''}tourninfo WHERE tourntitle ILIKE %s''',
        ('(%)',))
    conn.commit()

    cur.close()
    conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='TournScrape',
        description='Scrapes tourns')

    parser.add_argument('tourn_type', choices=['pioneer', 'standard', 'modern'], nargs=1)
    args = parser.parse_args().tourn_type[0]
    tourn_scraper(args)
