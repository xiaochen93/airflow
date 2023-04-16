import datetime
import streamlit as st
import requests
import ast
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt

DB_API = 'http://10.2.56.213:8086/getDocumentsByTimeframe'



start= st.date_input(
    "Start",
    datetime.date(2022, 1, 1), key="0")

end = st.date_input(
    "End",
    datetime.date(2022, 1, 1), key="1")

try:
    st.write(start, end)
    trans_response = requests.get(DB_API,params={'table':'dsta_db.news', 'start':f'{start} 00:00:00', 'end':f'{end} 23:59:59', 'order_by': 'published_datetime'})
    json_payload = (ast.literal_eval(trans_response.text))
    out = pd.DataFrame.from_records(json_payload['data'])


except Exception as e:
    out =  e

st.write(out)
