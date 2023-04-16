# -*- coding: utf-8 -*-
"""
Created on Mon Apr  4 22:40:05 2022

@author: liux5
"""
from dataclasses import dataclass, field

from datetime import datetime

import requests

from requests.adapters import HTTPAdapter

from urllib3.util.retry import Retry

import os.path

import pathlib

print('\n--DEBUG: __file__:    ', __file__)

class Constants:

    LINK_PATH : str = "/opt/airflow/src/news_comments_crawlers/crawlers/news_links/links_"

    RAW_PATH : str = "/opt/airflow/src/news_comments_crawlers/crawlers/output/raw/"
    
    DF_PATH : str = "/opt/airflow/src/news_comments_crawlers/crawlers/output/df/"
    
    OUT_FOLDER_PATH : str = "/opt/airflow/src/news_comments_crawlers/crawlers/out/"
    
    TODAY = str(datetime.now().date())
    
    LOG_FILE_PATH = OUT_FOLDER_PATH + TODAY + '.txt'
    
    #_ACCEPTED_LINKS = ['/singapore/','/world/','/southeast-asia/','/business/','/economic/']

    #ACCEPTED_LINKS : list = field(default_factory=lambda: ['/singapore/','/world/','/southeast-asia/','/business/','/economic/'])

    BLACKLISTED_LINKS = ['/container/','/tonton/','/infografik/','/foto/','/gaya-hidup/','/video/','/authors/','/life-style/','/forum/','/wencui/','/sport/','/wellness/','/commentary/','/cnainsider/','/advertorial/','/cna-insider/','/cna-lifestyle/','/cnalifestyle/','/obsessions/','/entertainment/','/watch/', '/brandstudio/', '/listen/','/tokyo-2020/','/taxonomy/','/author/','/rss/','/interactives/','/node/','/about-us/','/contact-us/','/lifestyle/','/horoscope/','/zodiac/','/videos/','/synopsis/','/beauty-fashion/','/food/','/fun-learning/','/sports/','/jk-zone/','/music/','/movies-shows/','/node/','/columns/','/life/','/stories/','/author/','/moe/','/x-over/','/travel/','/multimedia/']

    #BLACKLISTED_LINKS : list = field(default_factory =lambda: ['/forum/','/wencui/','/sport/','/wellness/','/commentary/','/cnainsider/','/advertorial/','/cna-insider/','/cna-lifestyle/','/cnalifestyle/','/obsessions/','/entertainment/','/watch/', '/brandstudio/', '/listen/','/tokyo-2020/','/taxonomy/','/author/','/rss/','/interactives/','/node/','/about-us/','/contact-us/','/lifestyle/','/horoscope/','/zodiac/','/videos/','/synopsis/','/beauty-fashion/','/food/','/fun-learning/','/sports/','/jk-zone/','/music/','/e-news/','/movies-shows/','/node/','/columns/','/life/','/stories/','/author/','/moe/','/x-over/','/news/','/travel/','/multimedia/'])
    
    USE_CACHE : bool = True

    HEADERS = {
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36', #Google Chrome user agent header
            'hl'        :  'en'
    }
    
    BEGIN_FROM = datetime.strptime('2022-01-01', '%Y-%m-%d')

    END_AT = datetime.strptime('2023-02-28', '%Y-%m-%d')
    
    MAX_PAGE = 20
    
    try:
        SESSION = requests.Session()
        SESSION.headers.update(HEADERS)
        SESSION.max_redirects = 10
        #_retry = Retry(connect=3, total=5, backoff_factor=0.1,status_forcelist=[ 500, 502, 503, 504 ])
        _retry = Retry(connect=3, backoff_factor=0.5)
        _adapter = HTTPAdapter(max_retries=_retry)
        SESSION.mount('http://', _adapter)
        SESSION.mount('https://', _adapter)
        print('\n-- Session Object : Good to go.')
    except Exception as e:
        print(e)
        print('\n-- Session Object : Failed to create.')
        
    try:
        TODAY_DIR = OUT_FOLDER_PATH + TODAY
        isdir = os.path.isdir(TODAY_DIR)
        if not isdir:
            os.mkdir(TODAY_DIR)

        LINK_DIR = TODAY_DIR + '/links/'
        isdir = os.path.isdir(LINK_DIR)
        if not isdir:
            os.mkdir(LINK_DIR)

        DATA_DIR = TODAY_DIR + '/data/'
        isdir = os.path.isdir(DATA_DIR)
        JSON_DATA_DIR = DATA_DIR + 'json/'
        DF_DATA_DIR = DATA_DIR + 'df/'
        if not isdir:
            os.mkdir(DATA_DIR)
            os.mkdir(JSON_DATA_DIR)
            os.mkdir(DF_DATA_DIR)

        print('\n-- Folders: Good to go.')

    except Exception as e:
        print('\n-- Log Folder: Failed to create.')
        print(e)
        