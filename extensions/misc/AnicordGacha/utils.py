from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from extensions.misc.AnicordGacha.bases import PulledCard


def get_burn_worths(pulls: list[PulledCard]) -> dict[int, int]:
    burn_worth: dict[int, int] = {}
    for c in pulls:
        c_burn_worth = c.rarity * 5
        burn_worth[c.rarity] = burn_worth.get(c.rarity, 0) + c_burn_worth
    burn_worth[6] = 1000
    return {k: burn_worth[k] for k in sorted(burn_worth)}


def check_pullall_author(author_id: int, embed_description: str) -> bool:
    lines = embed_description.split('\n')

    author_line = lines[0]

    author_id_parsed = re.findall(r'<@!?([0-9]+)>', author_line)

    if not author_id_parsed:
        return False

    return int(author_id_parsed[0]) == author_id
