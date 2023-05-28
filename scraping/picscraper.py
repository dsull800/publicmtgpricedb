import psycopg2
import time
import requests
import os
import boto3
from os.path import exists
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.getcwd())
from creds.credentials import host, dbname, password, user

conn = psycopg2.connect(host=host, user=user,
                        password=password, database=dbname)

cur = conn.cursor()

s3_bucket = os.environ['S3_PICS_BUCKET_NAME']

s3 = boto3.resource(service_name='s3')


def copy_to_s3(local_file, s3_path, override=False):
    assert s3_path.startswith('s3://')
    split = s3_path.split('/')
    bucket = split[2]
    print(bucket)
    path = '/'.join(split[3:])
    print(path)
    buk = s3.Bucket(bucket)

    if len(list(buk.objects.filter(Prefix=path))) > 0:
        if not override:
            print('File s3://{}/{} already exists.\nSet override to upload anyway.\n'.format(s3_bucket, s3_path))
            return
        else:
            print('Overwriting existing file')
    with open(local_file, 'rb') as data:
        print('Uploading file to {}'.format(s3_path))
        buk.put_object(Key=path, Body=data, ACL='public-read', ContentType="image/jpeg")


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
namerows = cur.fetchall()

for s3_prefix in namerows:
    if not exists('runtime_data/cardimages/' + s3_prefix[0] + '.jpg'):
        url = requests.get('https://api.scryfall.com/cards/search?q=' + s3_prefix[0])
        if "image_uris" in url.json()['data'][0]:
            url_value = url.json()['data'][0]['image_uris']['large']
        elif "card_faces" in url.json()['data'][0]:
            url_value = url.json()['data'][0]['card_faces'][0]['image_uris']['large']
        else:
            url_value = "https://c1.scryfall.com/file/scryfall-cards/normal/front/a/2/a219a031-2466-4850-b646-79a09e30cf18.jpg?1562257506"

        file = open('runtime_data/cardimages/' + s3_prefix[0] + '.jpg', "wb")
        fetched_pic = requests.get(url_value)
        file.write(fetched_pic.content)
        file.close()
        s3_data_path = "s3://{}/{}".format(s3_bucket, s3_prefix[0] + '.jpg')
        copy_to_s3('runtime_data/cardimages/' + s3_prefix[0] + '.jpg', s3_data_path)
        time.sleep(.5)
