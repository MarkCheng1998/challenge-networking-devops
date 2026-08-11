"""
Cisco Switch Configuration Module
=================================
Automates Cisco switch configuration using Netmiko, including:
- VLAN creation and naming
- Hostname modification
- Saving configuration to NVRAM
- Configuration backup
- Configuration validation

Supports both real devices and simulation mode (no physical switch required).
"""

import os
import re
from datetime import datetime
from netmiko import ConnectHandler
try:
    from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException
except ImportError:
    from netmiko.ssh_exception import NetmikoTimeoutException, NetmikoAuthenticationException


# Default VLAN configuration (per challenge requirements)
DEFAULT_VLANS = [
    {"id": "10", "name": "VLAN_DATOS"},
    {"id": "20", "name": "VLAN_VOZ"},
    {"id": "50", "name": "VLAN_SEGURIDAD"},
]

DEFAULT_HOSTNAME = "SWITCH_AUTOMATIZADO"


class SwitchConfigurator:
    """Cisco switch configurator encapsulating all switch interaction logic."""

    def __init__(self, host, username, password, port=22, device_type="cisco_ios", enable_password=None, simulate=False):
        """
        Initialize switch connection parameters.

        Args:
            host: Switch IP address
            username: SSH username
            password: SSH password
            port: SSH port, default 22
            device_type: Device type, default cisco_ios
            enable_password: Enable password (optional)
            simulate: Use simulation mode (for demo without real device)
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.device_type = device_type
        self.enable_password = enable_password or password
        self.simulate = simulate
        self.connection = None

        # Virtual configuration state for simulation mode
        self._sim_vlans = {}
        self._sim_hostname = "Switch"

    def _get_device_params(self):
        """Build Netmiko device parameter dictionary."""
        return {
            "device_type": self.device_type,
            "host": self.host,
            "username": self.username,
            "password": self.password,
            "port": self.port,
            "secret": self.enable_password,
        }

    def connect(self):
        """Establish SSH connection to the switch."""
        if self.simulate:
            return True
        try:
            self.connection = ConnectHandler(**self._get_device_params())
            self.connection.enable()
            return True
        except (NetmikoTimeoutException, NetmikoAuthenticationException) as e:
            raise ConnectionError(f"Failed to connect to switch {self.host}: {str(e)}")

    def disconnect(self):
        """Disconnect from the switch."""
        if self.connection and not self.simulate:
            self.connection.disconnect()
        self.connection = None

    def configure_vlans(self, vlans):
        """
        Configure VLANs on the switch.

        Args:
            vlans: List of VLANs, each as {"id": "10", "name": "VLAN_DATOS"}

        Returns:
            dict: Configuration result with success/failure status and output details
        """
        results = {"success": True, "details": [], "errors": []}

        if self.simulate:
            for vlan in vlans:
                self._sim_vlans[vlan["id"]] = vlan["name"]
                results["details"].append(f"[SIM] VLAN {vlan['id']} created, name: {vlan['name']}")
            return results

        # Build VLAN configuration commands
        config_commands = []
        for vlan in vlans:
            config_commands.extend([
                f"vlan {vlan['id']}",
                f"name {vlan['name']}",
            ])

        try:
            output = self.connection.send_config_set(config_commands)
            results["details"].append(output)
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"VLAN configuration failed: {str(e)}")

        return results

    def configure_hostname(self, hostname):
        """
        Modify the switch hostname.

        Args:
            hostname: New hostname

        Returns:
            dict: Configuration result
        """
        results = {"success": True, "details": [], "errors": []}

        if self.simulate:
            self._sim_hostname = hostname
            results["details"].append(f"[SIM] Hostname changed to: {hostname}")
            return results

        try:
            output = self.connection.send_config_set([f"hostname {hostname}"])
            results["details"].append(output)
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Hostname modification failed: {str(e)}")

        return results

    def save_config(self):
        """
        Save current configuration to NVRAM.

        Returns:
            dict: Save result
        """
        results = {"success": True, "details": [], "errors": []}

        if self.simulate:
            results["details"].append("[SIM] Configuration saved to NVRAM (write memory)")
            return results

        try:
            output = self.connection.save_config()
            results["details"].append(f"Configuration saved to NVRAM: {output}")
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Configuration save failed: {str(e)}")

        return results

    def backup_config(self, backup_dir="backups"):
        """
        Backup switch configuration to a local file.
        File name format: {hostname}_{YYYYMMDD_HHMMSS}.cfg

        Args:
            backup_dir: Backup file directory

        Returns:
            dict: Backup result including file path
        """
        results = {"success": True, "details": [], "errors": [], "file_path": None}

        # Get current hostname for file naming
        hostname = self.get_hostname()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{hostname}_{timestamp}.cfg"
        filepath = os.path.join(backup_dir, filename)

        # Ensure backup directory exists
        os.makedirs(backup_dir, exist_ok=True)

        if self.simulate:
            config_text = f"""!
! Saved configuration for {hostname}
! Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
! Mode: SIMULATED
!
hostname {hostname}
!
"""
            for vlan_id, vlan_name in self._sim_vlans.items():
                config_text += f"vlan {vlan_id}\n name {vlan_name}\n!\n"
            with open(filepath, "w") as f:
                f.write(config_text)
            results["details"].append(f"[SIM] Configuration backed up to: {filepath}")
            results["file_path"] = filepath
            return results

        try:
            output = self.connection.send_command("show running-config")
            with open(filepath, "w") as f:
                f.write(output)
            results["details"].append(f"Configuration backed up to: {filepath}")
            results["file_path"] = filepath
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Configuration backup failed: {str(e)}")

        return results

    def get_running_config(self):
        """
        Get the switch's current running configuration.

        Returns:
            str: Current running configuration text
        """
        if self.simulate:
            config = f"hostname {self._sim_hostname}\n"
            for vlan_id, vlan_name in self._sim_vlans.items():
                config += f"vlan {vlan_id}\n name {vlan_name}\n"
            return config

        return self.connection.send_command("show running-config")

    def get_hostname(self):
        """Get the current switch hostname."""
        if self.simulate:
            return self._sim_hostname

        output = self.connection.send_command("show running-config | include hostname")
        match = re.search(r"hostname\s+(\S+)", output)
        return match.group(1) if match else "unknown"

    def get_vlans(self):
        """
        Get the switch's current VLAN configuration.

        Returns:
            list: VLAN list, each as {"id": "10", "name": "VLAN_DATOS"}
        """
        if self.simulate:
            return [{"id": vid, "name": vname} for vid, vname in self._sim_vlans.items()]

        output = self.connection.send_command("show vlan brief")
        vlans = []
        for line in output.splitlines():
            # Match format: 10   VLAN_DATOS                     active
            match = re.match(r"^(\d+)\s+(\S+)", line.strip())
            if match:
                vlan_id = match.group(1)
                vlan_name = match.group(2)
                # Exclude default VLANs 1 and 1002-1005
                if vlan_id not in ("1", "1002", "1003", "1004", "1005"):
                    vlans.append({"id": vlan_id, "name": vlan_name})
        return vlans

    def apply_full_configuration(self, vlans, hostname, backup_dir="backups"):
        """
        Execute the complete configuration workflow: configure VLANs -> modify hostname -> save -> backup -> validate.

        Args:
            vlans: VLAN list
            hostname: Target hostname
            backup_dir: Backup directory

        Returns:
            dict: Complete execution result including each step's status
        """
        full_result = {
            "connection": False,
            "vlan_config": None,
            "hostname_config": None,
            "save": None,
            "backup": None,
            "validation": None,
            "success": False,
            "errors": [],
        }

        try:
            # Step 1: Connect
            self.connect()
            full_result["connection"] = True

            # Step 2: Configure VLANs
            full_result["vlan_config"] = self.configure_vlans(vlans)
            if not full_result["vlan_config"]["success"]:
                full_result["errors"].extend(full_result["vlan_config"]["errors"])

            # Step 3: Modify hostname
            full_result["hostname_config"] = self.configure_hostname(hostname)
            if not full_result["hostname_config"]["success"]:
                full_result["errors"].extend(full_result["hostname_config"]["errors"])

            # Step 4: Save configuration to NVRAM
            full_result["save"] = self.save_config()
            if not full_result["save"]["success"]:
                full_result["errors"].extend(full_result["save"]["errors"])

            # Step 5: Backup configuration
            full_result["backup"] = self.backup_config(backup_dir)
            if not full_result["backup"]["success"]:
                full_result["errors"].extend(full_result["backup"]["errors"])

            # Step 6: Validate configuration
            full_result["validation"] = self.validate_configuration(vlans, hostname)

            full_result["success"] = len(full_result["errors"]) == 0

        except Exception as e:
            full_result["errors"].append(str(e))
        finally:
            self.disconnect()

        return full_result

    def validate_configuration(self, expected_vlans, expected_hostname):
        """
        Validate that the switch's current configuration matches the expected configuration.

        Checks:
        - Hostname match
        - Each expected VLAN exists with correct name
        - Non-standard configuration (extra VLANs, etc.)

        Args:
            expected_vlans: Expected VLAN list
            expected_hostname: Expected hostname

        Returns:
            dict: Validation result including match status, discrepancy list, and alerts
        """
        result = {
            "is_valid": True,
            "alerts": [],
            "hostname_match": False,
            "vlan_matches": [],
            "vlan_mismatches": [],
            "extra_vlans": [],
        }

        # Validate hostname
        actual_hostname = self.get_hostname()
        if actual_hostname == expected_hostname:
            result["hostname_match"] = True
        else:
            result["is_valid"] = False
            result["alerts"].append(
                f"WARNING: Hostname mismatch! Expected: '{expected_hostname}', Actual: '{actual_hostname}'"
            )

        # Get current VLAN configuration
        actual_vlans = self.get_vlans()
        actual_vlan_map = {v["id"]: v["name"] for v in actual_vlans}
        expected_vlan_map = {v["id"]: v["name"] for v in expected_vlans}

        # Validate each expected VLAN
        for vlan_id, expected_name in expected_vlan_map.items():
            if vlan_id not in actual_vlan_map:
                result["is_valid"] = False
                result["vlan_mismatches"].append(
                    {"id": vlan_id, "issue": "missing", "expected_name": expected_name, "actual_name": None}
                )
                result["alerts"].append(
                    f"WARNING: VLAN {vlan_id} missing! Expected name: '{expected_name}'"
                )
            elif actual_vlan_map[vlan_id] != expected_name:
                result["is_valid"] = False
                result["vlan_mismatches"].append(
                    {"id": vlan_id, "issue": "name_mismatch", "expected_name": expected_name, "actual_name": actual_vlan_map[vlan_id]}
                )
                result["alerts"].append(
                    f"WARNING: VLAN {vlan_id} name mismatch! Expected: '{expected_name}', Actual: '{actual_vlan_map[vlan_id]}'"
                )
            else:
                result["vlan_matches"].append(
                    {"id": vlan_id, "name": expected_name, "status": "match"}
                )

        # Check for non-standard VLANs (not in expected list)
        for vlan_id, vlan_name in actual_vlan_map.items():
            if vlan_id not in expected_vlan_map:
                result["extra_vlans"].append({"id": vlan_id, "name": vlan_name})
                result["alerts"].append(
                    f"INFO: Non-standard VLAN {vlan_id} found (name: '{vlan_name}'), not in expected configuration"
                )

        if result["is_valid"]:
            result["alerts"].append("OK: Configuration validation passed! All VLANs and hostname match the expected configuration.")

        return result
