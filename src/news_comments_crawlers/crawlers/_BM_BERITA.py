# -*- coding: utf-8 -*-
"""
Created on Sun Mar  6 20:08:14 2022

@author: liux5
"""

from bs4 import BeautifulSoup
import time
from datetime import datetime
from Constants import Constants as CONS
from Functions import *
from ArticlesGrabber import getNewsByCSS
from config.Preprocessor import Preprocessor
import pandas as pd
import pickle
import math
#CNA WEB CRAWLER FOR BACK TRANSLATION

USE_CACHE = True
# SITEMAP_NUM_PAGES = 55 #MAX 55, change for debugging
NUM_URLS_TO_SCRAPE = -1 #change to -1 for all URLs to be scraped per sitemap page

DEFAULT_WEBSITE = 'https://berita.mediacorp.sg/'

DEFAULT_DOMAIN = 'berita.mediacorp.sg'

SITEMAP = 'https://berita.mediacorp.sg/Sitemap.xml'

CONS.WEBSITE = DEFAULT_WEBSITE

CONS.DOMAIN = DEFAULT_DOMAIN

CONS.SITEMAP = SITEMAP

NAME = 'BERITA'

LANG = 'BM'

S_ID = 6

HEADERS = CONS.HEADERS

BLACKLISTED_LINKS = CONS.BLACKLISTED_LINKS

BEGIN_FROM = CONS.BEGIN_FROM

END_AT = CONS.END_AT

JSON_FILEPATH = CONS.RAW_PATH + '{}_{}_{}.txt'.format(NAME,BEGIN_FROM.date(),END_AT.date())

DF_FILEPATH = CONS.DF_PATH + '{}_{}_{}.pickle'.format(NAME,BEGIN_FROM.date(),END_AT.date())

CACHE_FILEPATH = CONS.LINKS_PATH + '{}_{}_{}.txt'.format(NAME, BEGIN_FROM.date(),END_AT.date())

s = CONS.SESSION

s.headers.update(HEADERS)

css_paths = {
    'title': 'h1[class="h1 h1--page-title"]',
    'category': 'p[class="content-detail__category"]',
    'date': 'div[class*="article-publish article-publish--"]>span',
    'article': 'div[class="text"]>div[class="text-long"]'
    }

'''
desc:
input:
output:

'''

def gather_urls(save_to_cache = False):
    
    article_list, datetime_list, priority_list = [], [], []
    
    SITEMAP_LINKS = BeautifulSoup(s.get(SITEMAP).text,'lxml').find_all('loc')
    
    SITEMAP_NUM_PAGES = len(SITEMAP_LINKS)
    
    START = max(0, math.floor(SITEMAP_NUM_PAGES/2))
        
    for sitemap_page in range(START, SITEMAP_NUM_PAGES):
        # get the page url for the sitemap page
        page_url = c_restore_url(CONS,SITEMAP_LINKS[sitemap_page].get_text())
        
        # get the content of the sitemap page
        page_content = s.get(page_url).text
        
        soup = BeautifulSoup(page_content, 'lxml') #Parse LXML file
    
        i = 0
        
        for url_element in tqdm(soup.find_all('url')):
            #1. get the link for the news articles
            try:
                link = c_restore_url(CONS,url_element.select('loc')[0].get_text())
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

'''

'''
def extract_datetime_berita(raw, crawl):
    
    try:
        raw = (' '.join(raw.split(':')[1:])).strip()
    
        date_time = pd.to_datetime(raw, format='%d %b %Y %I %M%p')   
    except:
        
        date_time = crawl
    
    return date_time
    
def main():
    
    link_list = c_scrape_links(USE_CACHE, CACHE_FILEPATH, gather_urls)
    
    articles = c_scrape_articles(USE_CACHE, JSON_FILEPATH, {'data':link_list, 'param':css_paths, 'func':getNewsByCSS})
    
    articles_df = Preprocessor({'data':articles,'lang':LANG,'org':1, 'source': S_ID}).preprocess(func=extract_datetime_berita)
    
    articles_df = articles_df[articles_df['datetime'] > BEGIN_FROM]
    
    #save the dataframe object
    with open(DF_FILEPATH, 'wb') as output_file:
        pickle.dump(articles_df, output_file, protocol=pickle.HIGHEST_PROTOCOL)
    #save the raw json file
    with open(JSON_FILEPATH, 'w', encoding='utf-8') as output_file:
        json.dump(articles , output_file ,indent = 2, ensure_ascii=False, default=str)
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