import re
from datetime import datetime, timedelta
import random
import requests
import json
import time
from tqdm import tqdm
import argparse

TRANS_API_CN = 'http://10.2.56.190:8290/predictions/zh-en'

TRANS_API_BI = 'http://10.2.56.41:8079/predictions/id-en/'

TRANS_API_BM = 'http://10.2.56.41:8079/predictions/ms-en'

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
                r'^Edited by [^\s]+ at [\d\W]+(?:AM|PM)', # B-Cari starting phrase pattern
                r'This post contains more resources.*$', # B-Cari ending phrase pattern
               ]

postprocess_text_patterns = [
                r'https?://\S+|www\.\S+', # urls 
                r'[^\x00-\x7F]+', # non-english content
]

emoji_patterns = [
    u"\U0001F600-\U0001F64F",  # emoticons
    u"\U0001F300-\U0001F5FF",  # symbols & pictographs
    u"\U0001F680-\U0001F6FF",  # transport & map symbols
    u"\U0001F1E0-\U0001F1FF",  # flags (iOS)
    u"\U00002500-\U00002BEF",  # chinese char
    u"\U00002702-\U000027B0",
    u"\U00002702-\U000027B0",
    u"\U000024C2-\U0001F251",
    u"\U0001f926-\U0001f937",
    u"\U00010000-\U0010ffff",
    u"\u2640-\u2642", 
    u"\u2600-\u2B55",
    u"\u200d",
    u"\u23cf",
    u"\u23e9",
    u"\u231a",
    u"\ufe0f",  # dingbats
    u"\u3030"
]

postprocess_text_patterns = postprocess_text_patterns + emoji_patterns

# clean text based on provided pattern
def clean(text,patterns=[]):
    text = re.sub('\s+', ' ', text) # remove additional padding spaces

    for pattern in patterns:
        text = re.sub(pattern, "", text.strip()) # remove text pattern accordingly
    
    return (text.strip())

# helper - given a time, fetch a start time by stating hours
def getStartTimeStr(end="",hours=24):
    end = datetime.strptime(end, "%Y-%m-%d %H:%M:%S")
    time_span = timedelta(hours=hours)
    start = end - time_span
    return start.strftime("%Y-%m-%d %H:%M:%S")

# helper - fetch data from db into a list of records
def getDataWithListOfDicts(data_api='', table='', start='', end='',):
    t1 = time.perf_counter()
    response = requests.get(data_api,params={'table':table, 'start':start, 'end':end, 'org': True})
    t2 = time.perf_counter()

    if response.status_code==200:
        print(f"\n-- DEBUG: Used {t2-t1} seconds to fetch the data")
        json_payload = (json.loads(response.text))
        json_payload = [v for _, value in json_payload.items() for v in value]
    else:
        print(f"\n--DEBUG: Error occurs while pulling data from DB.")
        print(f"\n--DEBUG: {response.text}")
        json_payload = []

    return json_payload

# translate and clean news articles
def process_articles(start='',end=''):
    DATA_ART_API = 'http://10.2.56.213:8086/getNewsArticlesByTimeframe'
    lst_dicts = getDataWithListOfDicts(data_api=DATA_ART_API, table='dsta_db.test', start=start, end=end)
    print(f"\n-- DEBUG: Total {len(lst_dicts)} no. of documents required processing. ")

    try:
        for dict in tqdm(lst_dicts, desc="\n-- DEBUG: Step 1 - deep cleaning the original documents: "):
            # PRE-process org title 
            dict['org_title'] = clean(dict['org_title'], preprocess_text_patterns)
            # PRE-process org content
            dict['org_content'] = clean(dict['org_content'], preprocess_text_patterns)
    
    except Exception as e:
        print(f'\n-- DEBUG: PRE processing error occur on {e}')
    
    try:
        for dict in tqdm(lst_dicts, desc="\n-- DEBUG: Step 2 - get documents translated and processed accordingly"):
            if dict['lang'] == 'CN':
                temp_title = (requests.post(TRANS_API_CN, json={'data':[dict['org_title']]})).json()['translation'][0]
                temp_content = (requests.post(TRANS_API_CN, json={'data':[dict['org_content']]})).json()['translation'][0]
            
            elif dict['lang'] == 'BM':
                temp_title = requests.post(TRANS_API_BM, json={'data':[dict['org_title']]}).json()['translation'][0]
                temp_content = requests.post(TRANS_API_BM, json={'data':[dict['org_content']]}).json()['translation'][0]

            elif dict['lang'] == 'BI':
                temp_title = requests.post(TRANS_API_BI, json={'data':[dict['org_title']]}).json()['translation'][0]
                temp_content = requests.post(TRANS_API_BI, json={'data':[dict['org_content']]}).json()['translation'][0]
            
            else:
                temp_title = dict['org_title']
                temp_content = dict['org_content']

            # POST-process org title 
            dict['title'] = clean(temp_title.strip(), postprocess_text_patterns)

            # POST-process org content
            dict['content'] = clean(temp_content.strip(), postprocess_text_patterns)

            out = requests.put(UPDATE_API, json={"table": "dsta_db.test", "data": {"title": dict['title'], "content": dict['content'], "last_modified": str(start), "translated": True}, "where" : f"article_id = {dict['article_id']}" })
            
            if out.status_code == 500:
                print(out.text)
                raise
            else:
                article_id = dict['article_id']
            
    except Exception as e:
        print(f"\n-- DEBUG: Translation error occur with {e}")
        print(f"\n\t--DEBUG: {dict['org_title']} ")
        print(f"\n\t--DEBUG: {dict['org_content']} ")
        raise

# translate and clean comments
def process_comments(start='',end=''):
    DATA_CMT_API = 'http://10.2.56.213:8086/getCommentsByTimeframe'
    lst_dicts = getDataWithListOfDicts(data_api=DATA_CMT_API, table='dsta_db.test_24hr_comments', start=start, end=end)
    
    try:
        for dict in tqdm(lst_dicts, desc="\n-- DEBUG: Step 1 - deep cleaning the original documents: ", position=0, leave=True):
            # PRE-process org content 
            dict['cmt_org_content'] = clean(dict['cmt_org_content'], preprocess_text_patterns)
            
            
    except Exception as e:
        print(f'\n-- DEBUG: PRE processing error occur on {e}')
        raise

    try:
        for dict in tqdm(lst_dicts, desc="\n-- DEBUG: Step 2 - get comments translated and processed accordingly", position=1, leave=True):
            try:
                if dict['lang'] == 'CN':
                    temp_content = (requests.post(TRANS_API_CN, json={'data':[dict['cmt_org_content']]})).json()['translation'][0]
                
                elif dict['lang'] == 'BM':
                    temp_content = requests.post(TRANS_API_BM, json={'data':[dict['cmt_org_content']]}).json()['translation'][0]

                elif dict['lang'] == 'BI':
                    temp_content = requests.post(TRANS_API_BI, json={'data':[dict['cmt_org_content']]}).json()['translation'][0]
                
                else:
                    temp_content = dict['cmt_org_content']
            except Exception as e:
                continue
            # POST-process org content
            dict['cmt_content'] = clean(temp_content.strip(), postprocess_text_patterns)

            out = requests.put(UPDATE_API, json={"table": "dsta_db.test_24hr_comments", "data": {"cmt_content": dict['cmt_content'], "last_modified": str(start), "translated": True}, "where" : f"id = {dict['id']}" })
            if out.status_code == 500:
                print(f"\n-- Update Error - for comment {dict['id']}")
                print("\n\n-- ",out.text)
                pass
            else:
                cmt_id = dict['id']

    except Exception as e:
        print(f"\n-- DEBUG: Translation error occur with {e}")
        print(f"\n\t--DEBUG: {dict['cmt_org_content']} ")
        raise

    # perform the update, do not need to return anything
    #primary_ids = []
    #try:
    #    for dict in tqdm(lst_dicts, desc="\n-- DEBUG: Step 3 - update record to db", position=2, leave=True):

    #except Exception as e:       
    #    print(f"\n-- DEBUG: Update Error occur with {e}")

parser = argparse.ArgumentParser(description="Parameters to execute a web crawler")
# default datetime
CURRENT_DATETIME = datetime.today().strftime("%Y-%m-%d") + ' ' + datetime.today().strftime("%H:%M:%S")
# default datetime
START_DATETIME = getStartTimeStr(end=CURRENT_DATETIME,hours=24)

parser.add_argument(
        '--begain_datetime',
        type=str,
        help="end datetime - string - 2023-12-31 16:49:00",
        default=START_DATETIME,
        required=True
)

parser.add_argument(
        '--end_datetime',
        type=str,
        help="begin datetime - string - 2024-01-01 12:30:00",
        default=CURRENT_DATETIME,
        required=True
)

if __name__ == '__main__':
    args = parser.parse_args()

    begain_datetime = datetime.strptime(str(args.begain_datetime), "%Y-%m-%d %H:%M:%S")
    
    end_datetime = datetime.strptime(str(args.end_datetime), "%Y-%m-%d %H:%M:%S")

    process_articles(start=begain_datetime, end=end_datetime)

    process_comments(start=begain_datetime, end=end_datetime)