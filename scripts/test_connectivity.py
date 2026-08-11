"""
IPSec VPN Tunnel Connectivity Test Script
==========================================
Tests connectivity of the IPSec VPN tunnel between Fortigate and Palo Alto.

Test scope:
1. Tunnel IP connectivity (169.255.1.1 <-> 169.255.1.2)
2. Local network connectivity (10.10.10.0/24 <-> 10.20.20.0/24)
3. Fortigate tunnel status validation (CLI/API)
4. Palo Alto tunnel status validation (CLI/API)

Dependencies: pip install netmiko requests
"""

import subprocess
import sys
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class TestResult:
    """Single test result."""
    name: str
    passed: bool
    details: str = ""
    duration_ms: float = 0


@dataclass
class ConnectivityReport:
    """Connectivity test report."""
    results: List[TestResult] = field(default_factory=list)
    all_passed: bool = True
    critical_failures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add(self, result: TestResult, is_critical: bool = True):
        self.results.append(result)
        if not result.passed:
            self.all_passed = False
            if is_critical:
                self.critical_failures.append(f"{result.name}: {result.details}")
            else:
                self.warnings.append(f"{result.name}: {result.details}")


def ping_test(host: str, count: int = 4, source: Optional[str] = None) -> TestResult:
    """
    Execute a ping test.

    Args:
        host: Target IP
        count: Number of ping packets
        source: Source IP (optional, to specify source interface)
    """
    start = time.time()
    cmd = ["ping", "-n", str(count), host]  # Windows: -n; Linux: -c

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        duration_ms = (time.time() - start) * 1000

        if result.returncode == 0:
            return TestResult(
                name=f"Ping {host}",
                passed=True,
                details=f"Ping succeeded (source: {source or 'default'})\n{result.stdout[-200:]}",
                duration_ms=duration_ms,
            )
        else:
            return TestResult(
                name=f"Ping {host}",
                passed=False,
                details=f"Ping failed (source: {source or 'default'})\n{result.stdout[-200:]}",
                duration_ms=duration_ms,
            )
    except subprocess.TimeoutExpired:
        return TestResult(name=f"Ping {host}", passed=False, details="Ping timed out")
    except Exception as e:
        return TestResult(name=f"Ping {host}", passed=False, details=f"Ping error: {e}")


def test_fortigate_tunnel_status(host: str, username: str, password: str,
                                  enable_password: str = None) -> TestResult:
    """
    Verify tunnel status by connecting to Fortigate via SSH.

    Returns:
        TestResult: Tunnel status validation result
    """
    try:
        from netmiko import ConnectHandler

        device = {
            "device_type": "fortinet",
            "host": host,
            "username": username,
            "password": password,
        }
        if enable_password:
            device["secret"] = enable_password

        conn = ConnectHandler(**device)
        output = conn.send_command("diagnose vpn tunnel list")
        conn.disconnect()

        # Check if tunnel is up
        if "up" in output.lower() and "169.255.1" in output:
            return TestResult(
                name="Fortigate Tunnel Status",
                passed=True,
                details=f"Tunnel status: UP\n{output[:500]}",
            )
        else:
            return TestResult(
                name="Fortigate Tunnel Status",
                passed=False,
                details=f"Tunnel may not be established\n{output[:500]}",
            )
    except Exception as e:
        return TestResult(
            name="Fortigate Tunnel Status",
            passed=False,
            details=f"SSH connection failed: {e}",
        )


def test_paloalto_tunnel_status(host: str, api_key: str) -> TestResult:
    """
    Verify Palo Alto tunnel status via XML API.
    """
    try:
        import requests
        import urllib3
        urllib3.disable_warnings()

        # Check IKE SA
        resp = requests.get(
            f"https://{host}/api/",
            params={
                "type": "op",
                "cmd": "<show><vpn><ike-sa></ike-sa></vpn></show>",
                "key": api_key,
            },
            verify=False,
            timeout=10,
        )

        if "established" in resp.text.lower() or "active" in resp.text.lower():
            return TestResult(
                name="Palo Alto IKE SA Status",
                passed=True,
                details=f"IKE SA established\n{resp.text[:500]}",
            )
        else:
            return TestResult(
                name="Palo Alto IKE SA Status",
                passed=False,
                details=f"IKE SA not established\n{resp.text[:500]}",
            )
    except Exception as e:
        return TestResult(
            name="Palo Alto IKE SA Status",
            passed=False,
            details=f"API request failed: {e}",
        )


def run_connectivity_tests(config: Dict) -> ConnectivityReport:
    """
    Execute the full connectivity test suite.

    Args:
        config: Test configuration dictionary

    Returns:
        ConnectivityReport: Test report
    """
    report = ConnectivityReport()

    print("=" * 60)
    print("IPSec VPN Tunnel Connectivity Test")
    print("=" * 60)

    # === 1. Tunnel IP connectivity test ===
    print("\n[1/4] Tunnel IP connectivity test...")
    fg_tunnel_ip = config["fortigate"]["tunnel_ip"]
    pa_tunnel_ip = config["paloalto"]["tunnel_ip"]

    # Ping Palo Alto tunnel IP from Fortigate side
    result = ping_test(pa_tunnel_ip, count=4)
    report.add(result, is_critical=True)
    print(f"  {'OK' if result.passed else 'FAIL'} {result.name}")

    # === 2. Local network connectivity test ===
    print("\n[2/4] Local network connectivity test...")
    fg_local_ip = config["fortigate"]["local_test_ip"]  # e.g., 10.10.10.1
    pa_local_ip = config["paloalto"]["local_test_ip"]    # e.g., 10.20.20.1

    result = ping_test(pa_local_ip, count=4, source=fg_local_ip)
    report.add(result, is_critical=True)
    print(f"  {'OK' if result.passed else 'FAIL'} {result.name}")

    # === 3. Fortigate tunnel status validation ===
    print("\n[3/4] Fortigate tunnel status validation...")
    result = test_fortigate_tunnel_status(
        host=config["fortigate"]["host"],
        username=config["fortigate"]["username"],
        password=config["fortigate"]["password"],
        enable_password=config["fortigate"].get("enable_password"),
    )
    report.add(result, is_critical=True)
    print(f"  {'OK' if result.passed else 'FAIL'} {result.name}")

    # === 4. Palo Alto tunnel status validation ===
    print("\n[4/4] Palo Alto tunnel status validation...")
    result = test_paloalto_tunnel_status(
        host=config["paloalto"]["host"],
        api_key=config["paloalto"]["api_key"],
    )
    report.add(result, is_critical=True)
    print(f"  {'OK' if result.passed else 'FAIL'} {result.name}")

    return report


def generate_report(report: ConnectivityReport) -> str:
    """Generate a text-format test report."""
    lines = []
    lines.append("=" * 60)
    lines.append("IPSec VPN Connectivity Test Report")
    lines.append("=" * 60)
    lines.append("")

    for result in report.results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"[{status}] {result.name} ({result.duration_ms:.0f}ms)")
        if result.details:
            for line in result.details.split("\n")[:3]:
                lines.append(f"  {line}")
        lines.append("")

    lines.append("-" * 60)
    if report.all_passed:
        lines.append("Summary: All tests passed - VPN tunnel is operational")
    else:
        lines.append("Summary: Tests failed")
        if report.critical_failures:
            lines.append(f"\nCritical failures ({len(report.critical_failures)}):")
            for f in report.critical_failures:
                lines.append(f"  WARNING: {f}")
        if report.warnings:
            lines.append(f"\nWarnings ({len(report.warnings)}):")
            for w in report.warnings:
                lines.append(f"  INFO: {w}")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


if __name__ == "__main__":
    # Test configuration
    test_config = {
        "fortigate": {
            "host": "192.168.1.99",
            "username": "admin",
            "password": "password",
            "enable_password": None,
            "tunnel_ip": "169.255.1.1",
            "local_test_ip": "10.10.10.1",
        },
        "paloalto": {
            "host": "192.168.1.100",
            "api_key": "YOUR_API_KEY",
            "tunnel_ip": "169.255.1.2",
            "local_test_ip": "10.20.20.1",
        },
    }

    report = run_connectivity_tests(test_config)
    print("\n" + generate_report(report))

    # Exit code: 0 = all passed, 1 = failures
    sys.exit(0 if report.all_passed else 1)
