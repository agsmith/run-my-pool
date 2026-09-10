"""Deterministic first-pass posting filter; reports and human review handle context."""

import re
import unicodedata

_PATTERNS = [
    r"\b(?:fuck\w*|shit\w*|cunt\w*|motherfuck\w*)\b",
    r"\b(?:nigg(?:er|a)s?|faggots?|retards?)\b",
    r"\b(?:kill|hurt|shoot|rape)\s+(?:you|yourself|him|her|them)\b",
    r"\b(?:child porn|kiddie porn|go kill yourself)\b",
]


def objectionable(text: str) -> bool:
    text = unicodedata.normalize("NFKC", text).casefold()
    text = "".join(c for c in text if unicodedata.category(c) != "Cf")
    text = text.translate(
        str.maketrans(
            {
                "0": "o",
                "1": "i",
                "3": "e",
                "4": "a",
                "5": "s",
                "7": "t",
                "@": "a",
                "$": "s",
            }
        )
    )
    # Catch punctuation-separated and spaced spellings without matching substrings
    # of ordinary words such as Scunthorpe or assignment.
    variants = [text, re.sub(r"(?<=\w)[.*_\-]+(?=\w)", "", text)]
    variants.append(
        re.sub(r"\b(?:[a-z]\s+){2,}[a-z]\b", lambda m: re.sub(r"\s+", "", m[0]), text)
    )
    return any(re.search(pattern, value) for pattern in _PATTERNS for value in variants)
