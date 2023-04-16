# -*- coding: utf-8 -*-
"""
Created on Wed Apr 13 10:47:45 2022

@author: liux5
"""

from bs4 import BeautifulSoup
import time
from datetime import datetime
from Constants import Constants as CONS
from Functions import *
from ArticlesGrabber import getNewsByCSS
from config.Preprocessor import Preprocessor 
import re
import pandas as pd
#8WORLD WEB CRAWLER FOR BACK TRANSLATION

USE_CACHE = True

NUM_URLS_TO_SCRAPE = -1 #change to -1 for all URLs to be scraped per sitemap page

DEFAULT_WEBSITE = 'https://www.zaobao.com.sg/'

DEFAULT_DOMAIN = 'www.zaobao.com.sg'

SITEMAP = 'https://www.zaobao.com.sg/sitemap.xml'

CONS.WEBSITE = DEFAULT_WEBSITE

CONS.DOMAIN = DEFAULT_DOMAIN

CONS.SITEMAP = SITEMAP

NAME = 'ZB'

LANG = 'CN'

S_ID = 3

HEADERS = CONS.HEADERS

BLACKLISTED_LINKS = CONS.BLACKLISTED_LINKS

BEGIN_FROM = CONS.BEGIN_FROM

END_AT = CONS.END_AT

JSON_FILEPATH = CONS.RAW_PATH + '{}_{}_{}.txt'.format(NAME,BEGIN_FROM.date(),END_AT.date())

DF_FILEPATH = CONS.DF_PATH + '{}_{}_{}.pickle'.format(NAME,BEGIN_FROM.date(),END_AT.date())

CACHE_FILEPATH = CONS.LINKS_PATH + '{}_{}_{}.txt'.format(NAME, BEGIN_FROM.date(),END_AT.date())

CONS.WEBSITE = DEFAULT_WEBSITE

s = CONS.SESSION

s.headers.update(HEADERS)

css_paths = {
    'title': 'div[class*="article-title"]',
    'category': 'ul[class*="breadcrumbs-list"]',
    'date': 'div[class*="group-story-postdate"]',
    'article': 'div[class*="article-content-rawhtml"]'
    }



def gather_urls(save_to_cache = False):
    
    article_list, datetime_list, priority_list = [], [], []
    
    SITEMAP_LINKS = BeautifulSoup(s.get(SITEMAP).text,'lxml').find_all('loc')
    
    SITEMAP_NUM_PAGES = len(SITEMAP_LINKS)
    
    START = max(0, math.floor(SITEMAP_NUM_PAGES*0.8))
    
    for sitemap_page in range(START, SITEMAP_NUM_PAGES):
        # get the page url for the sitemap page
        page_url = c_restore_url(CONS,SITEMAP_LINKS[sitemap_page].get_text())
        
        # get the content of the sitemap page
        page_content = s.get(page_url).text
        
        soup = BeautifulSoup(page_content, 'xml') #Parse LXML file
    
        i = 0
        
        for url_element in tqdm(soup.find_all('url')):
            #1. get the link for the news articles
            try:
                link = url_element.select('loc')[0].get_text()
            except:
                print('\n-- No link was found, skip the link.')
                i = i + 1
                continue
            #2. get the datetime for the newslink else: scrape everything
            try:
                _date = url_element.select('lastmod')[0].get_text()
                _date = _date.split('T')[0] # get the news's date
                _date = datetime.strptime(_date, '%Y-%m-%d')
            except:
                _date = CONS.END_AT
                #print('\n-- DEBUG: No of record ',self.no_records,flush=True) 
          
            # check if to skip a link : link must be lowercase
            if c_determine_to_skip(CONS, link, _date):
                i = i + 1
                continue
            else: 
                article_list.append(link)
                datetime_list.append(_date)

        print('\n--DEBUG',sitemap_page,'/',SITEMAP_NUM_PAGES,' sitepage has skipped:', i, 'of records.',end="\r", flush=True)

    if save_to_cache:
        with open(CACHE_FILEPATH, 'w', encoding='utf-8') as cache_file:
            for link in article_list:
                cache_file.write(link + '\n')
            print(f'Saved URLs into {CACHE_FILEPATH}')

    return article_list

def extract_datetime_zaobao(raw_date_string, crawler_datetime):
    try:
        date_publish = datetime.today()
        
        raw_date_string = re.sub('\s+',' ',raw_date_string)
      
        date_time = re.findall(r'\d+[^\x00-\xff]+\d+[^\x00-\xff]+\d+[^\x00-\xff]+\s\d+\:\d+\s\w\w', raw_date_string)[0]
        
        date_time = pd.to_datetime(date_time, format='%Y年%m月%d日 %H:%M %p')
    except:
        date_time = crawler_datetime
        
    return date_time

def main():
    
    link_list = c_scrape_links(USE_CACHE, CACHE_FILEPATH, gather_urls)
    
    articles = c_scrape_articles(USE_CACHE, JSON_FILEPATH, {'data':link_list, 'param':css_paths, 'func':getNewsByCSS})
    
    #save the raw json file
    with open(JSON_FILEPATH, 'w', encoding='utf-8') as output_file:
        json.dump(articles , output_file ,indent = 2, ensure_ascii=False, default=str)    
    
    articles_df = Preprocessor({'data':articles,'lang':LANG,'org':1, 'source': S_ID}).preprocess(func=extract_datetime_zaobao)
    
    #save the dataframe object
    with open(DF_FILEPATH, 'wb') as output_file:
        pickle.dump(articles_df, output_file, protocol=pickle.HIGHEST_PROTOCOL)

    #save and write the data statistics - append mode
    with open(CONS.LOG_FILE_PATH, "a", encoding='utf-8') as output_file:
        output_file.write('\n')
        output_file.write('\n-- Platform: '+ NAME)
        output_file.write('\n\t-- No of. articles scraped: {}'.format(articles_df.shape[0]))
      

if __name__ == '__main__':
    t1 = time.perf_counter()
    main()
    t2 = time.perf_counter()
    print(f'Program took {t2-t1} seconds to complete')