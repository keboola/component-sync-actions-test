import logging

from keboola.component.base import ComponentBase
from keboola.component.exceptions import UserException

# configuration variables
KEY_TEST_CONNECTION = 'connection'

REQUIRED_PARAMETERS = []
REQUIRED_IMAGE_PARS = []


class Component(ComponentBase):
    def __init__(self):
        super().__init__()

    def testConnection(self):
        logging.info("Testing Connection")
        params = self.configuration.parameters
        connection = params.get(KEY_TEST_CONNECTION)
        if connection == "fail":
            raise UserException("failed")
        elif connection == "succeed":
            logging.info("succeed")
        return {'status': 'success'}

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
