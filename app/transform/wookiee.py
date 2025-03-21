"""
Module for Wookiee encoding transformation.

This module provides functionality to encode a given text into a
Wookiee-like language using a predefined character mapping.
"""


def wookiee_encode(text: str) -> str:
    """
    Encode text into a simple Wookiee-like language.

    This function translates each character in the input text into a
    corresponding Wookiee-like encoding using a predefined lookup table.
    Characters that do not have a defined encoding are returned unchanged.

    Args:
        text (str): The text to be encoded.

    Returns:
        str: The encoded text in a Wookiee-like language.
    """
    lookup = {
        "a": "ra", "b": "rh", "c": "oa", "d": "wa", "e": "wo", "f": "ww",
        "g": "rr", "h": "ac", "i": "ah", "j": "sh", "k": "or", "l": "an",
        "m": "sc", "n": "wh", "o": "oo", "p": "ak", "q": "rq", "r": "rc",
        "s": "c", "t": "ao", "u": "hu", "v": "ho", "w": "oh", "x": "k",
        "y": "ro", "z": "uf", " ": "waaa"
    }

    # Using list comprehension for efficient encoding of each character.
    return ''.join(lookup.get(c.lower(), c) for c in text)
