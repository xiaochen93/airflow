from Functions import *

import warnings

warnings.filterwarnings("ignore")

def get_datetime(days=1, hours=1):
    from datetime import datetime
    today = datetime.now().replace(microsecond=0)
    import datetime
    one_day = datetime.timedelta(days=days)
    one_hour = datetime.timedelta(hours=hours)
    last24hours = today - one_day - one_hour
    return today, last24hours

today, last24hours=get_datetime()

url= "https://old.reddit.com/r/singapore/top/"

INSERT_API = 'http://10.2.56.213:8086/insert'

PING_API = 'http://10.2.56.213:8086/ping'

source_id = 16

table = 'dsta_db.test'

latest=True

def getRedditPostItems(driver, url,label):
    out= []
    driver.get(url)
    time.sleep(1)
    #1. click to the time series
    xpath_dropdown = "//div[contains(@class,'dropdown lightdrop')]"
    xpath_choices = "//DIV[contains(@class,'drop-choices')]//A[contains(@class,'choice')]"
    #1. allocate the dropdown menu and click the timeseries
    timeseries = getDropdownChoices(driver,xpath_dropdown, xpath_choices)
    timeseries = [choice for choice in timeseries if choice.text == label]
    
    if not timeseries == []:
        timeseries[0].click()
        time.sleep(2)
    else:
        pass
    #3. loop and retrieve items on the page.
    searching = True
    noOfDocs = 0
    while searching:
        #2. load main page and pick relative items
        xpath_main_page_items = "//div[contains(@class,'thing id-t3')  and .//SPAN/@title='News']"
        
        items = getTableItems(driver, xpath_main_page_items)
    
        for item in items:
            # get the post id
            try:
                post_id = item.get_property("id")
            except NoSuchElementException:
                print('-- post id not found')
                post_id = ""
            # get the news title
            try:
                title = item.find_element("xpath",".//descendant-or-self::A[contains(@class,'title may-blank')]").text
            except NoSuchElementException:
                title = ""
            # get the news URL
            try:
                title_url = item.find_element("xpath",".//descendant-or-self::A[contains(@class,'title may-blank')]").get_property('href')
            except NoSuchElementException:
                title_url = ""
        
            # get the datetime
            try:
                datetime  = item.find_element("xpath", ".//descendant-or-self::p[contains(@class, 'tagline')]/time").get_attribute('datetime')
            except NoSuchElementException:
                datetime = ""
        
            # get the domain name
            try:
                domain = item.find_element("xpath", ".//descendant-or-self::SPAN[contains(@class, 'domain')]").text
            except NoSuchElementException:
                domain = ""

            domain = urlparse(title_url).netloc
            # get the news score
            try:
                scores = item.find_element("xpath", ".//descendant-or-self::div[contains(@class, 'score unvoted')]").text
            except NoSuchElementException:
                scores = ""
            # get the no of comments
            try:
                no_of_cmts = item.find_element("xpath", ".//descendant-or-self::li[contains(@class,'first')]/a").text.split()[0]
            except NoSuchElementException:
                no_of_cmts = "0"
            # get the comment URL
            try:
                cmt_url = item.find_element("xpath", ".//descendant-or-self::li[contains(@class,'first')]/a").get_property('href')
            except NoSuchElementException:
                cmt_url = ""
            # get the article content
            content = getNewsContentByArticle(Article, title_url)

            if content == "" or "reddit" in title_url:
                out_dict = getNewsContentByGoogle(title)
                content = out_dict['content']
                domain = out_dict['domain']
                title_url = out_dict['url'] #bug fixed for missing url
            
            # expand all clickable comment section
            
            one_instance = {
                'article_id': post_id,
                'title': title,
                'org_title': title,
                'url':title_url,
                #'post_domain':domain,
                'published_datetime': datetime,
                #'post_score': scores,
                #'post_no_of_cmts': no_of_cmts,
                'content': content,
                'org_content': content,
                'translated': 1,
                'last_modified': today,
                'cmt_url': cmt_url
            }
            
            out.append(one_instance)
            
            noOfDocs = noOfDocs + 1
            print('\n\tDEBUG -- {} no of records have collected.'.format(noOfDocs))
            
        
        # click next to go
        xpath_next = "//div[contains(@class, 'nav-buttons')]//a[contains(text(), 'next')]"
        
        # Wait for initialize, in seconds
        try:
            clickToGo(driver, xpath_next)
        except:
            print('\n-- DEBUG: The web scraping is completed.')
            break
        

    return out

def getCommentsList(items,p_id=""):
    
    out = []
    
    for idx, comment_item in enumerate(items):
        #1. comment id 
        try:
            c_id = (comment_item.find_element("xpath", ".//descendant-or-self::div[contains(@class, 'comment')]").get_attribute("id")).split('_')[-1]
        except NoSuchElementException:
            c_id = ""
            
        #2. comment user
        try:
            c_user = comment_item.find_element("xpath", ".//descendant-or-self::div[contains(@class,'entry unvoted')]//p[contains(@class, 'tagline')]/a[contains(@class,'author')]").text
        except NoSuchElementException:
            c_user = ''
            
        #3. comment datetime
        try:
            c_datetime = comment_item.find_element("xpath", ".//descendant-or-self::div[contains(@class,'entry unvoted')]//p[contains(@class, 'tagline')]/time").get_attribute('datetime')
        except NoSuchElementException:
            c_datetime = ''
        
        #4. comment text
        try:
            c_text = comment_item.find_element("xpath", ".//descendant-or-self::div[contains(@class, 'md')]").text
        except NoSuchElementException:
            c_text = ''
            
        #5. post score
        try:
            c_score = comment_item.find_element("xpath", ".//descendant-or-self::div[contains(@class,'entry unvoted')]//p[contains(@class, 'tagline')]//span[contains(@class,'score unvoted')]").text
        except NoSuchElementException:
            c_score = ''
        
        one_comment_item ={
                'cmt_id' : c_id,
                'cmt_replyTo' : p_id,
                'cmt_user': c_user,
                'cmt_likes':c_score,
                'cmt_content': c_text,
                'cmt_org_content': c_text,
                'cmt_published_datetime': c_datetime,
                'translated': 1,
                'lang': 'EN',
                'source_id': 16
        }
        if c_id != '' and c_user != '' and c_text != '' and c_datetime != '':
            out.append(one_comment_item)
        #6. check if has child element:
        try:
            # This comment has a child element, recursion goes on:
            child_element = comment_item.find_element("xpath", ".//descendant-or-self::div[contains(@class,'child')]")
            this_child = child_element.find_elements("xpath","./div[contains(@class,'sitetable listing')]/div[contains(@class,'thing') and not(contains(@class,'morechildren'))]")
            out.extend(getCommentsList(this_child, p_id=c_id))
        except Exception as e:
            # This comment does not has a child element:
            print(e)
            pass
    
    return out

def getRedditCommentItems(driver, c_url):
    
    driver.get(c_url)
    
    time.sleep(2.5)
    try:
        expanders = driver.find_elements("xpath", "//p[contains(@class, 'tag')]/a[text()='[+]']")
        for each in expanders:
            each.click()
    except NoSuchElementException:
        pass
    
    try:
        expanders = driver.find_elements("xpath", "//span[contains(text(),'more comments')]/a[text()='more comments']")
        for each in expanders:
            each.click()
    except NoSuchElementException:
        pass    
    
    xpath_comments_dir = "//div[contains(@class, 'sitetable nestedlisting')]/div[contains(@class, 'thing')]"
    
    #root_items = driver.find_elements("xpath", xpath_comments_dir)
    
    root_items = getTableItems(driver, xpath_comments_dir)
    
    out = getCommentsList(root_items, p_id="")
    
    return out

# with open('data/reddit-23-.json', 'w', encoding='utf-8') as output_file:
#     json.dump(items , output_file ,indent = 2)
if __name__ == '__main__':
    t1 = time.perf_counter()

    try:
        check_API_conn(PING_API)
    except Exception as e:
        print('\n-- DEBUG: API connection is failed .')

    driver = selenium_init(headless=True)
    # step 1 - get news post
    try:
        items = getRedditPostItems(driver, url, "past 24 hours")
        if latest: # filter out news articles that are posted before the execution datetime of yesterday (existing post)
            o_length = len(items)
            items = [item for item in items if pd.to_datetime(item['published_datetime'], format='%Y-%m-%dT%H:%M:%S+00:00') >= last24hours]
            print(f'\n--DEBUG: {len(items)} posts have been made in the past 24 hours, total {o_length}')
    except:
        print('\n -- DEBUG: Errors occured when collecting news/posts on reddit.')
        raise

    # step 2 - insert data into database
    try:
        for item in items:
            data = {'org_title': item['title'],
                'title': item['title'],
                'org_content': item['content'],
                'url': item['url'] + '|' + item['cmt_url'],
                'content': item['content'],
                'translated':1,
                'lang': 'EN',
                'source_id': source_id,
                'published_datetime': item['published_datetime']
            }
            try:
                response = requests.post(INSERT_API,json={'table':'dsta_db.test', 'data': data })
            except:
                print(f'\n--DEBUG: 1 post is failed to be added {str(item[url])}')
        print(f'\n--DEBUG: DB successful.')
    except Exception as e:
        print(f'\n--DEBUG: Error occured for insertion {e}')

    # step 3 - select news post that are posted in the latest 2 weeks include today
    try:
        QUERY_API = 'http://10.2.56.213:8086/query'
        response = requests.post(QUERY_API, json={'query':"SELECT article_id, url from dsta_db.test where source_id=16;"})
        json_payload = (json.loads(response.text))
    except:
        print('\n--DEBUG: selection is bug .')
    
    # step 4 - scrape news comments for a news post
    try:
        items = json_payload['result']
        for item in items:
            article_id = item['article_id']
            cmt_url = item['url'].split('|')[-1]
            try:
                comments = getRedditCommentItems(driver, cmt_url)
                print(f'\n--DEBUG: {len(comments)} no. of comments has been collected for {article_id}')
                #if latest:
                #    comments = [comment for comment in comments if pd.to_datetime(comment['cmt_published_datetime'], format='%Y-%m-%dT%H:%M:%S+00:00') >= last24hours]
                item['comments'] = comments
                time.sleep(1)
                print(f'\n--DEBUG: {len(comments)} no. of comments has been added for {article_id}')
            except Exception as e:
                print('\n', item['url'], e)
    except Exception as e:
        print('\n--DEBUG: error with json payload object, no json is fetched', e)
    
    if latest:
        for item in items:
            comments = [comment for comment in item['comments'] if pd.to_datetime(comment['cmt_published_datetime'], format='%Y-%m-%dT%H:%M:%S+00:00') >= last24hours]
            item['comments'] = comments
    
    # step 5 - insert new comments into the db
    try:
        # insert data into database
        for item in items:
            article_id = item['article_id']
            comments = item['comments']
            for comment in comments:
                data = {
                        'cmt_article_id': article_id,
                        'cmt_id' : comment['cmt_id'],
                        'cmt_replyTo' : comment['cmt_replyTo'],
                        'cmt_user': comment['cmt_user'],
                        'cmt_likes':comment['cmt_likes'],
                        'cmt_content': comment['cmt_content'],
                        'cmt_org_content': comment['cmt_content'],
                        'cmt_published_datetime': comment['cmt_published_datetime'],
                        'translated': 1,
                        'lang': 'EN',
                        'source_id': 16
                }
                try:
                    response = requests.post(INSERT_API,json={'table':'dsta_db.test_24hr_comments', 'data': data })
                    if response.status_code != 200:
                        print(response)
                        print(response.text)
                        print(data)
                        raise
                except Exception as e:
                    print(f'\n--DEBUG: comment insertion failed {e}')
        
        print(f'\n--DEBUG: DB successful for comments insertion .')

    except Exception as e:
        print('\n--DEBUG: Error occured for insertion', e) 

    driver.quit()

    t2 = time.perf_counter()
    print(f'Program took {t2-t1} seconds to complete')