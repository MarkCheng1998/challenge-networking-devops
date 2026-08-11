"""
Unit Tests for SwitchConfigurator
===================================
Tests the Cisco switch configuration module in simulation mode.
All tests run without a real network device.
"""

import os
from backend.switch_config import (
    SwitchConfigurator,
    DEFAULT_VLANS,
    DEFAULT_HOSTNAME,
)


class TestSwitchConfiguratorInit:
    """Tests for SwitchConfigurator initialization."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        sc = SwitchConfigurator(
            host="192.168.1.1",
            username="admin",
            password="admin",
        )
        assert sc.host == "192.168.1.1"
        assert sc.username == "admin"
        assert sc.password == "admin"
        assert sc.port == 22
        assert sc.device_type == "cisco_ios"
        assert sc.enable_password == "admin"
        assert sc.simulate is False

    def test_init_simulate_mode(self):
        """Test initialization in simulation mode."""
        sc = SwitchConfigurator(
            host="10.0.0.1",
            username="root",
            password="pass",
            simulate=True,
        )
        assert sc.simulate is True
        assert sc.connection is None

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        sc = SwitchConfigurator(
            host="172.16.0.1",
            username="netadmin",
            password="secret",
            port=2222,
            device_type="cisco_ios",
            enable_password="enable123",
            simulate=True,
        )
        assert sc.port == 2222
        assert sc.enable_password == "enable123"

    def test_init_enable_password_defaults_to_password(self):
        """Enable password should default to the SSH password when not provided."""
        sc = SwitchConfigurator(
            host="192.168.1.1",
            username="admin",
            password="mypassword",
        )
        assert sc.enable_password == "mypassword"


class TestSimConnection:
    """Tests for connection handling in simulation mode."""

    def test_sim_connect_returns_true(self, sim_configurator):
        """Simulation mode connect() should return True."""
        assert sim_configurator.connect() is True

    def test_sim_disconnect_clears_connection(self, sim_configurator):
        """Disconnect should clear the connection."""
        sim_configurator.connect()
        sim_configurator.disconnect()
        assert sim_configurator.connection is None

    def test_sim_get_device_params(self, sim_configurator):
        """Device params should contain all required keys."""
        params = sim_configurator._get_device_params()
        assert params["device_type"] == "cisco_ios"
        assert params["host"] == "192.168.1.1"
        assert params["username"] == "admin"
        assert params["port"] == 22
        assert "secret" in params


class TestSimVlanConfig:
    """Tests for VLAN configuration in simulation mode."""

    def test_configure_single_vlan(self, sim_configurator):
        """Configure a single VLAN in simulation mode."""
        vlans = [{"id": "10", "name": "VLAN_DATOS"}]
        result = sim_configurator.configure_vlans(vlans)
        assert result["success"] is True
        assert len(result["details"]) == 1
        assert "VLAN 10" in result["details"][0]
        assert "VLAN_DATOS" in result["details"][0]
        assert len(result["errors"]) == 0

    def test_configure_multiple_vlans(self, sim_configurator, sample_vlans):
        """Configure multiple VLANs."""
        result = sim_configurator.configure_vlans(sample_vlans)
        assert result["success"] is True
        assert len(result["details"]) == 3

    def test_configure_default_vlans(self, sim_configurator):
        """Configure the default VLAN set (10, 20, 50)."""
        result = sim_configurator.configure_vlans(DEFAULT_VLANS)
        assert result["success"] is True
        assert len(result["details"]) == 3

    def test_sim_state_persists_vlans(self, sim_configurator, sample_vlans):
        """VLANs should persist in simulation state."""
        sim_configurator.configure_vlans(sample_vlans)
        vlans = sim_configurator.get_vlans()
        assert len(vlans) == 3
        vlan_ids = [v["id"] for v in vlans]
        assert "10" in vlan_ids
        assert "20" in vlan_ids
        assert "50" in vlan_ids

    def test_configure_empty_vlans(self, sim_configurator):
        """Configuring empty VLAN list should succeed with no details."""
        result = sim_configurator.configure_vlans([])
        assert result["success"] is True
        assert len(result["details"]) == 0


class TestSimHostname:
    """Tests for hostname configuration in simulation mode."""

    def test_configure_hostname(self, sim_configurator, sample_hostname):
        """Set hostname in simulation mode."""
        result = sim_configurator.configure_hostname(sample_hostname)
        assert result["success"] is True
        assert sample_hostname in result["details"][0]

    def test_get_hostname_after_config(self, sim_configurator, sample_hostname):
        """Hostname should be retrievable after configuration."""
        sim_configurator.configure_hostname(sample_hostname)
        assert sim_configurator.get_hostname() == sample_hostname

    def test_default_hostname_is_switch(self, sim_configurator):
        """Before configuration, sim hostname should be 'Switch'."""
        assert sim_configurator.get_hostname() == "Switch"


class TestSimSaveConfig:
    """Tests for save_config in simulation mode."""

    def test_save_config_sim(self, sim_configurator):
        """Save config should succeed in simulation mode."""
        result = sim_configurator.save_config()
        assert result["success"] is True
        assert "NVRAM" in result["details"][0]
        assert len(result["errors"]) == 0


class TestSimBackupConfig:
    """Tests for backup_config in simulation mode."""

    def test_backup_creates_file(self, sim_configurator, sample_vlans, sample_hostname, tmp_path):
        """Backup should create a .cfg file."""
        sim_configurator.configure_vlans(sample_vlans)
        sim_configurator.configure_hostname(sample_hostname)
        result = sim_configurator.backup_config(str(tmp_path))
        assert result["success"] is True
        assert result["file_path"] is not None
        assert os.path.exists(result["file_path"])
        assert result["file_path"].endswith(".cfg")

    def test_backup_filename_contains_hostname(self, sim_configurator, sample_vlans, sample_hostname, tmp_path):
        """Backup filename should contain the hostname."""
        sim_configurator.configure_vlans(sample_vlans)
        sim_configurator.configure_hostname(sample_hostname)
        result = sim_configurator.backup_config(str(tmp_path))
        assert sample_hostname in os.path.basename(result["file_path"])

    def test_backup_file_contains_vlan_data(self, sim_configurator, sample_vlans, sample_hostname, tmp_path):
        """Backup file content should contain VLAN configuration."""
        sim_configurator.configure_vlans(sample_vlans)
        sim_configurator.configure_hostname(sample_hostname)
        result = sim_configurator.backup_config(str(tmp_path))
        with open(result["file_path"], "r") as f:
            content = f.read()
        assert "hostname SWITCH_AUTOMATIZADO" in content
        assert "vlan 10" in content
        assert "VLAN_DATOS" in content

    def test_backup_creates_dir_if_not_exists(self, sim_configurator, tmp_path):
        """Backup should create the target directory if it doesn't exist."""
        backup_dir = os.path.join(str(tmp_path), "newdir")
        result = sim_configurator.backup_config(backup_dir)
        assert result["success"] is True
        assert os.path.isdir(backup_dir)


class TestSimValidation:
    """Tests for configuration validation in simulation mode."""

    def test_validation_passes_after_config(self, sim_configurator_with_config, sample_vlans, sample_hostname):
        """Validation should pass when config matches expectations."""
        result = sim_configurator_with_config.validate_configuration(sample_vlans, sample_hostname)
        assert result["is_valid"] is True
        assert result["hostname_match"] is True
        assert len(result["vlan_matches"]) == 3
        assert len(result["vlan_mismatches"]) == 0

    def test_validation_fails_on_hostname_mismatch(self, sim_configurator_with_config, sample_vlans):
        """Validation should fail when hostname doesn't match."""
        result = sim_configurator_with_config.validate_configuration(sample_vlans, "WRONG_HOSTNAME")
        assert result["is_valid"] is False
        assert result["hostname_match"] is False
        assert any("Hostname mismatch" in a for a in result["alerts"])

    def test_validation_fails_on_missing_vlan(self, sim_configurator_with_config, sample_hostname):
        """Validation should fail when a VLAN is missing."""
        expected = [
            {"id": "10", "name": "VLAN_DATOS"},
            {"id": "99", "name": "VLAN_MISSING"},
        ]
        result = sim_configurator_with_config.validate_configuration(expected, sample_hostname)
        assert result["is_valid"] is False
        assert any("VLAN 99 missing" in a for a in result["alerts"])

    def test_validation_fails_on_vlan_name_mismatch(self, sim_configurator_with_config, sample_hostname):
        """Validation should fail when VLAN name doesn't match."""
        expected = [
            {"id": "10", "name": "WRONG_NAME"},
        ]
        result = sim_configurator_with_config.validate_configuration(expected, sample_hostname)
        assert result["is_valid"] is False
        assert any("name mismatch" in a for a in result["alerts"])

    def test_validation_detects_extra_vlans(self, sim_configurator, sample_vlans, sample_hostname):
        """Validation should detect non-standard VLANs."""
        # Add an extra VLAN not in expected set
        sim_configurator.configure_vlans(sample_vlans + [{"id": "99", "name": "VLAN_EXTRA"}])
        sim_configurator.configure_hostname(sample_hostname)
        result = sim_configurator.validate_configuration(sample_vlans, sample_hostname)
        # Extra VLAN is INFO, not WARNING, so is_valid might still be True
        assert len(result["extra_vlans"]) == 1
        assert result["extra_vlans"][0]["id"] == "99"
        assert any("Non-standard VLAN 99" in a for a in result["alerts"])

    def test_validation_alert_on_pass(self, sim_configurator_with_config, sample_vlans, sample_hostname):
        """Passing validation should include an OK alert."""
        result = sim_configurator_with_config.validate_configuration(sample_vlans, sample_hostname)
        assert any(a.startswith("OK:") for a in result["alerts"])


class TestSimFullWorkflow:
    """Tests for the full configuration workflow in simulation mode."""

    def test_full_workflow_success(self, sim_configurator, sample_vlans, sample_hostname, tmp_path):
        """Full workflow should succeed and return all step results."""
        result = sim_configurator.apply_full_configuration(
            vlans=sample_vlans,
            hostname=sample_hostname,
            backup_dir=str(tmp_path),
        )
        assert result["connection"] is True
        assert result["vlan_config"]["success"] is True
        assert result["hostname_config"]["success"] is True
        assert result["save"]["success"] is True
        assert result["backup"]["success"] is True
        assert result["validation"]["is_valid"] is True
        assert result["success"] is True
        assert len(result["errors"]) == 0

    def test_full_workflow_with_default_vlans(self, sim_configurator, tmp_path):
        """Full workflow with DEFAULT_VLANS and DEFAULT_HOSTNAME."""
        result = sim_configurator.apply_full_configuration(
            vlans=DEFAULT_VLANS,
            hostname=DEFAULT_HOSTNAME,
            backup_dir=str(tmp_path),
        )
        assert result["success"] is True

    def test_full_workflow_creates_backup(self, sim_configurator, sample_vlans, sample_hostname, tmp_path):
        """Full workflow should create a backup file."""
        result = sim_configurator.apply_full_configuration(
            vlans=sample_vlans,
            hostname=sample_hostname,
            backup_dir=str(tmp_path),
        )
        assert result["backup"]["file_path"] is not None
        assert os.path.exists(result["backup"]["file_path"])

    def test_full_workflow_validation_after_config(self, sim_configurator, sample_vlans, sample_hostname, tmp_path):
        """After full workflow, validation should show all VLANs match."""
        result = sim_configurator.apply_full_configuration(
            vlans=sample_vlans,
            hostname=sample_hostname,
            backup_dir=str(tmp_path),
        )
        assert result["validation"]["is_valid"] is True
        assert result["validation"]["hostname_match"] is True
        assert len(result["validation"]["vlan_matches"]) == 3


class TestSimRunningConfig:
    """Tests for get_running_config in simulation mode."""

    def test_running_config_contains_hostname(self, sim_configurator, sample_hostname):
        """Running config should contain the hostname."""
        sim_configurator.configure_hostname(sample_hostname)
        config = sim_configurator.get_running_config()
        assert sample_hostname in config

    def test_running_config_contains_vlans(self, sim_configurator, sample_vlans):
        """Running config should contain VLAN information."""
        sim_configurator.configure_vlans(sample_vlans)
        config = sim_configurator.get_running_config()
        assert "vlan 10" in config
        assert "VLAN_DATOS" in config
