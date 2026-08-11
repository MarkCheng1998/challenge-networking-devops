#!/usr/bin/env python3
"""
GNS3 Demo Runner Script
========================
Connects to a GNS3 Cisco switch and runs the full VLAN automation workflow,
printing detailed step-by-step output for demonstration purposes.

Usage:
    # Run against GNS3 switch (default 192.168.122.10)
    python scripts/gns3_demo.py

    # Specify custom switch IP
    python scripts/gns3_demo.py --host 192.168.122.10 --username admin --password admin

    # Run with custom VLANs
    python scripts/gns3_demo.py --vlans '[{"id":"10","name":"VLAN_DATOS"},{"id":"20","name":"VLAN_VOZ"}]'

    # Show pre-check (connectivity test) only
    python scripts/gns3_demo.py --check-only
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.switch_config import SwitchConfigurator, DEFAULT_VLANS, DEFAULT_HOSTNAME

# ANSI color codes for terminal output
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    @staticmethod
    def green(text):
        return f"{Colors.GREEN}{text}{Colors.RESET}"

    @staticmethod
    def red(text):
        return f"{Colors.RED}{text}{Colors.RESET}"

    @staticmethod
    def yellow(text):
        return f"{Colors.YELLOW}{text}{Colors.RESET}"

    @staticmethod
    def blue(text):
        return f"{Colors.BLUE}{text}{Colors.RESET}"

    @staticmethod
    def cyan(text):
        return f"{Colors.CYAN}{text}{Colors.RESET}"

    @staticmethod
    def bold(text):
        return f"{Colors.BOLD}{text}{Colors.RESET}"


def print_header(text):
    """Print a section header."""
    line = "=" * 70
    print()
    print(Colors.cyan(line))
    print(Colors.bold(f"  {text}"))
    print(Colors.cyan(line))


def print_step(num, text, status="running"):
    """Print a step with status indicator."""
    if status == "running":
        icon = Colors.blue("[...]")
    elif status == "ok":
        icon = Colors.green("[OK]")
    elif status == "fail":
        icon = Colors.red("[FAIL]")
    elif status == "warn":
        icon = Colors.yellow("[WARN]")
    else:
        icon = "[--]"
    print(f"  Step {num}: {text}")
    print(f"         {icon} ", end="")


def check_connectivity(host):
    """
    Check if the GNS3 switch is reachable via ping and SSH.

    Args:
        host: Switch IP address

    Returns:
        bool: True if both ping and SSH are reachable
    """
    print_header("PHASE 0: Pre-flight Connectivity Check")

    # Ping check
    print_step(1, f"Ping {host}", "running")
    try:
        result = subprocess.run(
            ["ping", "-n", "3", host],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if "TTL=" in result.stdout or "Reply from" in result.stdout:
            print("Ping successful")
        else:
            print(Colors.red("Ping failed"))
            print(f"  {result.stdout[-200:]}")
            return False
    except Exception as e:
        print(Colors.red(f"Ping error: {str(e)}"))
        return False

    # SSH check (TCP port 22)
    import socket
    print_step(2, f"TCP port 22 (SSH) check on {host}", "running")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    try:
        result = sock.connect_ex((host, 22))
        if result == 0:
            print("SSH port is open")
        else:
            print(Colors.red(f"SSH port closed (error code: {result})"))
            sock.close()
            return False
    except Exception as e:
        print(Colors.red(f"Connection error: {str(e)}"))
        sock.close()
        return False
    finally:
        sock.close()

    print()
    print(Colors.green("  ✓ Pre-flight checks passed. Switch is reachable."))
    return True


def run_demo(host, username, password, port, vlans, hostname, enable_password, backup_dir, skip_check=False):
    """
    Run the full demo workflow against a GNS3 switch.

    Args:
        host: Switch IP
        username: SSH username
        password: SSH password
        port: SSH port
        vlans: List of VLAN dicts
        hostname: Target hostname
        enable_password: Enable secret
        backup_dir: Backup directory
        skip_check: Skip connectivity check
    """
    start_time = datetime.now()

    # Phase 0: Connectivity check
    if not skip_check:
        if not check_connectivity(host):
            print()
            print(Colors.red("  ✗ Pre-flight checks failed. Cannot reach the switch."))
            print(Colors.yellow("  Troubleshooting:"))
            print(f"    1. Is GNS3 running? Is the switch started?")
            print(f"    2. Is the loopback adapter configured (192.168.122.1/24)?")
            print(f"    3. Is the GNS3 Cloud node bound to the loopback adapter?")
            print(f"    4. Does the switch have management IP {host} on Vlan 1?")
            print(f"    5. Is SSH enabled on the switch?")
            sys.exit(1)

    # Phase 1: Show current state
    print_header("PHASE 1: Current Switch State (Before Configuration)")

    configurator = SwitchConfigurator(
        host=host,
        username=username,
        password=password,
        port=port,
        enable_password=enable_password,
    )

    try:
        configurator.connect()

        print_step(1, "Reading current hostname", "running")
        current_hostname = configurator.get_hostname()
        print(f"Current hostname: {current_hostname}")

        print_step(2, "Reading current VLANs", "running")
        current_vlans = configurator.get_vlans()
        if current_vlans:
            print(f"Current VLANs:")
            for v in current_vlans:
                print(f"    VLAN {v['id']} - {v['name']}")
        else:
            print("No non-default VLANs found (only VLAN 1, 1002-1005)")

        configurator.disconnect()
    except Exception as e:
        print(Colors.red(f"Error reading switch state: {str(e)}"))
        configurator.disconnect()

    # Phase 2: Execute automation
    print_header("PHASE 2: Execute VLAN Configuration Automation")

    print(f"  Target VLANs:")
    for v in vlans:
        print(f"    VLAN {v['id']} - {v['name']}")
    print(f"  Target hostname: {hostname}")
    print(f"  Switch: {host}:{port} ({username})")
    print()

    print(Colors.bold("  Executing full workflow: connect -> config VLANs -> hostname -> save -> backup -> validate"))
    print()

    configurator = SwitchConfigurator(
        host=host,
        username=username,
        password=password,
        port=port,
        enable_password=enable_password,
    )

    result = configurator.apply_full_configuration(
        vlans=vlans,
        hostname=hostname,
        backup_dir=backup_dir,
    )

    # Display results
    print_header("PHASE 3: Execution Results")

    # Step-by-step output
    steps = [
        ("SSH Connection", result.get("connection")),
        ("VLAN Configuration", result.get("vlan_config")),
        ("Hostname Modification", result.get("hostname_config")),
        ("Save to NVRAM", result.get("save")),
        ("Configuration Backup", result.get("backup")),
        ("Configuration Validation", result.get("validation")),
    ]

    for i, (step_name, step_result) in enumerate(steps, 1):
        if step_result is None:
            continue

        if isinstance(step_result, bool):
            status = "ok" if step_result else "fail"
            print_step(i, step_name, status)
            print()
            continue

        success = step_result.get("success", False)
        if isinstance(success, bool):
            status = "ok" if success else "fail"
        elif isinstance(success, str):
            status = "ok" if success.lower() in ("true", "ok", "passed") else "fail"
        else:
            status = "ok"

        print_step(i, step_name, status)

        # Print details
        details = step_result.get("details", [])
        if details:
            print()
            for detail in details:
                for line in str(detail).split("\n"):
                    if line.strip():
                        print(f"           {line}")

        # Print errors
        errors = step_result.get("errors", [])
        if errors:
            for error in errors:
                print(f"           {Colors.red('ERROR: ' + str(error))}")

        # Print file path if backup
        if "file_path" in step_result and step_result["file_path"]:
            print(f"           Backup file: {step_result['file_path']}")

        print()

    # Validation details
    validation = result.get("validation", {})
    if validation:
        print_header("PHASE 4: Configuration Validation Details")

        # Hostname match
        hostname_match = validation.get("hostname_match", False)
        status = Colors.green("✓ MATCH") if hostname_match else Colors.red("✗ MISMATCH")
        print(f"  Hostname: {status}")

        # VLAN matches
        vlan_matches = validation.get("vlan_matches", [])
        if vlan_matches:
            print(f"\n  VLAN Matches ({len(vlan_matches)}):")
            for v in vlan_matches:
                print(f"    {Colors.green('✓')} VLAN {v['id']} - {v['name']}")

        # VLAN mismatches
        vlan_mismatches = validation.get("vlan_mismatches", [])
        if vlan_mismatches:
            print(f"\n  VLAN Mismatches ({len(vlan_mismatches)}):")
            for v in vlan_mismatches:
                print(f"    {Colors.red('✗')} VLAN {v['id']} - Issue: {v.get('issue', 'unknown')}")
                print(f"      Expected: {v.get('expected_name', 'N/A')}, Actual: {v.get('actual_name', 'N/A')}")

        # Extra VLANs
        extra_vlans = validation.get("extra_vlans", [])
        if extra_vlans:
            print(f"\n  Non-standard VLANs ({len(extra_vlans)}):")
            for v in extra_vlans:
                print(f"    {Colors.yellow('ℹ')} VLAN {v['id']} - {v['name']} (not in expected config)")

        # Alerts
        alerts = validation.get("alerts", [])
        if alerts:
            print(f"\n  Alerts:")
            for alert in alerts:
                if alert.startswith("OK"):
                    print(f"    {Colors.green(alert)}")
                elif alert.startswith("WARNING"):
                    print(f"    {Colors.yellow(alert)}")
                elif alert.startswith("INFO"):
                    print(f"    {Colors.cyan(alert)}")
                else:
                    print(f"    {alert}")

        # Overall validation
        is_valid = validation.get("is_valid", False)
        print()
        if is_valid:
            print(Colors.green("  ╔══════════════════════════════════════════════╗"))
            print(Colors.green("  ║  ✓ CONFIGURATION VALIDATION: ALL CHECKS PASS  ║"))
            print(Colors.green("  ╚══════════════════════════════════════════════╝"))
        else:
            print(Colors.red("  ╔══════════════════════════════════════════════╗"))
            print(Colors.red("  ║  ✗ CONFIGURATION VALIDATION: ISSUES DETECTED  ║"))
            print(Colors.red("  ╚══════════════════════════════════════════════╝"))

    # Phase 5: Post-configuration state
    print_header("PHASE 5: Post-Configuration Switch State")

    try:
        configurator2 = SwitchConfigurator(
            host=host,
            username=username,
            password=password,
            port=port,
            enable_password=enable_password,
        )
        configurator2.connect()

        print_step(1, "Reading hostname after configuration", "running")
        post_hostname = configurator2.get_hostname()
        print(f"Hostname: {post_hostname}")

        print_step(2, "Reading VLANs after configuration", "running")
        post_vlans = configurator2.get_vlans()
        print(f"VLANs:")
        for v in post_vlans:
            match = any(v["id"] == ev["id"] and v["name"] == ev["name"] for ev in vlans)
            icon = Colors.green("✓") if match else Colors.yellow("ℹ")
            print(f"    {icon} VLAN {v['id']} - {v['name']}")

        configurator2.disconnect()
    except Exception as e:
        print(Colors.red(f"Error reading post-config state: {str(e)}"))

    # Summary
    print_header("DEMO SUMMARY")

    elapsed = datetime.now() - start_time
    print(f"  Execution time: {elapsed.total_seconds():.1f} seconds")
    print(f"  Switch: {host}")
    print(f"  VLANs configured: {len(vlans)}")
    print(f"  Hostname: {hostname}")
    overall_success = result.get("success", False)
    if overall_success:
        print(Colors.green("  Status: ✓ ALL STEPS COMPLETED SUCCESSFULLY"))
    else:
        print(Colors.red("  Status: ✗ SOME STEPS FAILED"))
        print(f"  Errors: {len(result.get('errors', []))}")

    print()
    return 0 if overall_success else 1


def main():
    parser = argparse.ArgumentParser(
        description="GNS3 Demo Runner - Execute VLAN automation against a GNS3 Cisco switch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--host", type=str, default="192.168.122.10", help="Switch IP (default: 192.168.122.10)")
    parser.add_argument("--username", type=str, default="admin", help="SSH username (default: admin)")
    parser.add_argument("--password", type=str, default="admin", help="SSH password (default: admin)")
    parser.add_argument("--port", type=int, default=22, help="SSH port (default: 22)")
    parser.add_argument("--enable-password", type=str, default="admin", help="Enable secret (default: admin)")
    parser.add_argument("--hostname", type=str, default=DEFAULT_HOSTNAME, help=f"Target hostname (default: {DEFAULT_HOSTNAME})")
    parser.add_argument("--vlans", type=str, default=None, help="JSON array of VLANs (default: challenge VLANs 10/20/50)")
    parser.add_argument("--backup-dir", type=str, default="backups", help="Backup directory (default: backups)")
    parser.add_argument("--skip-check", action="store_true", help="Skip pre-flight connectivity check")
    parser.add_argument("--check-only", action="store_true", help="Only run connectivity check, then exit")

    args = parser.parse_args()

    # Parse VLANs
    if args.vlans:
        try:
            vlans = json.loads(args.vlans)
        except json.JSONDecodeError as e:
            print(f"Error parsing --vlans JSON: {str(e)}")
            sys.exit(1)
    else:
        vlans = DEFAULT_VLANS

    # Check-only mode
    if args.check_only:
        success = check_connectivity(args.host)
        sys.exit(0 if success else 1)

    # Run demo
    backup_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), args.backup_dir)
    exit_code = run_demo(
        host=args.host,
        username=args.username,
        password=args.password,
        port=args.port,
        vlans=vlans,
        hostname=args.hostname,
        enable_password=args.enable_password,
        backup_dir=backup_dir,
        skip_check=args.skip_check,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
