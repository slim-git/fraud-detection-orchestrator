import os
import logging
import requests
from airflow import DAG
from airflow.decorators import task
import json
import time
from dotenv import load_dotenv
from common import check_db_connection, default_args
from datetime import datetime, timedelta
from airflow.utils.task_group import TaskGroup
from airflow.operators.bash import BashOperator
from http.client import (
    TOO_MANY_REQUESTS, # 429
    INTERNAL_SERVER_ERROR # 500
)

# Load environment variables from .env file
load_dotenv()

DEFAULT_TRANSACTION_PRODUCER_ENDPOINT = "https://charlestng-real-time-fraud-detection.hf.space/current-transactions"
TRANSACTION_PRODUCER_ENDPOINT = os.getenv("TRANSACTION_PRODUCER_ENDPOINT", DEFAULT_TRANSACTION_PRODUCER_ENDPOINT)

@task(task_id="pull_transaction")
def _pull_transaction(ti, prefix: str = ''):
    """
    Pulls a new transaction from the fraud detection service and pushes it to XCom.
    """
    def get_current_transaction():
        if TRANSACTION_PRODUCER_API_KEY := os.getenv("TRANSACTION_PRODUCER_API_KEY"):
            headers = {'Authorization': TRANSACTION_PRODUCER_API_KEY}
        
        return requests.get(url=DEFAULT_TRANSACTION_PRODUCER_ENDPOINT, headers=headers)
    
    response = get_current_transaction()

    # If status code is 429 or 500, wait for a few seconds and retry
    if response.status_code in [TOO_MANY_REQUESTS, INTERNAL_SERVER_ERROR]:
        waiting_time = 15
        logging.warning(f"Rate limit exceeded. Retrying in {waiting_time} seconds...")
        time.sleep(waiting_time)
        response = get_current_transaction()

    # Check response status code
    response.raise_for_status()
    
    # Load the JSON data
    str_data = response.json()
    data = json.loads(str_data)

    transaction_dict = {key: value for key, value in zip(data['columns'], data['data'][0])}

    # Push the transaction dictionary to XCom
    ti.xcom_push(key=f"{prefix}_transaction_dict", value=transaction_dict)
    
    logging.info(f"Fetched data: {transaction_dict}")

@task(task_id="push_transaction")
def _push_transaction(ti, prefix: str = ''):
    """
    Pushes the transaction data to the fraud detection pipeline.
    This function is called after pulling the transaction data.
    It maps the transaction data to the required parameters for the API call.
    """
    params_mapping = {
        'transaction_number': 'trans_num',
        'transaction_amount': 'amt',
        'transaction_timestamp': 'current_time',
        'transaction_category': 'category',
        'transaction_is_real_fraud': 'is_fraud',
        'customer_credit_card_number': 'cc_num',
        'customer_first_name': 'first',
        'customer_last_name': 'last',
        'customer_gender': 'gender',
        'merchant_name': 'merchant',
        'merchant_latitude': 'merch_lat',
        'merchant_longitude': 'merch_long',
        'customer_latitude': 'lat',
        'customer_longitude': 'long',
        'customer_city': 'city',
        'customer_state': 'state',
        'customer_zip': 'zip',
        'customer_city_population': 'city_pop',
        'customer_job': 'job',
        'customer_dob': 'dob',
        'is_fraud': 'is_fraud',
    }

    # Pull the transaction dictionary from XCom
    transaction_dict = ti.xcom_pull(f"transactions.{prefix}.pull_transaction", key=f"{prefix}_transaction_dict")

    # Check if the transaction dictionary is empty
    if not transaction_dict:
        logging.error("No transaction data found.")
        return
    
    # Call the fraud detection pipeline with the transaction dictionary
    data = {key: transaction_dict[value] for key, value in params_mapping.items()}
    
    headers = {'Content-Type': 'application/json'}
    
    if TRANSACTION_CONSUMER_API_KEY := os.getenv("TRANSACTION_CONSUMER_API_KEY"):
        headers['Authorization'] = TRANSACTION_CONSUMER_API_KEY
    
    api_response = requests.post(
        url='https://slimg-fraud-detection-service-api.hf.space/transaction/process',
        data=json.dumps(data),
        headers=headers,
    )

    # Check response status code
    api_response.raise_for_status()

    # Load the JSON data
    data = api_response.json()

    logging.info(f"Fraud detection response: {data}")

# Copy default_args from the original code
dag_args = default_args.copy()
dag_args['start_date'] = datetime.now() - timedelta(minutes=2)

with DAG(dag_id="process_new_transaction",
         default_args=dag_args,
         max_active_runs=1,
         schedule_interval="*/1 * * * *") as dag:
    """
    DAG to fetch a new transaction and call the fraud detection pipeline
    """
    check_db = check_db_connection()

    with TaskGroup(group_id='transactions') as all_tasks:
        for i in range(1, 4):
            group = f'transaction_{i}'
            with TaskGroup(group_id=group) as transaction_group:
                pull = _pull_transaction(prefix=group)
                push = _push_transaction(prefix=group)
                
                pull >> push

    end_dag = BashOperator(task_id="end_dag", bash_command="echo 'End!'")
    
    check_db >> all_tasks >> end_dag
