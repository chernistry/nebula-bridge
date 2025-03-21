# tests/unit/test_wookiee.py
import pytest

from app.transform.wookiee import wookiee_encode


# ==== TEST: SIMPLE WOOKEE ENCODING ==== #
@pytest.mark.unit
def test_wookiee_encode_simple() -> None:
    """
    Verify that wookiee_encode correctly encodes a simple text string.

    The test checks if the encoded output contains the expected pattern (e.g.,
    the substring 'acwo') when the input text is "Hello".
    """
    text = "Hello"
    encoded = wookiee_encode(text)
    assert "acwo" in encoded.lower(), f"Unexpected encoding for 'Hello': {encoded}"


# ==== TEST: EMPTY STRING ENCODING ==== #
@pytest.mark.unit
def test_wookiee_encode_empty() -> None:
    """
    Verify that wookiee_encode returns an empty string when given an empty input.
    """
    text = ""
    assert wookiee_encode(text) == ""


# ==== TEST: ENCODING WITH SPACES ==== #
@pytest.mark.unit
def test_wookiee_encode_spaces() -> None:
    """
    Verify that wookiee_encode correctly encodes spaces within the text.

    The test ensures that spaces are replaced by the expected Wookiee encoding pattern
    (e.g., "waaa").
    """
    text = "A B"
    result = wookiee_encode(text)
    assert "waaa" in result, "Space should be replaced by wookiee pattern"
