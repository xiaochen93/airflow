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

pre_text_patterns= [r'Mediacorp News Group © 2022', 
                r'\s*（早报讯）',
                r'\s*Bisnis.com, ',
                r'(\[|\【).+(\]|\】)',
                r'本文为作者观点，不代表本网站立场', 
                r'请点击.+系列报道，阅读更多文章。',
                r'\s{1,}回复',
                r'Copyright © ANTARA 2021',
                r'Baca juga: .+',
                r'^.+\(ANTARA\)\s*\-\s*',
                r'^.+\s发表于\s[\d\-\s\:]+',
               ]

def clean(text,patterns=[]):
    #2. removing additional whitespace
    text = re.sub('\s+', ' ', text) # padding
    #1. subtracting text pattern in regular expression
    for pattern in patterns:
        text = re.sub(pattern, "", text.strip())
    #text = re.sub('([.,!?()])', r' \1 ', text) # padding
    #text = re.sub(r'[^\w\s]','', text) 
    #word_list = word_tokenize(text)
    #stem_text = [lemmatizer.lemmatize(text) for text in word_list if not text.isdigit() if not text.lower() in self.stop_words]
    #final_text = " ".join(stem_text)
    return (text.strip())

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
        
        df['source_id'] = self.source

        df['translated'] = False if self.lang != 'EN' else True
        
        return df
    
    def prepare(self, func=lambda x: x):
        try:
            df = self.df.dropna(subset = ['org_content'])
            
            # update the published_datetime into datetime object
            df['published_datetime'] = df.apply(lambda row: func(row['published_datetime'],row['crawled_datetime']), axis=1)

            df['published_datetime'] = df['published_datetime'].apply(lambda x: str(x))

            # drop the crawling_datetime column
            df = df.drop('crawled_datetime', axis=1)     

            # translate title and content ?
            if self.lang  == 'EN':
                df['content'] = df['org_content']
                df['title'] = df['org_title']
            else:
                df['content'] = ''
                df['title'] = ''
            
            # clean the original text
            df['content'] = df['content'].apply(lambda x: clean(x, pre_text_patterns))           
            df['content'] = df['content'].apply(lambda x: clean(x, pre_text_patterns))

        except Exception as e:
            print(e)
            raise

        return df
    
    def preprocess(self, func=lambda x: x):
        try:
            df = self.df.dropna(subset = ['org_content'])
            df['publish_datetime'] = df.apply(lambda row: func(row['publish_datetime'],row['date_crawler']), axis=1)
            #df = df[(df['publish_datetime'] >= CONS.BEGIN_FROM) & (df['publish_datetime'] <= CONS.END_AT)]
        
        except Exception as e:
            print(e)
            raise
            df = self.df
            df['publish_datetime'] = datetime.today()
            
        return df


    
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

        
    
    
        