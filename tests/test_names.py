from pyafrobarometer.names import normalize_country


def test_accents_and_punctuation_fold():
    assert normalize_country("Côte d'Ivoire") == normalize_country("Cote d Ivoire")


def test_common_aliases():
    assert normalize_country("Ivory Coast") == normalize_country("Côte d'Ivoire")
    assert normalize_country("Swaziland") == normalize_country("Eswatini")
    assert normalize_country("Cape Verde") == normalize_country("Cabo Verde")
    assert normalize_country("Sao Tome and Principe") == normalize_country(
        "São Tomé and Príncipe"
    )
