"""Command-line interface. Never modifies drivers or system configuration."""
from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

from . import __version__
from .windows import DiscoveryError, discover
from .vendors import support_candidates
from .updates import available_driver_offers
from .matching import match_offers
from .catalogue import CatalogueError, load_catalogue, candidates, verify_file
from .signatures import inspect_signature
from .oem import detect_system
from .hp import hp_softpaqs

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
    lookup = sub.add_parser('lookup', help='Show official support portals for matching devices')
    lookup.add_argument('query', help='Device name or hardware-ID fragment')
    lookup.add_argument('--oem', help='Computer manufacturer (e.g. Dell, HP, Lenovo)')
    updates = sub.add_parser('updates', help='Find driver updates offered by Windows Update (read-only)')
    updates.add_argument('--json', action='store_true', help='Print full JSON with update IDs and metadata')
    check = sub.add_parser('check', help='Match Windows Update offers to installed hardware IDs')
    check.add_argument('--json', action='store_true', help='Print detailed matching evidence')
    catalogue = sub.add_parser('catalogue', help='Evaluate local OEM catalogue metadata; no downloads')
    catalogue.add_argument('file', help='Locally reviewed catalogue JSON')
    catalogue.add_argument('--model', required=True, help='Exact computer model')
    catalogue.add_argument('--os', required=True, help='Exact OS label from catalogue')
    catalogue.add_argument('--arch', required=True, help='Exact architecture label')
    verify = sub.add_parser('verify', help='Check local file SHA-256 without executing it')
    verify.add_argument('file')
    verify.add_argument('--sha256', required=True)
    signature = sub.add_parser('signature', help='Inspect local Authenticode signature (Windows only)')
    signature.add_argument('file')
    sub.add_parser('oem', help='Detect PC manufacturer, model, OS and official support entry point')
    oem_catalog = sub.add_parser('oem-catalog', help='Query supported live OEM metadata (HP CMSL currently)')
    oem_catalog.add_argument('--provider', choices=['hp'], required=True)
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
    if args.command == 'oem-catalog':
        try:
            system = detect_system()
            result = hp_softpaqs(system.get('manufacturer') or '')
        except DiscoveryError as exc:
            print(f'Error: {exc}', file=sys.stderr)
            return 1
        print(json.dumps({'system': system, **result}, indent=2, ensure_ascii=False))
        return 0
    if args.command == 'oem':
        try:
            system = detect_system()
        except DiscoveryError as exc:
            print(f'Error: {exc}', file=sys.stderr)
            return 1
        from .vendors import OEM_SUPPORT
        manufacturer = (system.get('manufacturer') or '').casefold()
        portals = [{'name': name, 'url': url} for key, (name, url) in OEM_SUPPORT.items() if key in manufacturer]
        print(json.dumps({'system': system, 'official_support_portals': portals[:1], 'live_catalogue_checked': False}, indent=2))
        return 0
    if args.command == 'signature':
        try:
            result = inspect_signature(args.file)
        except (OSError, DiscoveryError) as exc:
            print(f'Error: {exc}', file=sys.stderr)
            return 1
        print(json.dumps(result, indent=2))
        return 0 if result['signature_valid'] else 2
    if args.command == 'verify':
        try:
            result = verify_file(args.file, args.sha256)
        except (OSError, CatalogueError) as exc:
            print(f'Error: {exc}', file=sys.stderr)
            return 1
        print(json.dumps(result, indent=2))
        return 0 if result['matches'] else 2
    if args.command == 'catalogue':
        try:
            packages = load_catalogue(args.file)
            devices = discover()
            result = candidates(devices, packages, model=args.model, os_name=args.os, architecture=args.arch)
        except (OSError, ValueError, DiscoveryError) as exc:
            print(f'Error: {exc}', file=sys.stderr)
            return 1
        print(json.dumps({'candidates': result, 'count': len(result), 'warning': 'Catalogue metadata is untrusted; package authenticity and compatibility NOT verified.'}, indent=2))
        return 0
    if args.command == 'check':
        try:
            devices = discover()
            offers = available_driver_offers()
        except DiscoveryError as exc:
            print(f'Error: {exc}', file=sys.stderr)
            return 1
        result = match_offers(devices, offers['updates'])
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Exact device matches: {len(result['matched'])}; unassigned offers: {len(result['unmatched'])}")
            for entry in result['matched']:
                print(f"- {entry['device']['name']}: {entry['device'].get('driver_version') or '?'} -> {entry['offer'].get('driver_version') or '?'} ({entry['version_comparison']}; manual review)")
            print(result['note'])
        return 0
    if args.command == 'updates':
        try:
            result = available_driver_offers()
        except DiscoveryError as exc:
            print(f'Error: {exc}', file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Driver offers from {result['source']}:")
            if not result['updates']:
                print('No applicable uninstalled driver offers found in configured update service.')
            for update in result['updates']:
                print(f"- {update['title']} [ID: {update['update_id']}]")
            print(result['note'])
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
    elif args.command in ('inspect', 'search', 'lookup'):
        matches = [d for d in devices if args.query.casefold() in (str(d['name']) + ' ' + str(d['hardware_id'])).casefold()]
        if not matches:
            print('No matching devices found.')
            return 2
        if args.command == 'lookup':
            print(json.dumps([support_candidates(item, args.oem) for item in matches], indent=2, ensure_ascii=False))
        else:
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
