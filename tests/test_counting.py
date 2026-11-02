import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Load counting.py directly: importing the package would import vantage6 (installed in the image, not needed here).
_SPEC = importlib.util.spec_from_file_location(
    "counting", Path(__file__).parent.parent / "v6_poc_count" / "counting.py"
)
counting = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(counting)


def _persons(male: int, female: int, other=()) -> pd.DataFrame:
    ids = [8507] * male + [8532] * female + list(other)
    return pd.DataFrame({"person_id": range(len(ids)), "gender_concept_id": ids})


def test_count_values_per_gender():
    result = counting.count_values(_persons(653, 689))
    assert result == {"total": 1342, "counts": {"8507": 653, "8532": 689}}


def test_count_values_other_column_and_missing_values():
    df = pd.DataFrame({"x": [1.0, 1.0, 2.0, np.nan]})
    result = counting.count_values(df, "x")
    assert result["total"] == 4
    assert result["counts"] == {"1": 2, "2": 1, "(missing)": 1}


def test_count_values_empty_dataframe():
    result = counting.count_values(pd.DataFrame({"gender_concept_id": []}))
    assert result == {"total": 0, "counts": {}}


def test_unknown_column_raises():
    with pytest.raises(ValueError, match="not found"):
        counting.count_values(_persons(1, 1), "nope")


def test_min_cell_size_masks_small_cells():
    result = counting.count_values(_persons(10, 3), min_cell_size=5)
    assert result["counts"] == {"8507": 10, "8532": None}
    assert result["total"] == 13


def test_min_cell_size_refuses_tiny_dataframe():
    with pytest.raises(ValueError, match="fewer rows"):
        counting.count_values(_persons(2, 1), min_cell_size=5)


def test_negative_min_cell_size_raises():
    with pytest.raises(ValueError, match="0 or larger"):
        counting.count_values(_persons(1, 1), min_cell_size=-1)


def test_combine_counts_matches_poc_data():
    """The two POC nodes (see the installation notes): 1342 and 1352 persons."""
    vm2 = counting.count_values(_persons(653, 689))
    vm3 = counting.count_values(_persons(668, 684))
    combined = counting.combine_counts([vm2, vm3])
    assert combined["total"] == 2694
    assert combined["organizations"] == 2
    assert combined["table"] == [
        {"value": "8507", "label": "MALE", "count": 1321},
        {"value": "8532", "label": "FEMALE", "count": 1373},
    ]


def test_combine_counts_group_missing_at_one_node():
    a = {"total": 3, "counts": {"8507": 3}}
    b = {"total": 2, "counts": {"8532": 2}}
    table = counting.combine_counts([a, b])["table"]
    assert {row["value"]: row["count"] for row in table} == {"8507": 3, "8532": 2}


def test_combine_counts_suppressed_cell_stays_suppressed():
    a = {"total": 10, "counts": {"8507": 7, "8532": None}}
    b = {"total": 20, "counts": {"8507": 5, "8532": 15}}
    combined = counting.combine_counts([a, b])
    assert {row["value"]: row["count"] for row in combined["table"]} == {"8507": 12, "8532": None}
    assert combined["total"] == 30


def test_combine_counts_labels_only_for_gender_column():
    results = [{"total": 1, "counts": {"8507": 1}}]
    assert counting.combine_counts(results, "gender_concept_id")["table"][0]["label"] == "MALE"
    assert counting.combine_counts(results, "race_concept_id")["table"][0]["label"] == "8507"


def test_combine_counts_sorts_numbers_numerically_and_missing_last():
    results = [{"total": 4, "counts": {"10": 1, "9": 1, "(missing)": 1, "abc": 1}}]
    order = [row["value"] for row in counting.combine_counts(results, "x")["table"]]
    assert order == ["9", "10", "abc", "(missing)"]
