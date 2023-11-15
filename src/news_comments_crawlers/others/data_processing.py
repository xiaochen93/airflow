import re
from datetime import datetime, timedelta
import random
import requests
import json
import time
from tqdm import tqdm

TRANS_API_CN = 'http://10.2.56.41:8090/predictions/zh-en/'

TRANS_API_BI = 'http://10.2.56.41:8082/predictions/id-en/'

TRANS_API_BM = 'http://10.2.56.41:8082/predictions/ms-en/'

DATA_ART_API = 'http://10.2.56.213:8086/getDocumentsByTimeframe'

DATA_CMT_API = 'http://10.2.56.213:8086/getCommentsByTimeframe'

UPDATE_API = "http://10.2.56.213:8086/update"

preprocess_text_patterns = [r'Mediacorp News Group © 2022', 
                r'\s*（早报讯）', # CN noise
                r'\s*Bisnis.com, ', # BM noise
                r'(\[|\【).+(\]|\】)', # caption noise
                r'本文为作者观点，不代表本网站立场', # CN noise tokens
                r'请点击.+系列报道，阅读更多文章。', # CN noise tokens
                r'\s{1,}回复', # redudant spacing
                r'Copyright © ANTARA 2021', # BI noise tokens
                r'Baca juga: .+', # BI noise
                r'^.+\(ANTARA\)\s*\-\s*', # BI noise
                r'^.+\s发表于\s[\d\-\s\:]+', #CN noise pattern
               ]

postprocess_text_patterns = [
                r'https?://\S+|www\.\S+', # urls 
                r'[^\x00-\x7F]+', # non-english content
]

def clean(text,patterns=[]):
    text = re.sub('\s+', ' ', text) # remove additional padding spaces

    for pattern in patterns:
        text = re.sub(pattern, "", text.strip()) # remove text pattern accordingly
    
    return (text.strip())

def getStartTimeStr(end="",hours=24):
    end = datetime.strptime(end, "%Y-%m-%d %H:%M:%S")
    time_span = timedelta(hours=hours)
    start = end - time_span
    return start.strftime("%Y-%m-%d %H:%M:%S")



def getDataWithListOfDicts(data_api='', table='', start='', end='',):
    t1 = time.perf_counter()
    response = requests.get(data_api,params={'table':table, 'start':start, 'end':end, 'org': True})
    t2 = time.perf_counter()

    if response.status_code==200:
        print(f"\n-- DEBUG: Used {t2-t1} seconds to fetch the data")
        json_payload = [each for each in response.json()]
    else:
        print(f"\n--DEBUG: Error occurs while pulling data from DB.")
        json_payload = []

    return json_payload

def process_articles(start='',end=''):
    DATA_ART_API = 'http://10.2.56.213:8086/getDocumentsByTimeframe'
    lst_dicts = getDataWithListOfDicts(data_api=DATA_ART_API, table='dsta_db.test', start=start, end=end)

    try:
        for dict in lst_dicts:
            # PRE-process org title 
            dict['org_title'] = clean(dict['org_title'], preprocess_text_patterns)
            # PRE-process org content
            dict['org_content'] = clean(dict['org_content'], preprocess_text_patterns)
    except Exception as e:
        print(f'\n--DEBUG: PRE processing error occur on {e}')
    
    try:
        for dict in lst_dicts:
            if dict['lang'] == 'CN':
                temp_title = (requests.post(TRANS_API_CN, json={'data':dict['org_title']})).json()['translation'][0]
                temp_content = (requests.post(TRANS_API_CN, json={'data':dict['org_content']})).json()['translation'][0]
            elif dict['lang'] == 'BM':
                temp_title = requests.post(TRANS_API_BM, json={'data':dict['org_title']})
                temp_content = requests.post(TRANS_API_BM, json={'data':dict['org_content']})
            elif dict['lang'] == 'BI':
                temp_title = requests.post(TRANS_API_BI, json={'data':dict['org_title']})
                temp_content = requests.post(TRANS_API_BI, json={'data':dict['org_content']})
            else:
                temp_title = dict['org_title']
                temp_content = dict['org_content']
            # POST-process org title 
            dict['title'] = clean(temp_title.strip(), postprocess_text_patterns)
            # PRE-process org content
            dict['content'] = clean(temp_content.strip(), postprocess_text_patterns)
        
    except Exception as e:
        print(f"\n-- DEBUG: Translation error occur with {e}")
        print(f"\n\t--DEBUG: {dict['org_title']} ")
        print(f"\n\t--DEBUG: {dict['org_content']} ")
        raise

    try:
        for dict in lst_dicts:
            out = requests.put(UPDATE_API, json={"table": "dsta_db.test", "data": {"title": dict['title'], "content": dict['content'], "last_modified": start, "translated": True}, "where" : f"id = {dict['article_id']}" })
    except Exception as e:       
        print(f"\n-- DEBUG: Update Error occur with {e}")

def process_comments(start='',end=''):
    #DATA_CMT_API = 'http://10.2.56.213:8086/getCommentsByTimeframe'
    #lst_dicts = getDataWithListOfDicts(data_api=DATA_CMT_API, table='dsta_db.test_24hr_comments', start=start, end=end)
    pass


if __name__ == '__main__':
    CURRENT_DATETIME = datetime.today().strftime("%Y-%m-%d") + ' ' + datetime.today().strftime("%H:%M:%S")
    START_DATETIME = getStartTimeStr(end=CURRENT_DATETIME,hours=24)

    process_articles(start=START_DATETIME, end=CURRENT_DATETIME)

    process_comments(start=START_DATETIME, end=CURRENT_DATETIME)