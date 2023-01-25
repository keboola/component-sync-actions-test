import json
import logging

from keboola.component.base import ComponentBase
from keboola.component.exceptions import UserException

# configuration variables
KEY_TEST_CONNECTION = 'connection'

REQUIRED_PARAMETERS = []
REQUIRED_IMAGE_PARS = []


def sync_action(func):
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


class Component(ComponentBase):
    def __init__(self):
        super().__init__()

    @sync_action
    def testConnection(self):
        logging.info("Testing Connection")
        params = self.configuration.parameters
        connection = params.get(KEY_TEST_CONNECTION)
        if connection == "fail":
            raise UserException("failed")
        elif connection == "succeed":
            logging.info("succeed")

    def run(self):
        logging.info("running")


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
