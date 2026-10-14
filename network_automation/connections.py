"""SSH connection lifecycle and configuration-save helpers."""

import logging
import time

from netmiko import ConnectHandler
from netmiko import NetMikoAuthenticationException

from .config import DEVICE_INFO, SSH_PASSWORD, SSH_SECRET, SSH_USERNAME


def connect_to_device(name, max_retries=3, retry_delay=5):
    """SSH connect with retry."""
    info = DEVICE_INFO[name]
    params = {
        'device_type': 'cisco_ios', 'ip': info['ip'],
        'username': SSH_USERNAME, 'password': SSH_PASSWORD,
        'secret': SSH_SECRET, 'port': 22,
    }
    for attempt in range(1, max_retries + 1):
        logging.info(f"Connecting to {name} ({info['ip']}) — attempt {attempt}/{max_retries}...")
        try:
            conn = ConnectHandler(**params)
            conn.enable()
            conn.send_command('terminal length 0')
            logging.info(f"Successfully connected to {name}")
            return conn
        except NetMikoAuthenticationException as e:
            logging.error(f"Auth failed for {name}: {e}")
            return None
        except Exception as e:
            logging.error(f"Connection to {name} failed: {e}")
            if attempt < max_retries:
                time.sleep(retry_delay)
    logging.error(f"All {max_retries} attempts failed for {name}")
    return None


def disconnect_device(conn, name):
    try:
        if conn:
            conn.disconnect()
            logging.info(f"Disconnected from {name}")
    except Exception:
        pass


def is_alive(conn):
    try:
        conn.find_prompt()
        return True
    except Exception:
        return False


def save_config(conn, name):
    logging.info(f"Saving configuration on {name}...")
    try:
        role = DEVICE_INFO.get(name, {}).get('role', '')
        if role == 'router':
            output = conn.send_command_timing('write memory', delay_factor=4, max_loops=300)
            time.sleep(3)
            output += conn.send_command_timing('', delay_factor=2)
        else:
            output = conn.save_config()
        logging.info(f"Configuration saved on {name}")
        print(f"  [PASS] Save Config ({name})")
        return True
    except Exception as e:
        logging.error(f"Failed to save config on {name}: {e}")
        print(f"  [FAIL] Save Config ({name}): {e}")
        return False