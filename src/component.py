import json
import logging
from functools import wraps

from keboola.component.base import ComponentBase
from keboola.component.exceptions import UserException

# configuration variables
KEY_TEST_CONNECTION = 'connection'

REQUIRED_PARAMETERS = []
REQUIRED_IMAGE_PARS = []

_SYNC_ACTIONS = dict()


def sync_action(action_name: str):
    def decorate(func):
        # to allow pythonic names / action name mapping
        _SYNC_ACTIONS[action_name] = func.__name__

        @wraps(func)
        def action_wrapper(self, *args, **kwargs):
            # override when run as sync action, because it could be also called normally within run
            is_sync_action = self.configuration.action != 'run'
            if is_sync_action:
                # set logger to stdout
                self.set_default_logger()

            # do operations with func
            result = func(self, *args, **kwargs)

            if is_sync_action:
                logging.info(json.dumps({'status': 'success'}))

            return result

        return action_wrapper

    return decorate


class Component(ComponentBase):
    def __init__(self):
        super().__init__()

    @sync_action('testConnection')
    def test_connection(self):
        logging.info("Testing Connection")
        params = self.configuration.parameters
        connection = params.get(KEY_TEST_CONNECTION)
        if connection == "fail":
            raise UserException("failed")
        elif connection == "succeed":
            logging.info("succeed")

    def run(self):
        logging.info("running")

    def execute_action(self):
        """
        Executes action defined in the configuration. The action name must match implemented method.
        The default action is 'run'.
        """
        action = self.configuration.action
        if not action:
            logging.warning("No action defined in the configuration, using the default run action.")
            action = 'run'

        logging.info(f"Running action: {action}")
        try:
            # apply action mapping
            if action != 'run':
                action = _SYNC_ACTIONS[action]

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
