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
from ForumTargetObject import ForumWebCrawler

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

class B_CARI_Crawler(ForumWebCrawler):

    def __init__(self, required_parameter):
        # Call the superclass' __init__ method to initialize the attribute
        super().__init__(required_parameter)
        #2024-03-12: no need to check existing URLs
        self.existing_URLs = []
        #2024-03-12: no need to check existing URLs
        #print(f'\n-- DEBUG: Existing urls are {len(self.existing_URLs)}')
        #print(f'\n-- DEBUG: Date range is from {self.begin_dt} to {self.end_dt}.')
        #print(f'\n\t-- DEBUG: We are looking at {self.noOfDays} no.of days for accumlating comments.')
        
    def scrape_comments(self):

        #test_url = "https://www.kaskus.co.id/thread/65a5ff757231b47a32216a30/survei-galidata-ganjar-mahfud-pimpin-elektabilitas-pilpres-2024"
        #posts_in_db = getExistingPostItems(self.end_dt,noOfDays=self.noOfDays,sid=self.source_id)
        posts_in_db = self._fetchPostByTimeRange(table="test", dt_label="published_datetime", lang='CN', end_datetime=self.end_dt, begain_datetime=self.begin_dt, sid=self.source_id)

        for post_item in posts_in_db:
            url, post_id = post_item['URL'].split('|')[-1], post_item['article_id']
            comments_this_post = self._test_scrape_cmt_workflow(url,self.driver, self.object['cmt_Xparam'], post_id)
            
            #2024-03-14: change the sequence for updating post(s)
            print(f'\n\t-- DEBUG: Total has scraped {len(comments_this_post)} comments for the post')
            comments_this_post = [self._test_cmt_item_processing(item, post_id=post_id) for item in comments_this_post]
            cmt_ids = getCommentIDsByArticleID(art_id=post_id, table='dsta_db.test_24hr_comments')
            cmt_ids = set([str(list(each.values())[0]) for each in cmt_ids])
            print(f"\n\t-- DEBUG: There are {len(cmt_ids)} existing no. of comments for the post {post_id}" )
            # filter existing comment by ids    
            comments_this_post = remove_duplicated_comments_by_ids(cmt_ids=cmt_ids, comments_this_post=comments_this_post)
            
            print(f'\n\t-- DEBUG: {len(comments_this_post)} no. of new comments will be added to post {post_id}')
            
            self.insert_to_db(comments_this_post, label="comments")

    def _test_scrape_cmt_workflow(self, cmt_url, driver, Xparam, post_id):
        all_cmt_items = []
        
        try:
            driver.get(cmt_url)
        except Exception as e:
            print(f'\n-- DEBUG: driver timeout with error {e} .')
        
        SEARCHING = True

        while SEARCHING: # Search for 1 post
            wait = WebDriverWait(driver, Xparam['wait'])
            page_loaded = wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            print(f"\n-- DEBUG: Page loaded successfully! Searching comments for {post_id}",end='\r')

            cmt_items = getPostListings(driver, Xparam['XP_CMT_LISTING'])
            print(f'\n\t-- DEBUG: Total {len(cmt_items)} no. of elements detected on the table .')
            
            # 2024-06-25 add a timer to wait
            time.sleep(Xparam['wait'])

            clickOne(driver, Xparam['XP_CMT_THREAD'])

            #2024-09-6 update mapping function for scrapping comments of one post
            mapping =  dict()
            #3. loop and get each post item from the table
            for item in cmt_items:
                this_cmt_item = self._test_scrape_cmt_items(item, indent=0, cmt_reply_to='', mapping=mapping, Xparam=Xparam)
                
                if isinstance(this_cmt_item, list):
                    all_cmt_items.extend(this_cmt_item)
                else:
                    all_cmt_items.append(this_cmt_item)
            try:
                #self.bypass_ads(Xparam['XP_CLOSE_ADS'])
                print("\n\t-- DEBUG: Go to Next Page")
                next_page = driver.find_element(By.XPATH, Xparam['XP_CMT_NEXT'])  
                current_url = driver.current_url                                    
                goNextPage(driver, Xparam['XP_CMT_NEXT'])
                if driver.current_url == current_url:
                    print(current_url, driver.url)
                    raise
            except Exception as e:
                print('\n\t-- DEBUG: An error occur has occured clicking next page or no more next page.')
                SEARCHING = False
                break
        
        return all_cmt_items

    # 2024-09-06: This is the only function require updating.
    def _test_scrape_cmt_items(self, item, indent=0, cmt_reply_to='', mapping={}, Xparam={}):
        # cmt id
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

        # cmt reply_to/ children
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
            cmt_published_datetime = cmt_published_datetime = datetime.now()
        
        #if cmt_published_datetime != '' and cmt_published_datetime >= self.begin_dt:
        #    cmt_published_datetime = (cmt_published_datetime.strftime("%Y-%m-%d %H:%M:%S"))
        
        out = {
                    "cmt_id": cmt_id,
                    "cmt_org_content": cmt_org_content_text,
                    "cmt_published_datetime": cmt_published_datetime,
                    "cmt_replyTo": cmt_reply_to,
                    "cmt_user" : cmt_user,
                    "lang" : self.lang,
                    "translated": 0,
                    "source_id": self.source_id
                }

        return out


    def _test_cmt_item_processing(self, item, post_id=None):
        try:
            
            if type(item['cmt_published_datetime']) != str:
                item['cmt_published_datetime'] = str(item['cmt_published_datetime'].strftime("%Y-%m-%d %H:%M:%S")) # updated: 2024-12-18 datetime parser
            else:
                item['cmt_published_datetime'] = " ".join(item['cmt_published_datetime'].split()[1:])
                item['cmt_published_datetime'] = datetime.strptime(str(item['cmt_published_datetime']), "%d-%m-%Y %H:%M %p")
                item['cmt_published_datetime'] = str(item['cmt_published_datetime'].strftime("%Y-%m-%d %H:%M:%S"))
            
            item['cmt_id'] = post_id if item['cmt_id'] == "" else item['cmt_id']
            item['cmt_article_id'] = post_id
            item['source_id'] = self.source_id
            item['translated'] = self.translated
            item['lang'] = self.lang
        except Exception as e:
            print('\n-- DEBUG: Error with comment item processing, error: ', e)
            print(item)
            raise e

        return item

# customized function for collecting post url
def _collect_item_fn(post, Xparam):

    post_title = getWebElementText(post, Xparam['XP_POST_TITLE'], label="post_title")

    #post_cate = getWebElementText(post, Xparam['XP_POST_CATE'], label="post_category")

    post_url = getWebElementAttribute(post, Xparam['XP_POST_URL'], "href", label="post_url")

    try:
        post_datetime = pd.to_datetime(getWebElementText(post, Xparam['XP_POST_DATETIME']), format=Xparam['POST_DATETIME_FMT'], errors='ignore')
    except:
        post_datetime = ''

    return {
        'category': "",
        'url': post_url,
        'org_title': post_title,
        'published_datetime':post_datetime,
    }

# customized function for collecting news articles
def _collect_content_fn(driver=None, xpath_content='', url=''):
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

parser.add_argument(
        '--begain_datetime',
        type=str,
        help="end datetime - string - 2023-12-31 16:49:00",
        required=True
)

parser.add_argument(
        '--end_datetime',
        type=str,
        help="begin datetime - string - 2024-01-01 12:30:00",
        required=True
)

parser.add_argument(
        '--noOfDays',
        type=str,
        help="noOfDays - int - ",
        required=True
)
    
if __name__ == '__main__':
    args = parser.parse_args()

    args = parser.parse_args()
    remote = eval(args.remote)
    headless = eval(args.headless)

    #2024-03-12: begain datetime and end datetime for accumlating posts and comments
    begain_datetime = datetime.strptime(str(args.begain_datetime), "%Y-%m-%d %H:%M:%S")
    end_datetime = datetime.strptime(str(args.end_datetime), "%Y-%m-%d %H:%M:%S")
    noOfDays = int(args.noOfDays)

    B_CARI_object = {
        'starting_page_url': "https://c.cari.com.my/forum.php?mod=forumdisplay&fid=564&page=1",
        'source_id': 17,
        'lang': 'CN',
        'links_threshold':300,
        'begin_datetime': begain_datetime,
        'end_datetime': end_datetime,
        'headless':headless, # headless true no display false display
        'remote': remote,
        'noOfDays':noOfDays,
        'main_Xparam':{
            'wait': 5,
            #'XP_CLOSE_ADS': "//div[contains(@id, 'innity_adslot_')]//a[contains(@id, 'iz_osn_close_1')]",
            'XP_CLOSE_ADS': [
                            "//div[contains(@class,'button-common close-button')]//span", 
                            "//div[contains(@class, 'iz_osn_card_1')]//span[contains(@class, 'close')]", 
                            "//div[contains(@id, 'dismiss-button')]/div",
                            "//div[contains(@id, 'innity_adslot_')]//a[contains(@id, 'iz_osn_close_1')]",
                            "//div[contains(@id, 'innity_adslot_')]//a[contains(@id, 'btn_close_')]"
            ],
            'XP_POST_LISTING': "//table[contains(@id, 'threadlisttableid')]//tbody[contains(@id, 'normalthread')]",
            'XP_POST_NEXT_BTN': "//span[contains(@id, 'fd_page_top')]//div[contains(@class,'pg')]//a[@class='nxt' and text()='下一页']",
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
            # 2024-09-06: Udpdate a click thread although there is no thread to be clicked for consistency
            'XP_CMT_THREAD': "//strong[contains(@class, 'mr-4') and contains(text(), 'Lihat')]/following-sibling::i",
            'XP_CMT_LISTING': "//tbody/tr/td/div[contains(@id, 'postlist')]/div[not(@class)]",
            'XP_CMT_ID': "",
            'XP_CMT_DATETIME':  ".//descendant-or-self::div[@class='pti']/div[contains(@class,'authi')]/em",
            'XP_CMT_CONTENT': " .//descendant-or-self::div[contains(@class, 't_fsz')]/table/tbody/tr/td",
            'XP_CMT_REPLY_TO': " .//descendant-or-self::div[contains(@class, 't_fsz')]/table/tbody/tr/td//blockquote",
            'XP_CMT_USER' :".//descendant-or-self::div[@class='pi']/div[contains(@class,'authi')]",
            'XP_CMT_NEXT' :  "//div[contains(@class,'pg')]/a[@class='nxt' and text()='下一页']",
            'XP_CMT_DEL': ".//descendant-or-self::font[(ancestor::blockquote)]",
            'CMT_DATETIME_FMT': "%d-%m-%Y %I:%M %p"
        }
    }

    start_time = time.perf_counter()
    
    B_CARI = B_CARI_Crawler(B_CARI_object)

    B_CARI.scrape_post(B_CARI_object['main_Xparam'], collect_item_fn=_collect_item_fn, collect_article_map=_collect_content_fn)

    B_CARI.scrape_comments()

    end_time = time.perf_counter()

    print(f'\n-- DEBUG: Used time {start_time - end_time}')