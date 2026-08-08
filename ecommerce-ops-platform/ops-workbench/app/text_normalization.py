from __future__ import annotations

import unicodedata


def normalize_tag_name(value: str) -> str:
    return " ".join(value.strip().split()).casefold()


def normalize_copy_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(
        char
        for char in normalized
        if not char.isspace()
        and not unicodedata.category(char).startswith(("P", "S"))
    )
