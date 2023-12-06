from Functions import *

import argparse

import warnings

from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
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
        self.object = object
        self.starting_page_url= object['starting_page_url']
        self.source_id = object['source_id']
        self.driver = self._selenium_init(headless=object['headless'],remote=object['remote'])
        self.links = []
        self.comments = []
        self.links_threshold = object['links_threshold']
        self.links_count = 0
        self.begin_dt = object['begin_datetime']
        self.end_dt = object['end_datetime']
        self.noOfDays = object['noOfDays']
        self.default_dt = datetime.now()
        self.existing_URLs = getExistingURLs(self.end_dt,noOfDays=self.noOfDays,sid=self.source_id)
        print(f'\n-- DEBUG: Existing urls are {len(self.existing_URLs)}')
        self._init_page()

    def _init_page(self):
        try:
            #self.driver.implicitly_wait(60)
            #self.bypass_ads(self.object['main_Xparam']['XP_CLOSE_ADS'])
            self.driver.get("https://b.cari.com.my/portal.php")
            self.bypass_ads(self.object['main_Xparam']['XP_CLOSE_ADS'])

            #self.bypass_ads(self.object['main_Xparam']['XP_CLOSE_ADS'])
            self.driver.get(str(self.starting_page_url))
            self.bypass_ads(self.object['main_Xparam']['XP_CLOSE_ADS'])
        except Exception as e:
            print('\n-- DEBUG: Driver initalisation error .')
            print('\n\t-- DEBUG: Error message is ',e)
            self.driver.get(str(self.starting_page_url))
            self.bypass_ads(self.object['main_Xparam']['XP_CLOSE_ADS'])

    def _selenium_init(self, headless=True, remote=True):
        _ROOT_DIR = os.path.join(os.path.dirname(os.path.join(os.path.dirname(__file__)))) #news_comments_crawlers
        _RES_PATH = _ROOT_DIR + '\selenium_crawlers\resources'
        
        #2023-11-21: initalise crawler option(s)
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--profile-directory=Default') 

        if headless:
            options.add_argument('--headless')
        
        #2023-11-21: disable notifications
        prefs = {"profile.default_content_setting_values.notifications" : 2}
        
        options.add_argument('--disable-notifications')
        options.add_experimental_option("prefs",prefs)
        options.add_experimental_option(
            "prefs", {"profile.managed_default_content_settings.images": 2}
        )

        #2023-12-06: disable image and video
        options.add_argument('--blink-settings=imagesEnabled=false')

        print('\n-- DEBUG: ROOT DIR - ', _ROOT_DIR)
        if not remote:
            print('\n-- DEBUG: Using local chrome driver .')
            try:
                chrome = ChromeDriverManager(path=_ROOT_DIR).install()
                service = Service(chrome)
                driver = webdriver.Chrome(service=service, options=options)
            except:
                print("\n-- DEBUG: Something wrong with auto-driver, using local copy instead.")
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
            #2023-11-21 increase the timeout to 5 seconds
            time.sleep(5)
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
                item['org_content'] = org_content
                if "cmt_url" in item.keys():
                    item['url'] = item['url'] + '|' + item['cmt_url']
                    del item['cmt_url']
                if "published_datetime" in item.keys() and item['published_datetime'] != '':
                    item['published_datetime'] = (item['published_datetime'].strftime("%Y-%m-%d %H:%M:%S"))
                else:
                    item['published_datetime'] = str(item['published_datetime'])
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
        if len(self.links) > 1:
            self._scrape_post_content(Xparam, collect_fn=_collect_art_fn)
        else:
            print(f'\n-- DEBUG: No new post will be added to the db. ')
        self.insert_to_db(label='post')

    def insert_to_db(self,label=''):
        items = self.links if label == 'post' else self.comments
        t_name = 'dsta_db.test' if label == 'post' else 'dsta_db.test_24hr_comments'
        for idx, item in enumerate(items):
            try:
                response = requests.post(INSERT_API,json={'table':t_name, 'data': item })
            except Exception as e:
                print(f'\n--DEBUG: 1 post is failed to be added {item["url"]}')
                print(e)

    def scrape_comments(self, Xparam):
        db_items = getExistingPostItems(self.end_dt,noOfDays=self.noOfDays,sid=self.source_id)

        for db_item in db_items:
            post_id, cmt_url = db_item['article_id'], db_item['URL'].split('|')[-1]
            _search_begin, SEARCHING = time.perf_counter(), True

            try:
                self.driver.get(cmt_url)
            except Exception as e:
                print(f'\n-- DEBUG: driver timeout with error {e} .')

            while SEARCHING: # Search for 1 post
                wait = WebDriverWait(self.driver, Xparam['wait'])
                page_loaded = wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                print(f"\n-- DEBUG: Page loaded successfully! Searching comments for post {post_id}",end='\r')

                self.bypass_ads(Xparam['XP_CLOSE_ADS'],i=1)  #close pop-up ads
                cmt_items = getPostListings(self.driver, Xparam['XP_CMT_LISTING'])
                print(f'\n-- DEBUG: Total {len(cmt_items)} no. of elements on the table .')
                
                cmts_for_one_post, mapping = [], dict()

                #3. loop and get each post item from the table
                for item in cmt_items:
                    try:
                        cmt_id = item.get_property('id') #1. cmt id
                    except Exception as e:
                        cmt_id = ''
                    # cmt text
                    try:
                        cmt_org_content_node = item.find_element("xpath", Xparam['XP_CMT_CONTENT'])
                        cmt_to_del = cmt_org_content_node.find_elements("xpath", Xparam['XP_CMT_DEL'])
                        cmt_org_content_text = cmt_org_content_node.text

                        for to_del in cmt_to_del:
                            cmt_org_content_text = re.sub(to_del.text, '', cmt_org_content_text)

                        cmt_org_content_text = re.sub('\s+', ' ', cmt_org_content_text) #remove additional white spaces
                        cmt_org_head = cmt_org_content_text[:100] if len(cmt_org_content_text) >= 100 else cmt_org_content_text

                        mapping[cmt_org_head] = cmt_id

                    except Exception as e:
                        cmt_org_content_text = ''

                    # cmt reply_to
                    try:
                        cmt_reply_to_ = item.find_element("xpath", Xparam['XP_CMT_REPLY_TO']).text
                        cmt_reply_to = (' '.join(cmt_reply_to_.split('\n')[1:])).strip()
                        cmt_reply_to = re.sub('\s+', ' ', cmt_reply_to)  #remove additional white spaces

                        cmt_reply_to = cmt_reply_to[:100] if len(cmt_reply_to) >=100 else cmt_reply_to
                        cmt_reply_to = mapping.get(cmt_reply_to,'')
                    except Exception as e:
                        cmt_reply_to = ''

                    # cmt user
                    try:
                        cmt_user = item.find_element("xpath",Xparam['XP_CMT_USER'] ).text
                    except Exception as e:
                        cmt_user = ''
                    
                    # cmt published datetime
                    try:
                        cmt_published_datetime = item.find_element("xpath", Xparam['XP_CMT_DATETIME']).text
                        cmt_published_datetime = (re.sub('Post time\s*', '', cmt_published_datetime)).strip()
                        cmt_published_datetime = pd.to_datetime(cmt_published_datetime, format=Xparam['CMT_DATETIME_FMT'], errors='ignore')
                    except Exception as e:
                        cmt_published_datetime = ''
                    
                    if cmt_published_datetime != '' and cmt_published_datetime >= self.begin_dt:
                        cmt_published_datetime = (cmt_published_datetime.strftime("%Y-%m-%d %H:%M:%S"))
                        cmts_for_one_post.append({
                                    "cmt_id": cmt_id,
                                    "cmt_org_content": cmt_org_content_text,
                                    "cmt_published_datetime": cmt_published_datetime,
                                    "cmt_replyTo": cmt_reply_to,
                                    "cmt_user" : cmt_user,
                                    'cmt_article_id': post_id,
                                    "lang" : 'BM',
                                    "translated": 0,
                                    "source_id": self.source_id
                                })

                #4. update the item accordingly
                _end_search = time.perf_counter()
                if _end_search - _search_begin > 180:
                    SEARCHING = False
                    continue
                try:
                    #self.bypass_ads(Xparam['XP_CLOSE_ADS'])
                    goNextPage(self.driver, Xparam['XP_CMT_NEXT']) 
                except Exception as e:
                    #print('\nDEBUG: An error occur has occured clicking next page.')
                    SEARCHING = False
                    continue
                self.bypass_ads(Xparam['XP_CLOSE_ADS'])
            
            # remove duplicates and existing cmt_items
            # Convert the list of dictionaries to a DataFrame
            cmt_ids = getCommentIDsByArticleID(art_id=post_id, table='dsta_db.test_24hr_comments')
            cmts_for_one_post = remove_duplicates_comments(cmts_for_one_post, existing_ids=cmt_ids)
            print(f'\n-- DEBUG: {len(cmts_for_one_post)} no. of comments will be added to post {post_id}')
            self.comments.extend(cmts_for_one_post)
            print(f'\n\t--DEBUG: Total scrape {len(self.comments)} comments for the post')
        
        self.insert_to_db(label='comments')

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
        if (item[dt_label]=="" or isinstance(item[dt_label], str) or item[dt_label] < self.begin_dt or item[dt_label] > self.end_dt):
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
        lines = org_content.split('\n') # Split the content into lines   
        lines = lines[4:] if len(lines) > 4 else lines #
        org_content = '\n'.join(lines)

    except Exception as e:
        org_content = ''

    return org_content


parser = argparse.ArgumentParser(description="Parameters to execute a web crawler")

parser.add_argument(
        '--remote',
        type=str,
        help="True if running on docker else False",
        required=True
)

parser.add_argument(
        '--headless',
        type=str,
        help="True if running on docker else False",
        required=True
)
    
if __name__ == '__main__':
    args = parser.parse_args()

    remote = eval(args.remote)

    headless = eval(args.headless)

    B_CARI_object = {
        'starting_page_url': "https://b.cari.com.my/forum.php?mod=forumdisplay&fid=154",
        'source_id': 17,
        'lang': 'BM',
        'links_threshold':50,
        'begin_datetime': last24hours,
        'end_datetime': now,
        'headless':headless,
        'remote': remote,
        'noOfDays':4,
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
        },
        'cmt_Xparam':{
            'wait': 5,
            'XP_CLOSE_ADS': ["//div[contains(@class,'button-common close-button')]//span", 
                            "//div[contains(@class, 'iz_osn_card_1')]//span[contains(@class, 'close')]", 
                            "//div[contains(@id, 'dismiss-button')]/div",
                            "//div[contains(@id, 'innity_adslot_')]//a[contains(@id, 'iz_osn_close_1')]"],
            'XP_CMT_LISTING': "//tbody/tr/td/div[contains(@id, 'postlist')]/div[not(@class)]",
            'XP_CMT_ID': "",
            'XP_CMT_DATETIME':  ".//descendant-or-self::div[@class='pti']/div[contains(@class,'authi')]/em",
            'XP_CMT_CONTENT': " .//descendant-or-self::div[contains(@class, 't_fsz')]/table/tbody/tr/td",
            'XP_CMT_REPLY_TO': " .//descendant-or-self::div[contains(@class, 't_fsz')]/table/tbody/tr/td//blockquote",
            'XP_CMT_USER' :".//descendant-or-self::div[@class='pi']/div[contains(@class,'authi')]",
            'XP_CMT_NEXT' : "//div[contains(@id, 'pgt')]//div[contains(@class,'pg')]/a[text()='Next']",
            'XP_CMT_DEL': ".//descendant-or-self::font[(ancestor::blockquote)]",
            'CMT_DATETIME_FMT': "%d-%m-%Y %I:%M %p"

        }
    }

    start_time = time.perf_counter()
    
    B_CARI = ForumWebCrawler(B_CARI_object)

    B_CARI.scrape_post(B_CARI_object['main_Xparam'], url_col_fn=_collect_url_fn, p_content_col_fn=_collect_art_fn)

    B_CARI.scrape_comments(B_CARI_object['cmt_Xparam'])

    end_time = time.perf_counter()

    print(f'\n-- DEBUG: Used time {start_time - end_time}')