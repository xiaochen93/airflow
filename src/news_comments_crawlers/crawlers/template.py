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

HEADERS = CONS.HEADERS

BLACKLISTED_LINKS = CONS.BLACKLISTED_LINKS

DEFAULT_WEBSITE = ???

CONS.WEBSITE = DEFAULT_WEBSITE

s = CONS.SESSION

LANG = ???

S_ID = ???

URLS = ???

css_paths = ???

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


# step 1 - update parameters
# step 2 - overwrite main functions (two main body)
# step 3 - rename datetime extraction function to private method signature