# -*- coding: utf-8 -*-
"""
Created on Wed Apr 13 10:47:45 2022

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

# 2023-05-07 update parameters for zaobao web crawler

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

HEADERS = CONS.HEADERS

BLACKLISTED_LINKS = CONS.BLACKLISTED_LINKS

DEFAULT_WEBSITE = 'https://www.zaobao.com.sg/'

CONS.WEBSITE = DEFAULT_WEBSITE

s = CONS.SESSION

LANG = 'CN'

S_ID = 3

URLS = ['https://www.zaobao.com.sg/realtime/singapore', 'https://www.zaobao.com.sg/realtime/china', 'https://www.zaobao.com.sg/realtime/world', 'https://www.zaobao.com.sg/realtime/finance']

css_paths = {
    'title': 'div[class*="article-title"]',
    'category': 'ul[class*="breadcrumbs-list"]',
    'date': 'div[class*="group-story-postdate"]',
    'article': 'div[class*="article-content-rawhtml"]'
    }

def _parse_datetime(relative_time_str):
    # Define a dictionary mapping Mandarin keywords to timedelta units
    time_units = {"分钟": "minutes", "小时": "hours", "天": "days"}

    # Extract the numerical value and time unit from the relative time string
    match = re.search(r"(\d+) ?(.+?)前", relative_time_str)
    if match is not None:
        num, unit = match.groups()
        # Map the time unit to a timedelta unit
        unit = time_units.get(unit)
        # Create a timedelta object and subtract it from the current datetime
        delta = timedelta(**{unit: int(num)})
        _dt = datetime.now() - delta
    else:
        # datetime string is 04/05/2023
        _dt = pd.to_datetime(relative_time_str, format='%d/%m/%Y')

    return _dt 

def gather_urls(save_to_cache = False):
    
    article_list, STOP, COUNTER = [], 25, 0

    for URL in URLS:

        init_URL = URL

        # Search the conceivable news articles on each sub page
        while True:
            soup = BeautifulSoup(s.get(URL).text, "html.parser")

            # STEP: find the css path that a news post is wrapped
            WEB_CARD_ELEMENTS= soup.select('div[class="col-12 col-lg-4"]')

            print(f'\n--DEBUG: No.of web card elements {len(WEB_CARD_ELEMENTS)}')

            for CARD_ELEMENT in WEB_CARD_ELEMENTS[:-1]:
                #print(CARD_ELEMENT)
                try:
                    # STEP: find the css path that contain the news link
                    link = CARD_ELEMENT.select('div[class*="article-type-content"] > a[class="article-type-link"]')[0]
                    link = DEFAULT_WEBSITE + str(link['href'])[1:]
                    #print('\n--DEBUG: Link - ',link)
                except Exception as e:
                    print(f'\n\t--DEBUG: URL - {URL}')
                    print(f'\n\t--DEBUG: No valid link is scraped, break. {e}')
                    break

                try:
                    #STEP 3: find the css path that contain the datetime object
                    link_datetime = CARD_ELEMENT.select('div[class*="article-type-meta"] > span')[0].get_text()
                    link_datetime = _parse_datetime(link_datetime)
                    #print(f'\n\tDEBUG: datetime - {link_datetime}')
                except Exception as e:
                    print(f'\n\t--DEBUG: No datetime is presented.  {e}')
                    break

                # STEP 4: determine the datetime of the link is in range + and -
                if link_datetime >= BEGIN_FROM and link_datetime <= END_AT:
                    article_list.append(link)
                else:
                    COUNTER += 1
            # STEP 5: go to the next page.
            print(f'\n--DEBUG: STOP {STOP} COUNTER {COUNTER}')
            if COUNTER < STOP:
                next_link = soup.find("a", {"class": "pagination-link pagination-link-next"})
                try:
                    URL = init_URL +  next_link['href']
                except:
                    break
                #print(f'\n--DEBUG: The next page is {URL}')
            else:
                break

    if save_to_cache:
        with open(LINK_FILEPATH, 'w', encoding='utf-8') as cache_file:
            for link in article_list:
                cache_file.write(link + '\n')
            print(f'Saved URLs into {LINK_FILEPATH}')

    return article_list

def _extract_datetime(raw_date_string, crawler_datetime):
    try:
        date_publish = datetime.today()
        
        raw_date_string = re.sub('\s+',' ',raw_date_string)
      
        date_time = re.findall(r'\d+[^\x00-\xff]+\d+[^\x00-\xff]+\d+[^\x00-\xff]+\s\d+\:\d+\s\w\w', raw_date_string)[0]
        
        date_time = pd.to_datetime(date_time, format='%Y年%m月%d日 %H:%M %p')
    except:
        date_time = crawler_datetime
        
    return date_time

def main():
    
    link_list = c_scrape_links(USE_CACHE, LINK_FILEPATH, gather_urls)

    articles = c_scrape_articles(USE_CACHE, DATA_JSON_FILEPATH, {'data':link_list, 'param':css_paths, 'func':getNewsByCSS})

    articles_df = Preprocessor({'data':articles,'lang':LANG,'org':1,'source': S_ID}).prepare(func=_extract_datetime)

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
    try:
        for idx, row in articles_df.iterrows():
            row = row.to_dict()
            insert_news_db(row)
        print(f'\n--DEBUG: {articles_df.shape[0]} has been written into database.')
    except Exception as e:
        print(f'\n--DEBUG: API error {e}')
      
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