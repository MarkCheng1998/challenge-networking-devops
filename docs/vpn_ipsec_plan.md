# IPSec VPN Automation Configuration Plan
## IPSec VPN Between Fortigate and Palo Alto

> This document details the complete planning for automating IPSec VPN configuration between Fortigate and Palo Alto firewalls.

---

## 1. Parameter Definitions

### 1.1 Network Topology

```
+-----------------+                        +-----------------+
|   Site A        |                        |   Site B        |
|  Fortigate      |     IPSec Tunnel       |  Palo Alto      |
|  10.10.10.0/24  |<----------------------->|  10.20.20.0/24  |
|  WAN: 200.1.1.1 |   169.255.1.0/30       |  WAN: 200.2.2.2 |
+-----------------+                        +-----------------+
```

### 1.2 WAN Interface Addresses

| Device | WAN IP | Role |
|--------|--------|------|
| Fortigate (Site A) | 200.1.1.1/30 | VPN tunnel endpoint A |
| Palo Alto (Site B) | 200.2.2.2/30 | VPN tunnel endpoint B |

### 1.3 Local Networks

| Site | Local Network | Description |
|------|---------------|-------------|
| Site A (Fortigate) | 10.10.10.0/24 | Data network |
| Site B (Palo Alto) | 10.20.20.0/24 | Data network |

### 1.4 Tunnel Network

| Parameter | Value |
|-----------|-------|
| Tunnel subnet | 169.255.1.0/30 |
| Fortigate tunnel IP | 169.255.1.1/30 |
| Palo Alto tunnel IP | 169.255.1.2/30 |

### 1.5 Phase 1 Parameters (IKE)

| Parameter | Value | Description |
|-----------|-------|-------------|
| IKE version | IKEv2 | Recommended |
| Encryption algorithm | AES-256-CBC | Strong encryption |
| Authentication algorithm | SHA-256 | Secure hash |
| DH group | Group 14 (2048-bit) | Secure Diffie-Hellman group |
| Authentication method | Pre-Shared Key (PSK) | Pre-shared key |
| PSK | `MySecurePSK!2024` | Example key (use a strong key in production) |
| Lifetime | 86400 seconds (24 hours) | Phase 1 SA lifetime |

### 1.6 Phase 2 Parameters (IPSec)

| Parameter | Value | Description |
|-----------|-------|-------------|
| Encryption algorithm | AES-256-CBC | ESP encryption |
| Authentication algorithm | SHA-256 | ESP authentication |
| DH group | Group 14 (2048-bit) | PFS (Perfect Forward Secrecy) |
| Lifetime | 3600 seconds (1 hour) | Phase 2 SA lifetime |
| Mode | Tunnel Mode | Tunnel mode |

---

## 2. Tool/API Identification

### 2.1 Fortigate Available Tools

| Tool/API | Description | Use Case |
|----------|-------------|----------|
| **FortiOS REST API** | Native REST API in FortiOS 7.0+, manages VPN config via HTTPS | Recommended: primary automation method |
| **FortiManager API** | Centralized management platform API | Large enterprise multi-device management |
| **SSH + CLI** | Execute CLI commands via SSH (Netmiko/Paramiko) | Legacy devices or API not supported |
| **Ansible** | Using `fortios` module collection | Infrastructure as Code |
| **Terraform** | FortiOS Provider | Infrastructure as Code |

**FortiOS REST API Example Endpoints:**
```
POST https://<fortigate-ip>/api/v2/cmdb/vpn.ipsec/phase1-interface
POST https://<fortigate-ip>/api/v2/cmdb/vpn.ipsec/phase2-interface
POST https://<fortigate-ip>/api/v2/cmdb/firewall/policy
```

### 2.2 Palo Alto Available Tools

| Tool/API | Description | Use Case |
|----------|-------------|----------|
| **Palo Alto XML API** | Native XML API, supports all configuration operations | Recommended: primary automation method |
| **Panorama API** | Centralized management platform API | Large-scale deployment |
| **SSH + CLI** | Execute CLI commands via SSH | Legacy devices |
| **Ansible** | Using `paloaltonetworks.panos` module collection | Infrastructure as Code |
| **Terraform** | PAN-OS Provider | Infrastructure as Code |

**Palo Alto XML API Example:**
```
https://<paloalto-ip>/api/?type=config&action=set&xpath=/config/devices/entry[@name='localhost.localdomain']/network/ike/gateway/entry[@name='VPN-GW']&element=<...>&key=<api-key>
```

### 2.3 Recommended Approach

**Hybrid approach using REST/XML API with SSH fallback:**

1. **Primary**: Configure via API (FortiOS REST API + Palo Alto XML API)
2. **Fallback**: Use SSH + CLI when API is unavailable
3. **Validation**: Use SSH to execute verification commands in both cases

Rationale:
- API is more stable and secure (no plaintext CLI commands)
- SSH offers better compatibility for legacy devices
- Hybrid approach ensures flexibility and reliability

---

## 3. Automation Steps

### 3.1 Prerequisites

```
+-----------------------------------+
| 1. Gather parameters (IP, PSK,    |
|    networks, etc.)                |
| 2. Verify device reachability     |
|    (ping/SSH)                      |
| 3. Obtain API Token / SSH creds   |
+----------------+------------------+
                 |
                 v
```

### 3.2 Fortigate Configuration Steps

```
+------------------------------------------+
| Step 1: Create Address Objects           |
|  - obj_local_net: 10.10.10.0/24          |
|  - obj_remote_net: 10.20.20.0/24         |
+------------------------------------------+
| Step 2: Configure Phase 1 (IKE Gateway)  |
|  - Interface: wan1                        |
|  - Peer IP: 200.2.2.2                    |
|  - IKE version: v2                       |
|  - Enc/Auth/DH: AES-256/SHA-256/G14     |
|  - PSK authentication                     |
+------------------------------------------+
| Step 3: Configure Phase 2 (IPSec Prop.)   |
|  - Enc/Auth: AES-256/SHA-256            |
|  - PFS: Group 14                         |
|  - Lifetime: 3600s                       |
|  - Source: 10.10.10.0/24                 |
|  - Destination: 10.20.20.0/24           |
+------------------------------------------+
| Step 4: Configure Firewall Policy        |
|  - Source: obj_local_net                 |
|  - Destination: obj_remote_net          |
|  - Action: ACCEPT                        |
|  - Outbound interface: VPN tunnel        |
+------------------------------------------+
| Step 5: Configure Tunnel Interface IP    |
|  - Interface: VPN-Tunnel                 |
|  - IP: 169.255.1.1/30                    |
+------------------------------------------+
| Step 6: Configure Static Route           |
|  - Destination: 10.20.20.0/24            |
|  - Next hop: VPN-Tunnel interface        |
+------------------------------------------+
```

### 3.3 Palo Alto Configuration Steps

```
+------------------------------------------+
| Step 1: Create Address Objects           |
|  - obj_local_net: 10.20.20.0/24          |
|  - obj_remote_net: 10.10.10.0/24         |
+------------------------------------------+
| Step 2: Configure IKE Crypto Profile     |
|  - Encryption: AES-256                   |
|  - Authentication: SHA-256               |
|  - DH: Group 14                          |
|  - Lifetime: 86400s                      |
+------------------------------------------+
| Step 3: Configure IKE Gateway            |
|  - Peer IP: 200.1.1.1                    |
|  - Authentication: PSK                   |
|  - IKE version: IKEv2                    |
|  - Local interface: ethernet1/1          |
+------------------------------------------+
| Step 4: Configure IPSec Crypto Profile    |
|  - Encryption: AES-256                   |
|  - Authentication: SHA-256               |
|  - DH: Group 14 (PFS)                   |
|  - Lifetime: 3600s                       |
+------------------------------------------+
| Step 5: Configure IPSec Tunnel           |
|  - IKE Gateway: VPN-GW                   |
|  - IPSec Crypto Profile: VPN-Crypto      |
|  - Tunnel interface: tunnel.1            |
+------------------------------------------+
| Step 6: Configure Tunnel Interface       |
|  - Interface: tunnel.1                   |
|  - IP: 169.255.1.2/30                    |
|  - Virtual Router: default               |
|  - Security Zone: VPN-Zone               |
+------------------------------------------+
| Step 7: Configure Static Route           |
|  - Destination: 10.10.10.0/24            |
|  - Next hop: tunnel.1                    |
+------------------------------------------+
| Step 8: Configure Security Policy        |
|  - Source Zone: VPN-Zone / Dest Zone: trust |
|  - Source address: obj_remote_net        |
|  - Destination address: obj_local_net    |
|  - Action: allow                         |
|  (Reverse policy similarly)              |
+------------------------------------------+
| Step 9: Commit Configuration             |
|  - Commit all changes to the device      |
+------------------------------------------+
```

### 3.4 Automation Script Flow

```
START
  |
  +--> Read configuration parameters (JSON/YAML)
  |
  +--> Fortigate Configuration Module
  |      +-- Login to obtain API Token
  |      +-- Create address objects
  |      +-- Configure Phase 1 (IKE Gateway)
  |      +-- Configure Phase 2 (IPSec Proposal)
  |      +-- Configure firewall policy
  |      +-- Configure tunnel interface IP
  |      +-- Configure static route
  |      +-- Validate configuration
  |
  +--> Palo Alto Configuration Module
  |      +-- Obtain API Key
  |      +-- Create address objects
  |      +-- Configure IKE Crypto Profile
  |      +-- Configure IKE Gateway
  |      +-- Configure IPSec Crypto Profile
  |      +-- Configure IPSec Tunnel
  |      +-- Configure tunnel interface
  |      +-- Configure static route
  |      +-- Configure security policy
  |      +-- Commit
  |      +-- Validate configuration
  |
  +--> Global Validation
  |      +-- Check tunnel status (both sides)
  |      +-- Test connectivity (ping)
  |      +-- Generate alert report
  |
END
```

---

## 4. Cross-Vendor Automation Considerations

### 4.1 Terminology Mapping

| Concept | Fortigate Term | Palo Alto Term |
|---------|---------------|----------------|
| IKE Phase 1 | Phase 1 Interface | IKE Gateway + IKE Crypto Profile |
| IKE Phase 2 | Phase 2 Interface | IPSec Tunnel + IPSec Crypto Profile |
| Firewall policy | Firewall Policy | Security Policy |
| Address object | Address | Address Object |
| Interface binding | Bound to VPN interface | Bound to Tunnel interface |
| Commit config | Takes effect immediately | Requires Commit operation |
| Interface type | VPN interface | Tunnel interface (tunnel.X) |

### 4.2 Key Challenges

1. **Configuration Commit Mechanism Differences**:
   - Fortigate: API calls take effect immediately, no additional commit needed
   - Palo Alto: Requires `commit` operation to apply configuration
   - Solution: Add a commit step at the end of the Palo Alto automation workflow

2. **API Format Differences**:
   - Fortigate: REST API, JSON format
   - Palo Alto: XML API, XML format
   - Solution: Implement separate API client modules for each vendor

3. **Tunnel Interface Numbering Differences**:
   - Fortigate: Uses named interfaces (e.g., "VPN-Tunnel")
   - Palo Alto: Uses numbered tunnel interfaces (e.g., tunnel.1)
   - Solution: Parameterize interface naming in configuration templates

4. **Phase 1/Phase 2 Configuration Granularity Differences**:
   - Fortigate: Phase 1 and Phase 2 are associated in a single interface configuration
   - Palo Alto: Requires separate Crypto Profile, Gateway, and Tunnel objects
   - Solution: Handle configuration order separately per vendor in automation scripts

5. **IKE Proposal Order**:
   - Different vendors may have different IKE proposal matching orders
   - Must ensure both sides have identical encryption parameters
   - Solution: Use standardized parameter configuration templates, avoid defaults

6. **NAT Traversal**:
   - Both sides must enable NAT-T
   - Fortigate: Enabled by default
   - Palo Alto: Must be enabled in IKE Gateway
   - Solution: Explicitly configure NAT-T

### 4.3 Security Considerations

- PSK should not be hardcoded in scripts; read from environment variables or a secret management service
- API Token/Key should be rotated periodically
- SSH connections should use key-based authentication instead of passwords
- All automation operations should be recorded in audit logs
- Back up current configuration automatically before any configuration changes

---

## 5. Configuration Validation and Alert Strategy

### 5.1 Validation Methods

#### Fortigate Validation Commands

```bash
# Check IKE Phase 1 status
diagnose vpn ike gateway list

# Check IPSec Phase 2 status
diagnose vpn tunnel list

# Check tunnel interface
diagnose vpn tunnel stats

# Check routes
diagnose ip route list

# Ping test
execute ping 169.255.1.2
execute ping source 10.10.10.1 10.20.20.1
```

#### Palo Alto Validation Commands

```bash
# Check IKE Phase 1 status
show vpn ike-sa

# Check IPSec Phase 2 status
show vpn ipsec-sa

# Check tunnel interface
show interface tunnel.1

# Check routes
show routing route

# Ping test
ping source 10.20.20.1 host 10.10.10.1
```

### 5.2 API Validation

#### Fortigate REST API Validation
```http
GET https://<fortigate-ip>/api/v2/monitor/vpn/ipsec
GET https://<fortigate-ip>/api/v2/monitor/vpn/ssl
```

#### Palo Alto XML API Validation
```http
https://<paloalto-ip>/api/?type=op&cmd=<show><vpn><ike-sa></ike-sa></vpn></show>&key=<api-key>
https://<paloalto-ip>/api/?type=op&cmd=<show><vpn><ipsec-sa></ipsec-sa></vpn></show>&key=<api-key>
```

### 5.3 Validation Checklist

| Check Item | Method | Expected Result | Alert Level |
|------------|--------|-----------------|-------------|
| Phase 1 SA established | API/CLI query | Status: established/up | Critical |
| Phase 2 SA established | API/CLI query | Status: up | Critical |
| Tunnel interface UP | CLI query | Interface status: up | Critical |
| Tunnel IP connectivity | Ping tunnel IP | 100% success rate | Critical |
| Local network connectivity | Ping remote local IP | 100% success rate | Critical |
| Route table correct | CLI route query | Target network reachable via tunnel | Warning |
| Firewall policy correct | API/CLI query | Bidirectional traffic allowed | Warning |
| Config parameters match | Compare both sides | Phase 1/2 parameters identical | Critical |
| No extra configuration | Compare to expected | No non-standard config | Info |

### 5.4 Alert Mechanism

```
Validation Flow:
+--------------+     +------------------+     +---------------+
| Execute      |---->| Compare to        |---->| Generate      |
| validation   |     | expected state   |     | alert report  |
| (API/CLI)    |     | (param/status)   |     | (graded)      |
+--------------+     +------------------+     +-------+-------+
                                                       |
                                     +-----------------+-----------------+
                                     |                 |                 |
                                     v                 v                 v
                               +----------+    +----------+    +----------+
                               | Critical |    | Warning  |    | Info     |
                               | (email + |    | (email   |    | (log     |
                               |  log)    |    |  notify) |    |  only)   |
                               +----------+    +----------+    +----------+
```

**Alert Level Definitions:**

- **Critical**: VPN tunnel cannot be established, Phase 1/2 SA failed, connectivity test failed
  - Trigger: Send alert email + write error log + script exit code 1
- **Warning**: Missing routes, incomplete policy, minor parameter discrepancies
  - Trigger: Send notification email + write warning log
- **Info**: Non-standard configuration found, extra objects present
  - Trigger: Write info log only

### 5.5 Rollback Strategy

If validation fails after automated configuration:

1. **Automatic Rollback**: Script restores configuration from backup
2. **Manual Rollback**: Send alert email with manual rollback steps
3. **Backup Retention**: Automatically back up current configuration before each change

---

## 6. Appendix

### 6.1 Configuration Parameter Template (JSON)

```json
{
  "fortigate": {
    "host": "200.1.1.1",
    "api_token": "<fortigate-api-token>",
    "wan_interface": "wan1",
    "tunnel_name": "VPN-to-PA",
    "tunnel_ip": "169.255.1.1",
    "tunnel_subnet": "255.255.255.252",
    "local_subnet": "10.10.10.0/24",
    "remote_subnet": "10.20.20.0/24",
    "remote_peer": "200.2.2.2",
    "psk": "MySecurePSK!2024",
    "phase1": {
      "ike_version": 2,
      "encryption": "aes256",
      "authentication": "sha256",
      "dh_group": 14,
      "lifetime": 86400
    },
    "phase2": {
      "encryption": "aes256",
      "authentication": "sha256",
      "dh_group": 14,
      "lifetime": 3600
    }
  },
  "paloalto": {
    "host": "200.2.2.2",
    "api_key": "<paloalto-api-key>",
    "wan_interface": "ethernet1/1",
    "tunnel_interface": "tunnel.1",
    "tunnel_ip": "169.255.1.2",
    "tunnel_subnet": "255.255.255.252",
    "local_subnet": "10.20.20.0/24",
    "remote_subnet": "10.10.10.0/24",
    "remote_peer": "200.1.1.1",
    "psk": "MySecurePSK!2024",
    "ike_crypto_profile": "VPN-IKE-Crypto",
    "ike_gateway": "VPN-GW",
    "ipsec_crypto_profile": "VPN-IPSec-Crypto",
    "ipsec_tunnel": "VPN-Tunnel",
    "vpn_zone": "VPN-Zone",
    "phase1": {
      "ike_version": "ikev2",
      "encryption": "aes-256-cbc",
      "authentication": "sha256",
      "dh_group": "group14",
      "lifetime": 86400
    },
    "phase2": {
      "encryption": "aes-256-cbc",
      "authentication": "sha256",
      "dh_group": "group14",
      "lifetime": 3600
    }
  }
}
```

### 6.2 Example CLI Configuration Commands

#### Fortigate CLI Configuration

```
# Address objects
config firewall address
    edit "obj_local_net"
        set subnet 10.10.10.0 255.255.255.0
    next
    edit "obj_remote_net"
        set subnet 10.20.20.0 255.255.255.0
    next
end

# Phase 1
config vpn ipsec phase1-interface
    edit "VPN-to-PA"
        set interface "wan1"
        set ike-version 2
        set peertype any
        set proposal aes256-sha256-dh14
        set remote-gw 200.2.2.2
        set psksecret MySecurePSK!2024
    next
end

# Phase 2
config vpn ipsec phase2-interface
    edit "VPN-to-PA-P2"
        set phase1name "VPN-to-PA"
        set proposal aes256-sha256
        set dhgrp 14
        set src-subnet 10.10.10.0 255.255.255.0
        set dst-subnet 10.20.20.0 255.255.255.0
    next
end

# Tunnel interface IP
config system interface
    edit "VPN-to-PA"
        set ip 169.255.1.1 255.255.255.252
    next
end

# Firewall policy
config firewall policy
    edit 1
        set srcintf "VPN-to-PA"
        set dstintf "internal"
        set srcaddr "obj_remote_net"
        set dstaddr "obj_local_net"
        set action accept
        set schedule "always"
        set service "ALL"
    next
    edit 2
        set srcintf "internal"
        set dstintf "VPN-to-PA"
        set srcaddr "obj_local_net"
        set dstaddr "obj_remote_net"
        set action accept
        set schedule "always"
        set service "ALL"
    next
end

# Static route
config router static
    edit 1
        set dst 10.20.20.0 255.255.255.0
        set device "VPN-to-PA"
    next
end
```

#### Palo Alto CLI Configuration

```
# Address objects
set network address obj_local_net ip-netmask 10.20.20.0/24
set network address obj_remote_net ip-netmask 10.10.10.0/24

# IKE Crypto Profile
set network ike crypto-profiles ike-crypto-profiles VPN-IKE-Crypto encryption aes-256-cbc
set network ike crypto-profiles ike-crypto-profiles VPN-IKE-Crypto authentication sha256
set network ike crypto-profiles ike-crypto-profiles VPN-IKE-Crypto dh-group group14
set network ike crypto-profiles ike-crypto-profiles VPN-IKE-Crypto lifetime hours 24

# IKE Gateway
set network ike gateway VPN-GW authentication pre-shared-key key MySecurePSK!2024
set network ike gateway VPN-GW protocol ikev2 ike-crypto-profile VPN-IKE-Crypto
set network ike gateway VPN-GW protocol ikev2 dpd enable
set network ike gateway VPN-GW peer-address ip 200.1.1.1
set network ike gateway VPN-GW local-address interface ethernet1/1

# IPSec Crypto Profile
set network ipsec-crypto-profiles ipsec-crypto-profiles VPN-IPSec-Crypto esp encryption aes-256-cbc
set network ipsec-crypto-profiles ipsec-crypto-profiles VPN-IPSec-Crypto esp authentication sha256
set network ipsec-crypto-profiles ipsec-crypto-profiles VPN-IPSec-Crypto dh-group group14
set network ipsec-crypto-profiles ipsec-crypto-profiles VPN-IPSec-Crypto lifetime hours 1

# IPSec Tunnel
set network tunnel ipsec VPN-Tunnel auto-key ike-gateway VPN-GW
set network tunnel ipsec VPN-Tunnel auto-key ipsec-crypto-profile VPN-IPSec-Crypto
set network tunnel ipsec VPN-Tunnel tunnel-interface tunnel.1

# Tunnel interface
set network interface tunnel tunnel.1 ip 169.255.1.2/30
set network interface tunnel tunnel.1 virtual-router default

# Security zone
set zone VPN-Zone network layer3 tunnel.1

# Static route
set network virtual-router default routing-table ip static-route 10.10.10.0/24 destination 10.10.10.0/24
set network virtual-router default routing-table ip static-route 10.10.10.0/24 interface tunnel.1

# Security policy
set rulebase security rules Allow-VPN-Inbound from VPN-Zone to trust source obj_remote_net destination obj_local_net action allow
set rulebase security rules Allow-VPN-Outbound from trust to VPN-Zone source obj_local_net destination obj_remote_net action allow

# Commit configuration
commit
```
