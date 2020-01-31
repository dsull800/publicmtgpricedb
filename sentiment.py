#!/usr/bin/env python
# coding: utf-8

# In[1]:


import numpy as np
import pandas as pd
import bs4
from bs4 import BeautifulSoup
import requests 
import datetime
import re


# In[2]:


sym = "AAPL"
df_close = pd.DataFrame()

df_temp = pd.read_json('https://cloud.iexapis.com/stable/stock/'+sym+'/chart/1y?token='+token+'')


# In[3]:


df_temp.head(4)


# In[4]:


df_temp.tail()


# In[5]:


url=[None] * 7
soupArr=[None] * 7
articles=[]
AAPLtimes=[]
dates=[]
links=[]
#Figure out how many times apple is mentioned on each page
for i in range(0,6):
    url[i]=requests.get('https://www.nasdaq.com/topic/technology?page=' + str(i+1))
    soupArr[i]=BeautifulSoup(url[i].text,'html.parser')
    articles.append(soupArr[i].find_all("section", attrs={"class": "article-category-section"}))
    for idx,j in enumerate(articles[i]):
        if len(j.find_all("a", attrs={"href": "https://www.nasdaq.com/symbol/aapl"}))>0:
            dates.append(j.find_all('span',attrs={"id":"two_column_main_content_rptArticles_lbArticleInfo_"+str(idx)}))
            inter0=j.find_all("b")
            links.append(inter0)
#                 for idx3,o in enumerate(inter0):
#                     intermediate=inter0.find_all("b")
#                     links.append(o.find_all("a"))
                        


# In[6]:


strlinks=[]
for idx,k in enumerate(links):
    for j in k:
        strlinks.append(j)


# In[7]:


reallinks=[]
for idx,i in enumerate(strlinks):
    reallinks.append(strlinks[idx].find_all("a")[0].get('href'))


# In[8]:


realdates=[]
for idx,i in enumerate(dates):
        realdates.append(dates[idx][0].text.split(",")[0])
uniquedates=np.unique(realdates,return_counts=True)
print(realdates)


# In[9]:


print(str(datetime.date.today()))


# In[10]:


datesandtimes=[]
for idx, i in enumerate(uniquedates[0]):
    datesandtimes.append(datetime.datetime.strptime(i,"%m/%d/%Y"))


# In[11]:


timedeltas=[]
for idx,i in enumerate(datesandtimes):
    tds=datesandtimes[idx]-datetime.datetime.today()
    timedeltas.append(tds.days+1)


# In[12]:


timedeltas


# In[13]:


# for idx,k in enumerate(articles):
#     for idx2,m in enumerate(articles[idx]):
#         intermediate=m.find_all("b")
#         print(intermediate)
#         for idx3,o in enumerate(intermediate):
#             links.append(o.find_all("a"))


# In[14]:


reallinks


# In[25]:


bsoupstuff=[]
for idx,i in enumerate(reallinks):
    soupy=BeautifulSoup(requests.get(i).text,'html.parser')
    # use articlebody
#     bsoupstuff.append(soupy.find_all('div',attrs={"id":"articleText"}))
    bsoupstuff.append(soupy.find_all('div',attrs={"id":"articlebody"}))
#     if idx==2:
#         print(soupy.prettify())


# In[26]:


goodwords=['growth','AAPL',"Apple","boom","high"]
contain=[]
for idx,i in enumerate(bsoupstuff):
    inter=[]
    for idx2,j in enumerate(i):
        for k in goodwords:
            inter.append(j.text.count(k))
            
    contain.append(inter)
    


# In[17]:


contain


# In[23]:


contain


# In[24]:


bsoupstuff[0][0].text


# In[27]:


bsoupstuff[0][0].text


# In[ ]:




