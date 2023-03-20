import contextlib
import dataclasses
import json
import logging
import sys
from abc import ABC
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Union, List, Optional

from keboola.component.base import ComponentBase
from keboola.component.dao import TableDefinition
from keboola.component.exceptions import UserException

# configuration variables
KEY_TEST_CONNECTION = 'connection'

REQUIRED_PARAMETERS = []
REQUIRED_IMAGE_PARS = []

# Mapping of sync actions "action name":"method_name"
_SYNC_ACTION_MAPPING = {"run": "run"}


def _convert_enum_value(obj):
    """
    Helper to get Enums value
    Args:
        obj:

    Returns:

    """
    if isinstance(obj, Enum):
        return obj.value
    return obj


@dataclass
class SyncActionResult(ABC):
    """
    Abstract base for sync action results
    """

    def __post_init__(self):
        """
         Right now the status is always success.
        In other cases exception is thrown and printed via stderr.
        Returns:

        """
        self.status = 'success'

    def __str__(self):
        dict_obj = dataclasses.asdict(self, dict_factory=lambda x: {k: _convert_enum_value(v) for (k, v) in x if
                                                                    v is not None})
        # hack to add default status
        if self.status:
            dict_obj['status'] = self.status
        return json.dumps(dict_obj)


class MessageType(Enum):
    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"
    DANGER = "danger"


@dataclass
class ValidationResult(SyncActionResult):
    message: str
    type: MessageType = MessageType.INFO


@dataclass
class SelectElement(SyncActionResult):
    """
    For select elements. Label is optional and value will be used
    """
    value: str
    label: Optional[str] = None

    def __post_init__(self):
        self.label = self.label or self.value
        # special case of element F with no status
        self.status = None


def _process_sync_action_result(result: Union[None, SyncActionResult, List[SyncActionResult]]):
    """
    Converts Sync Action result into valid string.
    Args:
        result: Union[None, SyncActionResult, List[SyncActionResult]]

    Returns:

    """
    if isinstance(result, SyncActionResult):
        result_str = str(result)
    elif isinstance(result, list):
        result_str = f'[{", ".join([str(r) for r in result])}]'
    elif result is None:
        result_str = json.dumps({'status': 'success'})
    elif isinstance(result, dict):
        # for backward compatibility
        result_str = json.dumps(result)
    else:
        raise ValueError("Result of sync action must be either None or an instance of SyncActionResult "
                         "or a List[SyncActionResult]")
    return result_str


def sync_action(action_name: str):
    """

       Decorator for marking sync actions method.
       For more info see [Sync actions](https://developers.keboola.com/extend/common-interface/actions/).
    Args:
        action_name: Name of the action registered in Developer Portal

    Returns:

    """

    def decorate(func):
        # to allow pythonic names / action name mapping
        if action_name == 'run':
            raise ValueError('Sync action name "run" is reserved base action! Use different name.')
        _SYNC_ACTION_MAPPING[action_name] = func.__name__

        @wraps(func)
        def action_wrapper(self, *args, **kwargs):
            # override when run as sync action, because it could be also called normally within run
            is_sync_action = self.configuration.action != 'run'

            # do operations with func
            if is_sync_action:
                stdout_redirect = None
                # mute logging just in case
                logging.getLogger().setLevel(logging.FATAL)
            else:
                stdout_redirect = sys.stdout

            try:
                # when success, only supported syntax can be in output / log, so redirect stdout before.
                with contextlib.redirect_stdout(stdout_redirect):
                    result: Union[None, SyncActionResult, List[SyncActionResult]] = func(self, *args, **kwargs)

                if is_sync_action:
                    # sync action expects valid JSON in stdout on success.
                    result_str = _process_sync_action_result(result)
                    sys.stdout.write(result_str)

                return result

            except Exception as e:
                if is_sync_action:
                    # sync actions expect stderr
                    sys.stderr.write(str(e))
                    exit(1)
                else:
                    raise e

        return action_wrapper

    return decorate


class Component(ComponentBase):
    def __init__(self):
        super().__init__()
        # to verify it works even when stdout logger is on.
        self.set_default_logger()

    def _get_input_table(self) -> TableDefinition:
        if not self.get_input_tables_definitions():
            raise UserException("No input table specified. Please provide one input table in the input mapping! "
                                f"{self.configuration.config_data}")
        return self.get_input_tables_definitions()[0]

    @sync_action('testColumns')
    def get_columns(self):
        return [
            SelectElement(label='Loaded from config parameters', value=self.configuration.parameters.get('test_value')),
            SelectElement(label='Joe', value='joe'),
            SelectElement(value='doe')
        ]

    @sync_action('testConnection')
    def test_connection(self):
        logging.info("Testing Connection")
        print("test print")
        params = self.configuration.parameters
        connection = params.get(KEY_TEST_CONNECTION)
        if connection == "fail":
            raise UserException("failed")
        elif connection == "succeed":
            # this is ignored by KBC when run as sync action.
            logging.info("succeed")

    @sync_action('test_input_columns')
    def list_table_columns(self):
        """
        Sync action to fill the UI element of primary keys.

        Returns:

        """
        if not self.configuration.tables_input_mapping:
            raise UserException("No input table specified. Please provide one input table in the input mapping!")
        input_table = self.configuration.tables_input_mapping[0]
        return [{"value": c, "label": c} for c in input_table.columns]

    @sync_action('validate_report')
    def validate_action(self):
        message_type = self.configuration.parameters['test_validation']['message_type']
        message = self.configuration.parameters['test_validation']['message']
        fail = self.configuration.parameters['test_validation']['fail']
        status = self.configuration.parameters['test_validation']['status']
        result = ValidationResult(message, message_type)
        result.status = status
        if fail:
            raise UserException(f"This is user exception, ony stderr content: {result}")

        return result

    def run(self):
        logging.info("running")

    # overriden temp
    def execute_action(self):
        """
        Executes action defined in the configuration.
        The default action is 'run'. See base._SYNC_ACTION_MAPPING
        """
        action = self.configuration.action
        if not action:
            logging.warning("No action defined in the configuration, using the default run action.")
            action = 'run'

        try:
            action = _SYNC_ACTION_MAPPING[action]
            action_method = getattr(self, action)
        except (AttributeError, KeyError) as e:
            raise AttributeError(f"The defined action {action} is not implemented!") from e
        return action_method()


"""
        Main entrypoint
"""
if __name__ == "__main__":
    try:
        comp = Component()
        # this triggers the run method by default and is controlled by the configuration.action parameter
        comp.execute_action()
    except UserException as exc:
        logging.exception(exc)
        exit(1)
    except Exception as exc:
        logging.exception(exc)
        exit(2)
