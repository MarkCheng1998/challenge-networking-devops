"""
Feature Flags Module
====================
Supports gray/canary release by controlling feature visibility at runtime.

Flags are loaded from:
1. Environment variables (highest priority, used in CI/CD)
2. config/feature_flags.json (default values, committed to repo)

Usage in code:
    from backend.feature_flags import FeatureFlags
    flags = FeatureFlags()
    if flags.get("canary_release"):
        # canary-only code path
"""

import os
import json


# Default flag values — safe defaults for production
_DEFAULT_FLAGS = {
    "canary_release": False,
    "canary_percentage": 0,
    "enable_validation_alerts": True,
    "enable_backup_on_config": True,
    "enable_sim_mode_default": False,
    "max_vlans_per_request": 50,
    "enable_ssh_timeout_override": False,
    "ssh_timeout_seconds": 30,
    "maintenance_mode": False,
    "enable_audit_log": True,
}


class FeatureFlags:
    """
    Feature flag manager for gray/canary releases.

    Flags can be toggled via:
    - Environment variables: FEATURE_CANARY_RELEASE=true
    - JSON config file: config/feature_flags.json
    - Runtime: flags.set("canary_release", True)
    """

    def __init__(self, config_path=None):
        self._flags = dict(_DEFAULT_FLAGS)
        self._config_path = config_path or os.path.join(
            os.path.dirname(__file__), "..", "config", "feature_flags.json"
        )
        self._loaded = False
        self.load()

    def load(self):
        """Load flags from config file and environment variables."""
        # Load from JSON file (if exists)
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r") as f:
                    file_flags = json.load(f)
                    self._flags.update(file_flags)
                    self._loaded = True
            except (json.JSONDecodeError, IOError):
                pass

        # Environment variables override file values
        # Format: FEATURE_<FLAG_NAME> in uppercase
        for key in list(self._flags.keys()):
            env_key = f"FEATURE_{key.upper()}"
            env_val = os.environ.get(env_key)
            if env_val is not None:
                self._flags[key] = self._parse_env_value(env_val)
                self._loaded = True

        # Mark as loaded if we have at least default flags
        if not self._loaded:
            self._loaded = True

    def _parse_env_value(self, val):
        """Parse environment variable string to appropriate type."""
        if val.lower() in ("true", "1", "yes", "on"):
            return True
        if val.lower() in ("false", "0", "no", "off"):
            return False
        try:
            return int(val)
        except ValueError:
            try:
                return float(val)
            except ValueError:
                return val

    def get(self, key, default=None):
        """Get a feature flag value."""
        return self._flags.get(key, default)

    def set(self, key, value):
        """Set a feature flag at runtime (not persisted)."""
        self._flags[key] = value

    def is_loaded(self):
        """Return True if flags have been loaded."""
        return self._loaded

    def dump(self):
        """Return all flags as a dict (for debugging/API)."""
        return dict(self._flags)

    def is_canary_enabled(self):
        """Check if canary release is active."""
        return self.get("canary_release", False) and self.get("canary_percentage", 0) > 0

    def should_route_to_canary(self, request_id=None):
        """
        Determine if a request should be routed to canary.

        Uses canary_percentage as a probability gate.
        If request_id is provided, uses hash-based routing for consistency.
        """
        if not self.is_canary_enabled():
            return False
        percentage = self.get("canary_percentage", 0)
        if percentage >= 100:
            return True
        if percentage <= 0:
            return False
        if request_id:
            # Hash-based consistent routing
            import hashlib
            hash_val = int(hashlib.md5(request_id.encode()).hexdigest(), 16)
            return (hash_val % 100) < percentage
        # Random routing
        import random
        return random.randint(1, 100) <= percentage
