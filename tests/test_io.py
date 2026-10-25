import zipfile

import pandas as pd
import pyreadstat
import pytest

from pyafrobarometer import io
from pyafrobarometer.errors import CacheError


def make_sav(path):
    df = pd.DataFrame({"COUNTRY": [3, 14], "Q37A": [0, 9]})
    pyreadstat.write_sav(
        df,
        str(path),
        column_labels=["Country", "Trust president"],
        variable_value_labels={
            "COUNTRY": {3: "Benin", 14: "Ghana"},
            "Q37A": {0: "Not at all", 3: "A lot", 9: "Don't know"},
        },
    )


def test_read_metadata_and_frame(tmp_path):
    p = tmp_path / "x.sav"
    make_sav(p)
    meta = io.read_metadata(p)
    assert meta["column_names"] == ["COUNTRY", "Q37A"]
    assert meta["variable_value_labels"]["COUNTRY"][3.0] == "Benin"
    df, _ = io.read_frame(p, usecols=["Q37A"])
    assert list(df.columns) == ["Q37A"]


def test_extract_rejects_traversal(tmp_path):
    archive = tmp_path / "x.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("../evil.sav", b"x")
        z.writestr("data.sav", b"y")
    out = io.safe_extract_sav(archive, tmp_path / "out")
    assert out.name == "data.sav"
    assert not (tmp_path / "evil.sav").exists()


def test_extract_requires_a_sav(tmp_path):
    archive = tmp_path / "x.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("readme.txt", b"x")
    with pytest.raises(CacheError):
        io.safe_extract_sav(archive, tmp_path / "out")
