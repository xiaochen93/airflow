# -*- coding: utf-8 -*-
"""
Created on Wed Mar 30 17:50:13 2022

@author: liux5
"""
from bs4 import BeautifulSoup
import time
from datetime import datetime
from Constants import Constants as CONS
from Functions import *
from config.Preprocessor import Preprocessor
import pandas as pd
import pickle
#8WORLD WEB CRAWLER FOR BACK TRANSLATION
from ArticlesGrabber import getNewsByCSS

USE_CACHE = True

DEFAULT_WEBSITE = 'https://theindependent.sg/'

DEFAULT_DOMAIN = 'theindependent.sg'

SITEMAP = 'https://theindependent.sg/sitemap.xml'

CONS.WEBSITE = DEFAULT_WEBSITE

CONS.DOMAIN = DEFAULT_DOMAIN

CONS.SITEMAP = SITEMAP

NAME = 'INDEPENDENT_SG'

LANG = 'EN'

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
    'title': 'div[class*="tdb_title"] > div > h2 ',
    'category': 'div[class*="tdb_breadcrumbs"] > div > span > a',
    'date': 'time[class*="updated td-module-date"]',
    'article':  'div[class*="tdb_single_content"] > div[class*="tdb-block-inner td-fix-index"]',
    'allow_redirects':False
}

def _extract_datetime(raw_date_string, crawl):
    
    raw_date_string = raw_date_string.split('+')
    
    try:
        date_time = pd.to_datetime(raw_date_string, format='%d/%m/%Y %H:%M')
        
    except Exception as e:
        print('\n-- DEBUG: ', e, ' give today\'s date instead')
        date_time = crawl

    return date_time

def gather_urls(save_to_cache = False):
    
    article_list, datetime_list, priority_list = [], [], []
    
    SITEMAP_LINKS = BeautifulSoup(s.get(SITEMAP).text,'lxml').find_all('loc')
    
    SITEMAP_NUM_PAGES = 5
    
    START = 1
        
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
            if _date < CONS.BEGIN_FROM or _date > CONS.END_AT:
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

def main():
    
    link_list = c_scrape_links(USE_CACHE, CACHE_FILEPATH, gather_urls)
    
    
    articles = c_scrape_articles(USE_CACHE, JSON_FILEPATH, {'data':link_list, 'param':css_paths, 'func':getNewsByCSS})
    
    articles_df = Preprocessor({'data':articles,'lang':LANG,'org':1, 'source': 14}).preprocess(func=_extract_datetime)
      
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