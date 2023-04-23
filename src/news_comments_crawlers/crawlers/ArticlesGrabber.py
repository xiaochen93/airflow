# -*- coding: utf-8 -*-
"""
Created on Thu Apr 28 10:18:27 2022

@author: liux5
"""
from bs4 import BeautifulSoup
from datetime import datetime
from config.Constants import Constants as CONS

SESSION = CONS.SESSION

def getNewsByCSS(article_url,css_paths):
    
    article, news_title, category, date_news, date_crawler = '', '', '', '', ''
    
    allow_redirects = css_paths.get('allow_redirects', True)

    page_content = SESSION.get(article_url,allow_redirects=allow_redirects)
        
    soup = BeautifulSoup(page_content.text, 'lxml')
    
    try:
        news_title = soup.select(css_paths['title'])[0].get_text().strip()
    except Exception as e:
        news_title = ''
    
    try:
        category = soup.select(css_paths['category'])[0].get_text().strip()
    except Exception as e:
        category = ''
    
    try:
        p_datetime = soup.select(css_paths['date'])[0].get_text().strip()
    except Exception as e:
        p_datetime = ''
        
    date_crawler = datetime.now()
        
    try:
        #get the article text    
        for p_div in soup.select(css_paths['article']):
            for paragraph in p_div.find_all('p'):
            #for paragraph in p_div.find_all('p', class_=''):
                if paragraph.get_text().find('\u00A0') != -1:
                    continue
                article += paragraph.get_text() + '\n'
        if len(article) == 0 or article.strip() == '':
            article = soup.select(css_paths['article'])[0].get_text().strip()
    except Exception as e:
        article = ''
    
    return {'url': article_url,
            'published_datetime': p_datetime.strip(),
            'crawled_datetime': date_crawler,
            'org_title': news_title.strip(),
            'category': category.strip(),
            'org_content': article.strip()}