"""
Integration Tests for Flask API
================================
Tests the Flask web application endpoints using the test client.
All tests use simulation mode (no real switch required).
"""

import json


class TestFlaskIndex:
    """Tests for the index page."""

    def test_index_returns_200(self, flask_client):
        """Index page should return HTTP 200."""
        response = flask_client.get("/")
        assert response.status_code == 200

    def test_index_contains_title(self, flask_client):
        """Index page should contain the application title."""
        response = flask_client.get("/")
        assert b"VLAN" in response.data or b"vlan" in response.data.lower()

    def test_index_contains_vlan_table(self, flask_client):
        """Index page should contain pre-populated VLAN data."""
        response = flask_client.get("/")
        html = response.data.decode()
        assert "10" in html
        assert "VLAN_DATOS" in html
        assert "20" in html
        assert "VLAN_VOZ" in html
        assert "50" in html
        assert "VLAN_SEGURIDAD" in html


class TestFlaskConfigureAPI:
    """Tests for the /api/configure endpoint."""

    def test_configure_sim_mode_success(self, flask_client):
        """Configuration in simulation mode should succeed."""
        payload = {
            "host": "192.168.1.1",
            "username": "admin",
            "password": "admin",
            "hostname": "SWITCH_AUTOMATIZADO",
            "vlans": [
                {"id": "10", "name": "VLAN_DATOS"},
                {"id": "20", "name": "VLAN_VOZ"},
                {"id": "50", "name": "VLAN_SEGURIDAD"},
            ],
            "simulate": True,
        }
        response = flask_client.post(
            "/api/configure",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["connection"] is True
        assert data["vlan_config"]["success"] is True
        assert data["hostname_config"]["success"] is True
        assert data["save"]["success"] is True
        assert data["backup"]["success"] is True
        assert data["validation"]["is_valid"] is True

    def test_configure_with_default_vlans(self, flask_client):
        """Configuration without explicit VLANs should use defaults."""
        payload = {
            "host": "10.0.0.1",
            "username": "admin",
            "password": "admin",
            "simulate": True,
        }
        response = flask_client.post(
            "/api/configure",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_configure_missing_host(self, flask_client):
        """Missing host should use default and still work in sim mode."""
        payload = {
            "username": "admin",
            "password": "admin",
            "simulate": True,
        }
        response = flask_client.post(
            "/api/configure",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_configure_invalid_json(self, flask_client):
        """Invalid JSON should not crash the server."""
        response = flask_client.post(
            "/api/configure",
            data="not json",
            content_type="application/json",
        )
        # Flask will return 400 or handle gracefully
        assert response.status_code in (200, 400, 415)


class TestFlaskValidateAPI:
    """Tests for the /api/validate endpoint."""

    def test_validate_sim_mode(self, flask_client):
        """Validation in simulation mode should work."""
        payload = {
            "host": "192.168.1.1",
            "username": "admin",
            "password": "admin",
            "expected_vlans": [
                {"id": "10", "name": "VLAN_DATOS"},
            ],
            "expected_hostname": "SWITCH_AUTOMATIZADO",
            "simulate": True,
        }
        response = flask_client.post(
            "/api/validate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "is_valid" in data
        assert "alerts" in data


class TestFlaskHealthAPI:
    """Tests for health check endpoints (added for CI/CD)."""

    def test_health_endpoint(self, flask_client):
        """/health should return 200 with status JSON."""
        response = flask_client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy"

    def test_ready_endpoint(self, flask_client):
        """/ready should return 200 with readiness info."""
        response = flask_client.get("/ready")
        assert response.status_code == 200
        data = response.get_json()
        assert "ready" in data
