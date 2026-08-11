"""
Pytest Configuration and Fixtures
==================================
Shared fixtures for unit and integration tests.
"""

import sys
import os
import pytest

# Add project root to path so we can import backend modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def sample_vlans():
    """Standard VLAN set for testing."""
    return [
        {"id": "10", "name": "VLAN_DATOS"},
        {"id": "20", "name": "VLAN_VOZ"},
        {"id": "50", "name": "VLAN_SEGURIDAD"},
    ]


@pytest.fixture
def sample_hostname():
    """Default hostname for testing."""
    return "SWITCH_AUTOMATIZADO"


@pytest.fixture
def sim_configurator():
    """A SwitchConfigurator instance in simulation mode."""
    from backend.switch_config import SwitchConfigurator

    return SwitchConfigurator(
        host="192.168.1.1",
        username="admin",
        password="admin",
        simulate=True,
    )


@pytest.fixture
def sim_configurator_with_config(sim_configurator, sample_vlans, sample_hostname):
    """A simulation configurator that already has VLANs and hostname configured."""
    sim_configurator.connect()
    sim_configurator.configure_vlans(sample_vlans)
    sim_configurator.configure_hostname(sample_hostname)
    return sim_configurator


@pytest.fixture
def flask_client():
    """Flask test client."""
    from app import app

    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
