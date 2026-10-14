"""VLAN, interface, EtherChannel, and router configuration commands."""

import logging
import time

from .connections import connect_to_device, disconnect_device, is_alive


def create_vlans(conn, name, vlan_list):
    commands = []
    for vid, vname in vlan_list:
        commands.extend([f"vlan {vid}", f"name {vname}"])
    try:
        conn.send_config_set(commands)
        logging.info(f"VLANs created on {name}")
        return True
    except Exception as e:
        logging.error(f"Failed to create VLANs on {name}: {e}")
        return False


def configure_access_ports(conn, name, port_configs):
    commands = []
    for cfg in port_configs:
        commands.extend([
            f"interface {cfg['port']}", "switchport mode access",
            f"switchport access vlan {cfg['vlan']}",
            "spanning-tree portfast", "no shutdown", "exit"
        ])
    try:
        conn.send_config_set(commands)
        logging.info(f"Access ports configured on {name}")
        return True
    except Exception as e:
        logging.error(f"Failed to configure access ports on {name}: {e}")
        return False


def configure_trunk(conn, name, interface, native_vlan, allowed_vlans):
    allowed_str = ','.join(str(v) for v in allowed_vlans)
    commands = [
        f"interface {interface}", "switchport trunk encapsulation dot1q",
        "switchport mode trunk", f"switchport trunk native vlan {native_vlan}",
        f"switchport trunk allowed vlan {allowed_str}", "no shutdown", "exit"
    ]
    try:
        conn.send_config_set(commands)
        logging.info(f"Trunk configured on {name} {interface}")
        return True
    except Exception as e:
        logging.error(f"Failed to configure trunk on {name}: {e}")
        return False


def push_portchannel_logical(conn, name, ch, allowed_vlans, native_vlan):
    """Configure port-channel logical interface (non-disruptive)."""
    allowed_str = ','.join(map(str, allowed_vlans))
    commands = [
        f'interface port-channel {ch}', 'switchport trunk encapsulation dot1q',
        'switchport mode trunk', f'switchport trunk allowed vlan {allowed_str}',
        f'switchport trunk native vlan {native_vlan}', 'no shutdown', 'exit'
    ]
    try:
        conn.send_config_set(commands)
        logging.info(f"Po{ch} logical interface configured on {name}")
        return True
    except Exception as e:
        logging.error(f"Po{ch} logical failed on {name}: {e}")
        return False


def push_member_port(conn, name, port, ch, allowed_vlans, native_vlan):
    """Push channel-group to ONE member port. Returns (conn|None, ok)."""
    allowed_str = ','.join(map(str, allowed_vlans))
    commands = [
        f'interface {port}', 'switchport trunk encapsulation dot1q',
        'switchport mode trunk', f'switchport trunk allowed vlan {allowed_str}',
        f'switchport trunk native vlan {native_vlan}',
        f'channel-group {ch} mode active', 'no shutdown', 'exit'
    ]
    try:
        conn.send_config_set(commands, read_timeout=60)
        logging.info(f"{name}: pushed channel-group {ch} to {port}")
        if is_alive(conn):
            return conn, True
        else:
            disconnect_device(conn, name)
            return None, 'unconfirmed'
    except Exception as e:
        logging.warning(f"{name}: {port} push raised {type(e).__name__}: {e}")
        disconnect_device(conn, name)
        return None, 'unconfirmed'


def verify_and_repush(access_name, port, ch, allowed_vlans, native_vlan):
    """Reconnect to access switch, check if channel-group applied, re-push if not."""
    logging.info(f"Waiting 20s for LACP convergence before reconnecting to {access_name}...")
    time.sleep(20)

    conn = connect_to_device(access_name, max_retries=5, retry_delay=8)
    if not conn:
        return None, False

    try:
        output = conn.send_command(f'show run interface {port}', read_timeout=20)
        if f'channel-group {ch}' in output:
            logging.info(f"{access_name}: {port} channel-group confirmed after reconnect")
            return conn, True
    except Exception:
        pass

    logging.info(f"{access_name}: re-pushing channel-group {ch} to {port}")
    allowed_str = ','.join(map(str, allowed_vlans))
    commands = [
        f'interface {port}', 'switchport trunk encapsulation dot1q',
        'switchport mode trunk', f'switchport trunk allowed vlan {allowed_str}',
        f'switchport trunk native vlan {native_vlan}',
        f'channel-group {ch} mode active', 'no shutdown', 'exit'
    ]
    try:
        conn.send_config_set(commands, read_timeout=60)
        logging.info(f"{access_name}: re-push of {port} succeeded")
        return conn, True
    except Exception as e:
        logging.error(f"{access_name}: re-push of {port} failed: {e}")
        disconnect_device(conn, access_name)
        return None, False


def configure_router_on_a_stick(conn, name, phys_intf, vlan_configs):
    commands = [f'interface {phys_intf}', 'no shutdown', 'exit']
    for vid, cfg in vlan_configs.items():
        commands.extend([
            f'interface {phys_intf}.{vid}', f'encapsulation dot1Q {vid}',
            f'ip address {cfg["ip"]} {cfg["mask"]}', 'no shutdown', 'exit'
        ])
    try:
        conn.send_config_set(commands)
        logging.info(f"Router-on-a-Stick configured on {name}")
        return True
    except Exception as e:
        logging.error(f"Router-on-a-Stick failed on {name}: {e}")
        return False