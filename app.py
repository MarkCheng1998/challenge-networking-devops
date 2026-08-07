"""
Flask Web应用
==============
Cisco交换机VLAN配置自动化前端。
提供Web界面让用户输入VLAN信息、交换机连接参数和主机名，
执行自动化配置并展示验证结果和告警。
"""

import os
from flask import Flask, render_template, request, jsonify
from backend.switch_config import SwitchConfigurator, DEFAULT_VLANS, DEFAULT_HOSTNAME

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False


@app.route("/")
def index():
    """渲染主页面。"""
    return render_template("index.html", default_vlans=DEFAULT_VLANS, default_hostname=DEFAULT_HOSTNAME)


@app.route("/api/configure", methods=["POST"])
def configure():
    """
    执行完整配置流程的API端点。

    接收JSON参数:
    - host: 交换机IP
    - username: SSH用户名
    - password: SSH密码
    - port: SSH端口（可选，默认22）
    - enable_password: enable密码（可选）
    - hostname: 目标主机名
    - vlans: VLAN列表 [{"id": "10", "name": "VLAN_DATOS"}, ...]
    - simulate: 是否使用模拟模式

    返回JSON结果，包含每一步的执行状态和验证告警。
    """
    data = request.json

    # 提取参数
    host = data.get("host", "192.168.1.1")
    username = data.get("username", "admin")
    password = data.get("password", "admin")
    port = int(data.get("port", 22))
    enable_password = data.get("enable_password", password)
    hostname = data.get("hostname", DEFAULT_HOSTNAME)
    vlans = data.get("vlans", DEFAULT_VLANS)
    simulate = data.get("simulate", False)

    # 创建配置器实例
    configurator = SwitchConfigurator(
        host=host,
        username=username,
        password=password,
        port=port,
        enable_password=enable_password,
        simulate=simulate,
    )

    # 执行完整配置流程
    result = configurator.apply_full_configuration(
        vlans=vlans,
        hostname=hostname,
        backup_dir=os.path.join(os.path.dirname(__file__), "backups"),
    )

    return jsonify(result)


@app.route("/api/validate", methods=["POST"])
def validate():
    """
    单独执行配置验证的API端点。

    接收与 /api/configure 相同的参数，加上 expected_vlans 和 expected_hostname。
    """
    data = request.json

    host = data.get("host", "192.168.1.1")
    username = data.get("username", "admin")
    password = data.get("password", "admin")
    port = int(data.get("port", 22))
    enable_password = data.get("enable_password", password)
    expected_vlans = data.get("expected_vlans", DEFAULT_VLANS)
    expected_hostname = data.get("expected_hostname", DEFAULT_HOSTNAME)
    simulate = data.get("simulate", False)

    configurator = SwitchConfigurator(
        host=host,
        username=username,
        password=password,
        port=port,
        enable_password=enable_password,
        simulate=simulate,
    )

    try:
        configurator.connect()
        result = configurator.validate_configuration(expected_vlans, expected_hostname)
    except Exception as e:
        result = {"is_valid": False, "alerts": [f"连接失败: {str(e)}"]}
    finally:
        configurator.disconnect()

    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
