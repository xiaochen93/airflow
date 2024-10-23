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

start_date = datetime.now(beijing_timezone).date()

# Calculate tomorrow's date
start_date = start_date + timedelta(days=1)

# Create a new datetime object for tomorrow at 12 PM
_start_date = datetime(
    2023,
    8,
    1,
    10,
    0,
    0,
    tzinfo=beijing_timezone)

timeout = timedelta(minutes=180)

# initializing the default arguments
default_args = {
		'owner': 'xiaochen',
		'start_date': _start_date,
		'retries': 10,
		'retry_delay': timedelta(minutes=5),
        'retry_exceeded_task_duration': True,
        'execution_timeout': timeout,
        'dagrun_timeout ' : timeout
}

#initializing the dag object
exe_web_crawlers_dag = DAG('DATA_Handling_dag',
		default_args=default_args,
		description='The dag object to execute: 1. data translation -> 2. data processing -> 3. data migration .',
		schedule_interval= '30 3 * * *', #schedule interval to execute the task '* * * * *' '0 */12 * * *'
		catchup=False,
		tags=['translation','cleaning','migration', '24hrs' 'temp -> avaliable']
)

CURRENT_DATETIME = datetime.now(beijing_timezone).date().strftime("%Y-%m-%d") + ' 23:59:59'
PREVIOUS_DATETIME = (datetime.now(beijing_timezone).date() - timedelta(days=90)).strftime("%Y-%m-%d") + ' 00:00:00'

task_1_script = f'python /opt/airflow/src/news_comments_crawlers/others/data_processing.py --begain_datetime="{PREVIOUS_DATETIME}" --end_datetime="{CURRENT_DATETIME}" '
task_1 = BashOperator(
    task_id = "id_1_translation_cleaning",
    bash_command = task_1_script,
    execution_timeout=timeout,
    dag = exe_web_crawlers_dag
)

task_2_script = f'python /opt/airflow/src/news_comments_crawlers/others/data_migration.py --limit=3000'
task_2 = BashOperator(
    task_id = "id_2_data_migration",
    bash_command = task_2_script,
    execution_timeout=timeout,
    dag = exe_web_crawlers_dag
)

task_3_script = f'python /opt/airflow/src/news_comments_crawlers/others/data_sql_runner.py'
task_3 = BashOperator(
    task_id = "id_3_data_sql_runner",
    bash_command = task_3_script,
    execution_timeout=timeout,
    dag = exe_web_crawlers_dag
)

task_1 >> task_2 >> task_3
