"""Command-line interface. Never modifies drivers or system configuration."""
from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

from . import __version__
from .windows import DiscoveryError, discover

LOGO = r'''
 _   _ ____   ____ ____  ___  ____  _____
| | | |  _ \ / ___|  _ \/ _ \|  _ \| ____|
| | | | |_) | |  _| |_) | (_) | | | |  _|
| |_| |  __/| |_| |  _ < (_) | |_| | |___
 \___/|_|    \____|_| \_\___/|____/|_____|
'''


def _print_devices(devices: list[dict]) -> None:
    if not devices:
        print('No matching devices found.')
        return
    for item in devices:
        code = item.get('problem_code')
        label = 'MISSING' if item['missing_driver'] else ('ISSUE' if code not in (None, 0) else 'OK')
        print(f"[{label:7}] {item['name']}  |  {item.get('driver_version') or 'unknown version'}")
    print(f'\n{len(devices)} device(s) listed.')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='upgr8de', description='Discover Windows hardware drivers safely.')
    parser.add_argument('--version', action='version', version=f'upgr8de {__version__}')
    sub = parser.add_subparsers(dest='command')
    sub.add_parser('scan', help='List devices and current driver versions')
    sub.add_parser('missing', help='List devices reporting missing drivers (Windows problem code 28)')
    inspect = sub.add_parser('inspect', help='Inspect matching devices by name or hardware ID')
    inspect.add_argument('query', help='Device name or hardware-ID fragment')
    search = sub.add_parser('search', help='Provide safe lookup guidance (no downloads)')
    search.add_argument('query', help='Device name or hardware-ID fragment')
    report = sub.add_parser('report', help='Save inventory as JSON')
    report.add_argument('--output', default='upgr8de-report.json')
    sub.add_parser('doctor', help='Check environment and OS compatibility')
    args = parser.parse_args(argv)
    if args.command is None:
        print(LOGO)
        print('DRIVER INTELLIGENCE ENGINE | Discover. Verify. Upgrade.\n')
        parser.print_help()
        return 0
    if args.command == 'doctor':
        print(f'upgr8de v{__version__}')
        print(f'Platform: {platform.platform()}')
        print(f'Windows discovery supported: {platform.system() == "Windows"}')
        print('Mode: read-only; driver updates are never installed')
        return 0
    try:
        devices = discover()
    except DiscoveryError as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
    if args.command == 'scan':
        _print_devices(devices)
    elif args.command == 'missing':
        _print_devices([d for d in devices if d['missing_driver']])
    elif args.command in ('inspect', 'search'):
        matches = [d for d in devices if args.query.casefold() in (str(d['name']) + ' ' + str(d['hardware_id'])).casefold()]
        if not matches:
            print('No matching devices found.')
            return 2
        print(json.dumps(matches, indent=2, ensure_ascii=False))
        if args.command == 'search':
            print('\nResearch exact hardware ID on device manufacturer or OEM official support site.')
            for item in matches:
                print(f"Search phrase: {item['hardware_id']} {item.get('manufacturer') or ''} driver")
            print('No download URL or driver compatibility is verified by this command.')
    elif args.command == 'report':
        target = Path(args.output)
        target.write_text(json.dumps({'version': __version__, 'platform': platform.platform(), 'devices': devices}, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f'Wrote {len(devices)} records to {target}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
