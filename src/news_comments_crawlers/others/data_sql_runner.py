import re
from datetime import datetime, timedelta
import random
import requests
import json
import time
from tqdm import tqdm
import argparse
import ast

DATA_QUERY_API = 'http://10.2.56.213:8086/non_return_query'
# default datetime
CURRENT_DATETIME = datetime.today().strftime("%Y-%m-%d") + ' ' + datetime.today().strftime("%H:%M:%S")

# query
DROP_VIEW_DATA_OVERVIEW = '''DROP VIEW IF EXISTS DATA_OVERVIEW;'''
CREATE_VIEW_DATA_OVERVIEW = '''CREATE VIEW DATA_OVERVIEW AS(SELECT a.source_id, sources.source, a.article_count, COALESCE(b.comment_count, NULL) AS comment_count FROM (SELECT source_id, COUNT(article_id) AS article_count FROM news WHERE DATE(published_datetime) >= "2021-01-01" GROUP BY source_id) AS a LEFT JOIN (SELECT source_id, COUNT(id) AS comment_count FROM comments WHERE DATE(cmt_published_datetime) >= "2021-01-01" GROUP BY source_id) AS b ON a.source_id = b.source_id LEFT JOIN sources on a.source_id = sources.source_id ORDER BY comment_count DESC);''' 

def execute_sql_query_task(query="", task_name=""):
    t1 = time.perf_counter()
    query = re.sub(r"\s+", " ", query)
    response = requests.post(DATA_QUERY_API, json={'query':query})
    
    t2 = time.perf_counter()

    if response.status_code==200:
        message = f"\n -- DEBUG: {CURRENT_DATETIME} - SQL for {task_name} execution is successful ."
    else:
        message = f"\n -- DEBUG: {CURRENT_DATETIME}  - SQL for {task_name} execution is failed ."
        message = message + "\n -- DEBUG: " + response.text
        raise
    
    print(message)


if __name__ == '__main__':
    execute_sql_query_task(query=DROP_VIEW_DATA_OVERVIEW, task_name="DROP VIEW DATA_OVERVIEW")
    execute_sql_query_task(query=CREATE_VIEW_DATA_OVERVIEW, task_name="CREATE VIEW DATA_OVERVIEW")