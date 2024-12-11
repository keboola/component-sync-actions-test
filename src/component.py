import json
import logging

from keboola.component.base import ComponentBase, sync_action
from keboola.component.dao import TableDefinition
from keboola.component.exceptions import UserException
# configuration variables
from keboola.component.sync_actions import SelectElement, ValidationResult

KEY_TEST_CONNECTION = 'connection'

REQUIRED_PARAMETERS = []
REQUIRED_IMAGE_PARS = []


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

    @sync_action('show_state')
    def show_state(self):
        return ValidationResult(json.dumps(self.get_state_file()), 'info')

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
