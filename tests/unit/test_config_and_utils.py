# tests/unit/test_config_and_utils.py
import os
import pytest

from app.config import get_base_url, USE_PROD, DEV_BASE_URL, PROD_BASE_URL


# ==== TEST: GET BASE URL IN DEV MODE ==== #
@pytest.mark.unit
def test_get_base_url_dev() -> None:
    """
    Simulate DEV mode and verify that get_base_url returns the development base URL.
    """
    os.environ["USE_PROD"] = "false"
    assert get_base_url() == DEV_BASE_URL



# ==== TEST: GET BASE URL IN PROD MODE ==== #
@pytest.mark.unit
def test_get_base_url_prod() -> None:
    """
    Simulate production mode and verify that get_base_url returns the production base URL.
    """
    os.environ["USE_PROD"] = "true"
    assert get_base_url() == PROD_BASE_URL



# ==== TEST: FORCE PRODUCTION BASE URL ==== #
@pytest.mark.unit
def test_get_base_url_force_prod() -> None:
    """
    Verify that get_base_url returns the production base URL when force_prod=True,
    regardless of environment settings.
    """
    os.environ["USE_PROD"] = "true"
    assert get_base_url(force_prod=True) == PROD_BASE_URL



# ==== TEST: ENVIRONMENT FLAGS PARSING ==== #
@pytest.mark.unit
def test_env_flags() -> None:
    """
    Verify that the environment flags in the .env file are correctly parsed.

    This test checks that USE_SQLITE is a boolean and REDIS_URL is a string.
    """
    from app.config import USE_SQLITE, REDIS_URL

    assert isinstance(USE_SQLITE, bool)
    assert isinstance(REDIS_URL, str)
