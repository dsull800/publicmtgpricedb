from __future__ import print_function
import psycopg2
import pytz
import math as math
import pickle
import os
import sys

sys.path.append(os.getcwd())
from creds.credentials import host, dbname, user, password

import sys
import json
import datetime

import boto3
import sagemaker
import numpy as np
import pandas as pd
from datetime import timedelta
from decouple import config

if config('ENV').lower() == 'local':
    raise Exception("No known local mode for training!")
    # from sagemaker.local import LocalSession
    # sagemaker_session = LocalSession(boto_session=boto3.session.Session())
elif config('ENV').lower() == 'production':
    sagemaker_session = sagemaker.Session(boto3.session.Session())
else:
    raise Exception("Use a correct ENV file")


s3_bucket = 'mtgmlbucketmultseriesnewgoatnewpiostand'  # replace with an existing bucket if needed
s3_prefix = 'mtgml-notebook'  # prefix used for all data stored within the bucket

# role = sagemaker.get_execution_role()
role = 'AmazonSageMaker-ExecutionRole-20200928T145084'

region = sagemaker_session.boto_region_name

s3_data_path = "s3://{}/{}/data".format(s3_bucket, s3_prefix)
s3_output_path = "s3://{}/{}/output".format(s3_bucket, s3_prefix)

image_name = sagemaker.amazon.amazon_estimator.get_image_uri(region, "forecasting-deepar", "latest")

conn = psycopg2.connect(host=host, user=user,
                        password=password, database=dbname)

freq = 'D'
prediction_length = 7
context_length = 7

utc_now = pytz.utc.localize(datetime.datetime.utcnow())
pst_now = utc_now.astimezone(pytz.timezone("America/Los_Angeles"))

start_date_othervarbs = pd.Timestamp("2019-10-16", freq=freq)
start_date = pd.Timestamp("2019-10-23", freq=freq)
end_dataset = pd.Timestamp(pst_now.date(), freq=freq)
end_training = end_dataset - timedelta(days=7)
mid_dataset = pd.Timestamp("2020-09-15", freq=freq)
end_testing = end_dataset
print(f'End training: {end_training}, End testing: {end_testing}')


cur = conn.cursor()

cur.execute('''SELECT overalltrans.cardname FROM 
((SELECT ebayname.cardname FROM ((SELECT DISTINCT(cardname) FROM transactions) AS ebayname
INNER JOIN 
(SELECT DISTINCT(cardname) FROM goatbot_card_defs) AS goat ON ebayname.cardname=goat.cardname)) 
as overalltrans 
INNER JOIN 
(SELECT pio.cardname FROM ((SELECT DISTINCT(cardname) FROM tourninfo) AS pio 
INNER JOIN 
(SELECT DISTINCT(cardname) FROM moderntourninfo) AS mod ON pio.cardname=mod.cardname)) 
as overalltourn ON overalltrans.cardname=overalltourn.cardname) ORDER BY overalltrans.cardname ASC''')

analynames = cur.fetchall()

cur.execute('''TRUNCATE TABLE public.model_cardnames''')
conn.commit()

training_data = []
test_data = []
target_series = []
for cat, analyname in enumerate(analynames):
    print(analyname)

    cur.execute('''SELECT date,price FROM public.actual_total_goatbot WHERE cardname=%s''', analyname)

    goatbotrows = cur.fetchall()

    goatdf = pd.DataFrame(goatbotrows, columns=["date", "price"]).set_index("date")

    goatdf.index = pd.to_datetime(goatdf.index, infer_datetime_format=True)

    goatdfarr = []

    goatdfarr.append(goatdf)

    goatdfarr[0].columns = ['price' + str(0)]

    cur.execute('''SELECT carddate,AVGE,MED FROM public.precomputed_ebay_prices WHERE cardname=%s''', analyname)

    ebayrows = cur.fetchall()

    # ebaydf=pd.DataFrame(ebayrows,columns=["carddate","avg","med"])
    ebaydf = pd.DataFrame(ebayrows, columns=["carddate", "AVG", "MED"]).set_index("carddate")
    ebaydf['MINAVGMED'] = ebaydf.apply(lambda row: math.log(np.minimum(row.AVG, row.MED)), axis=1)
    ebaydf = ebaydf.drop(columns=['AVG', 'MED'])
    ebaydf.index = pd.to_datetime(ebaydf.index, infer_datetime_format=True)

    cur.execute('''SELECT entrydate,ratio FROM public.precomputed_pioneer WHERE cardname=%s''', analyname)

    piotournrows = cur.fetchall()

    piotourndf = pd.DataFrame(piotournrows, columns=["carddate", "pioratio"]).set_index("carddate")
    piotourndf = piotourndf.astype({'pioratio': 'float64'})

    piotourndf.index = pd.to_datetime(piotourndf.index, infer_datetime_format=True)

    cur.execute('''SELECT entrydate,ratio FROM public.precomputed_modern WHERE cardname=%s''', analyname)

    moderntournrows = cur.fetchall()

    moderntourndf = pd.DataFrame(moderntournrows, columns=["carddate", "modratio"]).set_index("carddate")
    moderntourndf = moderntourndf.astype({'modratio': 'float64'})

    moderntourndf.index = pd.to_datetime(moderntourndf.index, infer_datetime_format=True)

    missingdatefix = pd.date_range(start='2019-10-15', end=end_dataset)

    moderntourndf = moderntourndf.reindex(missingdatefix)

    moderntourndf.index.name = 'carddate'

    cur.execute('''SELECT entrydate,ratio FROM public.precomputed_standard WHERE cardname=%s''', analyname)

    standardtournrows = cur.fetchall()

    if len(standardtournrows) == 0:
        standardtourndf = pd.DataFrame([['2020-04-03', 0], ['2020-04-04', 0]],
                                       columns=["carddate", "standratio"]).set_index("carddate")
    else:
        standardtourndf = pd.DataFrame(standardtournrows, columns=["carddate", "standratio"]).set_index("carddate")

    standardtourndf = standardtourndf.astype({'standratio': 'float64'})
    standardtourndf.index = pd.to_datetime(standardtourndf.index, infer_datetime_format=True)

    goatdfarr.insert(0, ebaydf)
    goatdfarr.append(piotourndf)
    goatdfarr.append(moderntourndf)
    goatdfarr.append(standardtourndf)
    overalldf = pd.concat(goatdfarr, axis=1, sort=True)

    #     overalldf.index=pd.to_datetime(overalldf.index,infer_datetime_format=True)

    #     overalldf.index.name='carddate'

    overalldf = pd.concat([overalldf['MINAVGMED'].fillna("NaN"),
                           overalldf.loc[:,
                           overalldf.columns.difference(['MINAVGMED', 'pioratio', 'standratio', 'modratio'])].fillna(
                               method='ffill').fillna(method='bfill'),
                           overalldf[['modratio', 'pioratio', 'standratio']].fillna(0)],
                          axis=1, join='inner')

    dynamic_feat_arr = []
    for col in overalldf.columns[1:]:
        dynamic_feat_arr.append(
            list(overalldf[start_date - timedelta(prediction_length):end_training - timedelta(prediction_length)][col]))

    dynamic_feat_arr_test = []

    for col in overalldf.columns[1:]:
        dynamic_feat_arr_test.append(list(
            overalldf[start_date - timedelta(days=prediction_length):end_dataset - timedelta(days=prediction_length)][
                col]))

    dynamic_feat_arr_series = []

    for col in overalldf.columns[1:]:
        dynamic_feat_arr_series.append(list(overalldf[start_date - timedelta(days=prediction_length):end_dataset][col]))

    if (np.array(dynamic_feat_arr).shape[1] == len(overalldf[start_date:end_training]['MINAVGMED']) and
            np.array(dynamic_feat_arr_test).shape[1] == len(overalldf[start_date:end_dataset]['MINAVGMED'])):
        training_data.append({"start": str(start_date),
                              "target": list(overalldf[start_date:end_training]['MINAVGMED']),
                              "cat": [cat],
                              "dynamic_feat": dynamic_feat_arr})

        test_data.append({"start": str(start_date),
                          "target": list(overalldf[start_date:end_dataset]['MINAVGMED']),
                          "cat": [cat],
                          "dynamic_feat": dynamic_feat_arr_test})

        target_series.append(
            [analyname[0], cat, dynamic_feat_arr_series, overalldf[start_date:end_dataset]['MINAVGMED']])

        cur.execute('''INSERT INTO public.model_cardnames (category,cardname,carddate) VALUES
        (%s,%s,%s)''', (cat, analyname[0], utc_now))
        conn.commit()
    else:
        print(str(analyname) + str('error'))
        sys.exit()

cur.close()
conn.close()


def write_dicts_to_file(path, data):
    with open(path, 'wb') as fp:
        for d in data:
            fp.write(json.dumps(d).encode("utf-8"))
            fp.write("\n".encode('utf-8'))


write_dicts_to_file("runtime_data/train.json", training_data)
write_dicts_to_file("runtime_data/test.json", test_data)

s3 = boto3.resource('s3')


def copy_to_s3(local_file, s3_path, override=True):
    assert s3_path.startswith('s3://')
    split = s3_path.split('/')
    bucket = split[2]
    path = '/'.join(split[3:])
    buk = s3.Bucket(bucket)

    if len(list(buk.objects.filter(Prefix=path))) > 0:
        if not override:
            print('File s3://{}/{} already exists.\nSet override to upload anyway.\n'.format(s3_bucket, s3_path))
            return
        else:
            print('Overwriting existing file')
    with open(local_file, 'rb') as data:
        print('Uploading file to {}'.format(s3_path))
        buk.put_object(Key=path, Body=data)


copy_to_s3("runtime_data/train.json", s3_data_path + "/train/train.json")
copy_to_s3("runtime_data/test.json", s3_data_path + "/test/test.json")

targetpickled = pickle.dumps(target_series)


def copy_to_s3_pred(local_file, s3_path, override=True):
    assert s3_path.startswith('s3://')
    split = s3_path.split('/')
    bucket = split[2]
    path = '/'.join(split[3:])
    buk = s3.Bucket(bucket)

    if len(list(buk.objects.filter(Prefix=path))) > 0:
        if not override:
            print('File s3://{}/{} already exists.\nSet override to upload anyway.\n'.format(s3_bucket, s3_path))
            return
        else:
            print('Overwriting existing file')

    print('Uploading file to {}'.format(s3_path))
    buk.put_object(Key=path, Body=local_file)


copy_to_s3_pred(targetpickled, s3_data_path + "/pred/ped.json")


estimator = sagemaker.estimator.Estimator(
    sagemaker_session=sagemaker_session,
    image_uri=image_name,
    role=role,
    train_instance_count=1,
    train_instance_type='ml.m5.xlarge',
    base_job_name='deepar-mtgml',
    output_path=s3_output_path
)

hyperparameters = {
    "time_freq": freq,
    "epochs": "120",
    "early_stopping_patience": "25",
    "mini_batch_size": "512",
    "learning_rate": "5e-4",
    "context_length": str(context_length),
    "num_cells": "100",
    "num_layers": "4",
    "prediction_length": str(prediction_length)
}

estimator.set_hyperparameters(**hyperparameters)

data_channels = {
    "train": "{}/train/".format(s3_data_path),
    "test": "{}/test/".format(s3_data_path)
}

estimator.fit(inputs=data_channels, wait=True)
