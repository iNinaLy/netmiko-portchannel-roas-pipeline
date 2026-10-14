# netmiko-portchannel-roas-pipeline
Python and Netmiko automation pipeline for Cisco enterprise networks, featuring LACP Port-Channel link aggregation, dynamic VLAN segmentation, and Router-on-a-Stick (ROAS) routing deployed in GNS3.

# ITT633 - Automated Network Configuration with VLAN Segmentation and EtherChannel Deployment

[![Python 3.14](https://img.shields.io/badge/Python-3.14-blue.svg)](https://www.python.org/)
[![Netmiko](https://img.shields.io/badge/Netmiko-SSH-orange.svg)](https://github.com/ktbyers/netmiko)
[![Cisco IOSvL2](https://img.shields.io/badge/Platform-Cisco%20IOSvL2%20%2F%20IOS-green.svg)](https://www.cisco.com)

An automated network provisioning and validation pipeline built with Python and Netmiko. This project automates a hierarchical 3-tier Cisco enterprise network topology in GNS3, featuring VLAN segmentation, LACP EtherChannel link aggregation, and Router-on-a-Stick inter-VLAN routing.

---

## Network Architecture & Topology

- **Core Layer:** Cisco 7200 Router (`R1`) handling Router-on-a-Stick inter-VLAN routing via 802.1Q subinterfaces.
- **Distribution Layer:** Core Switch (`S0`) managing LACP EtherChannel trunk bundles (`Po1`, `Po2`).
- **Access Layer:** Access Switches (`S1`, `S2`) connected via redundant LACP member ports, isolating department traffic.
- **VLAN Segmentation Scheme:**
  - **VLAN 1:** Management Network (`192.168.42.0/24`)
  - **VLAN 10:** Sales (`192.168.10.0/24`)
  - **VLAN 20:** IT (`192.168.20.0/24`)
  - **VLAN 30:** Marketing (`192.168.30.0/24`)

---

## Why Standard Scripts Fail

Standard network automation scripts often push batch port-channel commands simultaneously, causing disruptive LACP/STP renegotiations that instantly drop the active Netmiko SSH session. This leads to **silent partial configurations** where the first port joins the channel, but subsequent ports drop back to default settings without throwing explicit script errors.

### Interleaved Per-Port Welding (Solution)

To solve this self-referential dependency (where the management session traverses the exact links being reconfigured), this script implements a resilient **interleaved welding strategy**:
1. **Granular Per-Port Pushes:** Adds member ports to the LACP channel-group one port at a time.
2. **Out-of-Band Path Preservation:** Alternates pushes between the access switch and the Core Switch (`S0`)—which maintains a stable management path via the GNS3 cloud bridge.
3. **State Verification & Auto-Repush:** Automatically waits for LACP convergence, reconnects, reads back the live running configuration to verify if the channel-group successfully landed, and dynamically re-pushes if necessary.

---

## Key Features

- **Modular Python Scripting:** Cleanly structured code utilizing Netmiko for secure SSH automation, complete with environment-variable credential management.
- **Robust Exception Handling & Logging:** Automatically generates timestamped execution logs (`network_automation_YYYYMMDD_HHMMSS.log`) capturing session events and task success states.
- **Automated Verification:** Programmatically parses CLI output (`show etherchannel summary`, `show vlan brief`, `show ip route`) using regular expressions to confirm active operational states before exiting.

---

## 🛠️ Tech Stack & Tools

- **Simulator:** GNS3 (v2.2.59) running on a KVM-enabled GNS3 VM
- **Language:** Python 3.14
- **Library:** Netmiko (SSH Automation)
- **Devices:** Cisco IOSvL2 (Switches) and Cisco IOS 7200 (Router)

---