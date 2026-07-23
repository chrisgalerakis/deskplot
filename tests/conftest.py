import pytest

from deskplot.config import Config, get_config


@pytest.fixture(autouse=True)
def reset_config():
    """Restore the global config to defaults after every test."""
    yield
    defaults = Config()
    cfg = get_config()
    for field in Config.__dataclass_fields__:
        setattr(cfg, field, getattr(defaults, field))
