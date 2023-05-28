import traceback
import psycopg2
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import pytz
from sklearn.linear_model import LinearRegression
import math as math
import os
import sys

sys.path.append(os.getcwd())
from creds.credentials import host, dbname, password, user

conn = psycopg2.connect(host=host, user=user,
                        password=password, database=dbname)

cur = conn.cursor()
cur.execute('''SELECT cardname,date,price FROM public.actual_total_goatbot WHERE cardname
IN(SELECT distinct(cardname) FROM public.model_cardnames)''')
goatrows = cur.fetchall()

goatrows = pd.DataFrame(goatrows, columns=["cardname", "carddate", "price"])
goatrows['carddate'] = goatrows['carddate'].astype('datetime64[ns]')

utc_now = pytz.utc.localize(datetime.utcnow())
pst_now = utc_now.astimezone(pytz.timezone("America/Los_Angeles"))
yesterday = pst_now - timedelta(7)

overalllist = []
for cardname in goatrows["cardname"].unique():
    coeflist = []
    wowee = goatrows['cardname'] == cardname
    regvals = goatrows.loc[np.logical_and(wowee.values, goatrows['carddate'] > (yesterday).strftime('%Y-%m-%d'))]
    regvals["carddate"] = regvals["carddate"] - regvals.iloc[0]["carddate"]
    regvals["carddate"] = regvals["carddate"].astype('int64') / 86400000000000
    regprice = LinearRegression().fit(
        np.array(regvals.iloc[math.floor(len(regvals)) - 4:len(regvals)]["carddate"]).reshape(-1, 1),
        regvals.iloc[math.floor(len(regvals)) - 4:len(regvals)]["price"])
    pricecoef = regprice.coef_[0]
    coeflist.append(pricecoef)
    coeflist.append(cardname)
    overalllist.append(coeflist[::-1])

# coefdf=pd.DataFrame(overalllist,columns=["cardname","mecoef1","avgcoef1","medcoef.5","avgcoef.5"])
coefdf = pd.DataFrame(overalllist).sort_values(by=1, axis=0)
coefdf.columns = ["cardname", "slope"]


# Define function using cursor.executemany() to insert the dataframe
def execute_many(conn, datafrm, table):
    # Creating a list of tupples from the dataframe values
    tpls = [tuple(x) for x in datafrm.to_numpy()]

    # dataframe columns with Comma-separated
    cols = ','.join(list(datafrm.columns))

    # SQL query to execute
    sql = "INSERT INTO %s(%s) VALUES(%%s,%%s)" % (table, cols)
    conn = psycopg2.connect(host=host, user=user,
                            password=password, database=dbname)
    cursor = conn.cursor()
    try:
        cursor.execute('''DELETE FROM public.slopes''')
        cursor.executemany(sql, tpls)
        conn.commit()
        print("Data inserted using execute_many() successfully...")
    except (Exception, psycopg2.DatabaseError) as err:
        # pass exception to function
        traceback.format_exc()
        # show_psycopg2_exception(err)
        cursor.close()


execute_many(conn, coefdf, 'slopes')

cur.close()
conn.close()
