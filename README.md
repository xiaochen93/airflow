# Major Update Airflow (excluding minor maintaince)
2024-08-29
Update DSTA API for “update" related query and update the automation script.

2024-08-21
Update Zaobao web dag for new HTML tagging name

2024-08-15
Update Kaskus web dag for transpassing a notification pop up.

2024-08-07
Update data migrartion function for accumlating post for at least 3 days.
Include sql runner into the data handling part for generating dashboard and marking records.

2024-07-26
Update the Kaskus_v2 crawler due to another major update. 

2024-05-29
Update the Kaskus_v2 crawler, trying to get data from 2022-06-01 to 2022-12-31

2024-05-14
Update the data processing tools for data migration.

2024-05-10
Update data processing tools if translated input is too large for storing.
Update data processing tools for error handling.

2024-05-07
Update REDDIT and SG-EYE

2024-05-03
Build translation and data processing tools
python data_processing.py --begain_datetime="2024-03-01 00:00:00" --end_datetime="2024-03-01 02:00:00"

2024-05-01
Update Kasku web crawler as the HTML layout got updated for scraping links.

2024-03-14
Update Kasku web crawler for scraping posts within timeframe.

Update Kasku web crawler for scraping post(s) within 24hours.
- change the sequence of workflow -> attached attribute(s) -> check for duplicates
- create a cmt_id for "" post and post that nested under a main post as the forum does not provide this naming.

2024-02-08
Update the Kasku web crawler for collecting BI comments.
- remove duplicated article links
- remove duplicated comment by ids

Update the print out message for remove_duplicate_cmt function -> to not print out SQL error .

2024-01-31
Update the Kasku web crawler for collecting BI comments.
- updated class signature and method signature.
- updated crawling of comments from a single page.
- updated the execution work flow for collecting data witin 24 hours.
- updated the diagram for the web crawlers.

2023-12-05
Update the Kasku web crawler for data on BI forum.
- implemented xpath for scrapping post url & title.
- implemented web crawlers for URLs and main post on discussion
- separated the workflow from the web crawler.

2023-11-21
Update the following items on py code and airflow dag:
- consistent the naming for each dag, no numeric prefix in the names.
- increase the timeout to 300 secodns for selenium driver.
- add new setting for disable notifications for selenium driver.
- update zaobao main as duplicated main is provided to trigger memory overflow.
- update selection query due to update of sqlachlemy package, the previous accessing method is deprecated.

2023-09-28
Updated the dag activation time and make them running sequentially.

2023-09-27
Configured the default attribute of translated to be "0". Every crawled document would require additional processing.
- English - CNA, REDDIT
- Chinese - Zaobao, SG-EYE
- Malay   - Berita, B-CARI

Updated the dag of B-Cari to every 24 hours not 12 hours.

2023-07-27
Configured the automated start-date to tommorrow, otherwise the dags will not be triggered.

2023-07-26
Integrated SG-Eye into the platform
Solved the bug for scraing duplicated post, filtering URL for the post and cmt_id for the comment. (tested)

2023-06-14:
improved SQL query for comments and posts selection. It is now select the latest two weeks of posts (news articles) on the forum.
improved function for API access - selecting existing dataframe
configured the maximum timeout for selenium at 2hours due to the size of the data.

2023-5-29:
configured selenium max browser session and re-try overriding parameters.

2023-5-24:
deployed REDDIT24 web crawler to server, need to convert notebook to .py 
    - scrape news post that made in last 24 hours only.
    - pull news post from database within a week and
    - scrape news comments that made in last 24 hours only.

fixed timezone information for automation dag

deployed selenium standalone web browse

2023-5-12:
update dag and file structure

2023-5-5:
deploy the zaobao web crawler to server with pagination and controlled by datetime parameters

2023-4-23:
deploy the cna web crawler to server (version 2) without pagination

# Future:
1. implement pagination on CNA web crawlers.
2. deploy the translation engine as the 3rd task for non-English language web crawlers.
3. do not add duplicated content while running the crawler on the daily basis.
4. select data based on time range.


# STEPs after git pull on production environment.
1. docker-compose down -v
2. empty log folder
3. echo -e "AIRFLOW_UID=$(id -u)\nAIRFLOW_GID=0" > .env
4. docker-compose up airflow-init
5. docker-compose up -d

# whenever a new pip or init a new module in the environment
docker build . -f Dockerfile --pull --tag extending_airflow_img:latest

docker-compose up -d --no-deps --build airflow-webserver airflow-scheduler

# git process
git add .
