"""Credentials, device inventory, and network configuration data."""

import os


SSH_USERNAME = os.environ.get('NET_USERNAME', 'admin')
SSH_PASSWORD = os.environ.get('NET_PASSWORD', 'cisco123')
SSH_SECRET = os.environ.get('NET_SECRET', 'cisco')

DEVICE_INFO = {
    'S0': {'ip': '192.168.42.51', 'role': 'core_switch'},
    'S1': {'ip': '192.168.42.52', 'role': 'access_switch'},
    'S2': {'ip': '192.168.42.53', 'role': 'access_switch'},
    'R1': {'ip': '192.168.42.50', 'role': 'router'},
}

VLAN_CONFIG = {
    'vlans': [(10, 'SALES'), (20, 'IT'), (30, 'MARKETING')],
    'native_vlan': 1,
    'allowed_vlans': [1, 10, 20, 30]
}

ACCESS_PORTS = {
    'S1': [{'port': 'GigabitEthernet0/0', 'vlan': 10, 'device': 'PC1'}],
    'S2': [
        {'port': 'GigabitEthernet0/0', 'vlan': 20, 'device': 'PC2'},
        {'port': 'GigabitEthernet0/1', 'vlan': 30, 'device': 'PC3'},
    ],
}

TRUNK_PORTS = {'S0': ['GigabitEthernet0/0']}

ETHERCHANNEL_PAIRS = [
    {
        'access_switch': 'S1', 'channel_number': 1,
        's0_ports': ['GigabitEthernet1/1', 'GigabitEthernet1/2'],
        'access_ports': ['GigabitEthernet1/1', 'GigabitEthernet1/2'],
    },
    {
        'access_switch': 'S2', 'channel_number': 2,
        's0_ports': ['GigabitEthernet2/1', 'GigabitEthernet2/2'],
        'access_ports': ['GigabitEthernet2/1', 'GigabitEthernet2/2'],
    },
]

ROUTER_SUBINTERFACE_CONFIG = {
    10: {'ip': '192.168.10.1', 'mask': '255.255.255.0'},
    20: {'ip': '192.168.20.1', 'mask': '255.255.255.0'},
    30: {'ip': '192.168.30.1', 'mask': '255.255.255.0'},
}