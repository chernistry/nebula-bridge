import json
import jsonschema  # For validating Postman collections
import os


# ==== POSTMAN COLLECTION VALIDATION MODULE ==== #

def validate_postman_collection(collection: dict) -> None:
    """
    Validates the Postman collection JSON against the expected schema.

    Args:
        collection (dict): The Postman collection to validate.

    Raises:
        jsonschema.ValidationError: If the collection does not match the schema.
    """
    schema = {
        "type": "object",
        "properties": {
            "info": {"type": "object"},
            "item": {"type": "array"},
        },
        "required": ["info", "item"],
    }
    jsonschema.validate(instance=collection, schema=schema)



# ==== POSTMAN COLLECTION GENERATION MODULE ==== #

def generate_postman_collection() -> None:
    """
    Generates a Postman collection for Taboola integration tests,
    validates it against the schema, and writes it to a JSON file.
    """
    collection = {
        "info": {
            "name": "Taboola Integration Test Collection",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "event": [  # Global Postman test for the entire collection
            {
                "listen": "test",
                "script": {
                    "type": "text/javascript",
                    "exec": [
                        "pm.test('All responses are 200', function() {",
                        "    pm.expect(pm.response.code).to.eql(200);",
                        "});",
                    ],
                },
            }
        ],
        "item": [
            {
                "name": "GET Vehicles (DEV)",
                "request": {
                    "method": "GET",
                    "header": [],
                    "url": {
                        "raw": "{{DEV_BASE_URL}}/vehicles",  # URL replaced with variable
                        "host": ["{{DEV_BASE_URL}}"],
                        "path": ["vehicles"],
                    },
                },
            },
            {
                "name": "GET Vehicles (PROD)",
                "request": {
                    "method": "GET",
                    "header": [{"key": "API-TOKEN", "value": "{{API_TOKEN}}"}],
                    "url": {
                        "raw": "{{PROD_BASE_URL}}/vehicles",  # URL replaced with variable
                        "host": ["{{PROD_BASE_URL}}"],
                        "path": ["vehicles"],
                    },
                },
                "event": [
                    {
                        "listen": "test",
                        "script": {
                            "type": "text/javascript",
                            "exec": [
                                "pm.test('Vehicle filter works', function() {",
                                "    var jsonData = pm.response.json();",
                                "    pm.expect(jsonData.results[0].films)"
                                "        .to.include(pm.variables.get('PHANTOM_MENACE_URL'));",
                                "});",
                            ],
                        },
                    }
                ],
            },
        ],
    }

    # Validate the generated collection against the schema
    validate_postman_collection(collection)

    # Convert to absolute path in the repository root
    root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    file_path = os.path.join(root_path, "Taboola_Task.postman_collection.json")

    # Confirm the target file path
    print("Generating Postman collection at:", file_path)

    with open(file_path, "w") as f:
        json.dump(collection, f, indent=4)



# ==== MAIN EXECUTION BLOCK ==== #

if __name__ == "__main__":
    generate_postman_collection()
    print("Postman collection generated.")
