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
import pytz

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

parser.add_argument(
        '--headless',
        type=str,
        help="True if running on docker else False",
        required=True
)

def test_scrape_comment_items(item, indent=0, cmt_reply_to='', Xparam={}):
    try:
        cmt_id = (item.find_element("xpath", Xparam['XP_CMT_ID'])).get_attribute('href') #1. cmt id
        cmt_id = cmt_id.replace("https://www.kaskus.co.id/show_post/","")
    except Exception as e:
        cmt_id = ""
    print('\n--DEBUG: id: ', cmt_id)
    
    # cmt text
    try:
        cmt_org_content_text = item.find_element("xpath", Xparam['XP_CMT_CONTENT']).text
        cmt_org_content_text = re.sub("\s+"," ", cmt_org_content_text)
    except Exception as e:
        cmt_org_content_text = ''
        print(f"\n--DEBUG: error {e}")

    try:
        cmt_del_content_text = item.find_element("xpath", Xparam['XP_CMT_CONTENT_DEL']).text
        cmt_del_content_text = re.sub("\s+"," ", cmt_del_content_text)
    except Exception as e:
        cmt_del_content_text = ''
    
    cmt_org_content_text = cmt_org_content_text.replace(cmt_del_content_text, '')
    cmt_org_content_text = cmt_org_content_text.replace("Quote:", '')
    cmt_org_content_text = re.sub(r"@\w+\s","", cmt_org_content_text)
    
    print('\n--DEBUG: content: ', cmt_org_content_text[:200],'...')

    # cmt children
    try:
        cmt_children = item.find_elements("xpath", Xparam['XP_CMT_CHILDREN'])
    except Exception as e:
        cmt_children = []

    print('\n--DEBUG: no.of children: ', len(cmt_children), ' parent id: ', cmt_reply_to)
    cmt_children = [test_scrape_comment_items(child, indent=idx, cmt_reply_to=id, Xparam=Xparam) for idx, child in enumerate(cmt_children)]

    # cmt user
    try:
        cmt_user = item.find_element("xpath",Xparam['XP_CMT_USER'] ).text
    except Exception as e:
        cmt_user = ''
    print('\n--DEBUG: user: ', cmt_user)

    # cmt likes
    try:
        cmt_likes = item.find_element("xpath",Xparam['XP_CMT_LIKES'] ).text
    except Exception as e:
        cmt_likes = ''
    print('\n--DEBUG: likes: ', cmt_likes)

    # cmt published datetime
    try:
        desired_timezone = pytz.timezone("Asia/Shanghai")
        cmt_published_datetime = item.find_element("xpath", Xparam['XP_CMT_DATETIME']).get_attribute('datetime')
        cmt_published_datetime = datetime.utcfromtimestamp(int(cmt_published_datetime)).replace(tzinfo=pytz.utc).astimezone(desired_timezone)
        cmt_published_datetime = cmt_published_datetime.strftime("%Y-%m-%d %H:%M:%S")

    except Exception as e:
        cmt_published_datetime = datetime.now()
        #cmt_published_datetime = (cmt_published_datetime.strftime("%Y-%m-%d %H:%M:%S"))
    print('\n--DEBUG: datetime: ', cmt_published_datetime)

    return {
            "cmt_id": cmt_id,
            "cmt_org_content": cmt_org_content_text,
            "cmt_published_datetime": cmt_published_datetime,
            "cmt_replyTo": cmt_reply_to,
            "cmt_user" : cmt_user,
            "cmt_article_id": 'test_post',
            "lang" : 'BM',
            "translated": 0,
            "source_id": ''
            }

def test_scrape_comments_workflow(cmt_url, driver, Xparam):
    try:
        driver.get(cmt_url)
    except Exception as e:
        print(f'\n-- DEBUG: driver timeout with error {e} .')
    
    SEARCHING = True

    while SEARCHING: # Search for 1 post
        wait = WebDriverWait(driver, Xparam['wait'])
        page_loaded = wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        print(f"\n-- DEBUG: Page loaded successfully! Searching comments for test",end='\r')

        cmt_items = getPostListings(driver, Xparam['XP_CMT_LISTING'])
        print(f'\n-- DEBUG: Total {len(cmt_items)} no. of elements on the table .')
        
        clickOne(driver, Xparam['XP_CMT_THREAD'])

        #3. loop and get each post item from the table
        for item in cmt_items:
            test_scrape_comment_items(item, indent=0, cmt_reply_to='', Xparam=Xparam)
            print()

        try:
            #self.bypass_ads(Xparam['XP_CLOSE_ADS'])
            print("\n--DEBUG: Go to Next Page")
            goNextPage(driver, Xparam['XP_CMT_NEXT']) 
        except Exception as e:
            print('\n--DEBUG: An error occur has occured clicking next page.', e)
            SEARCHING = False
            continue
            
if __name__ == '__main__':
    args = parser.parse_args()
    remote = eval(args.remote)
    headless = eval(args.headless)
    test_url = "https://www.kaskus.co.id/thread/65a5ff757231b47a32216a30/survei-galidata-ganjar-mahfud-pimpin-elektabilitas-pilpres-2024"
    Kaskus_object = {
        'starting_page_url': "https://www.kaskus.co.id/komunitas/10/berita-dan-politik",
        'source_id': 19,
        'lang': 'BI',
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
        'cmt_Xparam' :{
            'wait': 5,
            'XP_CLOSE_ADS': ["//div[contains(@class,'button-common close-button')]//span", 
                            "//div[contains(@class, 'iz_osn_card_1')]//span[contains(@class, 'close')]", 
                            "//div[contains(@id, 'dismiss-button')]/div",
                            "//div[contains(@id, 'innity_adslot_')]//a[contains(@id, 'iz_osn_close_1')]",
                             "//strong[contains(@class, 'mr-4') and contains(text(), 'Lihat')]/following-sibling::i"
                            ],
            'XP_CMT_THREAD': "//strong[contains(@class, 'mr-4') and contains(text(), 'Lihat')]/following-sibling::i",
            'XP_CMT_LISTING': "//section[@class= 'mr-4 min-w-0 flex-auto']/div[@class='relative']//div[@class='w-full bg-white dark:bg-grey-7 mb-1' or @class='w-full bg-white dark:bg-grey-7 mb-2']",
            'XP_CMT_CHILDREN':".//descendant::div[@class='flex w-full flex-wrap border-t border-grey-1 pl-6 dark:border-grey-6']",
            'XP_CMT_ID': ".//descendant-or-self::div[contains(@class, 'relative flex w-full justify-between px-4 py-2') or contains(@class, 'relative mb-2 flex items-center justify-between text-xs')]//div[@class='flex items-center']//a",
            'XP_CMT_DATETIME':  ".//descendant-or-self::div[@class='flex items-center gap-2']//time",
            'XP_CMT_CONTENT': ".//descendant-or-self::div[contains(@class, 'htmlContentRenderer_html-content___EjM3 w-full')] | .//descendant-or-self::div[@class='relative mx-4 mt-4 break-words' or @class='w-full px-4' or @class='w-full']//div[contains(@class, 'htmlContentRenderer_html-content_')]",
            'XP_CMT_REPLY_TO': ".//descendant-or-self::div[@class='w-full bg-grey-0 dark:bg-grey-8']",
            'XP_CMT_USER' :".//descendant-or-self::div[@class='flex items-center gap-2']//div[contains(@class, 'htmlContentRenderer')]",
            'XP_CMT_NEXT' : "(//div[contains(@class, 'flex items-center text-sm')]//i[contains(@class, 'fa-angle-right')])[2]",
            'XP_CMT_CONTENT_DEL': ".//descendant-or-self::div[@class='quote expandable']",
            'XP_CMT_LIKES': "//div[@class='text-xs text-secondary dark:text-secondary-night']",
            'CMT_DATETIME_FMT': ""
        }
    }

    start_time = time.perf_counter()
    
    Kaskus = ForumWebCrawler(Kaskus_object)

    #Kaskus.scrape_post(Kaskus_object['main_Xparam'], collect_url_map=my_collect_url_fn, collect_article_map=my_collect_art_fn)

    test_scrape_comments_workflow(test_url, Kaskus.driver, Kaskus_object['cmt_Xparam'])

    end_time = time.perf_counter()

    print(f'\n-- DEBUG: Used time {start_time - end_time}')