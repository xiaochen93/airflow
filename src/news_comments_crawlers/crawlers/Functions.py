import os
import concurrent.futures
from tqdm import tqdm
import gc
import json
import pickle

def c_determine_to_skip(CONS, link, link_date):
    link = link.lower()
    # if the link is the website domain
    if link == CONS.WEBSITE: #Ignore front page aka (DEFAULT_WEBSITE)
        return True
    
    if link_date < CONS.BEGIN_FROM or link_date > CONS.END_AT:
        return True
    
    for bs_category in CONS.BLACKLISTED_LINKS:
        if bs_category.lower() in link:
            return True
    
    return False

def c_restore_url(CONS, url):
    url_elements = url.replace('http://','').replace('https://','').split('/')
    if url_elements[0] == CONS.WEBSITE:
        return url
    else:
        url_elements[0] = CONS.DOMAIN
        return 'https://'+'/'.join(url_elements)
    
def c_scrape_links(USE_CACHE, CACHE_FILEPATH, gather_urls):
    print(f'\n--DEBUG: {USE_CACHE}')
    article_list = []
    if USE_CACHE:
        if os.path.isfile(CACHE_FILEPATH) and os.path.getsize(CACHE_FILEPATH) > 0:
            print('\n--DEBUG: Using URLs from cache file')

            with open(CACHE_FILEPATH, 'r', encoding='utf-8') as cache_file:
                article_list = [line.strip() for line in cache_file]
        else:
            print('\n--DEBUG: Links file does not exist... creating now')
            article_list = gather_urls(save_to_cache=True)
    else:
        print('\n--DEBUG: New scraping request for links.') 
        article_list = gather_urls(save_to_cache=False)
    
    return article_list

def c_scrape_articles(USE_CACHE, JSON_PATH, obj):
    if USE_CACHE:
        if os.path.isfile(JSON_PATH) and os.path.getsize(JSON_PATH) > 0:
            print('\n--DEBUG: Using Articles from cache file')
            with open(JSON_PATH, encoding='utf-8') as JSON_FILE:
                #print(JSON_PATH)
                json_data = json.load(JSON_FILE,  strict=False)
        else:
            print('\n-- DEBUG: Articles does not exist... creating now')
            json_data = _scrape_articles_linear(data=obj['data'], param=obj['param'],func=obj['func'])
    
    else:
            print('\n--DEBUG: New scraping request for articles.') 
            json_data = _scrape_articles_linear(data=obj['data'], param=obj['param'],func=obj['func'])
   
       #save the raw json file
    with open(JSON_PATH, 'w', encoding='utf-8') as output_file:
        json.dump(json_data , output_file ,indent = 2, ensure_ascii=False, default=str) 
   
    return json_data

def _scrape_articles_linear(data=[], param={},func=None):
    results = []
    for each in data:
        article = func(each, param)
        results.append(article)
    
    return results

def _scrape_articles_concurrent(data=[], param={},func=None):
    
    NUM_URLS_TO_SCRAPE = -1
    
    if NUM_URLS_TO_SCRAPE != -1:
        data = data[:NUM_URLS_TO_SCRAPE]    
    
    results = []
    
    size = len(data)
    
    param = [param for i in range(size)]
    
    with concurrent.futures.ProcessPoolExecutor() as executor: 
       for out_dict in tqdm(executor.map(func, data, param), total=size):
           results.append(out_dict)

    gc.collect() #?
    
    return results
     
def save_pickle_object(obj, filename):
    with open(filename, 'wb') as outp:  # Overwrites any existing file.
        pickle.dump(obj, outp, pickle.HIGHEST_PROTOCOL)
