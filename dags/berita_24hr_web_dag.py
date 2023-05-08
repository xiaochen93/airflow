#datetime
from datetime import timedelta, datetime

# The DAG object
from airflow import DAG

# Operators
from airflow.operators.dummy_operator import DummyOperator

from airflow.operators.python_operator import PythonOperator

from airflow.operators.bash_operator import BashOperator

import os

# initializing the default arguments
default_args = {
		'owner': 'xiaochen',
		'start_date': datetime(2023, 4, 6),
		'retries': 3,
		'retry_delay': timedelta(minutes=45),
        'retry_exceeded_task_duration': True,
}

#initializing the dag object
exe_web_crawlers_dag = DAG('berita_24hr_web_dag',
		default_args=default_args,
		description='The dag object to execute a series of web crawlers for data/comments collection .',
		schedule_interval= '0 12 * * *', #schedule interval to execute the task '* * * * *' '0 */12 * * *'
		catchup=False,
		tags=['berita mediacorp','news articles','24hrs']
)



task_1 = BashOperator(
    task_id="id_1",
    bash_command="echo Hello World !!!! This is berita dag",
    dag = exe_web_crawlers_dag
)

task_2 = BashOperator(
    task_id = "id_2",
    bash_command = "python /opt/airflow/src/news_comments_crawlers/crawlers/_BM_BERITA.py --name BERITA",
    execution_timeout=timedelta(minutes=15),
    dag = exe_web_crawlers_dag
)

task_1.set_downstream(task_2)