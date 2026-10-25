import pickle

import pandas as pd

from pyafrobarometer import metadata
from pyafrobarometer.dataset import Dataset, Provenance

META = {
    "column_names": ["COUNTRY", "Q37A"],
    "column_labels": ["Country", "Trust"],
    "variable_value_labels": {
        "COUNTRY": {3.0: "Benin"},
        "Q37A": {0.0: "No", 9.0: "DK"},
    },
    "missing_ranges": {},
}


def make():
    df = pd.DataFrame({"COUNTRY": [3, 3], "Q37A": [0, 9]})
    prov = Provenance(
        ("https://www.afrobarometer.org/x.sav",),
        "2026-10-25T00:00:00Z",
        (9,),
        ("Benin",),
        "en",
    )
    return Dataset(df, variables=metadata.variable_info(META), provenance=prov, meta=META)


def test_delegation_and_getitem():
    ds = make()
    assert list(ds.columns) == ["COUNTRY", "Q37A"]
    assert len(ds) == 2 and ds["Q37A"].tolist() == [0, 9]
    assert ds.head(1).shape == (1, 2)


def test_to_pandas_modes():
    ds = make()
    assert ds.to_pandas()["Q37A"].tolist() == [0, 9]
    assert ds.to_pandas(normalize_missing=True)["Q37A"].isna().tolist() == [False, True]
    labelled = ds.to_pandas(labels=True)
    assert labelled["Q37A"].astype(str).tolist() == ["No", "DK"]


def test_source_map_applies_metadata_to_a_family_column():
    df = pd.DataFrame({"Q37A": [0, 9], "trust_president": [0, 9]})
    prov = Provenance(
        ("https://www.afrobarometer.org/x.sav",),
        "2026-10-25T00:00:00Z",
        (9,),
        ("Benin",),
        "en",
    )
    ds = Dataset(
        df,
        variables=metadata.variable_info(META),
        provenance=prov,
        meta=META,
        source_map={"Q37A": "Q37A", "trust_president": "Q37A"},
    )
    out = ds.to_pandas(normalize_missing=True, labels=True)
    values = out["trust_president"].tolist()
    assert values[0] == "No" and pd.isna(values[1])


def test_subset_and_pickle():
    ds = make()
    assert ds.subset(countries=["Benin"], columns=["Q37A"]).to_pandas().shape == (2, 1)
    assert pickle.loads(pickle.dumps(ds)).to_pandas().equals(ds.to_pandas())


def test_variables_frame_available():
    assert set(make().variables()["name"]) == {"COUNTRY", "Q37A"}
