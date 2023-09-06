from Functions import *

import argparse

import warnings

from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

warnings.filterwarnings("ignore")

now, last24hours=get_datetime()

INSERT_API = 'http://10.2.56.213:8086/insert'

PING_API = 'http://10.2.56.213:8086/ping'

QUERY_API = 'http://10.2.56.213:8086/query'

table = 'dsta_db.test'

latest=True

SEARCHING = True

'''
The forum object follows the sequence of 
1. initalization -> 2. additional step clearance (to URL items) -> 3. scrape URL items -> 4. additional step clearance -> 5. scrape content

'''
class ForumWebCrawler:
    def __init__(self, object):
        self.starting_page_url= object['starting_page_url']
        self.source_id = object['source_id']
        self.driver = selenium_init(headless=False,remote=False)
        self.driver.get(self.starting_page_url)
        self.links = []
        self.comments = []
        self.links_threshold = object['links_threshold']
        self.links_count = 0
        self.begin_dt = object['begin_datetime']
        self.end_dt = object['end_datetime']
        self.default_dt = datetime.now()
        self.existing_URLs = getExistingURLs(self.end_dt,sid=17)
        print(f'\n-- DEBUG: Existing urls are {self.existing_URLs}')

    '''
    Input: 
        Xparam: contains xpath(s) for scrapping post on forum
            wait: the time interval which awaits the page to be completely loaded
            XP_CLOSE_ADS: the xpath(s) for close Ads button, multiple items clickable
            XP_POST_LISTING: the xpath for post listing on a page
            XP_POST_NEXT_BTN: the xpath for next button on the page, single clickable

        map_fn: mapping function to return a scrapped item
    
    '''
    def _scrape_post_url(self, Xparam, collect_fn=lambda x: x):
        SEARCHING = True
        while SEARCHING:
            _search_begin = time.perf_counter()
            # check if the page is loaded 
            wait = WebDriverWait(self.driver, Xparam['wait'])
            page_loaded = wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            while not page_loaded:
                print('Page is not loaded, ')
            print("\n-- DEBUG: Page loaded successfully!",end='\r')
            #1. close pop-up ads
            self.bypass_ads(Xparam['XP_CLOSE_ADS'],i=1)

            post_items = getPostListings(self.driver, Xparam['XP_POST_LISTING'])
            print(f'\n-- DEBUG: Total {len(post_items)} no. of elements on the table .')
            #3. loop and get each post item from the table
            many_posts = [collect_fn(post, Xparam) for post in post_items]
            #4. update the item accordingly
            for post in many_posts:
                self.update_links(post)
            
            if self.links_count > self.links_threshold:
                SEARCHING = False
                continue

            try:
                self.bypass_ads(Xparam['XP_CLOSE_ADS'])
                goNextPage(self.driver, Xparam['XP_POST_NEXT_BTN']) 
                #clickMany(self.driver, Xparam['XP_CLOSE_ADS'])
            except Exception as e:
                print('\nDEBUG: An error occur has occured .')
                time.sleep(Xparam['wait']) #give program a pause to reset
            
            time.sleep(1)
            self.bypass_ads(Xparam['XP_CLOSE_ADS'])

    '''
    Input: 
        Xparam: The dictionary as above, containing the xpath for post elements.

        map_fn: mapping function to return a scrapped article/original post in its original language. 
                The output is '' by default.
    
    '''
    def _scrape_post_content(self, Xparam, collect_fn=lambda x: x):
        del_idxes = []
        for idx, item in enumerate(self.links):
            # get the original article_content
            org_content = collect_fn(driver=self.driver, xpath_content=Xparam['XP_POST_ART'], url=item['url'])
            
            if (org_content == '' or len(org_content) < 20 or org_content is None):
                del_idxes.append(idx)
            else:
                # Split the content into lines
                lines = org_content.split('\n')
                # Remove the first four lines (noise)
                lines = lines[4:]
                # Join the remaining lines back together
                org_content = '\n'.join(lines)
                item['org_content'] = org_content
                if "cmt_url" in item.keys():
                    item['url'] = item['url'] + '|' + item['cmt_url']
                    del item['cmt_url']
                if "published_datetime" in item.keys() and item['published_datetime'] != '':
                    item['published_datetime'] = item['published_datetime'].strftime("%Y-%m-%d %H:%M:%S")
                item['translated'] = 0
                item['lang'] = "BM"
                item['source_id'] = self.source_id

                self.links[idx] = item
        
        # delete the post item with empty content
        for del_idx in del_idxes:
            self.links.pop(del_idx)

    def scrape_post(self, Xparam, url_col_fn=lambda x: x, p_content_col_fn=lambda x: x):
        self._scrape_post_url(Xparam, collect_fn=_collect_url_fn)
        print(f'\n-- DEBUG: total no. of {len(self.links)} links has been collected. ')
        self._scrape_post_content(Xparam, collect_fn=_collect_art_fn)

    def insert_to_db(self,label=''):
        items = self.links if label == 'post' else self.comments

        for idx, item in enumerate(self.links):
            try:
                response = requests.post(INSERT_API,json={'table':'dsta_db.test', 'data': item })
            except Exception as e:
                print(f'\n--DEBUG: 1 post is failed to be added {item["url"]}')
                print(e)

    def bypass_ads(self,XP_ads,i=5):
        time.sleep(1)
        self.driver.execute_script("""
        const elements = document.getElementsByClassName("google-auto-placed");
        while (elements.length > 0) elements[0].remove();
                            """)

        time.sleep(1)
        self.driver.execute_script("""
        const elements = document.getElementsByClassName("adsbygoogle adsbygoogle-noablate");
        while (elements.length > 0) elements[0].remove();
                            """)

        while i > 0 and XP_ads != []:
            clickMany(self.driver, XP_ads)
            time.sleep(0.5)  
            i = i - 1

    def update_links(self, item, dt_label='published_datetime'):
        #print(item[dt_label], self.begin_dt, self.end_dt, (item[dt_label] < self.begin_dt or item[dt_label] > self.end_dt))
        if (item[dt_label]=="" or item[dt_label] < self.begin_dt or item[dt_label] > self.end_dt):
            self.links_count = self.links_count + 1 #accumulate  
        elif check_spams(item['org_title']): # the title of a post/article is mandatory.
            pass #do nothing
        elif item['url']=='' or (item['url'] in self.existing_URLs): # url already exists or empty
            pass
        else:
            self.links.append(item)

# customized function for collecting post url
def _collect_url_fn(post, Xparam):

    post_title = getWebElementText(post, Xparam['XP_POST_TITLE'])

    post_cate = getWebElementText(post, Xparam['XP_POST_CATE'])

    post_url = getWebElementAttribute(post, Xparam['XP_POST_URL'], "href")

    try:
        post_datetime = pd.to_datetime(getWebElementText(post, Xparam['XP_POST_DATETIME']), format=Xparam['POST_DATETIME_FMT'], errors='ignore')
    except:
        post_datetime = ''

    return {
        'category': post_cate,
        'url': post_url,
        'org_title': post_title,
        'published_datetime':post_datetime,
    }

# customized function for collecting news articles
def _collect_art_fn(driver=None, xpath_content='', url=''):
    driver.get(str(url))
    try:
        org_content = str(driver.find_element("xpath", xpath_content).text)
    except Exception as e:
        org_content = ''

    return org_content
    
B_CARI_object = {
    'starting_page_url': "https://b.cari.com.my/forum.php?mod=forumdisplay&fid=154&page=1",
    'source_id': 17,
    'lang': 'BM',
    'links_threshold':10,
    'begin_datetime': last24hours,
    'end_datetime': now,
    'main_Xparam':{
        'wait': 8,
        #'XP_CLOSE_ADS': "//div[contains(@id, 'innity_adslot_')]//a[contains(@id, 'iz_osn_close_1')]",
        'XP_CLOSE_ADS': ["//div[contains(@class,'button-common close-button')]//span", 
                         "//div[contains(@class, 'iz_osn_card_1')]//span[contains(@class, 'close')]", 
                         "//div[contains(@id, 'dismiss-button')]/div",
                         "//div[contains(@id, 'innity_adslot_')]//a[contains(@id, 'iz_osn_close_1')]"],
        'XP_POST_LISTING': "//table[contains(@id, 'threadlisttableid')]//tbody[contains(@id, 'normalthread')]",
        'XP_POST_NEXT_BTN': "//div[contains(@id, 'pgt')]//div[contains(@class,'pg')]/a[text()='Next']",
        'XP_POST_URL': ".//descendant-or-self::tr//th//a[contains(@class, 's xst')]",
        'XP_POST_TITLE': ".//descendant-or-self::tr//th//a[contains(@class, 's xst')]",
        'XP_POST_DATETIME': ".//descendant-or-self::tr//th//font//span",
        'XP_POST_CATE': ".//descendant-or-self::tr//th//div[contains(@class, 'fd_list_main')]//em",
        'XP_POST_ART': "//div[@id = 'postlist']//div[not(contains(@id, 'post_rate_div')) and contains(@id,  'post_')][1]",
        'POST_DATETIME_FMT': "%d-%m-%Y %I:%M %p"
    }
}

if __name__ == '__main__':
    B_CARI = ForumWebCrawler(B_CARI_object)

    B_CARI.scrape_post(B_CARI_object['main_Xparam'], url_col_fn=_collect_url_fn, p_content_col_fn=_collect_art_fn)

    B_CARI.insert_to_db(label='post')

    #for each in B_CARI.links:
        #print('\n-- DEBUG: ',each)