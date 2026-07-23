import pytest

import deskplot
from deskplot.config import Config


def test_defaults_are_neutral():
    cfg = deskplot.get_config()
    assert cfg.brand == "deskplot"
    assert cfg.brand_secondary == ""
    assert cfg.source == ""


def test_configure_updates_global_config():
    cfg = deskplot.configure(brand="ACME", color_primary="#00C853")
    assert cfg is deskplot.get_config()
    assert cfg.brand == "ACME"
    assert cfg.color_primary == "#00C853"


def test_configure_rejects_unknown_option():
    with pytest.raises(TypeError, match="Unknown deskplot config option"):
        deskplot.configure(nonsense="x")


def test_config_lists_all_fields_in_error():
    with pytest.raises(TypeError, match="brand"):
        deskplot.configure(bad_key=1)


def test_config_dataclass_roundtrip():
    c = Config(brand="X", source="Y")
    assert c.brand == "X"
    assert c.source == "Y"
