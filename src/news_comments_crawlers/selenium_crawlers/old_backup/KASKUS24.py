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
def _collect_item_fn(post, Xparam):
    #print('\n-- DEBUG: The post ', post.get_attribute("outerHTML")) #To print out the outter HTML layout for debugging
    #post_title = post.find_element("xpath", Xparam['XP_POST_TITLE'])
    #print('\n-- DEBUG: Post title - ',post_title)

    post_title = getWebElementAttribute(post, Xparam['XP_POST_TITLE'], "title")

    post_url = getWebElementAttribute(post, Xparam['XP_POST_URL'], "href")

    try:
        post_datetime = getWebElementText(post, Xparam['XP_POST_DATETIME'])
        print(f"\n-- DEBUG: raw published_datetime {post_datetime} ")
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
        print(f"\n-- DEBUG: Error occurs with published_datetime {e}")

    print({
        'category': "",
        'url': post_url,
        'org_title': post_title,
        'published_datetime':post_datetime,
    })
        
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

class Kaskus_Crawler(ForumWebCrawler):

    def scrape_comments(self):

        #test_url = "https://www.kaskus.co.id/thread/65a5ff757231b47a32216a30/survei-galidata-ganjar-mahfud-pimpin-elektabilitas-pilpres-2024"
        posts_in_db = getExistingPostItems(self.end_dt,noOfDays=self.noOfDays,sid=self.source_id)


        for post_item in posts_in_db:
            url, post_id = post_item['URL'].split('|')[-1], post_item['article_id']
            comments_this_post = self._test_scrape_cmt_workflow(url,self.driver, self.object['cmt_Xparam'], post_id)
            #comments_this_post = [each for each in comments_this_post if self.begin_dt <= each['cmt_published_datetime']] #check for 24 hours
            print(url)
            #2024-03-14: change the sequence for updating post(s)
            print(f'\n\t-- DEBUG: Total scrape {len(comments_this_post)} comments for the post')
            comments_this_post = [self._test_cmt_item_processing(item, post_id=post_id) for item in comments_this_post]
            for each in comments_this_post:
                print("\n-- DEBUG: * ", each)

            cmt_ids = getCommentIDsByArticleID(art_id=post_id, table='dsta_db.test_24hr_comments')
            cmt_ids = set([str(list(each.values())[0]) for each in cmt_ids])
            #print(cmt_ids)
            # filter existing comment by ids    
            comments_this_post = remove_duplicated_comments_by_ids(cmt_ids=cmt_ids, comments_this_post=comments_this_post)
            print(f'\n\t-- DEBUG: {len(comments_this_post)} no. of new comments will be added to post {post_id}')
            self.insert_to_db(comments_this_post, label="comments")
            
            time.sleep(2)
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

            # 2024-06-25 add a timer to wait
            time.sleep(Xparam['wait'])

            cmt_items = getPostListings(driver, Xparam['XP_CMT_LISTING'])
            print(f'\n\t-- DEBUG: Total {len(cmt_items)} no. of elements on the table .')
            
            clickOne(driver, Xparam['XP_CMT_THREAD'])

            #3. loop and get each post item from the table
            for item in cmt_items:
                this_cmt_item = self._test_scrape_cmt_items(item, indent=0, cmt_reply_to='', Xparam=Xparam)
                #2024-04-09: append children nodes in the list
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
                print('\n-- DEBUG: An error occur has occured clicking next page or no more next page.')
                SEARCHING = False
                break
        
        return all_cmt_items

    def _test_scrape_cmt_items(self, item, indent=0, cmt_reply_to='', Xparam={}):
        # 2024-03-14: update new cmt_id(s)
        try:
            cmt_id = (item.find_element("xpath", Xparam['XP_CMT_ID'])).get_attribute('href') #1. cmt id
            cmt_id = cmt_id.replace("https://www.kaskus.co.id/show_post/","")
            
        except Exception as e:
            if cmt_reply_to !="":
                cmt_id = cmt_reply_to + " -> " + str(indent)
            else:
                cmt_id = ""
        #print('\n--DEBUG: id: ', cmt_id)

        # cmt text
        try:
            cmt_org_content_text = item.find_element("xpath", Xparam['XP_CMT_CONTENT']).text
            cmt_org_content_text = re.sub("\s+"," ", cmt_org_content_text)
        except Exception as e:
            cmt_org_content_text = ''
            #print(f"\n--DEBUG: error {e}")

        try:
            cmt_del_content_text = item.find_element("xpath", Xparam['XP_CMT_CONTENT_DEL']).text
            cmt_del_content_text = re.sub("\s+"," ", cmt_del_content_text)
        except Exception as e:
            cmt_del_content_text = ''

        cmt_org_content_text = cmt_org_content_text.replace(cmt_del_content_text, '')
        cmt_org_content_text = cmt_org_content_text.replace("Quote:", '')
        cmt_org_content_text = re.sub(r"@\w+\s","", cmt_org_content_text)

        #print('\n--DEBUG: content: ', cmt_org_content_text[:200],'...')

        # cmt children
        #2023-03-15: update merge children node with the base node for yielding out.
        try:
            cmt_children = item.find_elements("xpath", Xparam['XP_CMT_CHILDREN'])
            #print('\n--DEBUG: no.of children: ', len(cmt_children), ' parent id: ', cmt_reply_to)
            cmt_children = [self._test_scrape_cmt_items(child, indent=idx + 1, cmt_reply_to=cmt_id, Xparam=Xparam) for idx, child in enumerate(cmt_children)]

        except Exception as e:
            cmt_children = []

        # cmt user
        try:
            cmt_user = item.find_element("xpath",Xparam['XP_CMT_USER'] ).text
        except Exception as e:
            cmt_user = ''
        #print('\n--DEBUG: user: ', cmt_user)

        # cmt likes
        try:
            cmt_likes = item.find_element("xpath",Xparam['XP_CMT_LIKES'] ).text
        except Exception as e:
            cmt_likes = ''
        #print('\n--DEBUG: likes: ', cmt_likes)

        # cmt published datetime
        try:
            desired_timezone = pytz.timezone("Asia/Shanghai")
            cmt_published_datetime = item.find_element("xpath", Xparam['XP_CMT_DATETIME']).get_attribute('datetime')
            cmt_published_datetime = datetime.utcfromtimestamp(int(cmt_published_datetime)).replace(tzinfo=pytz.utc).astimezone(desired_timezone)
            cmt_published_datetime = cmt_published_datetime.strftime("%Y-%m-%d %H:%M:%S")
            cmt_published_datetime = datetime.strptime(cmt_published_datetime, "%Y-%m-%d %H:%M:%S")
        except Exception as e:
            cmt_published_datetime = datetime.now()
            #cmt_published_datetime = (cmt_published_datetime.strftime("%Y-%m-%d %H:%M:%S"))
        #print('\n--DEBUG: datetime: ', cmt_published_datetime)

        #2024-03-15: merge children node with root node
        out = {
                "cmt_id": cmt_id,
                "cmt_org_content": cmt_org_content_text,
                "cmt_published_datetime": cmt_published_datetime,
                "cmt_replyTo": str(cmt_reply_to),
                "cmt_user" : cmt_user
            }
        
        #print(out)
        #print()
        if len(cmt_children) == 0:
            return out
        
        else:
            cmt_children.append(out)
            return cmt_children

    def _test_cmt_item_processing(self, item, post_id=None):
        item['cmt_published_datetime'] = str(item['cmt_published_datetime'].strftime("%Y-%m-%d %H:%M:%S"))
        item['cmt_id'] = post_id if item['cmt_id'] == "" else item['cmt_id']
        item['cmt_article_id'] = post_id
        item['source_id'] = self.source_id
        item['translated'] = self.translated
        item['lang'] = self.lang

        return item

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
            'wait': 4,
            #'XP_CLOSE_ADS': "//div[contains(@id, 'innity_adslot_')]//a[contains(@id, 'iz_osn_close_1')]",

            'XP_CLOSE_ADS': [
                            "//button[contains(text(), 'Lewati')]",
                            "//div[contains(@class,'button-common close-button')]//span", 
                            "//div[contains(@class, 'iz_osn_card_1')]//span[contains(@class, 'close')]", 
                            "//div[contains(@id, 'dismiss-button')]/div",
                            "//div[contains(@id, 'innity_adslot_')]//a[contains(@id, 'iz_osn_close_1')]"],
            # A list of post on the page
            # 2024-07-17 updated post listing -> 20 elements
            'XP_POST_LISTING': "//section//div[@class='bg-surface-primary']//div[contains(@class, 'flex w-full flex-col')]",

            # 2024-07-17 checked with no change
            'XP_POST_NEXT_BTN': "//div[contains(@class, 'flex items-center text-sm')]//i[contains(@class, 'fa-angle-right')]",

            # 2024-07-17 checked with no change
            'XP_POST_URL': ".//descendant-or-self::div[contains(@class,'mb-2 block flex-1 text-lg font-medium')]/a[@title]",

            # 2024-07-17 checked with no change
            'XP_POST_TITLE': ".//descendant-or-self::div[contains(@class,'mb-2 block flex-1 text-lg font-medium')]/a[@title]",

            # 2024-08-23 update datetime attribute tag
            'XP_POST_DATETIME': ".//descendant-or-self::div[contains(@class, 'text-tertiary flex-none')]",

            #'XP_POST_CATE': ".//descendant-or-self::tr//th//div[contains(@class, 'fd_list_main')]//em",
            # The first post of the discussion
            'XP_POST_ART': "//div[contains(@class, 'relative mx-4 mt-4 break-words')]",
            'POST_DATETIME_FMT': "%d-%m-%Y %H:%M"
        },
        'cmt_Xparam' :{
            'wait': 8,
            'XP_CLOSE_ADS': [
                            "//button[contains(text(), 'Lewati')]",
                            "//div[contains(@class,'button-common close-button')]//span", 
                            "//div[contains(@class, 'iz_osn_card_1')]//span[contains(@class, 'close')]", 
                            "//div[contains(@id, 'dismiss-button')]/div",
                            "//div[contains(@id, 'innity_adslot_')]//a[contains(@id, 'iz_osn_close_1')]",
                             "//strong[contains(@class, 'mr-4') and contains(text(), 'Lihat')]/following-sibling::i"
                            ],
            'XP_CMT_THREAD': "//strong[contains(@class, 'mr-4') and contains(text(), 'Lihat')]/following-sibling::i",

            # 2024-07-26 update xpath for comments listing, excluding the main post, this is a list containing n comments.
            'XP_CMT_LISTING': "//section//div[contains(@class,'relative')]//div[contains(@class, 'w-full md:rounded bg-surface-primary')]",
            
            # 2024-07-26 update xpath for comment children listing, this is a [...] containing n children comments.
            'XP_CMT_CHILDREN':".//descendant::div[contains(@class, 'w-full')]//div[contains(@class, 'flex w-full flex-wrap border-t')]",
            
            # 2024-07-26 update xpath for comment id, this is a single string item.
            'XP_CMT_ID': ".//descendant-or-self::div[contains(@class, 'relative flex w-full justify-between px-4 py-2')]//div[contains(@class, 'flex items-center')]/a",
            
            # 2024-07-26 update xpath for datetime, this is a datetime item.
            'XP_CMT_DATETIME':  ".//descendant-or-self::div[contains(@class, 'relative flex w-full justify-between px-4 py-2')]//time",
            
            # 2024-07-26 update xpath for comment item, this is a single string that write out the comment.
            'XP_CMT_CONTENT': ".//descendant-or-self::div[contains(@class, 'htmlContentRenderer_html-content__ePjqJ w-full break-words py-2 text-secondary') or contains(@class, 'htmlContentRenderer_html-content__ePjqJ w-full break-words px-4 py-1')]",
            
            # No use
            'XP_CMT_REPLY_TO': ".//descendant-or-self::div[@class='w-full bg-grey-0 dark:bg-grey-8']",
            
            # 2024-07-26 update xpath for comment user, this is a single string that write out the user name.
            'XP_CMT_USER' :".//descendant-or-self::div[@class='relative flex w-full justify-between px-4 py-2']//div[contains(@class, 'htmlContentRenderer_html-content__ePjqJ font-medium text-secondary')]",
            
            # 2024-07-26 update xpath for next button, this is a clickable link 
            'XP_CMT_NEXT' : "(//div[contains(@class, 'flex items-center text-sm')]//i[contains(@class, 'fa-angle-right')])[2]",
            
            # 2024-07-26 update xpath for grey text that should be removed from the main content
            'XP_CMT_CONTENT_DEL': ".//descendant-or-self::div[@class='quote expandable']",
            
            # 2024-07-26 update xpath for likes, this is a string that write off no. of likes / scores equivalent.
            'XP_CMT_LIKES': "//div[@class='text-xs text-secondary']",
            
            'CMT_DATETIME_FMT': ""
        }
    }

    start_time = time.perf_counter()
    
    Kaskus = Kaskus_Crawler(Kaskus_object)

    print(f'\n\t-- DEBUG: datetime beginning from {last24hours}  datetime end at {now}')

    Kaskus.scrape_post(Kaskus_object['main_Xparam'], collect_item_fn=_collect_item_fn, collect_article_map=_collect_content_fn)

    print("\n-- *************************************************************** DEBUG: End of collecting post link and content ***************************************************************")

    #test_url_2 = "https://www.kaskus.co.id/thread/667a1c9f54bd9e79b806cfeb/menkominfo-pemerintah-tidak-akan-bayar-permintaan-tebusan-8-juta-dollar-peretas-pdn?ref=threadlist-10&med=thread_list"
    
    #Kaskus._test_scrape_cmt_workflow(test_url_2, Kaskus.driver, Kaskus_object["cmt_Xparam"], "sample")

    Kaskus.scrape_comments()

    end_time = time.perf_counter()

    print(f'\n-- DEBUG: Used time {start_time - end_time}')