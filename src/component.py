import contextlib
import json
import logging
import sys
from functools import wraps

from keboola.component.base import ComponentBase
from keboola.component.exceptions import UserException

# configuration variables
KEY_TEST_CONNECTION = 'connection'

REQUIRED_PARAMETERS = []
REQUIRED_IMAGE_PARS = []

# this goes to base
_SYNC_ACTIONS = dict()


def sync_action(action_name: str):
    def decorate(func):
        # to allow pythonic names / action name mapping
        _SYNC_ACTIONS[action_name] = func.__name__

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

            # when success, only specified message can be on output, so redirect stdout before.
            with contextlib.redirect_stdout(stdout_redirect):
                result = func(self, *args, **kwargs)

            if is_sync_action:
                sys.stdout.write(json.dumps({'status': 'success'}))
            return result

        return action_wrapper

    return decorate


class Component(ComponentBase):
    def __init__(self):
        super().__init__()
        # to verify it works even when stdout logger is on.
        self.set_default_logger()

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

    def run(self):
        logging.info("running")

    # overriden base
    def execute_action(self):
        """
        Executes action defined in the configuration. The action name must match implemented method.
        The default action is 'run'.
        """
        action = self.configuration.action
        if not action:
            logging.warning("No action defined in the configuration, using the default run action.")
            action = 'run'

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
