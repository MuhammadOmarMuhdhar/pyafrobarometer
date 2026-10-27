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


def test_concept_column_uses_target_labels():
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
    assert values[0] == "Not at all" and pd.isna(values[1])


def test_to_pandas_uses_target_labels_across_rounds():
    df = pd.DataFrame({"round": [9], "trust_president": [1]})
    meta = {
        "variable_value_labels": {"Q37A": {1.0: "Source label"}},
        "missing_ranges": {},
    }
    prov = Provenance(
        ("https://www.afrobarometer.org/x.sav",),
        "2026-10-25T00:00:00Z",
        (9,),
        ("Benin",),
        "en",
    )
    ds = Dataset(
        df,
        variables=pd.DataFrame(
            columns=["name", "label", "value_labels", "missing_codes"]
        ),
        provenance=prov,
        meta={},
        source_map={"trust_president": "Q37A"},
        harmonized=True,
        round_meta={9: meta},
        round_source_map={9: {"trust_president": "Q37A"}},
    )
    assert ds.to_pandas(labels=True)["trust_president"].tolist() == [
        "Just a little"
    ]


def test_to_pandas_does_not_decode_text_concepts():
    df = pd.DataFrame({"round": [9], "interviewers_comment_verbatim": [1]})
    meta = {
        "variable_value_labels": {"Q119v": {1.0: "Ignored"}},
        "missing_ranges": {},
    }
    prov = Provenance(
        ("https://www.afrobarometer.org/x.sav",),
        "2026-10-25T00:00:00Z",
        (9,),
        ("Benin",),
        "en",
    )
    ds = Dataset(
        df,
        variables=pd.DataFrame(
            columns=["name", "label", "value_labels", "missing_codes"]
        ),
        provenance=prov,
        meta={},
        source_map={"interviewers_comment_verbatim": "Q119v"},
        harmonized=True,
        round_meta={9: meta},
        round_source_map={9: {"interviewers_comment_verbatim": "Q119v"}},
    )
    assert ds.to_pandas(labels=True)["interviewers_comment_verbatim"].tolist() == [1]



def test_subset_and_pickle():
    ds = make()
    assert ds.subset(countries=["Benin"], columns=["Q37A"]).to_pandas().shape == (2, 1)
    assert pickle.loads(pickle.dumps(ds)).to_pandas().equals(ds.to_pandas())


def test_variables_frame_available():
    assert set(make().variables()["name"]) == {"COUNTRY", "Q37A"}


def test_round_specific_labels():
    df = pd.DataFrame({"round": [8, 9], "gender": [1, 1]})
    meta8 = {
        "variable_value_labels": {"gender": {1.0: "Male", 2.0: "Female"}},
        "missing_ranges": {},
    }
    meta9 = {
        "variable_value_labels": {"gender": {1.0: "Woman", 2.0: "Man"}},
        "missing_ranges": {},
    }
    prov = Provenance(
        ("https://www.afrobarometer.org/x.sav",),
        "2026-10-25T00:00:00Z",
        (8, 9),
        ("Benin",),
        "en",
    )
    ds = Dataset(
        df,
        variables=pd.DataFrame(columns=["name", "label", "value_labels", "missing_codes"]),
        provenance=prov,
        meta={},
        source_map={"gender": "gender"},
        round_meta={8: meta8, 9: meta9},
        round_source_map={8: {"gender": "gender"}, 9: {"gender": "gender"}},
    )
    assert ds.to_pandas(labels=True)["gender"].tolist() == ["Male", "Woman"]


def test_dataset_codebook_uses_provenance(monkeypatch, tmp_path):
    import importlib

    codebook_module = importlib.import_module("pyafrobarometer.codebook")
    target = tmp_path / "cb.pdf"
    called = []
    monkeypatch.setattr(
        codebook_module,
        "download_codebook",
        lambda url: called.append(url) or target,
    )
    prov = Provenance(
        ("https://www.afrobarometer.org/x.sav",),
        "2026-10-25T00:00:00Z",
        (9,),
        ("Benin",),
        "en",
        codebook_url="https://www.afrobarometer.org/cb.pdf",
    )
    ds = Dataset(
        pd.DataFrame({"A": [1]}),
        variables=pd.DataFrame(columns=["name", "label", "value_labels", "missing_codes"]),
        provenance=prov,
        meta={},
    )
    assert ds.codebook() == target
    assert called == ["https://www.afrobarometer.org/cb.pdf"]


def test_repr_includes_countries():
    assert "Benin" in repr(make())


def test_subset_understands_country_alpha_and_updates_provenance():
    df = pd.DataFrame({"COUNTRY_ALPHA": ["Ghana", "Benin"], "Q37A": [0, 9]})
    prov = Provenance(
        ("https://www.afrobarometer.org/x.sav",),
        "2026-10-25T00:00:00Z",
        (5,),
        ("Ghana", "Benin"),
        "en",
    )
    ds = Dataset(
        df,
        variables=metadata.variable_info(META),
        provenance=prov,
        meta=META,
    )
    out = ds.subset(countries=["Ghana"])
    assert out.to_pandas()["COUNTRY_ALPHA"].tolist() == ["Ghana"]
    assert out.countries == ["Ghana"]
