import traceback
import sys
import os
sys.path.append(os.getcwd())
from creds.credentials import host, port, dbname, user, password
import pandas as pd
from datetime import datetime, timedelta
import pytz
import zipfile
import json
import psycopg2.extras

conn = psycopg2.connect(host=host, user=user,
                        password=password, database=dbname)

cur = conn.cursor()

utc_now = pytz.utc.localize(datetime.utcnow())
pst_now = utc_now.astimezone(pytz.timezone("US/Eastern"))
yesterday = pst_now - timedelta(1)

# os.system(
#     f'''curl -L -H 'Referer: https://www.goatbots.com/download-prices' -A 'Mozilla/5.0 (X11; Linux x86_64; rv:30.0) Gecko/20100101 Firefox/30.0' https://www.goatbots.com/download/card-definitions.zip''')


cur.execute('''SELECT DISTINCT(card_id) FROM public.goatbot_card_defs''')
collected_card_ids = cur.fetchall()
collected_card_ids = set([str(tup[0]) for tup in collected_card_ids])

utc_yest = pytz.utc.localize(datetime.utcnow()) - timedelta(1)
pst_yest = utc_yest.astimezone(pytz.timezone("US/Eastern"))
pst_yest = pst_yest.strftime('%Y-%m-%d')
utc_yest = utc_yest.strftime('%Y-%m-%d')
goat_defs_zip = zipfile.ZipFile('runtime_data/goat_scrapes/card-definitions.zip')

goat_defs_zip.extractall('runtime_data/goat_scrapes/card_definitions')
goat_defs_name = goat_defs_zip.namelist()
goat_defs_file = open(os.path.join('runtime_data/goat_scrapes/card_definitions', goat_defs_name[0]))
read_in_defs_file = goat_defs_file.read()
goat_defs_txt = json.loads(read_in_defs_file)
new_card_ids = set(goat_defs_txt.keys())
card_id_diff = new_card_ids - collected_card_ids
all_defs = [(key, value['name'], value['foil'] == 1, value['rarity'], value['cardset']) for key, value in
            goat_defs_txt.items() if key in card_id_diff]
psycopg2.extras.execute_values(cur,
                               '''INSERT INTO goatbot_card_defs (card_id,cardname,foil,rarity,cardset) VALUES %s''',
                               all_defs)

conn.commit()

cur.execute('''SELECT MAX(date) FROM public.goatbot_card_prices''')
max_date = cur.fetchall()

# os.system(f'''curl -L -H 'Referer: https://www.goatbots.com/download-prices' -A 'Mozilla/5.0 (X11; Linux x86_64; rv:30.0) Gecko/20100101 Firefox/30.0' https://www.goatbots.com/download/price-history.zip\?{utc_yest} >> price-history.zip''')
# os.system(
#     f'''curl -L -H 'Referer: https://www.goatbots.com/download-prices' -A 'Mozilla/5.0 (X11; Linux x86_64; rv:30.0) Gecko/20100101 Firefox/30.0' https://www.goatbots.com/download/price-history-2022.zip >> runtime_data/goat_scrapes/price-history.zip''')

goat_data_zip = zipfile.ZipFile('runtime_data/goat_scrapes/price-history-2023.zip')

extraction_dest = 'runtime_data/goat_scrapes/price-history'

goat_data_zip.extractall(extraction_dest)

max_string_date = (max_date[0][0] + timedelta(1)).strftime('%Y-%m-%d')
print(max_string_date)

for date in pd.date_range(max_string_date, '2028-01-27').to_list():
    stringed_date = date.strftime('%Y-%m-%d')
    try:
        goat_data_file = open(os.path.join(extraction_dest, 'price-history-' + stringed_date + '.txt'))
    except Exception as e:
        traceback.format_exception()
        break
    read_in_file = goat_data_file.read()
    goat_data_txt = json.loads(read_in_file)
    all_prices = [(key, stringed_date, value) for key, value in goat_data_txt.items()]
    psycopg2.extras.execute_values(cur, '''INSERT INTO goatbot_card_prices (card_id,date,price) VALUES %s''',
                                   all_prices)
    conn.commit()
    goat_data_file.close()

cur.close()
conn.close()
