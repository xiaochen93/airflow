#datetime
from datetime import timedelta, datetime

# The DAG object
from airflow import DAG

# Operators
from airflow.operators.dummy_operator import DummyOperator

from airflow.operators.python_operator import PythonOperator

from airflow.operators.bash_operator import BashOperator

import os

import pytz

# Get the Beijing time zone
beijing_timezone = pytz.timezone('Asia/Shanghai')

start_date = datetime.now(beijing_timezone)

# Calculate tomorrow's date
start_date = start_date - timedelta(days=1)

# Create a new datetime object for tomorrow at 12 PM
_start_date = datetime(
    2023,
    8,
    1,
    12,
    30,
    0,
    tzinfo=beijing_timezone)

# initializing the default arguments
default_args = {
		'owner': 'xiaochen',
		'start_date': _start_date,
		'retries': 10,
		'retry_delay': timedelta(minutes=5),
        'retry_exceeded_task_duration': True,
}

#initializing the dag object
exe_web_crawlers_dag = DAG('CN_zaobao_24hr_web_dag',
		default_args=default_args,
		description='The dag object to execute a series of web crawlers for data/comments collection .',
		schedule_interval= '30 2 * * *', #schedule interval to execute the task '* * * * *' '0 */12 * * *'
		catchup=False,
		tags=['Zaobao','news articles','24hrs']
)



task_1 = BashOperator(
    task_id="id_1",
    bash_command="echo Hello World !!!! This is zaobao dag",
    retries=4,
    retry_delay=timedelta(minutes=3),
    dag = exe_web_crawlers_dag
)

task_2 = BashOperator(
    task_id = "id_2",
    bash_command = "python /opt/airflow/src/news_comments_crawlers/crawlers/_CN_ZB.py --name ZAOBAO",
    execution_timeout=timedelta(minutes=15),
    retries=4,
    retry_delay=timedelta(minutes=3),
    dag = exe_web_crawlers_dag
)

task_1.set_downstream(task_2)