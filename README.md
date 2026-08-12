# Challenge Networking - DevOps

> Mercado Libre - Candidate Lab - Network Technology Automation Challenge

This project implements Cisco switch VLAN configuration automation (via a web frontend) and plans the automation of IPSec VPN configuration between Fortigate and Palo Alto firewalls.

---

## Project Structure

```
challenge-networking-devops/
├── README.md                         # Project documentation
├── CHANGELOG.md                      # Semantic versioning changelog
├── VERSION                           # Current version (1.1.0)
├── pyproject.toml                    # Python tooling config (pytest, flake8, black, bandit)
├── requirements.txt                  # Python dependencies
├── Dockerfile                        # Multi-stage Docker build
├── docker-compose.yml                # Production + canary deployment
├── docker-compose.staging.yml        # Staging environment
├── .gitignore
├── .github/
│   └── workflows/
│       ├── ci.yml                    # CI: lint → test → security → build
│       └── cd.yml                    # CD: staging deploy + canary release
├── app.py                            # Flask web application entry point
├── templates/
│   └── index.html                    # VLAN configuration frontend interface
├── static/
│   ├── style.css                     # Frontend styling
│   └── script.js                     # Frontend interaction logic
├── backend/
│   ├── __init__.py
│   ├── switch_config.py              # Cisco switch automation backend
│   └── feature_flags.py              # Feature flag system for gray release
├── config/
│   └── feature_flags.json            # Canary release configuration
├── nginx/
│   └── nginx.conf                    # Load balancer for canary traffic routing
├── backups/                          # Configuration backup directory
├── tests/
│   ├── conftest.py                   # Pytest fixtures
│   ├── test_switch_config.py         # Unit tests (SwitchConfigurator)
│   └── test_app.py                   # Integration tests (Flask API)
├── docs/
│   ├── vpn_ipsec_plan.md             # Part 2: IPSec VPN automation planning
│   ├── gns3_deployment_guide.md      # GNS3 step-by-step deployment guide
│   ├── gns3_topology.json            # GNS3 topology reference
│   └── cicd_strategy.md              # CI/CD pipeline and canary release guide
└── scripts/
    ├── fortigate_vpn_config.py       # Fortigate VPN configuration script (REST API)
    ├── paloalto_vpn_config.py        # Palo Alto VPN configuration script (XML API)
    ├── test_connectivity.py          # IPSec tunnel connectivity test script
    ├── gns3_switch_init.py           # GNS3 switch initial configuration
    ├── gns3_demo.py                  # GNS3 demo runner
    └── vpcs_config.sh               # VPCS host configuration script
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
git clone https://github.com/MarkCheng1998/challenge-networking-devops.git
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

- **Part 1**: Use GNS3 with a real Cisco IOS image to set up a fully functional switch simulation environment
  - See the [GNS3 Deployment Guide](docs/gns3_deployment_guide.md) for step-by-step instructions
  - Alternatively, use "Simulation Mode" for demonstration without any network equipment
- **Part 2**: VPN configuration is a planning document; no actual environment required. Example scripts can run on real devices

---

## GNS3 Deployment Guide

This project includes a comprehensive GNS3 deployment guide for setting up a real Cisco switch lab environment.

### Key Documents

| Document | Description |
|----------|-------------|
| [`docs/gns3_deployment_guide.md`](docs/gns3_deployment_guide.md) | Complete step-by-step guide: GNS3 installation, IOS image import, topology setup, network bridging, switch configuration, and demo walkthrough |
| [`docs/gns3_topology.json`](docs/gns3_topology.json) | Topology reference with all nodes, links, VLAN assignments, and port mappings |

### GNS3 Demo Scripts

| Script | Description |
|--------|-------------|
| `scripts/gns3_switch_init.py` | Generates and applies initial switch configuration (hostname, SSH, admin user, management IP) |
| `scripts/gns3_demo.py` | Runs the full VLAN automation workflow against a GNS3 switch with detailed terminal output |
| `scripts/vpcs_config.sh` | Configures Virtual PCs (VPCS) for VLAN connectivity testing |

### Quick Start with GNS3

```bash
# 1. Follow the GNS3 deployment guide to set up the topology
#    (Install GNS3, import IOS image, create topology, configure switch)

# 2. Generate the switch initial configuration
python scripts/gns3_switch_init.py --generate --output switch_base.cfg

# 3. Apply the configuration to the GNS3 switch
python scripts/gns3_switch_init.py --apply --host 127.0.0.1 --port 5001

# 4. Verify connectivity to the switch
python scripts/gns3_demo.py --check-only

# 5. Run the full VLAN automation demo
python scripts/gns3_demo.py --host 192.168.122.10 --username admin --password admin

# 6. Or use the Flask web UI
python app.py
# Open http://localhost:5000
# Enter: Switch IP = 192.168.122.10, admin/admin, uncheck Simulation Mode
```

### GNS3 Topology Overview

```
  Host PC (Flask + Netmiko)
       │ SSH
       │
  [Cloud Node] ←→ [Loopback Adapter 192.168.122.1/24]
       │
  ┌────┴────────────┐
  │  GNS3 Switch     │  192.168.122.10
  │  (vIOS-L2/c3725) │  VLAN 1 (mgmt)
  └──┬──────┬────┬──┘
     │      │    │
  PC1(V10) PC2(V10) PC3(V20)
```

---

## CI/CD Pipeline & Gray Release

This project includes a full CI/CD pipeline with gray/canary release support.

### CI Pipeline (`.github/workflows/ci.yml`)

Runs on every push and PR to `main`/`develop`:

| Stage | Tool | Gate |
|-------|------|------|
| Lint | flake8 + black | Zero errors |
| Test | pytest + pytest-cov | All tests pass, coverage ≥ 70% |
| Security | bandit | No HIGH severity issues |
| Build | Docker build + health check | Image builds, `/health` returns 200 |

### CD Pipeline (`.github/workflows/cd.yml`)

| Trigger | Action |
|---------|--------|
| Push to `main` | Build image → Deploy to staging → Smoke tests |
| Tag `v*.*.*` | Build image → Canary (10%) → Health check → Promote to production |
| Manual dispatch | Adjustable canary percentage |

### Gray / Canary Release

```
           ┌──────────────────────────────────────┐
           │     Nginx Load Balancer (:8080)      │
           │   90% → app-blue   10% → app-canary  │
           └────────┬────────────────┬────────────┘
                    │                │
           ┌────────▼────┐   ┌──────▼──────┐
           │  app-blue   │   │ app-canary  │
           │  :5000      │   │ :5001       │
           │  v1.0.0     │   │ v1.1.0      │
           │  (stable)   │   │ (canary)    │
           └─────────────┘   └─────────────┘
```

```bash
# Start canary deployment
docker-compose --profile canary up -d

# Check health
curl http://localhost:5000/health    # production
curl http://localhost:5001/health    # canary
curl http://localhost:8080/health    # via load balancer

# See which backend served your request
curl -v http://localhost:8080/ 2>&1 | grep X-Served-By

# Inspect feature flags
curl http://localhost:5000/api/features | python -m json.tool

# Rollback
docker-compose down && docker-compose up -d  # restarts only blue
```

### Health Check Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/health` | Liveness probe (is the process alive?) |
| `/ready` | Readiness probe (can the app serve traffic?) |
| `/api/features` | Feature flag state (debug canary config) |

### Running Tests Locally

```bash
# Install test dependencies
pip install pytest pytest-cov flake8 black bandit

# Run all tests with coverage
pytest tests/ -v --cov=backend --cov=app --cov-report=term-missing

# Run linter
flake8 app.py backend/ tests/ --max-line-length=120 --extend-ignore=E501,W503,E203

# Run security scan
bandit -r backend/ scripts/ app.py -ll

# Check formatting
black --check --line-length 120 app.py backend/ tests/ scripts/
```

### Docker Deployment

```bash
# Build production image
docker build -t challenge-networking:1.1.0 --build-arg APP_VERSION=1.1.0 .

# Run standalone
docker run -d -p 5000:5000 challenge-networking:1.1.0

# Full stack with canary (production + canary + nginx)
docker-compose --profile canary up -d

# Staging
docker-compose -f docker-compose.staging.yml up -d
```

Detailed CI/CD guide: [`docs/cicd_strategy.md`](docs/cicd_strategy.md)

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
| 9 | Add GNS3 deployment guide, topology reference, switch init script, demo runner, and VPCS config |
| 10 | Add CI/CD pipeline: GitHub Actions (CI+CD), test suite (42 tests), Docker, canary release, feature flags, health checks, versioning |

---

## Technical Highlights

1. **Layered Architecture**: Frontend (Flask/HTML/CSS/JS) -> API Layer -> Backend Automation Layer (Netmiko)
2. **Simulation Mode**: Built-in simulator for full workflow demonstration without equipment
3. **Validation-Driven**: Automatic validation after configuration to ensure correctness
4. **Secure Backup**: Automatic backup after each configuration change; filename includes hostname and timestamp
5. **Cross-Vendor Compatibility**: VPN planning covers Fortigate and Palo Alto differences
6. **CI/CD Pipeline**: GitHub Actions for lint, test, security, build, staging deploy, and canary release
7. **Gray Release**: Feature flags + Nginx load balancer for safe canary deployments
8. **Dockerized**: Multi-stage Docker build with health checks and non-root execution
9. **Test Coverage**: 42 tests covering backend logic and Flask API endpoints (100% pass rate)
