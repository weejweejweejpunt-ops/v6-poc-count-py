"""Counting logic, without any vantage6 imports so it can be unit-tested with only pandas.

The decorated vantage6 functions in ``partial.py`` and ``central.py`` are thin wrappers
around :func:`count_values` (runs on every node) and :func:`combine_counts` (runs in the
central step).
"""

from __future__ import annotations

import pandas as pd

GENDER_COLUMN = "gender_concept_id"
MISSING = "(missing)"

# Standard OMOP concepts of the Gender domain, used to label ``gender_concept_id``.
GENDER_LABELS = {
    8507: "MALE",
    8532: "FEMALE",
    8521: "OTHER",
    8551: "UNKNOWN",
    8570: "AMBIGUOUS",
}


def _key(value) -> str:
    """Turn a cell value into the string key that is used in the JSON results."""
    if pd.isna(value):
        return MISSING
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value)


def _sort_key(key: str) -> tuple:
    """Sort numeric keys numerically, other keys alphabetically, missing last."""
    if key.lstrip("-").isdigit():
        return (0, int(key), key)
    if key == MISSING:
        return (2, 0, key)
    return (1, 0, key)


def count_values(
    df: pd.DataFrame, column_name: str = GENDER_COLUMN, min_cell_size: int = 0
) -> dict:
    """Count the rows of a dataframe per value of one column.

    Parameters
    ----------
    df : pandas.DataFrame
        The dataframe of this node.
    column_name : str
        Column to count the values of.
    min_cell_size : int
        Basic disclosure control. A value that occurs fewer than this many times is
        reported as ``None`` instead of its count. If the whole dataframe has fewer
        rows than this, the function refuses (raises). ``0`` switches this off.

    Returns
    -------
    dict
        ``{"total": <number of rows>, "counts": {<value as string>: <count or None>}}``

    Raises
    ------
    ValueError
        If the column does not exist, or if the dataframe is smaller than
        ``min_cell_size``.
    """
    if column_name not in df.columns:
        raise ValueError(f"Column '{column_name}' not found in the dataframe")
    if min_cell_size < 0:
        raise ValueError("min_cell_size must be 0 or larger")
    if 0 < len(df) < min_cell_size:
        raise ValueError(
            f"The dataframe has fewer rows than the minimum cell size ({min_cell_size})"
        )
    counts = df[column_name].map(_key).value_counts()
    cells = {}
    for key, n in counts.items():
        n = int(n)
        cells[key] = None if 0 < n < min_cell_size else n
    return {"total": int(len(df)), "counts": cells}


def combine_counts(results: list[dict], column_name: str = GENDER_COLUMN) -> dict:
    """Add up the results of :func:`count_values` of all nodes.

    A value that is ``None`` (suppressed) at one or more nodes stays ``None`` in the
    total, because its true total is not known.

    Returns
    -------
    dict
        ``{"total": <rows over all nodes>, "organizations": <number of nodes>,
        "table": [{"value": ..., "label": ..., "count": ...}, ...]}``. The ``table`` is
        shown as a table in the portal.
    """
    merged: dict[str, int | None] = {}
    for result in results:
        for key, n in result["counts"].items():
            if key not in merged:
                merged[key] = 0
            if merged[key] is None or n is None:
                merged[key] = None
            else:
                merged[key] += n
    labels = GENDER_LABELS if column_name == GENDER_COLUMN else {}
    table = []
    for key in sorted(merged, key=_sort_key):
        label = labels.get(int(key)) if key.lstrip("-").isdigit() else None
        table.append({"value": key, "label": label or key, "count": merged[key]})
    return {
        "total": sum(result["total"] for result in results),
        "organizations": len(results),
        "table": table,
    }
