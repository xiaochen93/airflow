from ForumTargetObject import ForumWebCrawler
from Functions import *
from selenium.common.exceptions import NoSuchElementException
from urllib.parse import urlparse
import argparse, warnings, time
import pandas as pd

warnings.filterwarnings("ignore")

INSERT_API = 'http://10.2.56.213:8086/insert'
PING_API = 'http://10.2.56.213:8086/ping'
QUERY_API = 'http://10.2.56.213:8086/query'

def _collect_reddit_post_item(post, Xparam):
    try:
        post_id = post.get_property("id")
        title = post.find_element("xpath", Xparam['XP_POST_TITLE']).text
        article_url = post.find_element("xpath", Xparam['XP_POST_TITLE']).get_property('href')
        try:
            cmt_url = post.find_element("xpath", Xparam['XP_POST_CMT_URL']).get_property('href')

        except NoSuchElementException:
            cmt_url = ""
        datetime_ = post.find_element("xpath", Xparam['XP_POST_DATETIME']).get_attribute('datetime')
        datetime_ = pd.to_datetime(datetime_, format='%Y-%m-%dT%H:%M:%S+00:00')
        domain = urlparse(article_url).netloc
    except:
        return None
    
    content = getNewsContentByArticle(Article, article_url)
    if content == "" or "reddit" in article_url:
        out_dict = getNewsContentByGoogle(title)
        content = out_dict['content']
        domain = out_dict['domain']
        article_url = out_dict['url']

    return {
        'org_title': title,
        'url': article_url+'|'+cmt_url,
        'published_datetime': datetime_,
        'org_content': content,
        'translated': 0,
        'lang': 'EN'
    }

class RedditCrawler(ForumWebCrawler):
    def __init__(self, required_parameter):
        super().__init__(required_parameter)
        self.source_id = 16

        # 2025-05-22 refreshing the page
        print("Detected block — refreshing the page")
        self.driver.refresh()
        time.sleep(2)

    def scrape_comments(self):
        posts_in_db = self._fetchPostByTimeRange(table="test", dt_label="published_datetime", lang='EN', end_datetime=self.end_dt, begain_datetime=self.begin_dt, sid=self.source_id)

        for post_item in tqdm(posts_in_db):
            url, post_id = post_item['URL'].split('|')[-1], post_item['article_id']
            comments_this_post = self._test_scrape_cmt_workflow(url,self.driver, self.object['cmt_Xparam'], post_id)
            
            #2024-03-14: change the sequence for updating post(s)
            print(f'\n\t-- DEBUG: Total has scraped {len(comments_this_post)} comments for the post')
            comments_this_post = [self._test_cmt_item_processing(item, post_id=post_id) for item in comments_this_post]

            # 2025-05-21: remove duplicated comments with existing ids
            cmt_ids = getCommentIDsByArticleID(art_id=post_id, table='dsta_db.test_24hr_comments')
            cmt_ids = set([str(list(each.values())[0]) for each in cmt_ids])
            print(f"\n\t-- DEBUG: There are {len(cmt_ids)} existing no. of comments for the post {post_id}" )
            comments_this_post = remove_duplicated_comments_by_ids(cmt_ids=cmt_ids, comments_this_post=comments_this_post)
            print(f'\n\t-- DEBUG: {len(comments_this_post)} no. of new comments will be added to post {post_id}')
            
            self.insert_to_db(comments_this_post, label="comments")

    def _test_scrape_cmt_workflow(self, cmt_url, driver, Xparam, post_id):
        driver.get(cmt_url)
        time.sleep(2)
        try:
            expanders = driver.find_elements("xpath", Xparam['XP_CMT_EXPAND'])
            for each in expanders: each.click()
        except: pass

        try:
            more_links = driver.find_elements("xpath", Xparam['XP_CMT_MORE'])
            for each in more_links: each.click()
        except: pass

        root_items = getPostListings(driver, Xparam['XP_CMT_LISTING'])

        return self._test_scrape_comments(root_items, post_id, Xparam)

    def _test_scrape_comments(self, items, p_id, Xparam):
        out = []
        for item in items:
            try:
                cmt_id = item.find_element("xpath", Xparam['XP_CMT_ID']).get_attribute("id").split('_')[-1]
                cmt_user = item.find_element("xpath", Xparam['XP_CMT_USER']).text
                cmt_datetime = item.find_element("xpath", Xparam['XP_CMT_DATETIME']).get_attribute('datetime')
                cmt_content = item.find_element("xpath", Xparam['XP_CMT_CONTENT']).text
                cmt_score = item.find_element("xpath", Xparam['XP_CMT_SCORE']).text
            except:
                continue

            one_comment = {
                'cmt_id': cmt_id,
                'cmt_replyTo': p_id,
                'cmt_user': cmt_user,
                'cmt_likes': cmt_score,
                'cmt_content': cmt_content,
                'cmt_org_content': cmt_content,
                'cmt_published_datetime': cmt_datetime,
                'translated': 0,
                'lang': 'EN',
                'source_id': self.source_id
            }
            out.append(one_comment)

            # Recursive child comments
            try:
                child_element = item.find_element("xpath", Xparam['XP_CMT_CHILD_BLOCK'])
                children = child_element.find_elements("xpath", Xparam['XP_CMT_CHILD'])
                out.extend(self._extract_reddit_comments(children, cmt_id, Xparam))
            except:
                continue

        return out

    def _test_cmt_item_processing(self, item, post_id=None):
        try:
            if type(item['cmt_published_datetime']) != str:
                item['cmt_published_datetime'] = str(pd.to_datetime(item['cmt_published_datetime'], format='%Y-%m-%dT%H:%M:%S+00:00')) # updated: 2024-12-18 datetime parser
            else:
                item['cmt_published_datetime'] = str(pd.to_datetime(item['cmt_published_datetime'], format='%Y-%m-%dT%H:%M:%S+00:00'))
            
            item['cmt_id'] = post_id if item['cmt_id'] == "" else item['cmt_id']
            item['cmt_article_id'] = post_id
            item['source_id'] = self.source_id
            item['translated'] = self.translated
            item['lang'] = self.lang
        except Exception as e:
            print('\n-- DEBUG: Error with comment item processing, error: ', e)
            print("\n",item)
            raise e

        return item

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parameters to execute a web crawler")
    parser.add_argument('--remote', type=str, required=True)
    parser.add_argument('--headless', type=str, required=True)
    parser.add_argument('--begain_datetime', type=str, required=True)
    parser.add_argument('--end_datetime', type=str, required=True)
    parser.add_argument('--noOfDays', type=str, required=True)
    args = parser.parse_args()

    begain_datetime = datetime.strptime(args.begain_datetime, "%Y-%m-%d %H:%M:%S")
    end_datetime = datetime.strptime(args.end_datetime, "%Y-%m-%d %H:%M:%S")

    reddit_crawler_obj = {
        'starting_page_url': "https://old.reddit.com/r/singapore/top/?sort=top&t=month",
        #'starting_page_url': "https://old.reddit.com/r/singapore/",
        'source_id': 16,
        'lang': 'EN',
        'links_threshold': 200,
        'begin_datetime': begain_datetime,
        'end_datetime': end_datetime,
        'headless': eval(args.headless),
        'remote': eval(args.remote),
        'noOfDays': int(args.noOfDays),
        'main_Xparam': {
            'wait': 5,
            'XP_CLOSE_ADS': [],
            'XP_POST_LISTING':  "//div[contains(@class,'thing id-t3')  and .//SPAN/@title='News']",
            'XP_POST_TITLE': ".//descendant-or-self::A[contains(@class,'title may-blank')]",
            'XP_POST_DATETIME': ".//descendant-or-self::p[contains(@class, 'tagline')]/time",
            'XP_POST_NEXT_BTN': "//div[contains(@class, 'nav-buttons')]//a[contains(text(), 'next')]",
            "XP_POST_CMT_URL": ".//descendant-or-self::li[contains(@class,'first')]/a",
            'XP_POST_ART': ''
        },
        'cmt_Xparam': {
            'wait': 5,
            'XP_CMT_LISTING': "//div[contains(@class, 'sitetable nestedlisting')]/div[contains(@class, 'thing')]",
            'XP_CMT_ID': ".//descendant-or-self::div[contains(@class, 'comment')]",
            'XP_CMT_USER': ".//descendant-or-self::div[contains(@class,'entry unvoted')]//p[contains(@class, 'tagline')]/a[contains(@class,'author')]",
            'XP_CMT_DATETIME': ".//descendant-or-self::div[contains(@class,'entry unvoted')]//p[contains(@class, 'tagline')]/time",
            'XP_CMT_CONTENT': ".//descendant-or-self::div[contains(@class, 'md')]",
            'XP_CMT_SCORE': ".//descendant-or-self::div[contains(@class,'entry unvoted')]//p[contains(@class, 'tagline')]//span[contains(@class,'score unvoted')]",
            'XP_CMT_EXPAND': "//p[contains(@class, 'tag')]/a[text()='[+]']",
            'XP_CMT_MORE': "//span[contains(text(),'more comments')]/a[text()='more comments']",
            'XP_CMT_CHILD_BLOCK': ".//descendant-or-self::div[contains(@class,'child')]",
            'XP_CMT_CHILD': "./div[contains(@class,'sitetable listing')]/div[contains(@class,'thing') and not(contains(@class,'morechildren'))]"
        }
    }

    reddit_crawler = RedditCrawler(reddit_crawler_obj)
    reddit_crawler.scrape_post(Xparam=reddit_crawler_obj['main_Xparam'], collect_item_fn=_collect_reddit_post_item)
    reddit_crawler.scrape_comments()