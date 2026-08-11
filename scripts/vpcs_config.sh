#!/bin/sh
# ============================================================
# VPCS Configuration Script for GNS3 Lab
# ============================================================
# This script configures the Virtual PCs (VPCS) used in the
# GNS3 topology for the Challenge Networking-DevOps project.
#
# Usage: On each VPCS console, run:
#   copy tftp://192.168.122.1/vpcs_config.vpc startup.vpc
# or manually copy the commands for each PC below.
#
# Each PC section should be pasted individually into the
# corresponding VPCS console window in GNS3.
# ============================================================

# ----------------------------------------------------------
# PC1 - Ethernet0/1 on switch - VLAN 10 (Data)
# ----------------------------------------------------------
echo "=== PC1 Configuration (VLAN 10 - Data) ==="
echo "IP: 192.168.10.1/24"
ip 192.168.10.1 255.255.255.0 192.168.10.254
save

# ----------------------------------------------------------
# PC2 - Ethernet0/2 on switch - VLAN 10 (Data)
# ----------------------------------------------------------
echo "=== PC2 Configuration (VLAN 10 - Data) ==="
echo "IP: 192.168.10.2/24"
ip 192.168.10.2 255.255.255.0 192.168.10.254
save

# ----------------------------------------------------------
# PC3 - Ethernet0/3 on switch - VLAN 20 (Voice)
# ----------------------------------------------------------
echo "=== PC3 Configuration (VLAN 20 - Voice) ==="
echo "IP: 192.168.20.1/24"
ip 192.168.20.1 255.255.255.0 192.168.20.254
save

# ----------------------------------------------------------
# Connectivity Test Commands
# ----------------------------------------------------------
# From PC1 (192.168.10.1):
#   ping 192.168.10.2    -> Should succeed (same VLAN 10)
#   ping 192.168.20.1    -> Should fail (different VLAN, no routing)
#
# From PC2 (192.168.10.2):
#   ping 192.168.10.1    -> Should succeed (same VLAN 10)
#
# From PC3 (192.168.20.1):
#   ping 192.168.10.1    -> Should fail (different VLAN, no routing)
# ----------------------------------------------------------
