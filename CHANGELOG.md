# Changelog

All notable changes to this project are documented in this file.
This project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- CI/CD pipeline with GitHub Actions (lint, test, security scan, build)
- Docker containerization support (Dockerfile, docker-compose)
- Canary/gray release infrastructure (feature flags, Nginx load balancer)
- Health check endpoints (`/health`, `/ready`, `/api/features`)
- Feature flag system for runtime configuration
- Comprehensive test suite (42 tests, 100% pass rate)
- Pytest configuration in `pyproject.toml`

---

## [1.1.0] - 2026-08-07

### Added
- GNS3 deployment guide with 6-phase step-by-step instructions
- GNS3 topology reference (JSON format with nodes, links, VLAN assignments)
- Switch initialization script (`gns3_switch_init.py`)
- Full GNS3 demo runner with colored terminal output (`gns3_demo.py`)
- VPCS configuration script for VLAN connectivity testing

### Changed
- All documentation and code comments rewritten in English

---

## [1.0.0] - 2026-08-07

### Added
- Flask web application with VLAN configuration frontend
- REST API endpoints (`/api/configure`, `/api/validate`)
- Cisco switch automation backend using Netmiko
  - VLAN creation and naming (VLAN 10/20/50)
  - Hostname modification (default: SWITCH_AUTOMATIZADO)
  - Configuration save to NVRAM (`write memory`)
  - Configuration backup (hostname + timestamp in filename)
  - Configuration validation with alert mechanism
- Simulation mode for demoing without a real switch
- IPSec VPN automation planning document
  - Fortigate (REST API) and Palo Alto (XML API) configuration scripts
  - IPSec tunnel connectivity test script
- Pre-configured VLANs: 10 (VLAN_DATOS), 20 (VLAN_VOZ), 50 (VLAN_SEGURIDAD)
- Project structure with `.gitignore`, `requirements.txt`, `README.md`

### Technical Stack
- Python 3.11+, Flask 3.0+, Netmiko 4.3+
- Git for version control (9 commits)
