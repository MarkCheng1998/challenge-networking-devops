# GNS3 Deployment Guide

> Step-by-step guide to deploying the Cisco Switch VLAN Automation project using GNS3

This guide covers everything from GNS3 installation to running the Flask web application against a virtualized Cisco switch.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [GNS3 Installation (Windows)](#2-gns3-installation-windows)
3. [Importing the Cisco IOS Image](#3-importing-the-cisco-ios-image)
4. [Network Topology Design](#4-network-topology-design)
5. [Configuring Host-to-GNS3 Connectivity](#5-configuring-host-to-gns3-connectivity)
6. [Switch Initial Configuration](#6-switch-initial-configuration)
7. [Running the Flask Application](#7-running-the-flask-application)
8. [Step-by-Step Demo Walkthrough](#8-step-by-step-demo-walkthrough)
9. [Troubleshooting](#9-troubleshooting)
10. [GNS3 Topology Export/Import](#10-gns3-topology-exportimport)

---

## 1. Prerequisites

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 8 GB | 16 GB+ |
| Disk Space | 5 GB free | 20 GB free |
| CPU | 4 cores | 8 cores (VT-x/AMD-V enabled) |
| OS | Windows 10/11 64-bit | Windows 11 64-bit |

### Software Requirements

| Software | Version | Purpose |
|----------|---------|---------|
| GNS3 | 2.2.x (GUI + VM) | Network simulation |
| Wireshark | 4.x (optional) | Packet capture |
| Python | 3.9+ | Run Flask + Netmiko |
| Cisco IOS Image | See Section 3 | Switch emulation |

### Cisco IOS Image Options

| Image | Platform | L2 Support | Recommendation |
|-------|----------|------------|----------------|
| `viosl2-adventerprisek9-m.SPA` | vIOS-L2 | Full L2 switching | **Best choice** |
| `c3725-adventerprisek9-mz.124-15.T14` | c3725 | Basic switching | Widely available |
| `c3640-jo3s-mz.124-25d` | c3640 | NM-16ESW module | Fallback option |

> **Note**: The vIOS-L2 image provides the most realistic Layer 2 switch behavior. The c3725 with an NM-16ESW module is a common alternative if vIOS-L2 is not available.

---

## 2. GNS3 Installation (Windows)

### Step 2.1: Download GNS3

1. Go to **https://gns3.com/software/download**
2. Download the **GNS3-2.2.x.exe** all-in-one installer for Windows
3. Run the installer as Administrator

### Step 2.2: Install Components

During installation, select the following components:

| Component | Install? | Reason |
|-----------|----------|--------|
| GNS3 GUI | ✅ Yes | Main interface |
| Wireshark | ✅ Yes (if not installed) | Packet capture |
| SolarWinds Response Time Viewer | ❌ Optional | Not needed |
| Dynamips | ✅ Yes | Cisco IOS emulation |
| QEMU | ✅ Yes | Required for vIOS images |
| GNS3 VM | ❌ Not needed for single switch | Optional for heavy topologies |
| VPCS | ✅ Yes | Virtual PC simulator for testing |

### Step 2.3: First Run Setup

1. Launch **GNS3**
2. When prompted "Server type selection":
   - Select **"Run appliances on my local computer"** (not the GNS3 VM)
3. Click **Next** → the local server will start automatically
4. Verify the local server status indicator (bottom-right corner) shows **Green**

### Step 2.4: Verify Installation

```
GNS3 GUI → Help → About
```

Confirm:
- GNS3 Version: 2.2.x
- Dynamips: Installed
- QEMU: Installed
- Local server: Running (127.0.0.1:3080)

---

## 3. Importing the Cisco IOS Image

### Option A: vIOS-L2 (Recommended)

1. **Obtain the image file**: `viosl2-adventerprisek9-m.SPA.high_iron_20200929.qcow2`
   - This is a QEMU-based image (`.qcow2` format)

2. **Import the appliance template**:
   - Download `viosl2.gns3a` from the GNS3 appliances page: https://gns3.com/appliances
   - In GNS3 GUI: **File → Import Appliance** → select `viosl2.gns3a`
   - Follow the wizard, when prompted for the QEMU image, browse to your `.qcow2` file
   - Click **Import**

3. **Verify the appliance**:
   - **Edit → Preferences → QEMU VMs** → you should see "vIOS-L2"
   - Click it → verify the QEMU binary path is correct

### Option B: c3725 (Dynamips)

1. **Obtain the image file**: `c3725-adventerprisek9-mz.124-15.T14.bin`
   - This is a Dynamips image (`.bin` format)

2. **Add the IOS image**:
   - In GNS3 GUI: **Edit → Preferences → IOS Routers → New**
   - Browse to your `.bin` file
   - Platform: **c3725**
   - Image: auto-detected

3. **Configure memory and modules**:
   - RAM: **512 MB**
   - Under the **Slots** tab:
     - Slot 1: **NM-16ESW** (16-port switching module)
   - Under the **Idle-PC** tab:
     - Click **Idle-PC finder** (with the router running)
     - Select a value with `*` (asterisk = recommended)

4. **Save and verify**:
   - The router template should now appear in the left sidebar under "Cisco Routers"

---

## 4. Network Topology Design

### Topology Overview

```
┌─────────────────────────────────────────────────────┐
│                    Host PC (Windows)                 │
│                                                       │
│  ┌──────────┐         ┌──────────────────────────┐  │
│  │  Flask   │         │  Loopback Adapter          │  │
│  │  App     │         │  192.168.122.1/24          │  │
│  │ (Netmiko)│         │                            │  │
│  └────┬─────┘         └──────────┬──────────────────┘  │
│       │ SSH port 22              │ Bridge                │
│       │                          │                        │
└───────┼──────────────────────────┼──────────────────────┘
        │                          │
   ┌────┴──────────────────────────┴────┐
   │          GNS3 Cloud Node             │
   │    (bridges to Loopback adapter)     │
   └────────────────┬────────────────────┘
                    │
           ┌────────┴────────┐
           │   GNS3 Switch     │
           │   (vIOS-L2 / c3725)│
           │   Mgmt IP:         │
           │   192.168.122.10   │
           │   VLAN 1 (default) │
           └───────────────────┘
                    │
           ┌────────┴────────┐
           │   VPCS Hosts     │
           │   PC1 (VLAN 10)   │
           │   PC2 (VLAN 20)   │
           │   PC3 (VLAN 50)   │
           └──────────────────┘
```

### Step 4.1: Create the Topology

1. **Create a new project**:
   - GNS3 GUI → **File → New Project** → name it `challenge-switch-lab`

2. **Add the switch**:
   - Drag the **vIOS-L2** (or **c3725**) appliance from the left sidebar to the workspace

3. **Add VPCS hosts** (optional, for VLAN testing):
   - Drag **3x VPCS** from the "End devices" section

4. **Add the Cloud node**:
   - Drag **Cloud** from the "Switches" section (or "End devices" depending on version)
   - This bridges the GNS3 network to your host PC

5. **Connect the devices**:
   - **Cloud → Switch**: Ethernet0/0
   - **Switch → PC1**: Ethernet0/1 (will be assigned to VLAN 10)
   - **Switch → PC2**: Ethernet0/2 (will be assigned to VLAN 20)
   - **Switch → PC3**: Ethernet0/3 (will be assigned to VLAN 50)

6. **Start all devices**:
   - Click the **green Play button** in the toolbar

---

## 5. Configuring Host-to-GNS3 Connectivity

### Step 5.1: Install Microsoft Loopback Adapter (if not already installed)

1. Open **Device Manager** (Win+X → Device Manager)
2. Click **Action → Add legacy hardware**
3. Select **"Install the hardware that I manually select from a list"**
4. Select **Network adapters → Microsoft → Microsoft KM-TEST Loopback Adapter**
5. Click **Next** → **Finish**

### Step 5.2: Configure the Loopback Adapter IP

1. Open **Network Connections** (ncpa.cpl)
2. Find the new **"Microsoft KM-TEST Loopback Adapter"** (rename to `GNS3-Bridge` for clarity)
3. Right-click → **Properties → IPv4 → Properties**
4. Set:
   - IP address: `192.168.122.1`
   - Subnet mask: `255.255.255.0`
   - Leave gateway and DNS blank

### Step 5.3: Configure the GNS3 Cloud Node

1. Double-click the **Cloud node** in GNS3
2. Go to the **Ethernet interfaces** tab
3. From the dropdown, select **`GNS3-Bridge`** (the loopback adapter you just configured)
4. Click **Add** → **OK**

> **Alternative method**: Use the **NAT node** in GNS3 instead of Cloud+Loopback. This provides DHCP and NAT automatically, but the IP may change between runs.

### Step 5.4: Verify Connectivity

After starting the switch and configuring its management IP (next section):

```bash
# From host PC, verify reachability
ping 192.168.122.10
```

---

## 6. Switch Initial Configuration

### Step 6.1: Access the Switch Console

1. In GNS3, **double-click the switch** to open the console
2. Wait for IOS to boot (may take 30-60 seconds for first boot)
3. You should see the `Switch>` prompt

### Step 6.2: Apply Base Configuration

Copy and paste the following into the switch console:

```ios
! Enter privileged mode
enable
configure terminal

! Set hostname
hostname SW1

! Create admin user with privilege 15
username admin privilege 15 secret admin

! Set enable secret
enable secret admin

! Configure management interface (VLAN 1)
interface Vlan 1
 ip address 192.168.122.10 255.255.255.0
 no shutdown
exit

! Configure default gateway (if needed)
ip default-gateway 192.168.122.1

! Enable SSH
ip domain-name challenge.local
crypto key generate rsa modulus 2048
! When prompted for key size, enter 2048

! Configure SSH parameters
ip ssh version 2
ip ssh time-out 60
ip ssh authentication-retries 3

! Configure VTY lines for SSH
line vty 0 4
 transport input ssh
 login local
exit
line vty 5 15
 transport input ssh
 login local
exit

! Configure console
line con 0
 logging synchronous
exit

! Disable DNS lookup
no ip domain-lookup

! Save configuration
end
write memory
```

### Step 6.3: Verify SSH Access

```bash
# From the host PC terminal
ssh admin@192.168.122.10
# Password: admin
```

If the SSH prompt appears, the switch is ready for automation.

### Step 6.4: (Alternative) Use the Automated Init Script

Instead of manual configuration, you can use the provided script:

```bash
cd challenge-networking-devops
python scripts/gns3_switch_init.py --apply
```

This script generates the initial configuration and can optionally push it via Telnet (for first-time setup where SSH isn't configured yet).

---

## 7. Running the Flask Application

### Step 7.1: Install Python Dependencies

```bash
cd challenge-networking-devops

# Create virtual environment (if not already done)
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate    # Linux/Mac

pip install -r requirements.txt
```

### Step 7.2: Start the Flask App

```bash
python app.py
```

You should see:
```
 * Running on http://0.0.0.0:5000
```

### Step 7.3: Access the Web Interface

Open your browser: **http://localhost:5000**

### Step 7.4: Configure for GNS3 Switch

In the web interface, enter:

| Field | Value | Notes |
|-------|-------|-------|
| Switch IP | `192.168.122.10` | The GNS3 switch management IP |
| Username | `admin` | Created in Step 6.2 |
| Password | `admin` | Created in Step 6.2 |
| SSH Port | `22` | Default SSH port |
| Enable Password | `admin` | Same as password |
| Hostname | `SWITCH_AUTOMATIZADO` | Default challenge hostname |
| VLANs | 10/VLAN_DATOS, 20/VLAN_VOZ, 50/VLAN_SEGURIDAD | Pre-populated |
| Simulation Mode | ❌ **Unchecked** | We are using a real GNS3 switch |

### Step 7.5: Execute Configuration

Click **"Execute Automated Configuration"**

The script will:
1. Connect to the GNS3 switch via SSH (Netmiko)
2. Create VLAN 10/20/50 with names
3. Change hostname to SWITCH_AUTOMATIZADO
4. Save config to NVRAM (`write memory`)
5. Backup running-config to `backups/` directory
6. Validate the configuration

---

## 8. Step-by-Step Demo Walkthrough

### Phase 1: Pre-Demo Setup (30 min before demo)

1. Start GNS3 → Open the `challenge-switch-lab` project
2. Click **Start all devices** (green Play button)
3. Wait 60 seconds for the switch to boot
4. Verify connectivity: `ping 192.168.122.10` from host
5. Verify SSH: `ssh admin@192.168.122.10` → `exit`
6. Start Flask app: `python app.py`
7. Open browser: http://localhost:5000

### Phase 2: Demo Execution

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Show the GNS3 topology running | Switch is up, VPCS connected |
| 2 | Open switch console: `show vlan brief` | Only default VLANs (1, 1002-1005) visible |
| 3 | Open browser: http://localhost:5000 | Web UI loads with pre-populated VLANs |
| 4 | Enter switch IP: 192.168.122.10, admin/admin | Connection info filled |
| 5 | Uncheck "Simulation Mode" | Real device mode active |
| 6 | Click "Execute Automated Configuration" | Steps execute sequentially |
| 7 | Show result panel: VLANs created, hostname changed | All steps show ✅ |
| 8 | Open switch console: `show vlan brief` | VLAN 10/20/50 visible with names |
| 9 | Switch console: `show running-config \| include hostname` | Shows `hostname SWITCH_AUTOMATIZADO` |
| 10 | Show backup file in `backups/` directory | `.cfg` file with timestamp |
| 11 | Click "Validate Configuration Only" | Validation table shows all matches |

### Phase 3: Demo VLAN Assignment (Optional)

Assign switch ports to VLANs and test connectivity between VPCS hosts:

```ios
! On the switch console
configure terminal
interface range Ethernet0/1-2
 switchport mode access
 switchport access vlan 10
exit
interface Ethernet0/3
 switchport mode access
 switchport access vlan 20
exit
end
write memory
```

Then on VPCS hosts:
```bash
# PC1 (Ethernet0/1) - VLAN 10
ip 192.168.10.1 255.255.255.0 192.168.10.254

# PC2 (Ethernet0/2) - VLAN 10 (same VLAN, should ping)
ip 192.168.10.2 255.255.255.0 192.168.10.254

# PC3 (Ethernet0/3) - VLAN 20 (different VLAN, should NOT ping)
ip 192.168.20.1 255.255.255.0 192.168.20.254
```

Test:
- `ping 192.168.10.2` from PC1 → **Success** (same VLAN)
- `ping 192.168.20.1` from PC1 → **Fail** (different VLAN, no routing)

---

## 9. Troubleshooting

### Problem: Cannot reach the switch IP from host

| Check | Solution |
|-------|----------|
| Loopback adapter IP configured | Set to 192.168.122.1/24 |
| Cloud node bound to correct adapter | Re-check Cloud node config |
| Switch management interface up | `show ip interface brief` on switch |
| Windows Firewall blocking | Add inbound rule for port 22 from 192.168.122.0/24 |

### Problem: SSH connection refused

| Check | Solution |
|-------|----------|
| SSH enabled on switch | `show ip ssh` should show "SSH Enabled" |
| RSA keys generated | `crypto key generate rsa modulus 2048` |
| VTY lines configured | `show running-config \| section line vty` |
| Username/password correct | `show running-config \| include username` |

### Problem: Netmiko timeout or authentication error

| Check | Solution |
|-------|----------|
| Correct device_type | Should be `cisco_ios` |
| Enable password set | `enable secret admin` on switch |
| SSH version 2 enabled | `ip ssh version 2` |
| Firewall blocking port 22 | Add Windows Firewall rule |
| Netmiko version | `pip install --upgrade netmiko` |

### Problem: VLANs not showing in validation

| Check | Solution |
|-------|----------|
| Switch supports `vlan X` command | Some images use `vlan database` mode instead |
| Configuration applied successfully | Check result panel for errors |
| Switch in VTP server mode | `show vtp status`, set to server or transparent |

### Problem: GNS3 switch CPU at 100%

| Check | Solution |
|-------|----------|
| Idle-PC set (Dynamips only) | Right-click switch → Idle-PC → Auto Idle-PC finder |
| Too many devices | Reduce topology complexity |
| RAM allocation | Increase in appliance settings |

---

## 10. GNS3 Topology Export/Import

### Exporting Your Topology

1. GNS3 GUI → **File → Export portable project**
2. Choose a location and filename (`.gns3p` format)
3. This creates a portable package with all configuration

### Importing a Pre-Built Topology

1. GNS3 GUI → **File → Import project**
2. Select the `.gns3p` file
3. GNS3 will extract and configure everything

### Sharing with Evaluators

If you want to share the GNS3 topology with evaluators:

1. Export the project as `.gns3p`
2. **Note**: The IOS image file is NOT included in the export (licensing restrictions)
3. Include instructions for obtaining/importing the IOS image
4. Or provide a Docker-based GNS3 setup as an alternative

---

## Quick Reference: IP Address Table

| Device | Interface | IP Address | Subnet | VLAN |
|--------|-----------|------------|--------|------|
| Host PC (Loopback) | GNS3-Bridge | 192.168.122.1 | /24 | - |
| GNS3 Switch | Vlan 1 | 192.168.122.10 | /24 | 1 (mgmt) |
| PC1 (VPCS) | eth0 | 192.168.10.1 | /24 | 10 |
| PC2 (VPCS) | eth0 | 192.168.10.2 | /24 | 10 |
| PC3 (VPCS) | eth0 | 192.168.20.1 | /24 | 20 |

## Quick Reference: Switch Port Assignment

| Switch Port | Connected To | VLAN | Purpose |
|-------------|-------------|------|---------|
| Ethernet0/0 | Cloud (Host PC) | 1 (mgmt) | Management/SSH |
| Ethernet0/1 | PC1 (VPCS) | 10 | Data network |
| Ethernet0/2 | PC2 (VPCS) | 10 | Data network |
| Ethernet0/3 | PC3 (VPCS) | 20 | Voice network |

---

*This guide is part of the Challenge Networking-DevOps project.*
