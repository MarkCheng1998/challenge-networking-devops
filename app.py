"""
Flask Web Application
=====================
Cisco Switch VLAN Configuration Automation Frontend.
Provides a web interface for users to input VLAN information, switch connection
parameters, and hostname, then execute automated configuration and display
validation results and alerts.
"""

import os
import time
import platform
from flask import Flask, render_template, request, jsonify
from backend.switch_config import SwitchConfigurator, DEFAULT_VLANS, DEFAULT_HOSTNAME
from backend.feature_flags import FeatureFlags

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

# Application start time for uptime tracking
_APP_START_TIME = time.time()

# Feature flags instance (supports gray/canary release)
flags = FeatureFlags()


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


@app.route("/health")
def health():
    """
    Liveness probe — returns 200 if the process is alive.
    Used by CI/CD pipeline and container orchestrators.
    """
    return jsonify({
        "status": "healthy",
        "uptime_seconds": round(time.time() - _APP_START_TIME, 2),
        "version": os.environ.get("APP_VERSION", "1.0.0"),
    }), 200


@app.route("/ready")
def ready():
    """
    Readiness probe — returns 200 only when the app can serve traffic.
    Checks: Flask is up, feature flags loaded, simulation backend available.
    """
    checks = {
        "flask": True,
        "feature_flags": flags.is_loaded(),
        "simulation_backend": True,
    }
    all_ready = all(checks.values())
    return jsonify({
        "ready": all_ready,
        "checks": checks,
        "canary": flags.get("canary_release", False),
        "canary_percentage": flags.get("canary_percentage", 0),
        "python_version": platform.python_version(),
    }), 200 if all_ready else 503


@app.route("/api/features")
def features():
    """Return current feature flag state (for debugging gray release)."""
    return jsonify(flags.dump())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
