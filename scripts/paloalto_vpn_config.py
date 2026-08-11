"""
Palo Alto IPSec VPN Configuration Script
=========================================
Configures an IPSec VPN tunnel via the Palo Alto XML API.

Before use, obtain an API Key on the Palo Alto:
  curl -k "https://<paloalto-ip>/api/?type=keygen&user=<user>&password=<password>"

Dependencies: pip install requests
"""

import requests
import urllib3
from xml.etree import ElementTree
from typing import Dict, Any, Optional

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class PaloAltoVPNConfigurator:
    """Palo Alto IPSec VPN configurator using the XML API."""

    def __init__(self, host: str, api_key: str, verify_ssl: bool = False):
        """
        Args:
            host: Palo Alto management IP
            api_key: Palo Alto API Key
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = f"https://{host}/api/"
        self.api_key = api_key
        self.verify_ssl = verify_ssl

    def _api_request(self, params: Dict[str, str]) -> ElementTree.Element:
        """Send an XML API request."""
        params["key"] = self.api_key
        response = requests.get(self.base_url, params=params, verify=self.verify_ssl)
        root = ElementTree.fromstring(response.content)
        if root.attrib.get("status") != "success":
            raise Exception(f"API request failed: {ElementTree.tostring(root, encoding='unicode')}")
        return root

    @staticmethod
    def get_api_key(host: str, username: str, password: str, verify_ssl: bool = False) -> str:
        """Obtain an API Key using username and password."""
        response = requests.get(
            f"https://{host}/api/",
            params={"type": "keygen", "user": username, "password": password},
            verify=verify_ssl,
        )
        root = ElementTree.fromstring(response.content)
        return root.find(".//key").text

    def set_config(self, xpath: str, element: str) -> ElementTree.Element:
        """Set a configuration item."""
        return self._api_request({
            "type": "config",
            "action": "set",
            "xpath": xpath,
            "element": element,
        })

    def create_address_object(self, name: str, ip_netmask: str) -> ElementTree.Element:
        """Create an address object."""
        xpath = f"/config/devices/entry[@name='localhost.localdomain']/network/address/entry[@name='{name}']"
        element = f"<ip-netmask>{ip_netmask}</ip-netmask>"
        return self.set_config(xpath, element)

    def configure_ike_crypto_profile(self, name: str, encryption: str,
                                      authentication: str, dh_group: str,
                                      lifetime_hours: int) -> ElementTree.Element:
        """Configure an IKE Crypto Profile."""
        xpath = f"/config/devices/entry[@name='localhost.localdomain']/network/ike/crypto-profiles/ike-crypto-profiles/entry[@name='{name}']"
        element = f"""<encryption><member>{encryption}</member></encryption>
<hash><member>{authentication}</member></hash>
<dh-group><member>{dh_group}</member></dh-group>
<lifetime><hours>{lifetime_hours}</hours></lifetime>"""
        return self.set_config(xpath, element)

    def configure_ike_gateway(self, name: str, peer_ip: str, local_interface: str,
                               psk: str, ike_crypto_profile: str,
                               ike_version: str = "ikev2") -> ElementTree.Element:
        """Configure an IKE Gateway."""
        xpath = f"/config/devices/entry[@name='localhost.localdomain']/network/ike/gateway/entry[@name='{name}']"
        element = f"""<authentication><pre-shared-key><key>{psk}</key></pre-shared-key></authentication>
<protocol><{ike_version}><ike-crypto-profile>{ike_crypto_profile}</ike-crypto-profile><dpd><enable>yes</enable></dpd></{ike_version}></protocol>
<peer-address><ip>{peer_ip}</ip></peer-address>
<local-address><interface>{local_interface}</interface></local-address>"""
        return self.set_config(xpath, element)

    def configure_ipsec_crypto_profile(self, name: str, encryption: str,
                                        authentication: str, dh_group: str,
                                        lifetime_hours: int) -> ElementTree.Element:
        """Configure an IPSec Crypto Profile."""
        xpath = f"/config/devices/entry[@name='localhost.localdomain']/network/ipsec-crypto-profiles/ipsec-crypto-profiles/entry[@name='{name}']"
        element = f"""<esp><encryption><member>{encryption}</member></encryption><authentication><member>{authentication}</member></authentication></esp>
<dh-group>{dh_group}</dh-group>
<lifetime><hours>{lifetime_hours}</hours></lifetime>"""
        return self.set_config(xpath, element)

    def configure_ipsec_tunnel(self, name: str, ike_gateway: str,
                                ipsec_crypto_profile: str,
                                tunnel_interface: str) -> ElementTree.Element:
        """Configure an IPSec Tunnel."""
        xpath = f"/config/devices/entry[@name='localhost.localdomain']/network/tunnel/ipsec/entry[@name='{name}']"
        element = f"""<auto-key><ike-gateway>{ike_gateway}</ike-gateway><ipsec-crypto-profile>{ipsec_crypto_profile}</ipsec-crypto-profile></auto-key>
<tunnel-interface>{tunnel_interface}</tunnel-interface>"""
        return self.set_config(xpath, element)

    def configure_tunnel_interface(self, interface: str, ip: str) -> ElementTree.Element:
        """Configure the tunnel interface IP."""
        xpath = f"/config/devices/entry[@name='localhost.localdomain']/network/interface/tunnel/entry[@name='{interface}']"
        element = f"<ip>{ip}</ip>"
        return self.set_config(xpath, element)

    def configure_security_zone(self, zone_name: str, tunnel_interface: str) -> ElementTree.Element:
        """Configure a security zone."""
        xpath = f"/config/devices/entry[@name='localhost.localdomain']/zone/entry[@name='{zone_name}']"
        element = f"<network><layer3><member>{tunnel_interface}</member></layer3></network>"
        return self.set_config(xpath, element)

    def configure_static_route(self, dst_network: str, tunnel_interface: str) -> ElementTree.Element:
        """Configure a static route."""
        xpath = f"/config/devices/entry[@name='localhost.localdomain']/network/virtual-router/entry[@name='default']/routing-table/ip/static-route/entry[@name='route-{dst_network}']"
        element = f"""<destination>{dst_network}</destination>
<interface>{tunnel_interface}</interface>"""
        return self.set_config(xpath, element)

    def configure_security_policy(self, rule_name: str, from_zone: str, to_zone: str,
                                   src_addr: str, dst_addr: str) -> ElementTree.Element:
        """Configure a security policy."""
        xpath = f"/config/devices/entry[@name='localhost.localdomain']/rulebase/security/rules/entry[@name='{rule_name}']"
        element = f"""<from><member>{from_zone}</member></from>
<to><member>{to_zone}</member></to>
<source><member>{src_addr}</member></source>
<destination><member>{dst_addr}</member></destination>
<action>allow</action>"""
        return self.set_config(xpath, element)

    def commit(self) -> ElementTree.Element:
        """Commit all configuration changes."""
        return self._api_request({"type": "commit", "cmd": "<commit></commit>"})

    def get_ike_sa_status(self) -> ElementTree.Element:
        """Get IKE SA status."""
        return self._api_request({"type": "op", "cmd": "<show><vpn><ike-sa></ike-sa></vpn></show>"})

    def get_ipsec_sa_status(self) -> ElementTree.Element:
        """Get IPSec SA status."""
        return self._api_request({"type": "op", "cmd": "<show><vpn><ipsec-sa></ipsec-sa></vpn></show>"})

    def apply_full_config(self, params: Dict) -> Dict:
        """Execute the full VPN configuration workflow."""
        results = {"steps": [], "success": True, "errors": []}

        steps = [
            ("Create address object - local network", lambda: self.create_address_object(
                "obj_local_net", params["local_subnet"])),
            ("Create address object - remote network", lambda: self.create_address_object(
                "obj_remote_net", params["remote_subnet"])),
            ("Configure IKE Crypto Profile", lambda: self.configure_ike_crypto_profile(
                params["ike_crypto_profile"], "aes-256-cbc", "sha256", "group14", 24)),
            ("Configure IKE Gateway", lambda: self.configure_ike_gateway(
                params["ike_gateway"], params["remote_peer"],
                params["wan_interface"], params["psk"],
                params["ike_crypto_profile"])),
            ("Configure IPSec Crypto Profile", lambda: self.configure_ipsec_crypto_profile(
                params["ipsec_crypto_profile"], "aes-256-cbc", "sha256", "group14", 1)),
            ("Configure IPSec Tunnel", lambda: self.configure_ipsec_tunnel(
                params["ipsec_tunnel"], params["ike_gateway"],
                params["ipsec_crypto_profile"], params["tunnel_interface"])),
            ("Configure tunnel interface", lambda: self.configure_tunnel_interface(
                params["tunnel_interface"], params["tunnel_ip"])),
            ("Configure security zone", lambda: self.configure_security_zone(
                params["vpn_zone"], params["tunnel_interface"])),
            ("Configure static route", lambda: self.configure_static_route(
                params["remote_subnet"], params["tunnel_interface"])),
            ("Configure security policy - inbound", lambda: self.configure_security_policy(
                "Allow-VPN-Inbound", params["vpn_zone"], "trust",
                "obj_remote_net", "obj_local_net")),
            ("Configure security policy - outbound", lambda: self.configure_security_policy(
                "Allow-VPN-Outbound", "trust", params["vpn_zone"],
                "obj_local_net", "obj_remote_net")),
            ("Commit configuration", lambda: self.commit()),
        ]

        for step_name, step_func in steps:
            try:
                result = step_func()
                results["steps"].append({"step": step_name, "status": "success"})
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
        "host": "192.168.1.100",
        "api_key": "YOUR_PALO_ALTO_API_KEY",
        "wan_interface": "ethernet1/1",
        "tunnel_interface": "tunnel.1",
        "tunnel_ip": "169.255.1.2/30",
        "local_subnet": "10.20.20.0/24",
        "remote_subnet": "10.10.10.0/24",
        "remote_peer": "200.1.1.1",
        "psk": "MySecurePSK!2024",
        "ike_crypto_profile": "VPN-IKE-Crypto",
        "ike_gateway": "VPN-GW",
        "ipsec_crypto_profile": "VPN-IPSec-Crypto",
        "ipsec_tunnel": "VPN-Tunnel",
        "vpn_zone": "VPN-Zone",
    }

    configurator = PaloAltoVPNConfigurator(
        host=config["host"],
        api_key=config["api_key"],
    )

    result = configurator.apply_full_config(config)
    print(f"\nConfiguration complete: {'Success' if result['success'] else 'Failed'}")
    if result["errors"]:
        print(f"Errors: {result['errors']}")
