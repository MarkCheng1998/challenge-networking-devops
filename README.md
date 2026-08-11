# Challenge Networking - DevOps

> Mercado Libre - Candidate Lab - Network Technology Automation Challenge

This project implements Cisco switch VLAN configuration automation (via a web frontend) and plans the automation of IPSec VPN configuration between Fortigate and Palo Alto firewalls.

---

## Project Structure

```
challenge-networking-devops/
├── README.md                         # Project documentation
├── requirements.txt                  # Python dependencies
├── .gitignore
├── app.py                            # Flask web application entry point
├── templates/
│   └── index.html                    # VLAN configuration frontend interface
├── static/
│   ├── style.css                     # Frontend styling
│   └── script.js                     # Frontend interaction logic
├── backend/
│   ├── __init__.py
│   └── switch_config.py              # Cisco switch automation backend (VLAN/hostname/save/backup/validation)
├── backups/                          # Configuration backup directory
├── docs/
│   └── vpn_ipsec_plan.md             # Part 2: IPSec VPN automation planning document
└── scripts/
    ├── fortigate_vpn_config.py       # Fortigate VPN configuration script (REST API)
    ├── paloalto_vpn_config.py        # Palo Alto VPN configuration script (XML API)
    └── test_connectivity.py          # IPSec tunnel connectivity test script
```

---

## Part 1: Cisco Switch VLAN Configuration Automation

### Feature Overview

| Feature | Description |
|---------|-------------|
| VLAN Configuration | Input VLAN IDs and names via web interface; automatically create VLANs on the Cisco switch |
| Hostname Modification | Set the switch hostname via web interface (default: SWITCH_AUTOMATIZADO) |
| Configuration Save | Automatically execute `write memory` to save configuration to NVRAM |
| Configuration Backup | Automatically back up current configuration to a local file (filename includes hostname and timestamp) |
| Configuration Validation | Automatically validate VLANs and hostname after configuration; display alerts on discrepancies |
| Simulation Mode | Full workflow demonstration without a real switch (for testing and presentation) |

### Pre-configured VLANs

| VLAN ID | Name | Purpose |
|---------|------|---------|
| 10 | VLAN_DATOS | Data network |
| 20 | VLAN_VOZ | Voice network |
| 50 | VLAN_SEGURIDAD | Security network |

### Installation and Usage

#### 1. Install Dependencies

```bash
# Clone the repository
git clone https://github.com/<your-username>/challenge-networking-devops.git
cd challenge-networking-devops

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

#### 2. Run the Web Application

```bash
python app.py
```

After launch, open in your browser: **http://localhost:5000**

#### 3. Using the Frontend Interface

1. **Switch Connection Info**: Enter the switch IP, username, password, and SSH port
   - If no real device is available, check "Simulation Mode" to demonstrate the full workflow
2. **Hostname**: Enter the target hostname (default: SWITCH_AUTOMATIZADO)
3. **VLAN Configuration**: VLANs 10/20/50 are pre-populated; you can add/remove/modify VLANs
4. **Execute Configuration**: Click the "Execute Automated Configuration" button
   - The script will execute: Connect to switch -> Configure VLANs -> Modify hostname -> Save to NVRAM -> Backup configuration -> Validate configuration
5. **View Results**: The right panel shows execution status and validation alerts for each step
6. **Validate Only**: To validate the current configuration only, click "Validate Configuration Only"

### Backend Tech Stack

- **Flask**: Web framework, provides REST API and page rendering
- **Netmiko**: Network automation library, connects to Cisco switches via SSH
- **Regular Expressions**: Parse `show vlan brief` and `show running-config` output for validation

### Validation Logic

The configuration validation checks the following:
1. **Hostname Match**: Whether the current hostname matches the expected value
2. **VLAN Existence**: Whether each expected VLAN exists
3. **VLAN Name Match**: Whether the VLAN name matches the expected value
4. **Non-standard Configuration Detection**: Whether there are extra VLANs not in the expected list

Alert levels:
- **WARNING (Critical Alert)**: VLAN missing, name mismatch, hostname mismatch
- **INFO (Informational)**: Non-standard VLAN found (does not affect expected configuration)

---

## Part 2: IPSec VPN Automation Planning

### Document Location

Detailed planning document: [`docs/vpn_ipsec_plan.md`](docs/vpn_ipsec_plan.md)

### Document Contents

- **Parameter Definitions**: WAN IPs, local networks, tunnel network (169.255.1.0/30), Phase 1/2 parameters
- **Tool/API Identification**: FortiOS REST API, Palo Alto XML API, SSH+CLI, Ansible, Terraform
- **Automation Steps**: Complete configuration workflow for both devices (address objects -> IKE -> IPSec -> tunnel -> policy -> route)
- **Cross-Vendor Considerations**: Terminology mapping, commit mechanisms, API formats, interface numbering differences
- **Validation and Alert Strategy**: CLI/API validation methods, checklist, alert grading, rollback strategy

### Example Scripts (Optional Deliverables)

| Script | Description |
|--------|-------------|
| `scripts/fortigate_vpn_config.py` | Configure IPSec VPN via FortiOS REST API |
| `scripts/paloalto_vpn_config.py` | Configure Palo Alto IPSec VPN via XML API |
| `scripts/test_connectivity.py` | Test IPSec tunnel connectivity (Ping + status validation) |

---

## Test Environment Notes

- **Part 1**: Use Cisco Packet Tracer or GNS3 to set up a Cisco switch simulation environment
  - Alternatively, use "Simulation Mode" for demonstration without any network equipment
- **Part 2**: VPN configuration is a planning document; no actual environment required. Example scripts can run on real devices

---

## Git Commit History

This project uses Git for version control. Commit history:

| Commit | Description |
|--------|-------------|
| 1 | Initial project structure and base files (.gitignore, requirements.txt) |
| 2 | Implement backend Cisco switch configuration module (switch_config.py) |
| 3 | Develop Flask web frontend and API (app.py, templates, static) |
| 4 | Implement configuration validation and alert mechanism |
| 5 | Add IPSec VPN automation planning document (vpn_ipsec_plan.md) |
| 6 | Add Fortigate/Palo Alto VPN example scripts and connectivity test |
| 7 | Fix netmiko exception import for v4.7+ compatibility |
| 8 | Rewrite all project documentation and code comments in English |

---

## Technical Highlights

1. **Layered Architecture**: Frontend (Flask/HTML/CSS/JS) -> API Layer -> Backend Automation Layer (Netmiko)
2. **Simulation Mode**: Built-in simulator for full workflow demonstration without equipment
3. **Validation-Driven**: Automatic validation after configuration to ensure correctness
4. **Secure Backup**: Automatic backup after each configuration change; filename includes hostname and timestamp
5. **Cross-Vendor Compatibility**: VPN planning covers Fortigate and Palo Alto differences
