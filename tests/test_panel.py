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


def test_panel_preserves_round_metadata(monkeypatch):
    from pyafrobarometer import api
    from pyafrobarometer.dataset import Dataset, Provenance

    def make(round_number, value):
        df = pd.DataFrame(
            {
                "round": [round_number],
                "country": ["Ghana"],
                "year": [2020],
                "gender": [value],
            }
        )
        meta = {
            "variable_value_labels": {"gender": {9.0: "Don't know"}},
            "missing_ranges": {},
        }
        prov = Provenance(
            ("https://www.afrobarometer.org/x.sav",),
            "2026-10-25T00:00:00Z",
            (round_number,),
            ("Ghana",),
            "en",
            years=(2020,),
        )
        variables = pd.DataFrame(
            [
                {
                    "name": "gender",
                    "label": "Gender",
                    "value_labels": {9: "Don't know"},
                    "missing_codes": [9],
                    "source_var": "gender",
                }
            ]
        )
        return Dataset(
            df,
            variables=variables,
            provenance=prov,
            meta={},
            source_map={"gender": "gender"},
            harmonized=True,
            round_meta={round_number: meta},
            round_source_map={round_number: {"gender": "gender"}},
        )

    def fake_load(rounds=None, **kwargs):
        return make(rounds, 9 if rounds == 8 else 1)

    monkeypatch.setattr(api, "load", fake_load)
    panel = api.panel([8, 9], ["gender"])
    out = panel.to_pandas(normalize_missing=True)
    assert out["gender"].isna().tolist() == [True, False]
    assert set(panel.variables()["name"]) == {"gender"}


def test_panel_trust_president_preserves_round_metadata(monkeypatch):
    from pyafrobarometer import api
    from pyafrobarometer.dataset import Dataset, Provenance

    def make(round_number, value):
        df = pd.DataFrame(
            {
                "round": [round_number],
                "country": ["Ghana"],
                "year": [2020],
                "trust_president": [value],
            }
        )
        meta = {
            "variable_value_labels": {"Q37A": {9.0: "Don't know"}},
            "missing_ranges": {},
        }
        prov = Provenance(
            ("https://www.afrobarometer.org/x.sav",),
            "2026-10-25T00:00:00Z",
            (round_number,),
            ("Ghana",),
            "en",
            years=(2020,),
        )
        variables = pd.DataFrame(
            [
                {
                    "name": "trust_president",
                    "label": "Trust in the president",
                    "value_labels": {0: "Not at all", 1: "Just a little"},
                    "missing_codes": [9],
                    "source_var": "Q37A",
                    "source_vars": {round_number: "Q37A"},
                }
            ]
        )
        return Dataset(
            df,
            variables=variables,
            provenance=prov,
            meta={},
            source_map={"trust_president": "Q37A"},
            harmonized=True,
            round_meta={round_number: meta},
            round_source_map={round_number: {"trust_president": "Q37A"}},
        )

    def fake_load(rounds=None, **kwargs):
        return make(rounds, 9 if rounds == 8 else 1)

    monkeypatch.setattr(api, "load", fake_load)
    panel = api.panel([8, 9], ["trust_president"])
    out = panel.to_pandas(normalize_missing=True)
    assert out["trust_president"].isna().tolist() == [True, False]
    assert set(panel.variables()["name"]) == {"trust_president"}
    assert panel.round_source_map == {
        8: {"trust_president": "Q37A"},
        9: {"trust_president": "Q37A"},
    }
