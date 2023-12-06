from Functions import *

import argparse

import warnings

from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from datetime import timedelta
from ForumTargetObject import ForumWebCrawler

warnings.filterwarnings("ignore")

now, last24hours=get_datetime()

INSERT_API = 'http://10.2.56.213:8086/insert'

PING_API = 'http://10.2.56.213:8086/ping'

QUERY_API = 'http://10.2.56.213:8086/query'

table = 'dsta_db.test'

latest=True

SEARCHING = True

# customized function for collecting post url
def my_collect_url_fn(post, Xparam):
    #print('\n-- DEBUG: The post ', post.get_attribute("outerHTML")) #To print out the outter HTML layout for debugging
    #post_title = post.find_element("xpath", Xparam['XP_POST_TITLE'])
    #print('\n-- DEBUG: Post title - ',post_title)

    post_title = getWebElementAttribute(post, Xparam['XP_POST_TITLE'], "title")

    #post_cate = getWebElementText(post, Xparam['XP_POST_CATE'])

    post_url = getWebElementAttribute(post, Xparam['XP_POST_URL'], "href")

    try:
        post_datetime = getWebElementText(post, Xparam['XP_POST_DATETIME'])
        #print(f'\n-- DEBIG: datetime {post_datetime}')

        if "Hari ini" in post_datetime:
            today_date = datetime.now().date().strftime("%d-%m-%Y")
            today_date = str(today_date)
            post_datetime = (post_datetime.replace("Hari ini", "")).strip()
            post_datetime = today_date + ' ' + post_datetime
        elif "Kemarin" in post_datetime:
            yesterdate =  (datetime.now().date() - timedelta(days=1)).strftime("%d-%m-%Y")
            yesterdate = str(yesterdate)
            post_datetime = (post_datetime.replace("Kemarin", "")).strip()
            post_datetime = yesterdate + ' ' + post_datetime
        else:
            pass
        
        post_datetime = pd.to_datetime(post_datetime, format=Xparam['POST_DATETIME_FMT'], errors='ignore')

    except Exception as e:
        post_datetime = ''
        
    return {
        'category': "",
        'url': post_url,
        'org_title': post_title,
        'published_datetime':post_datetime,
    }

# customized function for collecting news articles
def my_collect_art_fn(driver=None, xpath_content='', url=''):
    driver.get(str(url))
    try:
        org_content = str(driver.find_element("xpath", xpath_content).text)
        lines = org_content.split('\n') # Split the content into lines   
        #lines = lines[4:] if len(lines) > 4 else lines #
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
    
if __name__ == '__main__':
    args = parser.parse_args()
    remote = eval(args.remote)

    Kaskus_object = {
        'starting_page_url': "https://www.kaskus.co.id/komunitas/10/berita-dan-politik",
        'source_id': 19,
        'lang': 'BI',
        'links_threshold':50,
        'begin_datetime': last24hours,
        'end_datetime': now,
        'headless':False,
        'remote': remote,
        'noOfDays':4,
        'main_Xparam':{
            'wait': 8,
            #'XP_CLOSE_ADS': "//div[contains(@id, 'innity_adslot_')]//a[contains(@id, 'iz_osn_close_1')]",
            'XP_CLOSE_ADS': ["//div[contains(@class,'button-common close-button')]//span", 
                            "//div[contains(@class, 'iz_osn_card_1')]//span[contains(@class, 'close')]", 
                            "//div[contains(@id, 'dismiss-button')]/div",
                            "//div[contains(@id, 'innity_adslot_')]//a[contains(@id, 'iz_osn_close_1')]"],
            # A list of post on the page
            'XP_POST_LISTING': "//section//div[contains(@class, 'bg-grey-1 dark:bg-black')]//div[contains(@class,'flex w-full flex-col justify-between bg-white px-4 py-3 dark:bg-grey-7 mb-2') and not(.//span[contains(@class, 'inline-block align-middle')])]",
            'XP_POST_NEXT_BTN': "//div[contains(@class, 'flex items-center text-sm')]//i[contains(@class, 'fa-angle-right')]",
            'XP_POST_URL': ".//descendant-or-self::div[contains(@class, 'mb-2 block flex-1 text-lg font-medium visited:text-tertiary dark:visited:text-tertiary-night')]/a[@title]",
            'XP_POST_TITLE': ".//descendant-or-self::div[contains(@class, 'mb-2 block flex-1 text-lg font-medium visited:text-tertiary dark:visited:text-tertiary-night')]/a[@title]",
            'XP_POST_DATETIME': ".//descendant-or-self::div[contains(@class, 'ml-1 text-tertiary dark:text-tertiary-night')]",
            #'XP_POST_CATE': ".//descendant-or-self::tr//th//div[contains(@class, 'fd_list_main')]//em",
            # The first post of the discussion
            'XP_POST_ART': "//section[contains(@class, 'mr-4 min-w-0 flex-auto')]//div[contains(@class, 'w-full bg-white dark:bg-grey-7 mb-2')]//div[contains(@class, 'relative mx-4 mt-4 break-words')]",
            'POST_DATETIME_FMT': "%d-%m-%Y %I:%M"
        },
        'cmt_Xparam':{
            'wait': 5,
            'XP_CLOSE_ADS': ["//div[contains(@class,'button-common close-button')]//span", 
                            "//div[contains(@class, 'iz_osn_card_1')]//span[contains(@class, 'close')]", 
                            "//div[contains(@id, 'dismiss-button')]/div",
                            "//div[contains(@id, 'innity_adslot_')]//a[contains(@id, 'iz_osn_close_1')]"],
            'XP_CMT_LISTING': "//div[contains(@class, 'mt-4 flex w-full')]//section[contains(@class, 'mr-4 min-w-0 flex-auto')]/div[contains(@class,'relative')]/div[not(@class)]//div[contains(@class, 'w-full bg-white dark:bg-grey-7 mb-1')]",
            'XP_CMT_ID': "",
            'XP_CMT_DATETIME':  ".//descendant-or-self::div[@class='pti']/div[contains(@class,'authi')]/em",
            'XP_CMT_CONTENT': " .//descendant-or-self::div[contains(@class, 't_fsz')]/table/tbody/tr/td",
            'XP_CMT_REPLY_TO': " .//descendant-or-self::div[contains(@class, 't_fsz')]/table/tbody/tr/td//blockquote",
            'XP_CMT_USER' :".//descendant-or-self::div[@class='pi']/div[contains(@class,'authi')]",
            'XP_CMT_NEXT' : "//div[contains(@id, 'pgt')]//div[contains(@class,'pg')]/a[text()='Next']",
            'XP_CMT_DEL': ".//descendant-or-self::font[(ancestor::blockquote)]",
            'CMT_DATETIME_FMT': "%d-%m-%Y %H:%M"

        }
    }

    start_time = time.perf_counter()
    
    Kaskus = ForumWebCrawler(Kaskus_object)

    Kaskus.scrape_post(Kaskus_object['main_Xparam'], collect_url_map=my_collect_url_fn, collect_article_map=my_collect_art_fn)

    '''
    B_CARI.scrape_comments(B_CARI_object['cmt_Xparam'])

    '''
    end_time = time.perf_counter()

    print(f'\n-- DEBUG: Used time {start_time - end_time}')