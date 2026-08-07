"""
Cisco交换机配置模块
====================
使用Netmiko实现对Cisco交换机的自动化配置，包括：
- VLAN创建与命名
- 主机名修改
- 配置保存到NVRAM
- 配置备份
- 配置验证

支持真实设备和模拟模式（无需真实交换机时自动切换）。
"""

import os
import re
from datetime import datetime
from netmiko import ConnectHandler
from netmiko.ssh_exception import NetmikoTimeoutException, NetmikoAuthenticationException


# 默认VLAN配置（符合挑战要求）
DEFAULT_VLANS = [
    {"id": "10", "name": "VLAN_DATOS"},
    {"id": "20", "name": "VLAN_VOZ"},
    {"id": "50", "name": "VLAN_SEGURIDAD"},
]

DEFAULT_HOSTNAME = "SWITCH_AUTOMATIZADO"


class SwitchConfigurator:
    """Cisco交换机配置器，封装所有与交换机的交互逻辑。"""

    def __init__(self, host, username, password, port=22, device_type="cisco_ios", enable_password=None, simulate=False):
        """
        初始化交换机连接参数。

        Args:
            host: 交换机IP地址
            username: SSH用户名
            password: SSH密码
            port: SSH端口，默认22
            device_type: 设备类型，默认cisco_ios
            enable_password: enable密码（可选）
            simulate: 是否使用模拟模式（无真实设备时用于演示）
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.device_type = device_type
        self.enable_password = enable_password or password
        self.simulate = simulate
        self.connection = None

        # 模拟模式下的虚拟配置状态
        self._sim_vlans = {}
        self._sim_hostname = "Switch"

    def _get_device_params(self):
        """构建Netmiko设备参数字典。"""
        return {
            "device_type": self.device_type,
            "host": self.host,
            "username": self.username,
            "password": self.password,
            "port": self.port,
            "secret": self.enable_password,
        }

    def connect(self):
        """建立与交换机的SSH连接。"""
        if self.simulate:
            return True
        try:
            self.connection = ConnectHandler(**self._get_device_params())
            self.connection.enable()
            return True
        except (NetmikoTimeoutException, NetmikoAuthenticationException) as e:
            raise ConnectionError(f"无法连接到交换机 {self.host}: {str(e)}")

    def disconnect(self):
        """断开与交换机的连接。"""
        if self.connection and not self.simulate:
            self.connection.disconnect()
        self.connection = None

    def configure_vlans(self, vlans):
        """
        在交换机上配置VLAN。

        Args:
            vlans: VLAN列表，每个元素为 {"id": "10", "name": "VLAN_DATOS"}

        Returns:
            dict: 配置结果，包含成功/失败状态和输出信息
        """
        results = {"success": True, "details": [], "errors": []}

        if self.simulate:
            for vlan in vlans:
                self._sim_vlans[vlan["id"]] = vlan["name"]
                results["details"].append(f"[模拟] VLAN {vlan['id']} 已创建，名称: {vlan['name']}")
            return results

        # 构建VLAN配置命令
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
            results["errors"].append(f"VLAN配置失败: {str(e)}")

        return results

    def configure_hostname(self, hostname):
        """
        修改交换机主机名。

        Args:
            hostname: 新的主机名

        Returns:
            dict: 配置结果
        """
        results = {"success": True, "details": [], "errors": []}

        if self.simulate:
            self._sim_hostname = hostname
            results["details"].append(f"[模拟] 主机名已修改为: {hostname}")
            return results

        try:
            output = self.connection.send_config_set([f"hostname {hostname}"])
            results["details"].append(output)
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"主机名修改失败: {str(e)}")

        return results

    def save_config(self):
        """
        将当前配置保存到NVRAM。

        Returns:
            dict: 保存结果
        """
        results = {"success": True, "details": [], "errors": []}

        if self.simulate:
            results["details"].append("[模拟] 配置已保存到NVRAM (write memory)")
            return results

        try:
            output = self.connection.save_config()
            results["details"].append(f"配置已保存到NVRAM: {output}")
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"配置保存失败: {str(e)}")

        return results

    def backup_config(self, backup_dir="backups"):
        """
        备份交换机配置到本地文件。
        文件名格式: {hostname}_{YYYYMMDD_HHMMSS}.cfg

        Args:
            backup_dir: 备份文件保存目录

        Returns:
            dict: 备份结果，包含文件路径
        """
        results = {"success": True, "details": [], "errors": [], "file_path": None}

        # 获取当前主机名用于文件命名
        hostname = self.get_hostname()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{hostname}_{timestamp}.cfg"
        filepath = os.path.join(backup_dir, filename)

        # 确保备份目录存在
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
            results["details"].append(f"[模拟] 配置已备份到: {filepath}")
            results["file_path"] = filepath
            return results

        try:
            output = self.connection.send_command("show running-config")
            with open(filepath, "w") as f:
                f.write(output)
            results["details"].append(f"配置已备份到: {filepath}")
            results["file_path"] = filepath
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"配置备份失败: {str(e)}")

        return results

    def get_running_config(self):
        """
        获取交换机当前运行配置。

        Returns:
            str: 当前运行配置文本
        """
        if self.simulate:
            config = f"hostname {self._sim_hostname}\n"
            for vlan_id, vlan_name in self._sim_vlans.items():
                config += f"vlan {vlan_id}\n name {vlan_name}\n"
            return config

        return self.connection.send_command("show running-config")

    def get_hostname(self):
        """获取当前交换机主机名。"""
        if self.simulate:
            return self._sim_hostname

        output = self.connection.send_command("show running-config | include hostname")
        match = re.search(r"hostname\s+(\S+)", output)
        return match.group(1) if match else "unknown"

    def get_vlans(self):
        """
        获取交换机当前VLAN配置。

        Returns:
            list: VLAN列表，每个元素为 {"id": "10", "name": "VLAN_DATOS"}
        """
        if self.simulate:
            return [{"id": vid, "name": vname} for vid, vname in self._sim_vlans.items()]

        output = self.connection.send_command("show vlan brief")
        vlans = []
        for line in output.splitlines():
            # 匹配格式: 10   VLAN_DATOS                     active
            match = re.match(r"^(\d+)\s+(\S+)", line.strip())
            if match:
                vlan_id = match.group(1)
                vlan_name = match.group(2)
                # 排除默认VLAN 1和1002-1005
                if vlan_id not in ("1", "1002", "1003", "1004", "1005"):
                    vlans.append({"id": vlan_id, "name": vlan_name})
        return vlans

    def apply_full_configuration(self, vlans, hostname, backup_dir="backups"):
        """
        执行完整的配置流程：配置VLAN → 修改主机名 → 保存 → 备份 → 验证。

        Args:
            vlans: VLAN列表
            hostname: 目标主机名
            backup_dir: 备份目录

        Returns:
            dict: 完整执行结果，包含每一步的状态
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
            # Step 1: 连接
            self.connect()
            full_result["connection"] = True

            # Step 2: 配置VLAN
            full_result["vlan_config"] = self.configure_vlans(vlans)
            if not full_result["vlan_config"]["success"]:
                full_result["errors"].extend(full_result["vlan_config"]["errors"])

            # Step 3: 修改主机名
            full_result["hostname_config"] = self.configure_hostname(hostname)
            if not full_result["hostname_config"]["success"]:
                full_result["errors"].extend(full_result["hostname_config"]["errors"])

            # Step 4: 保存配置到NVRAM
            full_result["save"] = self.save_config()
            if not full_result["save"]["success"]:
                full_result["errors"].extend(full_result["save"]["errors"])

            # Step 5: 备份配置
            full_result["backup"] = self.backup_config(backup_dir)
            if not full_result["backup"]["success"]:
                full_result["errors"].extend(full_result["backup"]["errors"])

            # Step 6: 验证配置
            full_result["validation"] = self.validate_configuration(vlans, hostname)

            full_result["success"] = len(full_result["errors"]) == 0

        except Exception as e:
            full_result["errors"].append(str(e))
        finally:
            self.disconnect()

        return full_result

    def validate_configuration(self, expected_vlans, expected_hostname):
        """
        验证交换机当前配置是否与期望配置一致。

        检查项:
        - 主机名是否匹配
        - 每个期望VLAN是否存在且名称正确
        - 是否存在非标准配置（额外VLAN等）

        Args:
            expected_vlans: 期望的VLAN列表
            expected_hostname: 期望的主机名

        Returns:
            dict: 验证结果，包含匹配状态、偏差列表和告警信息
        """
        result = {
            "is_valid": True,
            "alerts": [],
            "hostname_match": False,
            "vlan_matches": [],
            "vlan_mismatches": [],
            "extra_vlans": [],
        }

        # 验证主机名
        actual_hostname = self.get_hostname()
        if actual_hostname == expected_hostname:
            result["hostname_match"] = True
        else:
            result["is_valid"] = False
            result["alerts"].append(
                f"⚠ 主机名不匹配！期望: '{expected_hostname}'，实际: '{actual_hostname}'"
            )

        # 获取当前VLAN配置
        actual_vlans = self.get_vlans()
        actual_vlan_map = {v["id"]: v["name"] for v in actual_vlans}
        expected_vlan_map = {v["id"]: v["name"] for v in expected_vlans}

        # 验证每个期望VLAN
        for vlan_id, expected_name in expected_vlan_map.items():
            if vlan_id not in actual_vlan_map:
                result["is_valid"] = False
                result["vlan_mismatches"].append(
                    {"id": vlan_id, "issue": "缺失", "expected_name": expected_name, "actual_name": None}
                )
                result["alerts"].append(
                    f"⚠ VLAN {vlan_id} 缺失！期望名称: '{expected_name}'"
                )
            elif actual_vlan_map[vlan_id] != expected_name:
                result["is_valid"] = False
                result["vlan_mismatches"].append(
                    {"id": vlan_id, "issue": "名称不匹配", "expected_name": expected_name, "actual_name": actual_vlan_map[vlan_id]}
                )
                result["alerts"].append(
                    f"⚠ VLAN {vlan_id} 名称不匹配！期望: '{expected_name}'，实际: '{actual_vlan_map[vlan_id]}'"
                )
            else:
                result["vlan_matches"].append(
                    {"id": vlan_id, "name": expected_name, "status": "匹配"}
                )

        # 检查是否有非标准VLAN（不在期望列表中的VLAN）
        for vlan_id, vlan_name in actual_vlan_map.items():
            if vlan_id not in expected_vlan_map:
                result["extra_vlans"].append({"id": vlan_id, "name": vlan_name})
                result["alerts"].append(
                    f"ℹ 发现非标准VLAN {vlan_id}（名称: '{vlan_name}'），不在期望配置中"
                )

        if result["is_valid"]:
            result["alerts"].append("✓ 配置验证通过！所有VLAN和主机名均与期望配置一致。")

        return result
