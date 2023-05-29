# airflow
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


# STEPs after git pull on production environment.
1. docker-compose down -v
2. empty log folder
3. echo -e "AIRFLOW_UID=$(id -u)\nAIRFLOW_GID=0" > .env
4. docker-compose up airflow-init
5. docker-compose up -d

# whenever a new pip or init a new module in the environment
docker build . -f Dockerfile --pull --tag extending_airflow_img:latest

docker-compose up -d --no-deps --build airflow-webserver airflow-scheduler