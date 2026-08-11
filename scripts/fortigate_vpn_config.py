"""
Fortigate IPSec VPN Configuration Script
=========================================
Configures an IPSec VPN tunnel via the FortiOS REST API.

Before use, enable API Token on the Fortigate:
  System -> Administrators -> REST API Admin -> Create Token

Dependencies: pip install requests
"""

import requests
import json
import urllib3
from typing import Dict, Any

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class FortigateVPNConfigurator:
    """Fortigate IPSec VPN configurator using the FortiOS REST API."""

    def __init__(self, host: str, api_token: str, verify_ssl: bool = False):
        """
        Args:
            host: Fortigate management IP (e.g., 192.168.1.99)
            api_token: FortiOS REST API Token
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = f"https://{host}/api/v2"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        })
        self.verify_ssl = verify_ssl

    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        """Send an API request."""
        url = f"{self.base_url}{endpoint}"
        response = self.session.request(method, url, json=data, verify=self.verify_ssl)
        result = response.json()
        if result.get("http_status") != 200 and result.get("http_status") != 201:
            raise Exception(f"API request failed [{endpoint}]: {json.dumps(result, indent=2)}")
        return result

    def create_address_object(self, name: str, subnet: str) -> Dict:
        """Create an address object."""
        ip, mask = subnet.split("/")
        return self._request("POST", "/cmdb/firewall/address", {
            "name": name,
            "type": "ipmask",
            "subnet": f"{ip} {mask}",
        })

    def configure_phase1(self, name: str, interface: str, remote_gw: str,
                          psk: str, ike_version: int = 2) -> Dict:
        """Configure Phase 1 (IKE Gateway)."""
        return self._request("POST", "/cmdb/vpn.ipsec/phase1-interface", {
            "name": name,
            "interface": interface,
            "ike-version": str(ike_version),
            "peertype": "any",
            "proposal": "aes256-sha256-dh14",
            "remote-gw": remote_gw,
            "psksecret": psk,
        })

    def configure_phase2(self, name: str, phase1_name: str,
                          src_subnet: str, dst_subnet: str) -> Dict:
        """Configure Phase 2 (IPSec Proposal)."""
        return self._request("POST", "/cmdb/vpn.ipsec/phase2-interface", {
            "name": name,
            "phase1name": phase1_name,
            "proposal": "aes256-sha256",
            "dhgrp": "14",
            "src-subnet": src_subnet,
            "dst-subnet": dst_subnet,
        })

    def configure_tunnel_interface(self, name: str, ip: str, mask: str) -> Dict:
        """Configure the tunnel interface IP."""
        return self._request("PUT", f"/cmdb/system/interface/{name}", {
            "ip": ip,
            "mask": mask,
        })

    def configure_firewall_policy(self, policy_id: int, src_intf: str, dst_intf: str,
                                   src_addr: str, dst_addr: str) -> Dict:
        """Configure a firewall policy."""
        return self._request("POST", "/cmdb/firewall/policy", {
            "policyid": policy_id,
            "srcintf": [{"name": src_intf}],
            "dstintf": [{"name": dst_intf}],
            "srcaddr": [{"name": src_addr}],
            "dstaddr": [{"name": dst_addr}],
            "action": "accept",
            "schedule": "always",
            "service": [{"name": "ALL"}],
        })

    def configure_static_route(self, dst_subnet: str, device: str) -> Dict:
        """Configure a static route."""
        ip, mask = dst_subnet.split("/")
        return self._request("POST", "/cmdb/router/static", {
            "dst": f"{ip} {mask}",
            "device": device,
        })

    def get_vpn_status(self) -> Dict:
        """Get VPN tunnel status."""
        return self._request("GET", "/monitor/vpn/ipsec")

    def apply_full_config(self, params: Dict) -> Dict:
        """
        Execute the full VPN configuration workflow.

        Args:
            params: Configuration parameter dictionary (see JSON template in vpn_ipsec_plan.md)

        Returns:
            dict: Execution result for each step
        """
        results = {"steps": [], "success": True, "errors": []}

        steps = [
            ("Create address object - local network", lambda: self.create_address_object(
                "obj_local_net", params["local_subnet"])),
            ("Create address object - remote network", lambda: self.create_address_object(
                "obj_remote_net", params["remote_subnet"])),
            ("Configure Phase 1 (IKE)", lambda: self.configure_phase1(
                params["tunnel_name"], params["wan_interface"],
                params["remote_peer"], params["psk"])),
            ("Configure Phase 2 (IPSec)", lambda: self.configure_phase2(
                f"{params['tunnel_name']}-P2", params["tunnel_name"],
                params["local_subnet"], params["remote_subnet"])),
            ("Configure tunnel interface IP", lambda: self.configure_tunnel_interface(
                params["tunnel_name"], params["tunnel_ip"],
                params["tunnel_subnet_mask"])),
            ("Configure firewall policy - inbound", lambda: self.configure_firewall_policy(
                1, params["tunnel_name"], "internal",
                "obj_remote_net", "obj_local_net")),
            ("Configure firewall policy - outbound", lambda: self.configure_firewall_policy(
                2, "internal", params["tunnel_name"],
                "obj_local_net", "obj_remote_net")),
            ("Configure static route", lambda: self.configure_static_route(
                params["remote_subnet"], params["tunnel_name"])),
        ]

        for step_name, step_func in steps:
            try:
                result = step_func()
                results["steps"].append({"step": step_name, "status": "success", "result": result})
                print(f"[OK] {step_name}")
            except Exception as e:
                results["steps"].append({"step": step_name, "status": "failed", "error": str(e)})
                results["errors"].append(f"{step_name}: {str(e)}")
                results["success"] = False
                print(f"[FAIL] {step_name}: {e}")

        return results


if __name__ == "__main__":
    # Example usage
    config = {
        "host": "192.168.1.99",
        "api_token": "YOUR_FORTIGATE_API_TOKEN",
        "wan_interface": "wan1",
        "tunnel_name": "VPN-to-PA",
        "tunnel_ip": "169.255.1.1",
        "tunnel_subnet_mask": "255.255.255.252",
        "local_subnet": "10.10.10.0 255.255.255.0",
        "remote_subnet": "10.20.20.0 255.255.255.0",
        "remote_peer": "200.2.2.2",
        "psk": "MySecurePSK!2024",
    }

    configurator = FortigateVPNConfigurator(
        host=config["host"],
        api_token=config["api_token"],
    )

    result = configurator.apply_full_config(config)
    print(f"\nConfiguration complete: {'Success' if result['success'] else 'Failed'}")
    if result["errors"]:
        print(f"Errors: {result['errors']}")
