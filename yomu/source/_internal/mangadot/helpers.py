from typing import Any
from .dto import *


def has_next_page(pagination: PaginationDto) -> bool:
    if pagination.get("current") is not None and pagination.get("total") is not None:
        return pagination["current"] < pagination["total"]
    return pagination.get("next_cursor") is not None


def decode_rsc(flat: list[Any]) -> Any:
    cache: list[Any | None] = [None] * len(flat)

    def resolve(i: int) -> Any:
        if i < 0:
            return None

        if cache[i] is not None:
            return None if cache[i] is None else cache[i]

        el = flat[i]

        if el is None:
            result = None

        elif isinstance(el, (str, int, float, bool)):
            result = el

        elif isinstance(el, list):
            result = [resolve(int(item)) for item in el]

        elif isinstance(el, dict):
            result = {
                flat[int(k.removeprefix("_"))]: resolve(int(v)) for k, v in el.items()
            }

        else:
            raise TypeError(f"Unsupported element type: {type(el)}")

        cache[i] = None if result is None else result
        return result

    return resolve(0)
