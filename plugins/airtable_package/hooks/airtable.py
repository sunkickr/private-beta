import json
import logging
import os
import requests
from requests.auth import HTTPBasicAuth
import urllib.parse
from typing import Any, Callable, Dict, Optional, Union

from airflow.hooks.base import BaseHook

logger = logging.getLogger(__name__)

class AirTableHook(BaseHook):
    """
    AirTable Hook that interacts with an HTTP endpoint the Python requests library.

    :param method: the API method to be called
    :type method: str
    :param airtable_conn_id: connection that has the base API url i.e https://www.google.com/
        and optional authentication credentials. Default headers can also be specified in
        the Extra field in json format.
    :type airtable_conn_id: str
    :param auth_type: The auth type for the service
    :type auth_type: AuthBase of python requests lib
    """

    conn_name_attr = 'conn_airtable'
    default_conn_name = 'http_default'
    conn_type = 'http'
    hook_name = 'HTTP'

    def __init__(
        self,
        airtable_conn_id: str = default_conn_name,
        auth_type: Any = HTTPBasicAuth,
    ) -> None:
        super().__init__()
        self.airtable_conn_id = airtable_conn_id
        self.base_url: str = ""
        self.auth_type: Any = auth_type

    def get_conn(self, table_name: str, headers: Optional[Dict[Any, Any]] = None) -> requests.Session:
        """
        Returns http session to use with requests.

        :param headers: additional headers to be passed through as a dictionary
        :type headers: dict
        """
        session = requests.Session()

        if self.airtable_conn_id:
            conn = self.get_connection(self.airtable_conn_id)

            if conn.host and "://" in conn.host:
                self.base_url = os.path.join(conn.host, table_name)
            else:
                # schema defaults to HTTP
                schema = conn.schema if conn.schema else "http"
                host = conn.host if conn.host else ""
                self.base_url = schema + "://" + host

        session.headers.update({"Authorization": "Bearer " + conn.password, "Content-Type": "application/json"})
        if headers:
            session.headers.update(headers)
        
        return session

    def run_with_update(
        self,
        table_name: Optional[str] = None,
        endpoint: Optional[str] = None,
        data: Optional[Union[Dict[str, Any], str]] = None,
        headers: Optional[Dict[str, Any]] = None,
        filter_by_fields: list = [],
        **request_kwargs: Any,
    ) -> Any:
        r"""
        Performs the request


        :param table_name: Name of table in AirTable
        :type table_name: str
        :param endpoint: the endpoint to be called i.e. resource/v1/query?
        :type endpoint: str
        :param data: payload to be uploaded or request parameters
        :type data: dict
        :param headers: additional headers to be passed through as a dictionary
        :type headers: dict
        :param filter_by_fields: filter where specified AirTable column names match payload's
        :type filter_by_fields: dict
        """

        session = self.get_conn(table_name, headers)
        
        # AirTable filter expression.
        # Filter by unique value in the fields listed in `filter_by_fields`
        querystring = ("filterByFormula=AND(%s)" % urllib.parse.quote_plus(','.join(list(map(lambda x: f"{{{x}}}='{data[x]}'", filter_by_fields))))) if len(filter_by_fields) >= 1 else ''
        
        try:
            r = requests.get(self.base_url, headers=session.headers, params=querystring)
            matching_records = r.json()['records']
        except Exception as e:
            logger.error("Failed to query AirTable API.")
            logger.error(e)
            return e

        # PATCH if record id exists, else POST
        if len(matching_records) == 0:
            logger.info('Posting...')
            r = requests.post(self.base_url, 
                headers=session.headers, 
                json={"records": [{"fields": data}],"typecast": True})
        else:
            logger.info('Patching...')
            record_id = matching_records[0]['id']
            r = requests.patch(self.base_url,
                headers=session.headers,
                json={"records": [{"id": record_id,"fields": data}],"typecast": True})
        
        if r.status_code == 200:
            return json.dumps(r.json())
        else:
            logger.error(r.json())
            raise Exception('%s error when fetching %s' % (r.status_code, self.base_url))
