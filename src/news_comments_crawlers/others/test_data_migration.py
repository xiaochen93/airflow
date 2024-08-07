import re
from datetime import datetime, timedelta
import random
import requests
import json
import time
from tqdm import tqdm
import argparse
import ast

TRANS_API_CN = 'http://10.2.56.190:8290/predictions/zh-en'

TRANS_API_BI = 'http://10.2.56.41:8079/predictions/id-en/'

TRANS_API_BM = 'http://10.2.56.41:8079/predictions/ms-en'

DATA_ART_API = 'http://10.2.56.213:8086/getDocumentsByTimeframe'

DATA_CMT_API = 'http://10.2.56.213:8086/getCommentsByTimeframe'

DATA_QUERY_API = 'http://10.2.56.213:8086/query'

UPDATE_API = "http://10.2.56.213:8086/update"

INSERT_API = 'http://10.2.56.213:8086/insert'

cmt_sources = ["","","",""]

def getStartTimeStr(end="",hours=24):
    end = datetime.strptime(end, "%Y-%m-%d %H:%M:%S")
    time_span = timedelta(hours=hours)
    start = end - time_span
    return start.strftime("%Y-%m-%d %H:%M:%S")

def getTranslatedRecords(data_api='', table='', limit="", article_id=""):
    if article_id != "":
        add_query_1 = f'cmt_article_id={article_id} and'
        add_query_2 = ""
    else:
        add_query_1 = ""
        add_query_2 = f'LIMIT {limit}'

    data_query= f'''SELECT * FROM dsta_db.{table} WHERE {add_query_1} translated=1 and deleted=0 {add_query_2};'''

    t1 = time.perf_counter()
    response = requests.post(data_api, json={'query':data_query})
    t2 = time.perf_counter()

    if response.status_code==200:
        #print(f"\n-- DEBUG: Used {t2-t1} seconds to fetch the data")
        json_payload = (json.loads(response.text))
        json_payload = [v for _, value in json_payload.items() for v in value]
    else:
        print(f"\n--DEBUG: Error occurs while pulling data from DB.")
        print(f"\n--DEBUG: {response.text}")
        json_payload = []

    return json_payload

def migrate_data(limit=500):

    # 1. fetch news articles
    news_articles = getTranslatedRecords(data_api=DATA_QUERY_API, table="test", limit=limit)

    for each_article in tqdm(news_articles):
        test_article_id, test_last_modified = each_article['article_id'], each_article['last_modified']
        associated_comments = getTranslatedRecords(data_api=DATA_QUERY_API, table="test_24hr_comments", limit=limit, article_id=test_article_id)
        
        # delete the test_article_id
        del each_article["article_id"]
        del each_article["org"]

        # update the last modified to today's date
        each_article["last_modified"] = CURRENT_DATE
        each_article["published_datetime_old"] = each_article["published_datetime"]
        each_article["published_datetime"] = each_article["published_datetime"] + ".001"

        # insert the article to the news table and obtain the new article_id
        response = requests.post(INSERT_API,json={'table':'dsta_db.news', 'data': each_article})
        new_article_id = ast.literal_eval(response.text)['lastrowid']
        
        # 2024-07-31 : if this post is scrapped from comment forum, 
        article_datetime = datetime.strptime((each_article["published_datetime_old"].split("."))[0], "%Y-%m-%dT%H:%M:%S")
        current_datetime = datetime.strptime(CURRENT_DATETIME, "%Y-%m-%d %H:%M:%S")
        
        datetime_cond = (current_datetime - article_datetime).days <= 3

        #print(f"\n-- DEBUG: source id {each_article['source_id']} and date difference {(current_datetime - article_datetime).days}")
        _is_from_forum = int(each_article['source_id']) in [5,16,17,19]
        _is_within_time_range = datetime_cond
        if _is_from_forum and _is_within_time_range:
            print(f"\n-- DEBUG: article {each_article['title']}")
            print('\n-- DEBUG: ',article_datetime, current_datetime)
            print(f"\n\t-- DEBUG: 1. is the data from comment forum ? {_is_from_forum} - 2.  accumlate ? {_is_within_time_range} - days {(current_datetime - article_datetime).days}")
            print(f'\n\t-- DEBUG: This will not be deleted at the moment.')
        
        #print("old article_id: ", test_article_id, "new article_id: ", new_article_id)

parser = argparse.ArgumentParser(description="Parameters to execute a web crawler")
# default datetime
CURRENT_DATETIME = datetime.today().strftime("%Y-%m-%d") + ' ' + datetime.today().strftime("%H:%M:%S")

CURRENT_DATE = str(datetime.today().strftime("%Y-%m-%d"))

parser.add_argument(
        '--limit',
        type=str,
        help="threshold value for how many records to process in one batch.",
        default=500,
        required=True
)

if __name__ == '__main__':
    args = parser.parse_args()
    limit = int(args.limit)
    #end_datetime = datetime.strptime(str(args.end_datetime), "%Y-%m-%d %H:%M:%S")
    migrate_data(limit=limit)