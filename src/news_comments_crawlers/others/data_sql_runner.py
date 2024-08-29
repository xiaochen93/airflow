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

UPDATE_QUERY_API = 'http://10.2.56.213:8086/update_raw_query'
# default datetime
CURRENT_DATETIME = datetime.today().strftime("%Y-%m-%d") + ' ' + datetime.today().strftime("%H:%M:%S")

# drop/create the statistics view
DROP_VIEW_DATA_OVERVIEW = '''DROP VIEW IF EXISTS DATA_OVERVIEW;'''
CREATE_VIEW_DATA_OVERVIEW = '''CREATE VIEW DATA_OVERVIEW AS(SELECT a.source_id, sources.source, sources.lang, a.article_count, COALESCE(b.comment_count, NULL) AS comment_count FROM (SELECT source_id, COUNT(article_id) AS article_count FROM news WHERE DATE(published_datetime) >= "2021-01-01" GROUP BY source_id) AS a LEFT JOIN (SELECT source_id, COUNT(id) AS comment_count FROM comments WHERE DATE(cmt_published_datetime) >= "2021-01-01" GROUP BY source_id) AS b ON a.source_id = b.source_id LEFT JOIN sources on a.source_id = sources.source_id ORDER BY comment_count DESC);''' 

# drop/create the no. of news articles view
DROP_VIEW_NO_OF_NEWS_DATE = '''DROP VIEW IF EXISTS NO_OF_NEWS_DATE;'''
CREATE_VIEW_NO_OF_NEWS_DATE = '''CREATE VIEW NO_OF_NEWS_DATE as (SELECT DATE(published_datetime) as "date", count(article_id) FROM news WHERE DATE(published_datetime) >= '2022-01-01' GROUP BY DATE(published_datetime));''' 

# drop/create the no. of comments
DROP_VIEW_NO_OF_COMMENTS_DATE = '''DROP VIEW IF EXISTS NO_OF_COMMENTS_DATE;'''
CREATE_VIEW_NO_OF_COMMENTS_DATE = '''CREATE VIEW NO_OF_COMMENTS_DATE as (SELECT DATE(cmt_published_datetime) as "date", count(id) FROM comments WHERE DATE(cmt_published_datetime) >= '2022-01-01' GROUP BY DATE(cmt_published_datetime));''' 


# 
DROP_VIEW_DUPLICATES = '''DROP VIEW IF EXISTS VIEW_DUPLICATES;'''

CREATE_VIEW_DUPLICATES = '''
    CREATE VIEW VIEW_DUPLICATES AS (
        SELECT 
        max(article_id) as article_id,
        url,
        DATE(published_datetime) as "unique_date_index",
        COUNT(*) AS total_urls,
        SUM(CASE WHEN deleted = 0 THEN 1 ELSE 0 END) AS no_of_remain,
        SUM(CASE WHEN deleted = 1 THEN 1 ELSE 0 END) AS no_of_deleted
        FROM news
        WHERE (url IS NOT NULL and url != 'Unknown' and url != '')
        GROUP BY url, DATE(published_datetime)
        HAVING total_urls > 1
        ORDER BY DATE(published_datetime) DESC
    );
'''

# mark duplicated records with deleted =1  
REMOVE_DUPLICATED_NEWS_RECORDS = '''
    UPDATE news
    SET deleted = 1, last_modified = CURDATE()
    WHERE (url IS NOT NULL and url != 'Unknown' and url != '')
    AND news.published_datetime BETWEEN '2024-06-01 00:00:00' AND '2024-12-31 23:59:59'
    AND EXISTS (
    SELECT 1
        FROM VIEW_DUPLICATES
        WHERE news.url = VIEW_DUPLICATES.url
        AND DATE(news.published_datetime) = VIEW_DUPLICATES.unique_date_index
        AND news.article_id != VIEW_DUPLICATES.article_id
    );
'''
REMOVE_DUPLICATED_COMMENTS = '''UPDATE comments SET deleted = 1, last_modified = "2000-01-01" WHERE deleted=0 and cmt_article_id IN (SELECT * FROM (SELECT article_id FROM news WHERE deleted=1) AS subquery);'''

def execute_sql_query_task(query="", task_name="", DATA_QUERY_API=DATA_QUERY_API):
    t1 = time.perf_counter()
    query = re.sub(r"\s+", " ", query)
    response = requests.post(DATA_QUERY_API, json={'query':query})

    print(response)
    print(response.text)
    
    t2 = time.perf_counter()

    if response.status_code==200:
        message = f"\n -- DEBUG: {CURRENT_DATETIME} - SQL for {task_name} execution is successful ."
    else:
        message = f"\n -- DEBUG: {CURRENT_DATETIME}  - SQL for {task_name} execution is failed ."
        message = message + "\n -- DEBUG: " + response.text
        raise
    
    print(message)
    #print(f"\t\t-- DEBUG: {response.text}")

if __name__ == '__main__':
    # 4. mark duplicated records deleted
    execute_sql_query_task(query=DROP_VIEW_DUPLICATES, task_name="DROP DUPLICATES")
    execute_sql_query_task(query=CREATE_VIEW_DUPLICATES, task_name="CREATE DUPLICATE VIEW")

    execute_sql_query_task(query=REMOVE_DUPLICATED_NEWS_RECORDS, task_name="UPDATE NEWS ARTICLES DELETED=1",DATA_QUERY_API=UPDATE_QUERY_API)
    execute_sql_query_task(query=REMOVE_DUPLICATED_COMMENTS, task_name="UPDATE NEWS COMMENTS DELETED=1", DATA_QUERY_API=UPDATE_QUERY_API)

    # 1. drop/create the statistics view
    execute_sql_query_task(query=DROP_VIEW_DATA_OVERVIEW, task_name="DROP VIEW DATA_OVERVIEW")
    execute_sql_query_task(query=CREATE_VIEW_DATA_OVERVIEW, task_name="CREATE VIEW DATA_OVERVIEW")
    
    # 2. drop/create the no. of news view
    execute_sql_query_task(query=DROP_VIEW_NO_OF_NEWS_DATE, task_name="DROP VIEW NO. OF NEWS ARTICLES TIMELINE")
    execute_sql_query_task(query=CREATE_VIEW_NO_OF_NEWS_DATE, task_name="CREATE VIEW NO. OF NEWS ARTICLES TIMELINE")
    
    # 3. drop/create the no. of comments view
    execute_sql_query_task(query=DROP_VIEW_NO_OF_COMMENTS_DATE, task_name="DROP VIEW NO. OF COMMENTS TIMELINE")
    execute_sql_query_task(query=CREATE_VIEW_NO_OF_COMMENTS_DATE, task_name="CREATE VIEW NO. OF COMMENTS TIMELINE")
    
    