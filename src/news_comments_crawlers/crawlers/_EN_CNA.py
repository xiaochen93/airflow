# -*- coding: utf-8 -*-
"""
Created on Sun Mar  6 20:08:14 2022

@author: liux5
"""
import time
from config.Preprocessor import Preprocessor
from config.Constants import Constants as CONS
from config.db_functions import *
from Functions import *
from ArticlesGrabber import *
import re
import pandas as pd
import json
import argparse
import pickle
from datetime import datetime, timedelta

NOW = datetime.today().now()

AGO = NOW - timedelta(hours=24)

NOW = NOW.strftime('%Y-%m-%d %H:%M:%S')

AGO = AGO.strftime('%Y-%m-%d %H:%M:%S')

CONS = CONS

parser = argparse.ArgumentParser(description="Parameters to execute a web crawler")

parser.add_argument(
        '--name',
        type=str,
        help="The name of a news/social media channel",
        required=True
)

#add parameter start-datetime
parser.add_argument(
        '--start_datetime',
        type=lambda dt: pd.to_datetime(dt, format="%Y-%m-%d %H:%M:%S"),
        default=str(AGO),
        help="The start datetime in format YYYY-mm-dd hh:mm:ss "
)

#add parameter start-datetime
parser.add_argument(
        '--end_datetime',
        type=lambda dt: pd.to_datetime(dt, format="%Y-%m-%d %H:%M:%S"),
        default=str(NOW),
        help="The end datetime in format YYYY-mm-dd hh:mm:ss "
)

parser.add_argument(
     '--use_cache',
     type=bool,
     default=True,
     help="Set true if you want to crawl articles from previous scraped news links."
)

args = parser.parse_args()

#CNA WEB CRAWLER FOR BACK TRANSLATION

USE_CACHE = args.use_cache
# SITEMAP_NUM_PAGES = 55 #MAX 55, change for debugging

BEGIN_FROM = args.start_datetime

END_AT = args.end_datetime

NAME = args.name

# The file name that contains scrapped article/comment in json format
DATA_JSON_FILEPATH = CONS.JSON_DATA_DIR + '{}_{}_{}.json'.format(NAME,END_AT.date(),END_AT.hour)

# The file name that contains scrapped article/comment in dataframe object
DATA_DF_FILEPATH = CONS.DF_DATA_DIR + '{}_{}_{}.pickle'.format(NAME,END_AT.date(),END_AT.hour)

# The file name that contains links of article/comment(s)
LINK_FILEPATH = CONS.LINK_DIR + '{}_{}_{}.txt'.format(NAME,END_AT.date(),END_AT.hour)

DEFAULT_WEBSITE = 'https://www.channelnewsasia.com'

HEADERS = CONS.HEADERS

BLACKLISTED_LINKS = CONS.BLACKLISTED_LINKS

CONS.WEBSITE = DEFAULT_WEBSITE

s = CONS.SESSION

LANG = 'EN'

S_ID = 1

URLS = ['https://www.channelnewsasia.com/latest-news']

css_paths = {
    'title': 'h1[class*="h1--page-title"]',
    'category': 'p[class*="content-detail__category"]',
    'date': 'div[class*="article-publish"]',
    'article': 'div[class="text"]>div[class*="text-long"]'
    }

'''
desc: Scrapes links of news articles from a given sitemap. Every news channel has its customized 
sitemap structure. This function has to be bespoke for the page layout. 
input: sitemap and credentials for news channels.
output: a json of news links that qualifies the news category and datetime.

'''
def extract_datetime_cna(raw_date_string, crawl):
    try:
        raw_date_string = re.sub('\s+',' ',raw_date_string)
        
        date_time = re.findall(r'\d+\s\w+\s\w+\s\d+\:\d+[AP]M', raw_date_string)[0]
        
        date_time = pd.to_datetime(date_time, format='%d %b %Y %H:%M%p')
                
    except Exception as e:
        date_time = crawl
        #print('\n--DEBUG: ', e)
    
    return date_time
    
def gather_urls(save_to_cache = False):
    
    article_list, datetime_list, priority_list = [], [], []

    for URL in URLS:

        WEB_CARD_ELEMENTS= BeautifulSoup(s.get(URL).text, "html.parser").select('div[class="list-object"]')

        for CARD_ELEMENT in WEB_CARD_ELEMENTS:
            try:
                link = CARD_ELEMENT.select('div[class*="quick-link--list-object"]')[0].attrs['data-link_absolute']
                #print('\n-- ',link.strip())
            except:
                print('\n--DEBUG: No valid link is scraped, break.')
                break

            try:
                timestamp = CARD_ELEMENT.select('span[class*="timeago"]')[0].get_text()
            except:
                #today's datetime instead
                pass

            try:
                import datetime
                timestamp_int64 = int(CARD_ELEMENT.select('span[class*="timeago"]')[0].get_attribute_list('data-lastupdated')[0])
                timestamp_int64 = datetime.datetime.fromtimestamp(timestamp_int64)
                #print('\n-- ',timestamp_int64)
            except:
                #today's datetime instead
                pass

            # if timestamp is within the specific timerange then save, else discard:
            if timestamp_int64 >= BEGIN_FROM and timestamp_int64 <= END_AT:
                article_list.append(link)

    if save_to_cache:
        with open(LINK_FILEPATH, 'w', encoding='utf-8') as cache_file:
            for link in article_list:
                cache_file.write(link + '\n')
            print(f'Saved URLs into {LINK_FILEPATH}')

    return article_list

'''
desc: Preprocess the news article data into a dataframe object, it should contain title, content, datetime, url, and news category.
'''
def main():
    
    link_list = c_scrape_links(USE_CACHE, LINK_FILEPATH, gather_urls)

    articles = c_scrape_articles(USE_CACHE, DATA_JSON_FILEPATH, {'data':link_list, 'param':css_paths, 'func':getNewsByCSS})

    articles_df = Preprocessor({'data':articles,'lang':LANG,'org':1,'source': S_ID}).prepare(func=extract_datetime_cna)

    #save the raw json file
    with open(DATA_JSON_FILEPATH, 'w', encoding='utf-8') as output_file:
        json.dump(articles , output_file ,indent = 2, ensure_ascii=False, default=str)

    #save the dataframe object
    with open(DATA_DF_FILEPATH, 'wb') as output_file:
        pickle.dump(articles_df, output_file, protocol=pickle.HIGHEST_PROTOCOL)

    #save and write the data statistics - append mode
    with open(CONS.LOG_FILE_PATH, "a", encoding='utf-8') as output_file:
        output_file.write('\n')
        output_file.write('\n-- Platform: '+ NAME)
        output_file.write('\n\t-- No of. articles scraped: {}'.format(articles_df.shape[0]))

    #save data into the database
    for idx, row in articles_df.iterrows():
        row = row.to_dict()
        insert_news_db(row)


            
if __name__ == '__main__':
    t1 = time.perf_counter()
    print('\n--DEBUG: Platform - ', args.name)
    print('\n--DEBUG: Start-time - ', args.start_datetime)
    print('\n--DEBUG: End-time - ', args.end_datetime)
    print('\n--DEBUG: Link Path -', LINK_FILEPATH)
    print('\n--DEBUG: JSON Data Path -', DATA_JSON_FILEPATH)
    print('\n--DEBUG: DF Data Path -', DATA_DF_FILEPATH)
    main()
    t2 = time.perf_counter()
    print(f'Program took {t2-t1} seconds to complete')