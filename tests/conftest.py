import pytest

import deskplot.config as config_mod
from deskplot.config import Config, get_config


@pytest.fixture(autouse=True)
def reset_config(monkeypatch):
    """Isolate every test from any real deskplot.toml and restore defaults."""
    # Pretend the file was already loaded so tests never pick up a stray
    # deskplot.toml from the developer's cwd or user config dir. Tests that
    # exercise file discovery reset this flag themselves.
    monkeypatch.setattr(config_mod, "_file_config_loaded", True)
    yield
    defaults = Config()
    cfg = get_config()
    for field in Config.__dataclass_fields__:
        setattr(cfg, field, getattr(defaults, field))
