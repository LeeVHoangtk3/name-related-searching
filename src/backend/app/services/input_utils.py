import re


def normalize_input(text: str) -> str:
    """
    Normalize user input for cache key & search consistency.

    Rules:
    - strip leading/trailing spaces
    - lowercase
    - collapse multiple spaces
    """

    if not text:
        return ""

    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)

    return text
