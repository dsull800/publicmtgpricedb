#!/usr/bin/env python
# coding: utf-8

# In[1]:


import psycopg2

from itertools import chain
import numpy as np
import pandas as pd
import bs4
from bs4 import BeautifulSoup
import requests 
from datetime import datetime, timedelta
import re
import pytz


# In[2]:


conn = psycopg2.connect()


# In[3]:


cur=conn.cursor()


# In[4]:


cur.execute('''SELECT name FROM public.cards WHERE rarity IN('mythic','rare') AND setcode IN(SELECT code FROM public.sets WHERE type IN ('expansion','core') and releasedate>=(SELECT releasedate FROM public.sets WHERE mcmname='Return to Ravnica'))''')


# In[5]:


rows=cur.fetchall()
rows=set(rows)


# In[6]:


type((datetime.now() - timedelta(1)).strftime('%Y-%m-%d'))


# In[7]:


cardraritys=cur.fetchall()
cardraritys=set(cardraritys)


# In[8]:


headers = requests.utils.default_headers()
headers.update({
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0',
})

xfun=lambda x:"x"+str(x)
funx=lambda x:str(x)+"x"
xspacefun=lambda x:"x "+str(x)
funspacex=lambda x:str(x)+" x"

titlequantities=list(chain.from_iterable((xfun(x), funx(x), xspacefun(x), funspacex(x)) for x in range(1,11))) #all lowercase
#remember to add 1 x and x 1 to title quantities
titlekeywords=["promo","expedition","invocation","invention","extended art"]#altered art?
titlelanguages=['english','korean','japanese','chinese','russian','spanish']
titleconditions=['NM','LP','MP','HP','Mint','Lightly Played','Moderately Played','Heavily Played']

utc_now = pytz.utc.localize(datetime.utcnow())
pst_now = utc_now.astimezone(pytz.timezone("America/Los_Angeles"))
yesterday=pst_now - timedelta(1)

print(yesterday)
print(type(yesterday))

for cardname in rows:
    if (cardname,'rare') in cardraritys:
        rarity='rare'
    else:
        rarity='mythic'
    
    if cardname is None:
        print(cardname+"NONE")
    else:
        cur.execute('''SELECT printings FROM public.cards WHERE name=%s''',(cardname))
        cardprintings=cur.fetchall()
        cardstring=cardprintings[0][0]
        setlist=cardstring.split(",")
        
        url=requests.get('https://www.ebay.com/sch/i.html?_nkw='+cardname[0]+' mtg'+'&rt=nc&LH_Sold=1&LH_Complete=1&_ipg=200&_pgn=1')

        rawtext=BeautifulSoup(url.text,'html.parser')
        transactions=rawtext.find_all('div',attrs={"class":"s-item__info clearfix"})

        

        for transaction in transactions:

            transactionsetcode=None
            price=None
            title=None
            carddate=None
            IsFoil=None
            saletype=None
            cardquantity=None
            cardspecial=None
            cardlanguage=None
            cardcondition=None
            shipping=None
            possiblybad=False
            isBanned=False
                         
            if len(transaction.find_all('span',attrs={"class":"s-item__ended-date s-item__endedDate"}))==0:
                pass

            else:
                carddate=datetime.strptime(transaction.find_all('span',attrs={"class":"s-item__ended-date s-item__endedDate"})[0].string,'%b-%d %H:%M').date()

#                 if carddate.month>3:
#                     carddate=carddate.replace(year=2019)
#                 else:
                carddate=carddate.replace(year=2020)
                    
                if (yesterday).strftime('%Y-%m-%d')>str(carddate):
                    break
                         
                elif (yesterday).strftime('%Y-%m-%d')==str(carddate):

                    if transaction.find_all('h3',attrs={"class":"s-item__title"})[0].string==None or len(transaction.find_all('h3',attrs={"class":"s-item__title"}))==0:
                        pass

                    else:        
                        title=transaction.find_all('h3',attrs={"class":"s-item__title"})[0].string
                        
                        for setcode in setlist:
                            setcode=setcode.strip()
                            if title.lower().find(setcode.lower())!=-1:
                                transactionsetcode=setcode
                                
                                break
                            else:
                                cur.execute("""SELECT name FROM public.sets WHERE code=%s""",[setcode])
                                setname=cur.fetchall()
                                if title.lower().find(setname[0][0].lower())!=-1:
                                    transactionsetcode=setcode
                                    
                                    break

                        if title.lower().find(cardname[0].lower())==-1:
                            pass
                        else:
                            for quantity in titlequantities:
                                if title.lower().find(quantity.lower())!=-1:
                                    quant = re.findall("(\d+)", quantity)
                                    cardquantity=quant[0]
                                    break

                            IsFoil=title.lower().find("foil")!=-1

                            for keyword in titlekeywords:
                                if title.lower().find(keyword.lower())!=-1:
                                    cardspecial=keyword
                                    break

                            for language in titlelanguages:
                                if title.lower().find(language.lower())!=-1:
                                    cardlanguage=language
                                    break

                            for condition in titleconditions:
                                if title.lower().find(condition.lower())!=-1:
                                    cardcondition=condition
                                    break





                            if len(transaction.find_all('span',attrs={"class":"POSITIVE"}))==0:
                                possiblybad=True

                            else:
                                price=float(re.sub(r'[^\d.]', '', transaction.find_all('span',attrs={"class":"POSITIVE"})[0].string))
                                positiveprice=str(transaction.find_all('span',attrs={"class":"POSITIVE"})[0])

                                if positiveprice.find('class="POSITIVE"')!=-1:
                                    saletype='normal'
                                elif positiveprice.find('class="POSITIVE ITALIC"')!=-1:
                                    saletype='italic'
                                else:
                                    saletype='BO accepted'


                            if len(transaction.find_all('span',attrs={"class":"s-item__shipping s-item__logisticsCost"}))==0:
                                possiblybad=True

                            elif re.sub(r'[^\d.]', '', transaction.find_all('span',attrs={"class":"s-item__shipping s-item__logisticsCost"})[0].string)=='':
                                pass
                            else:
                                shipping=float(re.sub(r'[^\d.]', '', transaction.find_all('span',attrs={"class":"s-item__shipping s-item__logisticsCost"})[0].string))




                            cur.execute('''INSERT INTO transactions (cardname,price,carddate,IsFoil,saletype,cardquantity,
                            cardspecial,cardlanguage,cardcondition,title,possiblybad,isBanned,shipping,cardset,rarity) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',(cardname,price,carddate,IsFoil,saletype,cardquantity,cardspecial,cardlanguage,cardcondition,title,possiblybad,isBanned,shipping,transactionsetcode,rarity))
                            #conn.commit() #place this so that it commits only when the transactions for a specific card are done
                else:
                    pass
    conn.commit() #place this so that it commits only when the transactions for a specific card are done


# In[9]:


cur.close()
conn.close()

