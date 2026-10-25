import pandas as pd
import pytest

from pyafrobarometer.errors import HarmonizationError
from pyafrobarometer.harmonize.panel import concat_frames


def test_concat_preserves_order_and_adds_round_country():
    a = pd.DataFrame(
        {"round": [8], "country": ["Ghana"], "year": [2022], "trust_president": [2]}
    )
    b = pd.DataFrame(
        {"round": [9], "country": ["Benin"], "year": [2023], "trust_president": [1]}
    )
    out = concat_frames([a, b], variables=["trust_president"])
    assert out["round"].tolist() == [8, 9]
    assert out["trust_president"].tolist() == [2, 1]


def test_concat_missing_column_raises():
    with pytest.raises(HarmonizationError):
        concat_frames([pd.DataFrame({"round": [9]})], variables=["trust_president"])
