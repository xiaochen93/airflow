
import pandas as pd
import requests
import json
from datetime import datetime
import ast
import time

INSERT_API = 'http://10.2.56.213:8086/insert'

def insert_news_db(row):

    try:
        response = requests.post(INSERT_API,json={'table':'dsta_db.test', 'data': row })
    
    except Exception as e:
        print('\n-- INSERTION ERROR: ', row['article_id'], ' with error message ', e, ' .')
    if response.status_code == 500:
        print(response.text)
    else:
        pass

    return response.status_code