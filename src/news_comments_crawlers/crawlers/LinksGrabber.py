# -*- coding: utf-8 -*-
"""
Created on Wed Apr 13 18:13:22 2022

@author: liux5
"""
from bs4 import BeautifulSoup
from tqdm import tqdm
from datetime import datetime
from Constants import Constants as CONS
from random import choice
import gzip
from urllib.request import urlopen
import math
'''
desc: determine if a url is skipped.

'''
import sys, os

class HiddenPrints:
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stdout = self._original_stdout

class LinksGrabber:
    def __init__(self, nsObject, dates):
        self.domain = nsObject.DOMAIN
        self.website = nsObject.WEBSITE
        self.sitemap = nsObject.SITEMAP
        self.name = nsObject.NAME
        self.begain = dates[0]
        self.end = dates[1]
        self.cache_path = CONS.LINKS_PATH + self.name + '_'+str(dates[0].date()) +'_' +str(dates[1].date()) +'.txt'
        print('\n-- Cache_path:',self.cache_path)
        self.parser = nsObject.PARSER
        self.no_records = 0
        
    def unit_test(self,save_to_cache= False):
        #1. test the session conntection between local client and sitemap
        try:
            sitemap_object = CONS.SESSION.get(self.sitemap)
            print('\n-- UNIT TEST: Passed. -- DEBUG: An session object is created with the sitemap.')
        except Exception as e:
            print('\n-- UNIT TEST: Failed. -- DEBUG: No session object is found.')
            return False
        
        #2. sitemap links can be found
        try:
            sitemap_links = BeautifulSoup(sitemap_object.text,self.parser).find_all('loc')
            if len(sitemap_links) <= 1:
                raise
            print('\n-- UNIT TEST: Passed. -- DEBUG: Links can be found on the BS object.')

        except Exception as e:
            print('\n-- UNIT TEST: Failed. -- DEBUG: No Links can be found.')
            return False
        
        #print('\n-- DEBUG: ',sitemap_links)
        
        #3. A random sitemap link can be accessed
        try:
            test_url = sitemap_links[choice(list(range(len(sitemap_links))))]
            
            test_url = self.restore_url_domain(test_url.get_text())
            
            if test_url.find(self.domain) == -1 and test_url.find('page') == -1:
                raise
            print('\n-- UNIT TEST: Passed. -- DEBUG: A valid sitemap page can be retrieved.') 
            print('\n\t-- The test url is ', test_url)
            #print('\n\t-- UNIT TEST: The link is {}'.format(selected_link))
        except Exception as e:
            print('\n-- UNIT TEST: Failed. -- DEBUG: No sitemap page cannot be accessed.')
            return False
        
        #4. check the file type to determine which web crawler it should use.
        try:
            page_content = self.get_sitemap_content(test_url)
            print('\n\t-- UNIT TEST: The sitemap is in format of ', self.check_sitemap_page_layout(test_url))
            soup = BeautifulSoup(page_content, self.parser)
            urls = soup.find_all('url')
            random_news_link = urls[choice(list(range(len(urls))))]
            if random_news_link != None:
                print('\n\t-- UNIT TEST: Passed. --',random_news_link.select('loc')[0].get_text() )
            else:
                print('\n\t-- UNIT TEST: Failed. -- DEBUG: Format of news link is unusual.')
        except Exception as e:
            print('\n-- UNIT TEST:', e)
            print('\n-- UNIT TEST: Failed. -- DEBUG: No sitemap page cannot be accessed.')
            return False        
        
        return True
    
    def get_sitemap_content(self, page_url):
        if self.check_sitemap_page_layout(page_url) == 'gz':
            page_content = gzip.open(urlopen(page_url),'rb').read()
        else:
            page_content = CONS.SESSION.get(page_url).text
            
        return page_content
    
    def gather_urls(self, save_to_cache = False):
        
        article_list, datetime_list, priority_list = [], [], []
        
        SITEMAP_LINKS = BeautifulSoup(CONS.SESSION.get(self.sitemap).text,self.parser).find_all('loc')
        
        SITEMAP_NUM_PAGES = len(SITEMAP_LINKS)
        
        START = max(0, math.floor(SITEMAP_NUM_PAGES/3))
        
        for sitemap_page in range(START*2, SITEMAP_NUM_PAGES):
            # get the page url for the sitemap page
            page_url = self.restore_url_domain(SITEMAP_LINKS[sitemap_page].get_text())
            
            # get the content of the sitemap page
            page_content = self.get_sitemap_content(page_url)
            
            soup = BeautifulSoup(page_content, self.parser) #Parse LXML file
        
            i = 0
            
            for url_element in tqdm(soup.find_all('url')):
                #1. get the link for the news articles
                try:
                    link = self.restore_url_domain(url_element.select('loc')[0].get_text())
                except:
                    print('\n-- No link was found, skip the link.')
                    i = i + 1
                    continue
                #2. get the datetime for the newslink else: scrape everything
                try:
                    _date = url_element.select('lastmod')[0].get_text()
                    _date = _date.split('T')[0] # get the news's date
                    _date = datetime.strptime(_date, '%Y-%m-%d')
                    _date = _date.date()
                except:
                    _date = self.end.date()
                if self.if_skip_link(link, _date):
                    i = i + 1
                    continue
                else:
                    self.no_records = self.no_records + 1
                    #print('\n-- DEBUG: No of record '+self.no_records,flush=True) 
                    article_list.append(link)
                    datetime_list.append(_date)
                    #priority_list.append(priority)
            
            print('\n--DEBUG',sitemap_page,'/',SITEMAP_NUM_PAGES,' sitepage has skipped:', i, 'of records.',end="\r", flush=True)

        if save_to_cache:
            with open(self.cache_path, 'w', encoding='utf-8') as cache_file:
                for link in article_list:
                    cache_file.write(link + '\n')
                print(f'Saved URLs into {self.cache_path}')
    
        return article_list
          
    def if_skip_link(self, link, link_date):
        link = link.lower()
        # if the link is the website domain
        if link == self.website: #Ignore front page aka (DEFAULT_WEBSITE)
            return True
        
        if link_date < self.begain.date() or link_date > self.end.date():
            return True
        
        for bs_category in CONS.BLACKLISTED_LINKS:
            if bs_category.lower() in link:
                return True
        
        return False

    '''
    desc  : make sure a sitemap url is always begun with its default website domain.
    input : an url for sitemap link 
    output: an url for sitemap link with default website
    '''
    def restore_url_domain(self, url):
        url_elements = url.replace('http://','').replace('https://','').split('/')
        if url_elements[0] == self.website:
            return url
        else:
            url_elements[0] = self.domain
            return 'https://'+'/'.join(url_elements)
        
    # determine if an sitemap is xml or other type of file    
    def check_sitemap_page_layout(self, url):
        end = url.split('.')[-1]
        if end.lower() == 'gz':
            return 'gz'
        else:
            return 'xml'
        
    def get_article_links(self):
        if CONS.USE_CACHE:
            if os.path.isfile(self.cache_path) and os.path.getsize(self.cache_path) > 0:
                print('\n-- DEBUG: Using URLs from cache file')
    
                with open(self.cache_path, 'r', encoding='utf-8') as cache_file:
                    self.article_list = [line.strip() for line in cache_file]
            else:
                print('\n-- DEBUG: Cache file does not exist... creating now')
                self.article_list = self.gather_urls(save_to_cache=True)
        else:
            self.article_list = self.gather_urls(save_to_cache=False)   
        print('\n-- DEBUG: Scraping article links completed')
        
