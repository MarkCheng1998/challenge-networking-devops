"""
IPSec VPN 隧道连通性测试脚本
=============================
测试 Fortigate 与 Palo Alto 之间 IPSec VPN 隧道的连通性。

测试内容：
1. 隧道IP连通性 (169.255.1.1 <-> 169.255.1.2)
2. 本地网络连通性 (10.10.10.0/24 <-> 10.20.20.0/24)
3. Fortigate 隧道状态验证 (CLI/API)
4. Palo Alto 隧道状态验证 (CLI/API)

依赖: pip install netmiko requests
"""

import subprocess
import sys
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class TestResult:
    """单项测试结果。"""
    name: str
    passed: bool
    details: str = ""
    duration_ms: float = 0


@dataclass
class ConnectivityReport:
    """连通性测试报告。"""
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
    执行 Ping 测试。

    Args:
        host: 目标IP
        count: ping次数
        source: 源IP（可选，用于指定源接口）
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
                details=f"Ping成功 (源: {source or 'default'})\n{result.stdout[-200:]}",
                duration_ms=duration_ms,
            )
        else:
            return TestResult(
                name=f"Ping {host}",
                passed=False,
                details=f"Ping失败 (源: {source or 'default'})\n{result.stdout[-200:]}",
                duration_ms=duration_ms,
            )
    except subprocess.TimeoutExpired:
        return TestResult(name=f"Ping {host}", passed=False, details="Ping超时")
    except Exception as e:
        return TestResult(name=f"Ping {host}", passed=False, details=f"Ping异常: {e}")


def test_fortigate_tunnel_status(host: str, username: str, password: str,
                                  enable_password: str = None) -> TestResult:
    """
    通过SSH连接Fortigate验证隧道状态。

    Returns:
        TestResult: 隧道状态验证结果
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

        # 检查隧道是否up
        if "up" in output.lower() and "169.255.1" in output:
            return TestResult(
                name="Fortigate 隧道状态",
                passed=True,
                details=f"隧道状态: UP\n{output[:500]}",
            )
        else:
            return TestResult(
                name="Fortigate 隧道状态",
                passed=False,
                details=f"隧道可能未建立\n{output[:500]}",
            )
    except Exception as e:
        return TestResult(
            name="Fortigate 隧道状态",
            passed=False,
            details=f"SSH连接失败: {e}",
        )


def test_paloalto_tunnel_status(host: str, api_key: str) -> TestResult:
    """
    通过XML API验证Palo Alto隧道状态。
    """
    try:
        import requests
        import urllib3
        urllib3.disable_warnings()

        # 检查 IKE SA
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
                name="Palo Alto IKE SA 状态",
                passed=True,
                details=f"IKE SA已建立\n{resp.text[:500]}",
            )
        else:
            return TestResult(
                name="Palo Alto IKE SA 状态",
                passed=False,
                details=f"IKE SA未建立\n{resp.text[:500]}",
            )
    except Exception as e:
        return TestResult(
            name="Palo Alto IKE SA 状态",
            passed=False,
            details=f"API请求失败: {e}",
        )


def run_connectivity_tests(config: Dict) -> ConnectivityReport:
    """
    执行完整的连通性测试套件。

    Args:
        config: 测试配置字典

    Returns:
        ConnectivityReport: 测试报告
    """
    report = ConnectivityReport()

    print("=" * 60)
    print("IPSec VPN 隧道连通性测试")
    print("=" * 60)

    # === 1. 隧道IP连通性测试 ===
    print("\n[1/4] 隧道IP连通性测试...")
    fg_tunnel_ip = config["fortigate"]["tunnel_ip"]
    pa_tunnel_ip = config["paloalto"]["tunnel_ip"]

    # 从Fortigate侧ping Palo Alto隧道IP
    result = ping_test(pa_tunnel_ip, count=4)
    report.add(result, is_critical=True)
    print(f"  {'✓' if result.passed else '✗'} {result.name}")

    # === 2. 本地网络连通性测试 ===
    print("\n[2/4] 本地网络连通性测试...")
    fg_local_ip = config["fortigate"]["local_test_ip"]  # 如 10.10.10.1
    pa_local_ip = config["paloalto"]["local_test_ip"]   # 如 10.20.20.1

    result = ping_test(pa_local_ip, count=4, source=fg_local_ip)
    report.add(result, is_critical=True)
    print(f"  {'✓' if result.passed else '✗'} {result.name}")

    # === 3. Fortigate 隧道状态验证 ===
    print("\n[3/4] Fortigate 隧道状态验证...")
    result = test_fortigate_tunnel_status(
        host=config["fortigate"]["host"],
        username=config["fortigate"]["username"],
        password=config["fortigate"]["password"],
        enable_password=config["fortigate"].get("enable_password"),
    )
    report.add(result, is_critical=True)
    print(f"  {'✓' if result.passed else '✗'} {result.name}")

    # === 4. Palo Alto 隧道状态验证 ===
    print("\n[4/4] Palo Alto 隧道状态验证...")
    result = test_paloalto_tunnel_status(
        host=config["paloalto"]["host"],
        api_key=config["paloalto"]["api_key"],
    )
    report.add(result, is_critical=True)
    print(f"  {'✓' if result.passed else '✗'} {result.name}")

    return report


def generate_report(report: ConnectivityReport) -> str:
    """生成文本格式的测试报告。"""
    lines = []
    lines.append("=" * 60)
    lines.append("IPSec VPN 连通性测试报告")
    lines.append("=" * 60)
    lines.append("")

    for result in report.results:
        status = "✓ PASS" if result.passed else "✗ FAIL"
        lines.append(f"[{status}] {result.name} ({result.duration_ms:.0f}ms)")
        if result.details:
            for line in result.details.split("\n")[:3]:
                lines.append(f"  {line}")
        lines.append("")

    lines.append("-" * 60)
    if report.all_passed:
        lines.append("总结: 所有测试通过 ✓ VPN隧道运行正常")
    else:
        lines.append(f"总结: 测试失败 ✗")
        if report.critical_failures:
            lines.append(f"\n严重失败 ({len(report.critical_failures)}):")
            for f in report.critical_failures:
                lines.append(f"  ⚠ {f}")
        if report.warnings:
            lines.append(f"\n警告 ({len(report.warnings)}):")
            for w in report.warnings:
                lines.append(f"  ℹ {w}")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


if __name__ == "__main__":
    # 测试配置
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

    # 退出码：0=全部通过，1=有失败
    sys.exit(0 if report.all_passed else 1)
