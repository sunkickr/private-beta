import json
from typing import Any, Callable, Dict, Optional

from airflow.exceptions import AirflowException
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults

from plugins.airtable_package.hooks.airtable import AirTableHook


class AirTableOperator(BaseOperator):
    """
    Calls an endpoint on an HTTP system to execute an action.

    :param airtable_conn_id: connection to run the operator with
    :type airtable_conn_id: str
    :param endpoint: The relative part of the full url. (templated)
    :type endpoint: str
    :param method: The HTTP method to use, default = "POST"
    :type method: str
    :param data: The data to pass
    :type data: a dictionary of key/value string pairs
    :param headers: The HTTP headers to be added to the request
    :type headers: a dictionary of string key/value pairs
    :param filter_by_fields: filter where specified AirTable column names match payload's
    :type filter_by_fields: dict
    """

    # Specify the arguments that are allowed to parse with jinja templating
    template_fields = [
        'endpoint',
        'data',
        'headers',
    ]
    template_fields_renderers = {'headers': 'json', 'data': 'py'}
    template_ext = ()
    ui_color = '#f4a460'

    @apply_defaults
    def __init__(
        self,
        *,
        endpoint: Optional[str] = None,
        table_name: str = None,
        data: Any = None,
        filter_by_fields: list = [],
        headers: Optional[Dict[str, str]] = None,
        extra_options: Optional[Dict[str, Any]] = None,
        airtable_conn_id: str = 'conn_sample',
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.airtable_conn_id = airtable_conn_id
        self.endpoint = endpoint
        self.headers = headers or {}
        self.data = data or {}
        self.table_name = table_name
        self.extra_options = extra_options or {}
        self.filter_by_fields = filter_by_fields
  
    def execute(self, context: Dict[str, Any]) -> Any:
        self.log.info(self.data)
        
        hook = AirTableHook(airtable_conn_id=self.airtable_conn_id)

        self.log.info("Run AirTable Operator")
        response = hook.run_with_update(self.table_name, self.endpoint, self.data, self.headers, self.filter_by_fields)

        self.log.info(response)

        return response
