"""Compatibility boundary for KOSIS candidate search during hot deployment."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any


def search_candidates_with_context(
    searcher: Callable[..., list[Any]],
    sentence: str,
    search_index: object,
    *,
    metadata_client: object | None,
    previous_profile: object | None,
    metadata_limit: int = 3,
) -> list[Any]:
    """Use context when available; tolerate a temporarily cached old callable."""
    try:
        return searcher(
            sentence,
            search_index,
            metadata_client=metadata_client,
            previous_profile=previous_profile,
            metadata_limit=metadata_limit,
        )
    except TypeError as error:
        if "unexpected keyword argument 'previous_profile'" not in str(error):
            raise
        return searcher(sentence, search_index, metadata_client=metadata_client)
