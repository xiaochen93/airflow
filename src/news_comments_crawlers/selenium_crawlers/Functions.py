from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium import webdriver    
import time
import pandas as pd
import re
import collections
import nltk
from nltk import word_tokenize, Text, FreqDist
from nltk.corpus import wordnet as wn
from nltk.corpus import PlaintextCorpusReader
from nltk.corpus import stopwords
import pathlib
from newspaper import Article
from urllib.parse import urlparse
# importing itertools for accumulate()
import itertools
# importing functools for reduce()
import functools
from tqdm.notebook import tqdm_notebook
import json
import praw
import seaborn as sns
import requests
from bs4 import BeautifulSoup
import os
import concurrent.futures
import time
from tqdm import tqdm
import gc
from nltk.corpus import stopwords
import pickle
from datetime import datetime
from urllib.parse import urlparse
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime

stop_words = set(stopwords.words('english'))
wnl = nltk.WordNetLemmatizer()

tests_extract_domain = [
    'https://www.independent.co.uk/news/singapore-malaysia-kuala-lumpur-facebook-lawyers-b2017147.html',
    'https://independent.co.uk/news/singapore-malaysia-kuala-lumpur-facebook-lawyers-b2017147.html'
]

INSERT_API = 'http://10.2.56.213:8086/insert'

PING_API = 'http://10.2.56.213:8086/ping'

QUERY_API = 'http://10.2.56.213:8086/query'

def extract_domain(url):
    #pattern = r'(?<=\/|\.)(\w+)(?=\.)'
    pattern = r'(www\.|\..+\b)'
    url = urlparse(url).netloc
    domain = re.sub(pattern,'',url)
    if domain == 'sg':
        domain = 'Yahoo'
    return domain

def preprocess(text):
    text = re.sub("[\(\[].*?[\)\]]", "", text)
    text = re.sub('([.,!?()])', r' \1 ', text) # padding
    text = re.sub('\s{2,}', ' ', text) # padding
    text = text.lower()
    text = re.sub(r'[^\w\s]','', text) 
    word_list = word_tokenize(text)
    stem_text = [lemmatizer.lemmatize(text) for text in word_list if not text.isdigit() if not text.lower() in stop_words]
    final_text = " ".join(stem_text)
    
    return final_text.strip()

def drop_na(df):
    df = df.applymap(lambda x: np.nan if x=="" else x)
    na_num = max(df.isnull().sum())
    if na_num == 0:
        print('\n-- No records contains null value, passed')  
    else:
        print('\n-- {} records have been dropped due to null values'.format(na_num))
        plt.figure(figsize=(15,5))
        sns.heatmap(df.isna().transpose(),
                    cmap="YlGnBu",
                    cbar_kws={'label': 'Missing Data'})
        #plt.savefig("visualizing_missing_data_with_heatmap_Seaborn_Python.png", dpi=100)     
        df.dropna(inplace=True)
        df.isnull().sum()
    return df

def generate_wc(title, path, words):
    #color_list=['#050505','#393939','#757474']
    #colormap=colors.ListedColormap(color_list)
    wc = WordCloud(  
        background_color='white',       
        max_words=100, 
        colormap='twilight', 
        max_font_size=1000
        #random_state=1
        #font_path = 'Times New Roman'
    )
    #print(words)
    wordcloud = wc.generate_from_frequencies(words)
    plt.figure(figsize=(20, 15))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.title(title,fontsize=15)
    #plt.savefig('{}/wc-{}.png'.format(path,title[:12].replace('.','')))
    
def plot_bars(counts,words,title,path):
    font_size = 15
    fig, ax = plt.subplots(figsize=(15, 5))
    bars = ax.bar(counts, words,color=(0.2, 0.4, 0.6, 0.6),align='center', width=0.8)
    
    ax.set_title(title, fontsize=font_size,pad=50)
    ax.title.set_color("Black")
    ax.set_ylabel('TF', fontsize=font_size)
    
    ax.yaxis.set_ticks_position('left')
    ax.xaxis.set_ticks_position('bottom')
    
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    
    for rect in bars:
        height = rect.get_height()
        ax.text(rect.get_x() + rect.get_width()/2., 1.05*height,
            int(height),
        ha='center', va='bottom',fontsize=round(font_size*0.8))
    
    ax.tick_params(axis='x', labelsize=font_size*1.2)
    ax.tick_params(axis='y', labelsize=font_size*1.2)
    
    plt.xticks(rotation=90)
    leg = ax.legend()
    plt.show()
    fig.set_size_inches((15, 15), forward=False)
    #fig.savefig('{}/{}.png'.format(path,title[:12].replace('.','')))
    
def plotFreqDistByGroup(df, name = 'domain',group_label = None, freq_label= None):
    y_values,x_labels = list(), list()
    for x_label, y_count in df.groupby(group_label)[freq_label].count().items():
        y_values.append(y_count)
        x_labels.append(x_label)
    plot_bars(x_labels,y_values,'Total no of {} by {} on {}'.format(freq_label,group_label,name),'')


'''

Input : Xpath for the dropdown list 
Output: Xpath for the choices in the dropdown

'''

def getNewsContentByArticle(Article, url):
    # get content 
    try:
        content = Article(url)
        content.download()
        content.parse()
        content = content.text
    except Exception as e:
        print(e)
        content = ""
    return content

def getNewsContentByGoogle(title):
    
    from googlesearch import search

    query = "news:" + title
 
    content, domain, url = "", "", ""
    
    count = 0
    
    try:
        for j in search(query, num_results=10, unique=True):
            url = j

            domain = urlparse(j).netloc
            
            content = getNewsContentByArticle(Article,j)

            count = count + 1

            if not content != "" or count > 10:
                break    
            time.sleep(1)
    except:
        pass
    
    return {'content':content, 'domain':domain,'url':url}
        

def getPostListings(driver, xpath_items):
    try:
        items = driver.find_elements("xpath", xpath_items)
    except Exception as e:
        print('\n Empty post listing due to ',e)
        items = []
        pass
    return items

def getTableItems(driver, xpath_items):
    try:
        items = driver.find_elements("xpath", xpath_items)
    except Exception as e:
        items = []
        print(e)
        pass
    return items

def getDropdownChoices(driver, xpath_dropdown, xpath_choices):
    # Wait for initialize, in seconds
    wait = WebDriverWait(driver, 10)

    dropdown = wait.until(EC.visibility_of_element_located((By.XPATH, xpath_dropdown)))
    
    time.sleep(1)
    
    dropdown.click()
    
    #2. find the choices on the list
    try:
        dropdown = driver.find_elements("xpath",xpath_choices)
    except ElementClickInterceptedException:
        print('\n-- No dropdown list found --')
        pass
    
    return dropdown

def getChildElement(node, xpath):
    xpath = ".//descendant-or-self::" + xpath
    
    try:
        child_node = node.find_element("xpath", xpath)
    except NoSuchElementException:
        print("\n-- Unable to find the child element")
        raise
        
    return child_node

def clickMany(driver,lst_xpath):
    for each in lst_xpath:
        clickOne(driver, each)

def clickOne(driver, xpath):
    try:
        expanders = driver.find_elements("xpath", xpath)
        for each in expanders:
            each.click()
    except:
        pass

def clickToGo(driver, xpath):
    try:
        button = driver.find_element("xpath",xpath)
        button.click()
        time.sleep(1)
    except:
        #print('\n-- No element {} found --'.format(xpath))
        raise

def goNextPage(driver, xpath):
    try:
        button = driver.find_element("xpath",xpath)
        button.click()
        time.sleep(1)
    except:
        #print('\n-- No element {} found --'.format(xpath))
        raise

def selenium_init(headless=True, remote=True, strict=True):
    _ROOT_DIR = os.path.join(os.path.dirname(os.path.join(os.path.dirname(__file__)))) #news_comments_crawlers
    _RES_PATH = _ROOT_DIR + '\selenium_crawlers\resources'
    
    #2023-11-21: initalise crawler option(s)
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--profile-directory=Default')

    #2024-02-08 disable images
    options.add_argument('--blink-settings=imagesEnabled=false')

    if headless:
        options.add_argument('--headless')
    
    #2023-11-21: disable notifications
    prefs = {"profile.default_content_setting_values.notifications" : 2}
    options.add_argument('--disable-notifications')
    options.add_experimental_option("prefs",prefs)
    #2024-02-08: disable images
    options.add_experimental_option(
    "prefs", {"profile.managed_default_content_settings.images": 2}
)

    print('\n-- DEBUG: ROOT DIR - ', _ROOT_DIR)
    if not remote:
        print('\n-- DEBUG: Using local chrome driver .')
        try:
            chrome = ChromeDriverManager(path=_ROOT_DIR).install()
            service = Service(chrome)
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            print("\n-- DEBUG: Something wrong with auto-driver, using local copy instead.")
            print(e)
            driver = webdriver.Chrome()
    else:
        print('\n-- DEBUG: Using remote chrome driver, make sure docker standalone browser is on .')
        try:
            name = "remote_chromedriver"
            driver = webdriver.Remote(command_executor=f"http://{name}:4444",options=options)
        except Exception as e:
            print("\n-- DEBUG: Driver error -", e)
            raise
    
    #2023-11-21: adding page timeout to 300 seconds
    driver.set_page_load_timeout(300)

    return driver

def getWebElementAttribute(item, xpath, name, label=""):
    try:
        text = item.find_element("xpath", xpath).get_property(name)
    except Exception as e:
        print(f'\n-- DEBUG: No element is found for label {label}.')
        text = ''
    return text

def getWebElementText(item, xpath, label=""):
    try:
        text = item.find_element("xpath", xpath).text
    except Exception as e:
        print(f'\n-- DEBUG: No element is found for label {label}.')
        text = ''
    return text

def check_spams(text):
    digit_pattern = r'\d'  # Regular expression pattern for a digit
    digit_count = len(re.findall(digit_pattern, text))
    
    return digit_count >= 6

def save_pickle_object(obj, filename):
    with open(filename, 'wb') as outp:  # Overwrites any existing file.
        pickle.dump(obj, outp, pickle.HIGHEST_PROTOCOL)

def load_pickle_object(file_path):
    with open(file_path, "rb") as input_file:
        data = pickle.load(input_file)
        return data
    
def write_csv(data):
    # Write data to the CSV file one row at a time
    writer = csv.writer(open("data.csv", "w"))
    for row in data:
        writer.writerow(str(row))
        yield ','.join(str(row)) + '\n' 

def check_API_conn(PING_API):
    ping_response = requests.get(PING_API)
    if ping_response.status_code == 200:
        data = ping_response.json()
        message = data["message"]
        print(f"\n-- DEBUG: API is alive. Message: {message}")
    else:
        print("\n-- DEBUG: Failed to reach the API")

def get_datetime(days=1, hours=1):
    from datetime import datetime
    today = datetime.now().replace(microsecond=0)
    import datetime
    one_day = datetime.timedelta(days=days)
    one_hour = datetime.timedelta(hours=hours)
    last24hours = today - one_day - one_hour
    return today, last24hours

def execute_query(QUERY_API, query=''):
    try:
        response = requests.post(QUERY_API, json={'query':query})
        json_payload = (json.loads(response.text))
        items = json_payload['result']  

    except Exception as e:
        print(f'\n\t-- DEBUG: execute_query with error - {e} Probablly no existing records found with the id given ?')
        items = []

    return items


# get the existing comments by post id
def getCommentIDsByArticleID(art_id='', table=''):
    query = f'SELECT cmt_id FROM {table} WHERE cmt_article_id={art_id}' + ';'

    out_items = execute_query(QUERY_API,query=query)

    if len(out_items) == 0:
        print(f"\n\t-- DEBUG: no existing comments found under the article id. ")

    return out_items

# get the existing URLs from the DB
def getExistingURLs(today, type='comments', noOfDays=6, QUERY_API=QUERY_API, table='dsta_db.test', pid='article_id', dt_label='published_datetime',URL_label='URL', sid=None):
    from datetime import timedelta
    items, one_day=[pid, 'source_id', 'URL'], timedelta(days=1)
    query = f"SELECT {', '.join(items)} FROM {table} WHERE ({dt_label} <= '{today.date() + one_day}' AND {dt_label} >= '{today.date() + one_day}' - INTERVAL {noOfDays} DAY) AND source_id={sid} AND deleted=0;"
    out_items = fetch_db_response(query)
    if out_items != []:
        URL_index = -1 if type == 'comments' else 0
        URLs = set([item['URL'].split('|')[URL_index] for item in out_items])
    else:
        URLs = []
    return URLs

def getExistingPostItems(today, type='comments', noOfDays=6, QUERY_API=QUERY_API, table='dsta_db.test', pid='article_id', dt_label='published_datetime',URL_label='URL', sid=None):
    from datetime import timedelta
    items, one_day=[pid, 'source_id', 'URL'], timedelta(days=1)
    query = f"SELECT {', '.join(items)} FROM {table} WHERE ({dt_label} <= '{today.date() + one_day}' AND {dt_label} >= '{today.date() + one_day}' - INTERVAL {noOfDays} DAY) AND source_id={sid} AND deleted=0;"
    out_items = fetch_db_response(query) # remove duplicate and size
    return out_items    

def remove_duplicates_comments(cmts_for_one_post,existing_ids=[]):
    temp_df = pd.DataFrame(cmts_for_one_post)
    temp_df = temp_df.drop_duplicates()

    if 'cmt_id' in temp_df.columns and (existing_ids != [] or existing_ids != None):
        temp_df = temp_df[~temp_df['cmt_id'].isin(existing_ids)]

    non_duplicates = temp_df.to_dict('records')

    return non_duplicates

def remove_duplicated_comments_by_ids(cmt_ids=set(), comments_this_post=[]):
    comments_this_post = [each for each in comments_this_post if not str(each['cmt_id']) in cmt_ids]
    return comments_this_post

def fetch_db_response(query):
    try:
        response = requests.post(QUERY_API, json={'query':query})
        json_payload = (json.loads(response.text))
        out = json_payload['result']
    except Exception as e:
        print(f'\n-- DEBUG: Request error occurs {e}, return [] object .')
        out = []
    return out

def select_existing_items(QUERY_API, today, pre_datetime, source_id, table='dsta_db.test',dt='published_datetime', items=['article_id, URL']):
    try:
        from datetime import timedelta
        one_day = timedelta(days=1)
        # datetime <= todaty.date() + one day -> here onwards
        # datetime >= today.date() + n days -> posted before No.of days.
        query = f"SELECT {', '.join(items)} FROM {table} WHERE ({dt} <= '{today.date() + one_day}' AND {dt} >= '{today.date() + one_day}' - INTERVAL {6} DAY) AND source_id={source_id} AND deleted=0;"
        print(f"\n\t-- DEBUG: query - {query}")
        response = requests.post(QUERY_API, json={'query':query})
        json_payload = (json.loads(response.text))
        out = json_payload['result'] 
    
    except Exception as e:
        print(f'\n\t-- DEBUG: error message - {e}.')
        response = requests.post(QUERY_API, json={'query':query})
        print(f"\n\t-- DEBUG: error message from API {response.text}")
        print(f"\n\t-- DEBUG: returning empty list instead.")
        out = []

    return out