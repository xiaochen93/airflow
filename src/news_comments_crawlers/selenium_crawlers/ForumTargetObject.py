'''
The forum object follows the sequence of 
1. initalization -> 2. additional step clearance (to URL items) -> 3. scrape URL items -> 4. additional step clearance -> 5. scrape content

'''
from Functions import *

'''
The forum object follows the sequence of 
1. initalization -> 
2. additional step clearance (to URL items) -> 
3. scrape URL items -> 
4. additional step clearance -> 
5. scrape content

'''
class ForumWebCrawler:
    def __init__(self, object):
        self.object = object
        self.starting_page_url= object['starting_page_url']
        self.source_id = object['source_id']
        self.driver = selenium_init(headless=object['headless'],remote=object['remote'])
        self.driver.get(self.starting_page_url)
        self.links = []
        self.comments = []
        self.links_threshold = object['links_threshold']
        self.links_count = 0
        self.begin_dt = object['begin_datetime']
        self.end_dt = object['end_datetime']
        self.noOfDays = object['noOfDays']
        self.default_dt = datetime.now()
        self.existing_URLs = getExistingURLs(self.end_dt,noOfDays=self.noOfDays,sid=self.source_id)
        self.lang = object['lang']
        self.translated = 0
        print(f'\n-- DEBUG: Existing urls are {len(self.existing_URLs)}')
        print(f'\n-- DEBUG: Date range is from {self.begin_dt} to {self.end_dt}.')
        print(f'\n\t-- DEBUG: We are looking at {self.noOfDays} no.of days for accumlating comments.')

    def scrape_post(self, Xparam, collect_item_fn=lambda x: x, collect_article_map=lambda x: x):
        self._scrape_post_workflow(Xparam, collect_item_fn=collect_item_fn)
        # To-be-Implemented: remove duplicated URLs 

        self.links = [each for each in self.links if self.begin_dt <= each['published_datetime'] <= self.end_dt]

        print(f'\n-- DEBUG: Total no. of {len(self.links)} links has been collected. ')
        if len(self.links) > 1:
            self._scrape_post_content(Xparam, collect_article=collect_article_map)
        else:
            print(f'\n-- DEBUG: No new post will be added to the db. ')
        self.insert_to_db(self.links, label='post')



    '''
    private Function, loop through pages and scrape post url from a given forum.

    No implementation on workflow but require mapping page items.

    Input: 
        Xparam: contains xpath(s) for scrapping post on forum
            wait: the time interval which awaits the page to be completely loaded
            XP_CLOSE_ADS: the xpath(s) for close Ads button, multiple items clickable
            XP_POST_LISTING: the xpath for post listing on a page
            XP_POST_NEXT_BTN: the xpath for next button on the page, single clickable

        map_fn: mapping function to return a scrapped item
    
    '''
    def _scrape_post_workflow(self, Xparam, collect_item_fn=lambda x: x):
        SEARCHING = True
        while SEARCHING:
            _search_begin = time.perf_counter()
            # check if the page is loaded 
            wait = WebDriverWait(self.driver, Xparam['wait'])
            page_loaded = wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            print("\n-- DEBUG: Page loaded successfully!")
            #1. close pop-up ads
            self.bypass_ads(Xparam['XP_CLOSE_ADS'],i=1)

            post_items = getPostListings(self.driver, Xparam['XP_POST_LISTING'])
            print(f'\n-- DEBUG: Total {len(post_items)} no. of elements on the table .')
            #3. loop and get each post item from the table
            many_posts = [collect_item_fn(post, Xparam) for post in post_items]

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
    private function, scrape the inital post/article for that post from a given discussion (post) URL.

    No implementation on workflow but require mapping page items.

    Input: 
        Xparam: The dictionary as above, containing the xpath for post elements.

        map_fn: mapping function to return a scrapped article/original post in its original language. 
                The output is '' by default.
    '''
    def _scrape_post_content(self, Xparam, collect_article=lambda x: x):
        del_idxes = []
        for idx, item in enumerate(self.links):
            # get the original article_content
            org_content = collect_article(driver=self.driver, xpath_content=Xparam['XP_POST_ART'], url=item['url'])
            time.sleep(Xparam['wait']/2)
            if (org_content == '' or len(org_content) < 20 or org_content is None):
                del_idxes.append(idx)
                continue
            item['org_content'] = org_content
            if "cmt_url" in item.keys():
                item['url'] = item['url'] + '|' + item['cmt_url']
                del item['cmt_url']
            if "published_datetime" in item.keys() and item['published_datetime'] != '':
                item['published_datetime'] = (item['published_datetime'].strftime("%Y-%m-%d %H:%M:%S"))
            else:
                item['published_datetime'] = str(item['published_datetime'])
            
            item['translated'] = self.translated
            item['lang'] = self.lang
            item['source_id'] = self.source_id

            self.links[idx] = item
            

        
        # delete the post item with empty content
        for del_idx in del_idxes:
            self.links.pop(del_idx)
    


    '''
    Insert one record at a time to db via provided API.

    No implementation

    Input:
        Label: db name e.g. post or comments
    
    '''
    def insert_to_db(self, items, label=''):
        t_name = 'dsta_db.test' if label == 'post' else 'dsta_db.test_24hr_comments'
        
        for idx, item in enumerate(items):
            try:
                response = requests.post(INSERT_API,json={'table':t_name, 'data': item })       
            except Exception as e:
                print(f'\n--DEBUG: 1 post is failed to be added {item["url"]} - index {idx}')
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
        #print('\n--DEBUG: If a post datetime is a string or empty ? ',item[dt_label]=="" or isinstance(item[dt_label], str))
        #print(f'\n\t--DEBUG: {item[dt_label]}')
        #print(f'\n--DEBUG: If a post datetime is in range {self.begin_dt} - {self.end_dt} ? ', item[dt_label] < self.begin_dt or item[dt_label] > self.end_dt)
        
        if (item[dt_label]=="" or isinstance(item[dt_label], str) or item[dt_label] < self.begin_dt or item[dt_label] > self.end_dt):
            self.links_count = self.links_count + 1 #accumulate  
        elif check_spams(item['org_title']): # the title of a post/article is mandatory.
            pass #do nothing
        elif item['url']=='' or (item['url'] in self.existing_URLs): # url already exists or empty
            pass
        else:
            self.links.append(item)