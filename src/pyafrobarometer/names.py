"""Country-name normalization and common aliases."""

from __future__ import annotations

import re
import unicodedata

ALIASES = {
    "ivory coast": "cote d ivoire",
    "swaziland": "eswatini",
    "cape verde": "cabo verde",
    "drc": "democratic republic of the congo",
    "congo kinshasa": "democratic republic of the congo",
    "democratic republic of congo": "democratic republic of the congo",
    "congo brazzaville": "republic of the congo",
    "republic of congo": "republic of the congo",
    "united republic of tanzania": "tanzania",
    "czech republic": "czechia",
    "burma": "myanmar",
    "macedonia": "north macedonia",
}


def normalize_country(name: str) -> str:
    text = unicodedata.normalize("NFKD", str(name))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return ALIASES.get(text, text)
