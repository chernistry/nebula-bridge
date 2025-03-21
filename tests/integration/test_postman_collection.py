# tests/integration/test_postman_collection.py
import os
import sys
import json

import pytest
from jsonschema import validate

# Ensure the parent directory is in the path for module imports.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.extract.postman import generate_postman_collection


# ==== PREPARATION STEP: GENERATE POSTMAN COLLECTION ==== #
# Regenerate the Postman collection to ensure it contains global events.
generate_postman_collection()



# ==== TEST: POSTMAN COLLECTION SCHEMA VALIDATION ==== #
@pytest.mark.integration
def test_postman_collection_schema() -> None:
    """
    Verify that the Postman collection JSON file conforms to the base JSON schema.
    The schema requires an object with 'info' (object) and 'item' (array) properties.
    """
    with open("Taboola_Task.postman_collection.json", "r", encoding="utf-8") as f:
        collection = json.load(f)

    schema = {
        "type": "object",
        "properties": {
            "info": {"type": "object"},
            "item": {"type": "array"},
        },
        "required": ["info", "item"],
    }

    validate(instance=collection, schema=schema)



# ==== TEST: POSTMAN COLLECTION GLOBAL 200 RESPONSE TEST ==== #
@pytest.mark.integration
def test_postman_contains_global_200_test() -> None:
    """
    Ensure that the Postman collection includes a global test for HTTP 200 responses.
    It verifies that there is at least one event with a test script that checks if
    pm.response.code equals 200.
    """
    with open("Taboola_Task.postman_collection.json", "r", encoding="utf-8") as f:
        collection = json.load(f)

    events = collection.get("event", [])
    assert len(events) > 0, "No global events found"

    # Retrieve the test script from the first event.
    test_script = events[0].get("script", {}).get("exec", [])
    contains_200_test = any(
        "pm.expect(pm.response.code).to.eql(200)" in line for line in test_script
    )
    assert contains_200_test, "Global test for 200 code is missing"
