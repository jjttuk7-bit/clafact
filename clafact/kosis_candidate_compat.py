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
    profile: object | None = None,
    metadata_limit: int = 3,
) -> list[Any]:
    """Use a confirmed profile when supported; tolerate cached older callables."""
    kwargs = {
        "metadata_client": metadata_client,
        "previous_profile": previous_profile,
        "profile": profile,
        "metadata_limit": metadata_limit,
    }
    try:
        return searcher(sentence, search_index, **kwargs)
    except TypeError as error:
        message = str(error)
        if "unexpected keyword argument 'profile'" in message:
            kwargs.pop("profile")
            try:
                return searcher(sentence, search_index, **kwargs)
            except TypeError as retry_error:
                message = str(retry_error)
        if "unexpected keyword argument 'metadata_limit'" in message:
            kwargs.pop("metadata_limit", None)
            try:
                return searcher(sentence, search_index, **kwargs)
            except TypeError as retry_error:
                message = str(retry_error)
        if "unexpected keyword argument 'previous_profile'" in message:
            return searcher(sentence, search_index, metadata_client=metadata_client)
        raise
