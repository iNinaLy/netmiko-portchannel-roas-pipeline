"""Five-phase network automation workflow."""

import logging
import time

from .config import (
    ACCESS_PORTS,
    ETHERCHANNEL_PAIRS,
    ROUTER_SUBINTERFACE_CONFIG,
    TRUNK_PORTS,
    VLAN_CONFIG,
)
from .connections import connect_to_device, disconnect_device, is_alive, save_config
from .device_config import (
    configure_access_ports,
    configure_router_on_a_stick,
    configure_trunk,
    create_vlans,
    push_member_port,
    push_portchannel_logical,
    verify_and_repush,
)
from .logging_config import LOG_FILENAME
from .verification import verify_etherchannel, verify_router, verify_switch


logging.info("=" * 60)
logging.info("NETWORK AUTOMATION SCRIPT v6 STARTED")
logging.info("=" * 60)

execution_summary = {}


def main():
    logging.info("Starting network automation v6...")
    print("\n" + "=" * 60)
    print("NETWORK AUTOMATION SCRIPT v6 — ITT633 PROJECT")
    print("=" * 60)

    print(f"\n{'=' * 50}\nPHASE 1: Core switch (S0)\n{'=' * 50}")
    s0 = connect_to_device('S0')
    if not s0:
        print("FATAL: Cannot reach S0. Aborting.")
        return

    ts0 = {}
    ts0['VLAN Creation'] = create_vlans(s0, 'S0', VLAN_CONFIG['vlans'])
    print(f"  [{'PASS' if ts0['VLAN Creation'] else 'FAIL'}] VLAN Creation (S0)")

    for intf in TRUNK_PORTS.get('S0', []):
        k = f'Trunk {intf}'
        ts0[k] = configure_trunk(s0, 'S0', intf, VLAN_CONFIG['native_vlan'], VLAN_CONFIG['allowed_vlans'])
        print(f"  [{'PASS' if ts0[k] else 'FAIL'}] {k} (S0)")

    for pair in ETHERCHANNEL_PAIRS:
        aname = pair['access_switch']
        ch = pair['channel_number']
        s0_ports = pair['s0_ports']
        acc_ports = pair['access_ports']

        print(f"\n{'=' * 50}\nPHASE 2: {aname} + EtherChannel Po{ch}\n{'=' * 50}")

        acc = connect_to_device(aname)
        if not acc:
            execution_summary[aname] = None
            continue

        tasks = {}

        tasks['VLAN Creation'] = create_vlans(acc, aname, VLAN_CONFIG['vlans'])
        print(f"  [{'PASS' if tasks['VLAN Creation'] else 'FAIL'}] VLAN Creation ({aname})")

        if aname in ACCESS_PORTS:
            tasks['Access Ports'] = configure_access_ports(acc, aname, ACCESS_PORTS[aname])
            print(f"  [{'PASS' if tasks['Access Ports'] else 'FAIL'}] Access Ports ({aname})")

        tasks[f'Po{ch} Logical'] = push_portchannel_logical(acc, aname, ch, VLAN_CONFIG['allowed_vlans'], VLAN_CONFIG['native_vlan'])
        print(f"  [{'PASS' if tasks[f'Po{ch} Logical'] else 'FAIL'}] Po{ch} Logical ({aname})")

        ts0[f'Po{ch} Logical'] = push_portchannel_logical(s0, 'S0', ch, VLAN_CONFIG['allowed_vlans'], VLAN_CONFIG['native_vlan'])
        print(f"  [{'PASS' if ts0[f'Po{ch} Logical'] else 'FAIL'}] Po{ch} Logical (S0)")

        print(f"\n  --- Welding Po{ch}: one port at a time ---")

        for i, (ap, sp) in enumerate(zip(acc_ports, s0_ports)):
            pnum = i + 1
            print(f"\n  >> Port {pnum}/{len(acc_ports)}: {aname} {ap} <-> S0 {sp}")

            acc, result = push_member_port(
                acc, aname, ap, ch,
                VLAN_CONFIG['allowed_vlans'], VLAN_CONFIG['native_vlan'])

            if acc is None:
                print(f"    {aname} {ap}: session lost (expected)")

                s0, _ = push_member_port(
                    s0, 'S0', sp, ch,
                    VLAN_CONFIG['allowed_vlans'], VLAN_CONFIG['native_vlan'])
                print(f"    S0 {sp}: pushed")

                acc, confirmed = verify_and_repush(
                    aname, ap, ch,
                    VLAN_CONFIG['allowed_vlans'], VLAN_CONFIG['native_vlan'])
                status = "confirmed" if confirmed else "FAILED"
                print(f"    {aname} {ap}: {status} after reconnect")
            else:
                print(f"    {aname} {ap}: push OK")
                s0, _ = push_member_port(
                    s0, 'S0', sp, ch,
                    VLAN_CONFIG['allowed_vlans'], VLAN_CONFIG['native_vlan'])
                print(f"    S0 {sp}: pushed")

            if i < len(acc_ports) - 1:
                print(f"    Waiting 15s for port {pnum} LACP...")
                time.sleep(15)
                if acc and not is_alive(acc):
                    disconnect_device(acc, aname)
                    acc = connect_to_device(aname, max_retries=5, retry_delay=8)

        print(f"\n  Waiting 15s for final LACP convergence...")
        time.sleep(15)

        bundled, states = verify_etherchannel(s0, 'S0', ch, s0_ports)
        ts0[f'Po{ch} Bundle (S0)'] = bundled
        print(f"  [{'PASS' if bundled else 'FAIL'}] Po{ch} S0-side: {states}")

        tasks[f'EtherChannel Po{ch}'] = bundled
        execution_summary[aname] = tasks
        if acc:
            disconnect_device(acc, aname)

    print(f"\n{'=' * 50}\nPHASE 3: Save & verify S0\n{'=' * 50}")
    ts0['Save Config'] = save_config(s0, 'S0')
    verify_switch(s0, 'S0')
    execution_summary['S0'] = ts0
    disconnect_device(s0, 'S0')

    for pair in ETHERCHANNEL_PAIRS:
        aname = pair['access_switch']
        ch = pair['channel_number']
        print(f"\n{'=' * 50}\nPHASE 4: Finalize {aname}\n{'=' * 50}")

        if execution_summary.get(aname) is None:
            print(f"  Skipping {aname}")
            continue

        conn = connect_to_device(aname, max_retries=5, retry_delay=8)
        if not conn:
            print(f"  WARNING: {aname} unreachable")
            execution_summary[aname][f'Po{ch} Bundle ({aname})'] = False
            continue

        bundled, states = verify_etherchannel(conn, aname, ch, pair['access_ports'])
        execution_summary[aname][f'Po{ch} Bundle ({aname})'] = bundled
        print(f"  [{'PASS' if bundled else 'FAIL'}] Po{ch} {aname}-side: {states}")

        execution_summary[aname]['Save Config'] = save_config(conn, aname)
        verify_switch(conn, aname)
        disconnect_device(conn, aname)

    print(f"\n{'=' * 50}\nPHASE 5: Router (R1)\n{'=' * 50}")
    r1 = connect_to_device('R1')
    if r1:
        tr1 = {}
        tr1['Router-on-a-Stick'] = configure_router_on_a_stick(
            r1, 'R1', 'GigabitEthernet0/0', ROUTER_SUBINTERFACE_CONFIG)
        print(f"  [{'PASS' if tr1['Router-on-a-Stick'] else 'FAIL'}] Router-on-a-Stick")
        tr1['Save Config'] = save_config(r1, 'R1')
        verify_router(r1, 'R1')
        execution_summary['R1'] = tr1
        disconnect_device(r1, 'R1')
    else:
        execution_summary['R1'] = None

    print("\n" + "=" * 60)
    print("EXECUTION SUMMARY")
    print("=" * 60)
    total, passed = 0, 0
    any_fail = False

    for dev, tasks in execution_summary.items():
        if tasks is None:
            print(f"\n  {dev}: UNREACHABLE")
            continue
        p = sum(1 for v in tasks.values() if v)
        t = len(tasks)
        total += t
        passed += p
        print(f"\n  {dev}: {p}/{t} tasks passed")
        for task, result in tasks.items():
            mark = "PASS" if result else "FAIL"
            print(f"    [{mark}] {task}")
            if not result and 'Bundle' in task:
                any_fail = True

    print(f"\n  TOTAL: {passed}/{total} tasks passed")
    if any_fail:
        print("\n  *** WARNING: EtherChannel bundle issue — check FAIL lines above")
    print("=" * 60)
    print(f"\nLog: {LOG_FILENAME}")
    logging.info(f"Total: {passed}/{total} tasks passed")
    logging.info("NETWORK AUTOMATION SCRIPT v6 COMPLETED")


def run():
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        print(f"\n[!] Unexpected error: {e}")


if __name__ == "__main__":
    run()