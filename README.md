# airflow

2023-5-5:
deploy the zaobao web crawler to server with pagination and controlled by datetime parameters

2023-4-23:
deploy the cna web crawler to server (version 2) without pagination

#TO-DO:
1. implement pagination on CNA web crawlers.
2. deploy the translation engine as the 3rd task for non-English language web crawlers.


# STEPs after git pull on production environment.
1. docker-compose down -v
2. empty log folder
3. echo -e "AIRFLOW_UID=$(id -u)\nAIRFLOW_GID=0" > .env
4. docker-compose up airflow-init
5. docker-compose up -d


docker build . -f Dockerfile --pull --tag extending_airflow_img:latest