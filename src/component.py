import logging

from keboola.component.base import ComponentBase, sync_action
from keboola.component.exceptions import UserException

# configuration variables
KEY_TEST_CONNECTION = 'connection'

REQUIRED_PARAMETERS = []
REQUIRED_IMAGE_PARS = []


class Component(ComponentBase):
    def __init__(self):
        super().__init__()
        # to verify it works even when stdout logger is on.
        self.set_default_logger()

    @sync_action('testColumns')
    def get_columns(self):
        return [
            {"label": 'Joe', "value": 'joe'},
            {"label": 'Doe', "value": 'doe'},
            {"label": 'Loaded from config parameters', "value": self.configuration.config_data}
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
