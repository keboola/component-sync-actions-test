import contextlib
import dataclasses
import json
import logging
import sys
from dataclasses import dataclass
from functools import wraps
from typing import Literal

from keboola.component.base import ComponentBase
from keboola.component.dao import TableDefinition
from keboola.component.exceptions import UserException

# configuration variables
KEY_TEST_CONNECTION = 'connection'

REQUIRED_PARAMETERS = []
REQUIRED_IMAGE_PARS = []

# Mapping of sync actions "action name":"method_name"
_SYNC_ACTION_MAPPING = {"run": "run"}


class SyncActionJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)


class SyncActionResult:
    """
    Abstract base for sync action results
    """

    def __str__(self):
        return json.dumps(self, cls=SyncActionJSONEncoder)


@dataclass
class ValidationResult(SyncActionResult):
    message: str
    type: Literal["info", "warning", "danger"] = "info"
    status: Literal["success", "error"] = "success"


def sync_action(action_name: str):
    """
    Decorator for marking sync actions method.
    For more info see [Sync actions](https://developers.keboola.com/extend/common-interface/actions/).

    Usage:

    ```
    import csv
    import logging

    from keboola.component.base import ComponentBase, sync_action

    class Component(ComponentBase):

        def run(self):
            '''
            Main execution code
            '''
            pass

        # sync action that is executed when configuration.json "action":"testConnection" parameter is present.
        @sync_action('testConnection')
        def test_connection(self):
            connection = self.configuration.parameters.get('test_connection')
            if connection == "fail":
                raise UserException("failed")
            elif connection == "succeed":
                # this is ignored when run as sync action.
                logging.info("succeed")


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
    ```

    Args:
        action_name:

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
                # when success, only specified message can be on output, so redirect stdout before.
                with contextlib.redirect_stdout(stdout_redirect):
                    result = func(self, *args, **kwargs)

                if is_sync_action:
                    # sync action expects valid JSON in stdout on success.
                    if result:
                        # expect array or object:
                        encoder = None
                        if dataclasses.is_dataclass(result):
                            encoder = SyncActionJSONEncoder
                        sys.stdout.write(json.dumps(result, cls=encoder))
                    else:
                        sys.stdout.write(json.dumps({'status': 'success'}))

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
            {"label": 'Joe', "value": 'joe'},
            {"label": 'Doe', "value": 'doe'},
            {"label": 'Loaded from config parameters', "value": self.configuration.parameters.get('test_value')}
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
        if fail:
            result = ValidationResult(message, message_type, 'error')
            raise UserException(result)
        else:
            return ValidationResult(message, message_type)

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
