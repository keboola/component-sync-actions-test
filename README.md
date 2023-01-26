# UI Testing in Keboola Connection

Description

**Table of contents:**

[TOC]

## Sync Action limitations

Data is exchanged via `stdout` or `stderr`.

- All success responses have to output valid JSON string. Meaning nothing can log into the stdout during the action exectution
- For success action the output needs to be always `{"status":"success"}` in stdout.
- Sync actions need to be registered in the Developer Portal first.

## Framework Support

Decorator `sync_action` was added. It takes one parameter `action_name` that will create mapping between the actual method 
and the sync action name registered in the Developer Portal.

- Decorated methods can also be called from within the program and return values. 
- They can log normally -> when run as sync action all logging within the method is muted.
- When a return value is produced, it is expected to be `dict` or `list` object. These will be printed to stdout at the end.
- Exceptions can be thrown normally and the message will be propagated to the platform.


### Example

```python
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
```

## Test Connection

Action name must be `testConnection`

```json
"test_connection": {
      "type": "button",
      "format": "test-connection"
    }
```

```python
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
```

## Populate select/multiselect values

Allows populating select values. 

```json
{
  ...select or multiselect properties,
  "options": {
    "async" {
      "label": "button text", // optional, default is "Load data"
      "action": "sync-action-name"
    }
  }
}
```

**NOTE**: The element must resolve to select/multiselect => empty `"enum":[]` must be defined on the element.

**EXAMPLE**

```json
 "test_columns": {
      "type": "array",
      "format": "select",
      "uniqueItems": true,
      "items": {
        "enum": [],
        "type": "string"
      },
      "options": {
        "async": {
          "label": "Re-load test columns",
          "action": "testColumns"
        }
      }
    }
```

```python
@sync_action('testColumns')
    def get_columns(self):
        return [
            {"label": 'Joe', "value": 'joe'},
            {"label": 'Doe', "value": 'doe'},
            {"label": 'Jane', "value": 'jane'}
        ]
```