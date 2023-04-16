# -*- coding: utf-8 -*-
"""
Created on Wed Apr 27 16:08:07 2022

@author: liux5
"""
from Constants import Constants as CONS
from NewsTargetObject import NewsTargetObject
from LinksGrabber import LinksGrabber
import time
from config import Objects
from datetime import datetime
from ArticlesGrabber import getNewsByCSS
from config.Preprocessor import Preprocessor 
import re
import pandas as pd
import pickle
from Functions import *

antara_params = Objects.antara_params

begain = datetime.strptime('2022-01-01', '%Y-%m-%d')

end = datetime.strptime('2022-11-30', '%Y-%m-%d')

dates = [begain, end]

NAME = 'ANT'

LANG = 'BI'

JSON_FILEPATH = CONS.RAW_PATH + '{}_{}_{}.txt'.format(NAME,begain.date(),end.date())

DF_FILEPATH = CONS.DF_PATH + '{}_{}_{}.pickle'.format(NAME,begain.date(),end.date())

USE_CACHE = True

def extract_datetime_antara(raw, crawl):
    try:
        _months = {'Januari':'January','Februari':'February','Maret':'March','Mei':'May','Juni':'June','Juli':'July','Agustus':'August','Oktober':'October','Desember':'December'}
        
        _string = re.sub('WIB', '', raw)
        
        lst = _string.split(',')[1].split()
        
        _month = _months.get(lst[1], 'December')
        
        lst[1] = _month
        
        lst[0] = lst[0] if len(lst[0]) > 1 else '0'+lst[0]
        
        _datetime = ' '.join(lst)
        
        _date_time = pd.to_datetime(_datetime, format='%d %B %Y %H:%M')
    except Exception as e:
        print('\n-- DEBUG:', e)
        _date_time = crawl
    
    return _date_time

def main():
    #set up target
    nsObject = NewsTargetObject(antara_params).nsObject
    #set up links grabber for sitemap
    links_grabber = LinksGrabber(nsObject,dates)
    #perform unit tests for gathering urls
    links_grabber.unit_test()
    #perform gathering urls
    links_grabber.get_article_links()
    
    article_list = links_grabber.article_list
    
    articles = c_scrape_articles(USE_CACHE, JSON_FILEPATH, {'data':article_list, 'param':antara_params.css_paths, 'func':getNewsByCSS})
    
    articles_df = Preprocessor({'data':articles,'lang':LANG,'org':1}).preprocess(func=extract_datetime_antara)
    
    articles_df = articles_df[articles_df['datetime'] > begain]
    
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
    
