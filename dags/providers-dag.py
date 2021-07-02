from datetime import datetime, timedelta
from typing import Dict
import requests
import logging

from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.operators.dummy_operator import DummyOperator
from plugins.airtable_package.hooks.airtable import AirTableHook

log = logging.getLogger(__name__)


default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
    'start_date': datetime(2021, 1, 1),
    'execution_timeout': timedelta(minutes=10),
    'dagrun_timeout': timedelta(minutes=2),
}

@dag('unoffical_providers_dag',
     schedule_interval='@daily',
     default_args=default_args,
     catchup=False,
     tags=['github scrape'],
     concurrency=60,
     max_active_runs=1)
def unoffical_providers_dag():

    # Start the pipeline.
    t0 = DummyOperator(
        task_id='start'
    )

    @task
    def get_plugin_list() -> Dict:
        headers = {"Authorization": "token %s" % Variable.get('github_api_token')}
        url = 'https://api.github.com/search/repositories?q=airflow+provider&per_page=100'
        page=1
        X = True
        plugins =[]
        while X == True:
            res = requests.get(url + '&page=' + str(page), headers=headers)
            print(res.json())
            plugins.extend(res.json()['items'])
            if len(res.json()['items']) == 100:
                page += 1
            else:
                X = False

          
        return {"plugins": plugins}
    
    @task
    def transform_plugin_list(response: Dict) -> Dict:

        records = []

        for plugin in response['plugins']:


            record = {
                "name": plugin['name'],
                "html_url": plugin['html_url'],
                "api_url":plugin['url'],
                "description": plugin['description'],
                "size": plugin['size'],
                "stargazers_count": plugin['stargazers_count'],
                "watchers_count": plugin['watchers_count'],
                "forks_count": plugin['forks_count'],
                "score": plugin['score'],
                "open_issues_count": plugin['open_issues_count']
            }

            records.append(record)
        
        return {"records": records}

    @task
    def send_to_airtable(response: Dict):
        
        table_name = 'UNOFFICAL_PROVIDERS'
        endpoint = None
        headers = {}
        filter_by_fields = ['name', 'html_url']
        hook = AirTableHook(airtable_conn_id='conn_airtable')

        for data in response['records']:
            response = hook.run_with_update(table_name, endpoint, data, headers, filter_by_fields)

            log.info(response)

    send_to_airtable(transform_plugin_list(t0 >> get_plugin_list()))

dag = unoffical_providers_dag()