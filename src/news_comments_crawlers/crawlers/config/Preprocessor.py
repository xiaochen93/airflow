# -*- coding: utf-8 -*-
"""
Created on Thu Dec 15 16:39:31 2022

@author: liux5
"""
import abc

import re

from nltk.stem import WordNetLemmatizer 

from nltk.tokenize import word_tokenize

from nltk.corpus import stopwords

import numpy as np

import seaborn as sns

import matplotlib.pyplot as plt

import pandas as pd

from datetime import datetime

from config.Constants import Constants as CONS

import os

print(os.listdir())

class Preprocessor:
    
    def __init__(self, obj):
        self.json, self.lang, self.org, self.source = obj['data'], obj['lang'], obj['org'], obj['source']
        self.df = self.create_dataframe()
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        
    def create_dataframe(self):
        df = pd.DataFrame.from_dict(self.json,orient='columns')
    
        df['lang'] = self.lang
        
        df['org'] = self.org
        
        df['source'] = self.source
        
        return df
    
    def preprocess(self, func=lambda x: x):
        try:
            df = self.df.dropna(subset = ['org_content'])
            df['publish_datetime'] = df.apply(lambda row: func(row['publish_datetime'],row['date_crawler']), axis=1)
            df = df[(df['publish_datetime'] >= CONS.BEGIN_FROM) & (df['publish_datetime'] <= CONS.END_AT)]
        
        except Exception as e:
            print(e)
            raise
            df = self.df
            df['publish_datetime'] = datetime.today()
            
        return df

def clean(text):
    text = re.sub("[\(\[].*?[\)\]]", "", text)
    text = re.sub('([.,!?()])', r' \1 ', text) # padding
    text = re.sub('\s{2,}', ' ', text) # padding
    text = text.lower()
    text = re.sub(r'[^\w\s]','', text) 
    #word_list = word_tokenize(text)
    #stem_text = [lemmatizer.lemmatize(text) for text in word_list if not text.isdigit() if not text.lower() in self.stop_words]
    #final_text = " ".join(stem_text)
    return text
    
    
def drop_na(df):
    df = df.applymap(lambda x: np.nan if x=="" else x)
    na_num = max(df.isnull().sum())
    if na_num == 0:
        print('\n-- No records contains null value, passed')  
    else:
        print('\n-- {} records have been dropped due to null values'.format(na_num))
        df.dropna(inplace=True)
        #df.isnull().sum()
    return df

        
    
    
        