"""
Flask Web Application
=====================
Cisco Switch VLAN Configuration Automation Frontend.
Provides a web interface for users to input VLAN information, switch connection
parameters, and hostname, then execute automated configuration and display
validation results and alerts.
"""

import os
from flask import Flask, render_template, request, jsonify
from backend.switch_config import SwitchConfigurator, DEFAULT_VLANS, DEFAULT_HOSTNAME

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False


@app.route("/")
def index():
    """Render the main page."""
    return render_template("index.html", default_vlans=DEFAULT_VLANS, default_hostname=DEFAULT_HOSTNAME)


@app.route("/api/configure", methods=["POST"])
def configure():
    """
    API endpoint to execute the full configuration workflow.

    Accepts JSON parameters:
    - host: Switch IP
    - username: SSH username
    - password: SSH password
    - port: SSH port (optional, default 22)
    - enable_password: Enable password (optional)
    - hostname: Target hostname
    - vlans: VLAN list [{"id": "10", "name": "VLAN_DATOS"}, ...]
    - simulate: Whether to use simulation mode

    Returns JSON result containing each step's execution status and validation alerts.
    """
    data = request.json

    # Extract parameters
    host = data.get("host", "192.168.1.1")
    username = data.get("username", "admin")
    password = data.get("password", "admin")
    port = int(data.get("port", 22))
    enable_password = data.get("enable_password", password)
    hostname = data.get("hostname", DEFAULT_HOSTNAME)
    vlans = data.get("vlans", DEFAULT_VLANS)
    simulate = data.get("simulate", False)

    # Create configurator instance
    configurator = SwitchConfigurator(
        host=host,
        username=username,
        password=password,
        port=port,
        enable_password=enable_password,
        simulate=simulate,
    )

    # Execute full configuration workflow
    result = configurator.apply_full_configuration(
        vlans=vlans,
        hostname=hostname,
        backup_dir=os.path.join(os.path.dirname(__file__), "backups"),
    )

    return jsonify(result)


@app.route("/api/validate", methods=["POST"])
def validate():
    """
    API endpoint to execute configuration validation only.

    Accepts the same parameters as /api/configure, plus expected_vlans and expected_hostname.
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
        result = {"is_valid": False, "alerts": [f"Connection failed: {str(e)}"]}
    finally:
        configurator.disconnect()

    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
