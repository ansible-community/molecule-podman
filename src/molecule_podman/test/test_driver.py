"""Unit tests."""
from molecule import api


def test_driver_is_detected():
    """Asserts that molecule recognizes the driver."""
    assert any(str(d) == "podman" for d in api.drivers())
