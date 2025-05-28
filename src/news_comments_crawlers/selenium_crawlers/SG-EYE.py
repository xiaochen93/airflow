from Functions import *

import warnings

from datetime import datetime, timedelta

import argparse

url= "https://www.xinjiapoyan.com/forum-jishixinwen-1.html"

INSERT_API = 'http://10.2.56.213:8086/insert'

PING_API = 'http://10.2.56.213:8086/ping'

QUERY_API = 'http://10.2.56.213:8086/query'

source_id = 5

table = 'dsta_db.test'

latest=True

parser = argparse.ArgumentParser(description="Parameters to execute a web crawler")

parser.add_argument(
        '--remote',
        type=str,
        help="True if running on docker else False",
        required=True
)

xpath_post_listings = "//table[contains(@id,'thread')]/tbody[not(contains(@class, 'emptb'))]"

xpath_title = ".//descendant-or-self::th[contains(@class,'new') or contains(@class,'common')]//a[contains(@class, 'xstt')]" #post title

xpath_author = ".//descendant-or-self::td[contains(@class,'by')]//a"

xpath_last_modified_attr = ".//descendant-or-self::td[contains(@class,'byy')]/em//span[boolean(@title)]" #

xpath_last_modified_text = ".//descendant-or-self::td[contains(@class,'byy')]/em/span" #

xpath_no_of_cmts = ".//descendant-or-self::td[contains(@class,'num')]/a"

xpath_views = ".//descendant-or-self::td[contains(@class,'num')]/span[not(string-length(@*))]"

xpath_url = ".//descendant-or-self::td[contains(@class,'icn')]/a" #the url for the post and associated comments

xpath_main_page_next = "//div[contains(@class, 'pg')]//a[contains(@class, 'nxt')]"

xpath_sub_page_next = "//div[contains(@class, 'pg')]//a[contains(@class, 'nxt')]"

def convert_datetime(datetime_str):
    from datetime import datetime
    # Define the input datetime format
    input_format = "%H:%M'T'%Y-%m-%d"

    # Parse the datetime string into a datetime object
    parsed_datetime = datetime.strptime(datetime_str, input_format)

    # If you want to convert it back to a different format, you can use strftime
    # For example, converting it to "YYYY-MM-DD HH:MM:SS" format
    output_format = "%Y-%m-%d %H:%M:%S"
    formatted_datetime = parsed_datetime.strftime(output_format)

    return formatted_datetime


def getPostListingItems(post_listing):
    try:
        title = post_listing.find_element("xpath", xpath_title).text
    except Exception as e:
        #print('\n--',e)
        title = ''
    
    try:
        url = post_listing.find_element("xpath", xpath_url).get_property('href')
    except Exception as e:
        url = ''        
    
    try:
        author = post_listing.find_element("xpath", xpath_author).text
    except Exception as e:
        author = ''
        
    try:
        last_modified_1 = post_listing.find_element("xpath", xpath_last_modified_text).text
    except Exception as e:
        last_modified_1 = ''
        
    try:
        last_modified_2 = post_listing.find_element("xpath", xpath_last_modified_attr).get_property('title')
    except Exception as e:
        last_modified_2 = ''
        
    date = last_modified_1 +'T'+ last_modified_2
    
    try:
        no_of_cmts = post_listing.find_element("xpath", xpath_no_of_cmts).text
    except Exception as e:
        no_of_cmts = ''
    
    try:
        views = post_listing.find_element("xpath", xpath_views).text
    except Exception as e:
        views = ''
        
    #print('\n--DEBUG:',title,url,author,no_of_cmts,views,date)
    
    return {
        'title':title.strip(),
        'p_url':url.strip(),
        'author':author.strip(),
        'no_of_cmts':no_of_cmts.strip(),
        'views': views.strip(),
        'datetime': re.sub('[\u4E00-\u9FFF]+','',date.strip())
    }

if __name__ == '__main__':
    t1 = time.perf_counter()
    args = parser.parse_args()
    remote = eval(args.remote)

    today, last_14_days =get_datetime(days=14,hours=0)

    END_AT, BEGIN_FROM = get_datetime(days=1,hours=1)
    
    # instantiate the web driver
    driver = selenium_init(headless=True, remote=remote)
    driver.get(url)
    print(f'\n-- DEBUG: BEGIN DATETIME - {BEGIN_FROM} and END DATETIME - {END_AT} .')

    try:
        out = select_existing_items(QUERY_API, today, last_14_days, source_id, table=table, items=['article_id', 'URL', 'source_id'])
        URLs = set([each['URL'] for each in out])
        
    except Exception as e:
        URLs = set()
        print('\n-- DEBUG: Selection of URLs error with ', e)
    print('\n-- DEBUG: Existing URLs are : ', URLs)

    # get new post made within 24 hours
    def get_post_links():
        linkscache = []
        # scrape news links from 
        SEARCHING, count, out_of_range, threshold = True, 0, 0, 100
        while SEARCHING:
            items = getPostListings(driver, xpath_post_listings)
            for item in items:
                out_items = getPostListingItems(item)
                try:
                    no_of_cmts = int(out_items['no_of_cmts'])
                except:
                    no_of_cmts = 0

                if no_of_cmts > 0:
                    try:
                        #date = [each for each in out_items['datetime'].split('T') if each.find('-')!=-1][0]
                        date = [each for each in out_items['datetime'].split('T') if each.find('-')!=-1][0]
                        date = datetime.strptime(date, '%Y-%m-%d')
                        out_items['date'] = date

                    except Exception as e:
                        print('\n null date attribute:', e)
                        continue

                    # determine if the post is within the datetime
                    #print(f'{date.date()} - {BEGIN_FROM.date()} - {END_AT.date()}', date.date() >= BEGIN_FROM.date() and date.date() <= END_AT.date())
                    if date.date() >= BEGIN_FROM.date() and date.date() <= END_AT.date():
                        linkscache.append(out_items)
                        count = count + 1
                        print('\n\t-- {} reocords have been collected on SG-Eye.'.format(count))

                    else:
                        out_of_range = out_of_range + 1

                    if out_of_range >= threshold:
                        SEARCHING = False
                        break
                else:
                    pass #do nothing
            try:
                goNextPage(driver, xpath_main_page_next)
            except Exception as e:
                SEARCHING = False
        return linkscache
    items = get_post_links()

    # step 2 - insert data into database
    try:
        for item in items:
            if not (item['p_url'] in URLs):
                data = {
                    'org_title': item['title'],
                    'title': item['title'],
                    'org_content': item['title'],
                    'url': item['p_url'],
                    'content': '',
                    'translated':0,
                    'lang': 'CN',
                    'source_id': source_id,
                    'published_datetime': (item['datetime']).strip().split('T')[-1] + ' 00:00:00'
                }
                try:
                    response = requests.post(INSERT_API,json={'table':table, 'data': data })
                except Exception as e:
                    print(f'\n--DEBUG: 1 post is failed to be added {e}')
        
        print(f'\n--DEBUG: DB successful.')
    except Exception as e:
        print(f'\n--DEBUG: Error occured for insertion {e}')
    
    # step 3 - select news post that are posted in the latest 2 weeks include today
    try:
        out = select_existing_items(QUERY_API, today, last_14_days, source_id, table=table, items=['article_id', 'URL', 'source_id'])
        dicts = dict({each['URL']: each['article_id'] for each in out})
        URLs = list(dicts.keys())
    except Exception as e:
        URLs = list()
        print('\n-- DEBUG: Selection of URLs error with ', e)
    #print('\n-- DEBUG: Existing URLs are : ', URLs)

    # step 4 - scrape comments for each URL
    def get_comments(linkscache):
        xpath_posts = "//div[contains(@id, 'postlist')]//div[contains(@id,'post_') and not(contains(@id,'post_rate') or contains(@id,'post_new'))]" #the content of the post
        out_comments = []

        for item in tqdm(linkscache):
            driver.get(item)    
            #print('\n-- DEBUG: post_url - ',item['p_url'])
            count = 0
            comments = []    
            while True:
                cmts = getPostListings(driver,xpath_posts)
                for post in cmts:
                    xpath_c_id = ""
                    try:
                        c_id = post.get_attribute('id').split('_')[-1]
                    except Exception as e:
                        c_id = 'n/a'
                    #print('-- DEBUG: c_id :',c_id)            
                    #p_id
                    xpath_p_id = ".//descendant-or-self::div[contains(@class, 'pct')]//div[contains(@class, 'quote')]//a"
                    
                    pattern_p_id = "pid=([0-9]+)"
                    
                    try:
                        c_p_id = post.find_element("xpath", xpath_p_id).get_property('href')
                        match = re.search(pattern_p_id, c_p_id, re.IGNORECASE)
                        
                        if match:
                            c_p_id = match.group(1)
                        
                    except Exception as e:
                        c_p_id = ""
                    #datetime
                    xpath_c_datetime = ".//descendant-or-self::div[contains(@class, 'pti')]/div[contains(@class, 'authi')]/em/span"
                    
                    try:
                        c_datetime = post.find_element("xpath", xpath_c_datetime).get_attribute('title')                
                    #print('-- DEBUG: datetime :',c_datetime)                     
                        
                    except Exception as e:
                        c_datetime = "n/a"
                    #print('-- DEBUG: datetime :',c_datetime) 
                    
                    #user
                    xpath_c_user = ".//descendant-or-self::div[contains(@class, 'pi')]/div[contains(@class, 'authi')]/a"
                    try:
                        c_user = post.find_element("xpath", xpath_c_user).text      
                    except Exception as e:
                        c_user = "n/a"         
                    #print('-- DEBUG: user :',c_user)   
                    
                    #comment
                    xpath_comment = ".//descendant-or-self::div[contains(@class,'pcb')]"
                    try:
                        c_text = post.find_element("xpath", xpath_comment).text
                        c_text = re.sub('来自: (Android|iPhone)客户端','',c_text)
                        c_text = re.sub('\s+', ' ', c_text.strip())
                    except Exception as e:
                        #print('\n-- DEBUG: something wrong with scraping comments, ',e)
                        c_text = 'n/a'
                    #print('-- DEBUG: text :',c_text)             
                    
                    comments.append({
                        'cmt_id' : c_id,
                        'cmt_replyTo' : c_p_id,
                        'cmt_user': c_user,
                        'cmt_content': c_text,
                        'cmt_score': '',
                        'cmt_published_datetime': c_datetime            
                    })

                try:
                    goNextPage(driver, xpath_main_page_next)
                except:
                    #print('\n-- Scraping completed for post:',item['title'])
                    break
            out_comments.append(comments)
        return out_comments
    comments = get_comments(URLs)
    # article_id : comments
    comments = {dicts[url]: comments[idx] for idx, url in enumerate(URLs)}
    # get existing cmt_id
    if latest:
        try:
            # select the cmt_id for the existing post
            cmt_id_items = select_existing_items(QUERY_API, today, '', source_id, dt='cmt_published_datetime', table='dsta_db.test_24hr_comments', items=['cmt_id'])
            cmt_id_items = set([item['cmt_id'].strip() for item in cmt_id_items])
            comments = {article_id: [comment for comment in comments if not (comment['cmt_id'] in cmt_id_items)] for article_id, comments in comments.items()}
            print(f'\n--DEBUG: {sum([len(each) for each in comments.values()])} no. of comments (new) will be added to the database .')
        except:
            print(f'\n--DEBUG: Insert all comments .')
            pass
    # insertion of comments into database
    for article_id, many_comments in comments.items():
        for comment in many_comments:
            data = {
                    'cmt_article_id': article_id,
                    'cmt_id' : comment['cmt_id'],
                    'cmt_replyTo' : comment['cmt_replyTo'],
                    'cmt_user': comment['cmt_user'],
                    #'cmt_likes':comment['cmt_likes'],
                    'cmt_content': comment['cmt_content'],
                    'cmt_org_content': comment['cmt_content'],
                    'cmt_published_datetime': comment['cmt_published_datetime'],
                    'translated': 0,
                    'lang': 'CN',
                    'source_id': source_id
            }
            try:
                response = requests.post(INSERT_API,json={'table':'dsta_db.test_24hr_comments', 'data': data })
                if response.status_code != 200:
                    print('\n\t--DEBUG:',response)
                    print('\n\t--DEBUG:',response.text)
                    print('\n\t--DEBUG:',data)
                    raise
            except Exception as e:
                print(f'\n--DEBUG: comment insertion failed {e} .')
    t2 = time.perf_counter()
    print(f'Program took {t2-t1} seconds to complete')