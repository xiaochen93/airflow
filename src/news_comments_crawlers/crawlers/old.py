# -*- coding: utf-8 -*-
"""
Created on Wed Mar 30 17:50:13 2022

@author: liux5
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import os
import concurrent.futures
import time
from tqdm import tqdm
import gc
import functools
import json
from datetime import datetime
#8WORLD WEB CRAWLER FOR BACK TRANSLATION

USE_CACHE = True
SITEMAP_START = 3 #Access denied from page 1 and 2
SITEMAP_NUM_PAGES = 63 #MAX 63
NUM_URLS_TO_SCRAPE = -1 #change to -1 for all URLs to be scraped per sitemap page
OUTPUT_FILEPATH = 'output/8w_1-9.txt'
CACHE_FILEPATH = 'cache/linkcache_8w.txt'
DEFAULT_WEBSITE = 'https://www.8world.com/'
DEFAULT_DOMAIN = 'www.8world.com'
SITEMAP = 'https://www.8world.com/Sitemap.xml'
HEADERS = {
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36', #Google Chrome user agent header
    'hl'        :  'en'
    }
BLACKLISTED_LINKS = ['/horoscope/', 
                     '/zodiac/', 
                     '/videos/',
                     '/synopsis/',
                     '/beauty-fashion/',
                     '/food/',
                     '/fun-learning/',
                     '/sports/',
                     '/jk-zone/',
                     '/music/',
                     '/movies-shows/',
                     '/node/',
                     '/columns/',
                     '/life/',
                     '/stories/',
                     '/author/',
                     '/moe/',
                     '/x-over/',
                     '/news/',
                     '/travel/'
                     '/multimedia/'
                     ]

s = requests.Session()
s.headers.update(HEADERS)
retry = Retry(connect=3, backoff_factor=0.5)
adapter = HTTPAdapter(max_retries=retry)
s.mount('http://', adapter)
s.mount('https://', adapter)

BEGIN_FROM = datetime.strptime('2022-11-01', '%Y-%m-%d')

END_AT = datetime.strptime('2022-11-30', '%Y-%m-%d')

OUTPUT_FILEPATH = 'output/8W_{}_{}.txt'.format(BEGIN_FROM.date(),END_AT.date())

CACHE_FILEPATH = 'cache/linkcache_8W_{}_{}.txt'.format(BEGIN_FROM.date(),END_AT.date())

def ifSkip(link,date):
    toSkip = False
    link = link.lower()
    # if the link is the website domain
    if link == f'{DEFAULT_WEBSITE}':
        return True

    if link.split(DEFAULT_WEBSITE)[1].find('/') == -1: #Ignore section pages like https://www.channelnewsasia.com/international
        return True
    
    if date < BEGIN_FROM or date > END_AT:
        return True
    
    for blacklisted_link in BLACKLISTED_LINKS:
        if link.find(blacklisted_link) != -1:
            toSkip = True
            break

    return toSkip

def beautify_url(url):
    url_elements = url.replace('http://','').replace('https://','').split('/')
    if url_elements[0] == DEFAULT_WEBSITE:
        return url
    else:
        url_elements[0] = DEFAULT_DOMAIN
        return 'https://'+'/'.join(url_elements)

def gather_urls(save_to_cache = False):
    
    article_list, datetime_list, priority_list = [], [], []
    
    SITEMAP_NUM_PAGES = len(BeautifulSoup(s.get(SITEMAP).text,'lxml').find_all('sitemap'))
    
    print('\n-- ',SITEMAP_NUM_PAGES)
    
    for sitemap_page in range(1, SITEMAP_NUM_PAGES+1):
        
        r = s.get(SITEMAP, params={'page' : sitemap_page})
        
        soup = BeautifulSoup(r.text, 'lxml') #Parse XML file

        i = 0

        for url_element in soup.find_all('url'):
            #print('\n--DEBUG url element: \n',url_element)
            try:
                link = beautify_url(url_element.select('loc')[0].get_text())
                date = url_element.select('lastmod')[0].get_text()
                date = date.split('T')[0] # get the news's date
                date = datetime.strptime(date, '%Y-%m-%d')
                priority = url_element.select('priority')[0].get_text()
                
            except Exception as e:
                print('\n--Error:', e)
                continue
            
            if ifSkip(link,date): 
                i = i + 1
                continue
            else:

                article_list.append(link)
                datetime_list.append(datetime)
                priority_list.append(priority)
        print('\n--DEBUG',sitemap_page,' sitepage has skipped:', i, 'of records.')
        print('\n--DEBUG', f'Scraping URLs from page {sitemap_page}/{SITEMAP_NUM_PAGES}')


    if save_to_cache:
        with open(CACHE_FILEPATH, 'w', encoding='utf-8') as cache_file:
            for link in article_list:
                cache_file.write(link + '\n')
            print(f'Saved URLs into {CACHE_FILEPATH}')

    return article_list

def scrape_news_By_CSS_Selector(article_url):
    
    article, news_title, category, date, = '', '', '', ''

    try:
        r = s.get(article_url)
        
        soup = BeautifulSoup(r.text, 'lxml')
        
        news_title = soup.select('header[class="article-header"]')[0].get_text().strip()
        
        category = soup.select('ul > li[class="topic"]')[0].get_text().strip()
        
        date = soup.select('div[class*="field--type-datetime"] > time')[0].get_text().strip()
        
        #get the article text    
        for p_div in soup.select('div[class="text-long"]'):
            for paragraph in p_div.find_all('p', class_=''):
                if paragraph.get_text().find('\u00A0') != -1:
                    continue
                article += paragraph.get_text() + '\n'
        
        article = article.strip()
        
    except Exception as e:
        print('\n--',e,' for the link:',article_url)
        # any of the elements cannot be found above return nth
    
    return {'url': article_url,
            'date_publish': date,
            'news_title': news_title,
            'news_category': category,
            'article': article}

def main():
    print(f'{USE_CACHE=}')

    if USE_CACHE:
        if os.path.isfile(CACHE_FILEPATH) and os.path.getsize(CACHE_FILEPATH) > 0:
            print('Using URLs from cache file')

            with open(CACHE_FILEPATH, 'r', encoding='utf-8') as cache_file:
                article_list = [line.strip() for line in cache_file]
        else:
            print('Cache file does not exist... creating now')
            article_list = gather_urls(save_to_cache=True)
    else:
        article_list = gather_urls(save_to_cache=False)
    
    print('Starting article scraping...')
    
    results = []
    
    with concurrent.futures.ProcessPoolExecutor() as executor: 
        for article in tqdm(executor.map(scrape_news_By_CSS_Selector, article_list), total=len(article_list)):
            results.append(article)
    gc.collect()

    with open(OUTPUT_FILEPATH, 'w', encoding='utf-8') as output_file:
        json.dump(results , output_file ,indent = 2, ensure_ascii=False)

if __name__ == '__main__':
    t1 = time.perf_counter()
    main()
    t2 = time.perf_counter()
    print(f'Program took {t2-t1} seconds to complete')