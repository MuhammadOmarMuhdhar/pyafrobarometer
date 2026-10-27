import pytest

from pyafrobarometer import catalog, fetch, io
from pyafrobarometer.harmonize.crosswalk import canonical_map, question_map
from pyafrobarometer.harmonize.schema import resolve_column

pytestmark = pytest.mark.network


@pytest.mark.parametrize("round_number", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
def test_every_mapping_exists_in_real_data(round_number, tmp_path):
    entries = [
        e
        for e in catalog.resolve_catalog(refresh=True)
        if e.kind == "merged" and e.round == round_number and e.language == "en"
    ]
    assert entries, f"no merged entry for round {round_number}"
    e = entries[0]
    dest = tmp_path / e.filename
    fetch.download(e.data_url, dest)
    path = io.safe_extract_sav(dest, tmp_path) if dest.suffix == ".zip" else dest
    meta = io.read_metadata(path)
    names = set(meta["column_names"])
    for mapping in canonical_map().values():
        if round_number in mapping:
            assert resolve_column(mapping[round_number].var, names) is not None
    for name, question in question_map().items():
        entry = question.rounds.get(round_number)
        if entry is None or entry.exclude:
            continue
        assert entry.var is not None
        assert resolve_column(entry.var, names) is not None, (
            f"{name} missing in R{round_number}"
        )
