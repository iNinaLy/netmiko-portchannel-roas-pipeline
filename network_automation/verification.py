"""Device state checks and verification output."""

import logging
import re


def parse_etherchannel_summary(output, ch):
    port_states = {}
    in_group = False
    for line in output.splitlines():
        s = line.strip()
        if re.match(rf'^{ch}\s+Po{ch}', s):
            in_group = True
        elif re.match(r'^\d+\s+Po\d+', s) and not s.startswith(f'{ch} '):
            in_group = False
        if in_group:
            for m in re.finditer(r'([A-Za-z]+[\d/]+)\((\w)\)', s):
                port_states[m.group(1)] = m.group(2)
    return port_states


def verify_etherchannel(conn, name, ch, expected_ports):
    try:
        output = conn.send_command('show etherchannel summary', read_timeout=20)
    except Exception as e:
        logging.error(f"Could not get etherchannel summary on {name}: {e}")
        return False, {}

    states = parse_etherchannel_summary(output, ch)
    logging.info(f"{name} Po{ch} states: {states}")

    all_ok = True
    for port in expected_ports:
        short = re.sub(r'^GigabitEthernet', 'Gi', port)
        if states.get(short) != 'P':
            all_ok = False
            logging.warning(f"{name}: {port} NOT bundled (flag={states.get(short, 'not found')})")
    return all_ok, states


def verify_switch(conn, name):
    for cmd in ["show vlan brief", "show interfaces trunk", "show etherchannel summary"]:
        try:
            output = conn.send_command(cmd, read_timeout=30)
            print(f"\n  --- {name}: {cmd} ---")
            print(output)
            logging.info(f"{name} {cmd}:\n{output}")
        except Exception:
            print(f"\n  --- {name}: {cmd} FAILED ---")


def verify_router(conn, name):
    for cmd in ["show ip interface brief", "show ip route"]:
        try:
            output = conn.send_command(cmd, read_timeout=30)
            print(f"\n  --- {name}: {cmd} ---")
            print(output)
            logging.info(f"{name} {cmd}:\n{output}")
        except Exception:
            print(f"\n  --- {name}: {cmd} FAILED ---")