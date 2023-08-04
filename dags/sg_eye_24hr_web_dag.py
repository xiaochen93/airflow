#datetime
from datetime import timedelta, datetime, date

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
start_date = datetime(
    start_date.year,
    start_date.month,
    start_date.day,
    12,
    0,
    0,
    tzinfo=beijing_timezone)

timeout = timedelta(minutes=120)

# initializing the default arguments
default_args = {
		'owner': 'xiaochen',
		'start_date': start_date,
		'retries': 10,
		'retry_delay': timedelta(minutes=5),
        'retry_exceeded_task_duration': True,
        'execution_timeout': timeout,
        'dagrun_timeout ' : timeout
}

#initializing the dag object
exe_web_crawlers_dag = DAG('CN_sg_eye_web_dag',
		default_args=default_args,
		description='The dag object to execute a series of web crawlers for data/comments collection .',
		schedule_interval= '0 12 * * *', #schedule interval to execute the task '* * * * *' '0 */12 * * *'
		catchup=False,
		tags=['CN','comments','24hrs', '14 days']
)

task_1 = BashOperator(
    task_id="id_1",
    bash_command="echo Hello World !!!! This is SG-Eye dag",
    
    dag = exe_web_crawlers_dag
)

task_2 = BashOperator(
    task_id = "id_2",
    bash_command = "python /opt/airflow/src/news_comments_crawlers/selenium_crawlers/SG-EYE.py --remote=True",
    execution_timeout=timeout,
    dag = exe_web_crawlers_dag
)

task_1.set_downstream(task_2)