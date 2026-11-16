# upgr8de

**Discover. Verify. Upgrade.** Windows-first, read-only hardware and driver discovery CLI with an ASCII terminal banner.

## MVP features

- Inspect Windows PnP devices using built-in CIM PowerShell commands.
- Report installed driver versions, providers, INF filenames and driver-signature state when available.
- Identify missing drivers via Windows Configuration Manager problem code **28**.
- Report other device errors without assuming that every device error means a missing driver.
- Search inventory by device name or hardware ID and generate safe vendor lookup phrases.
- Parse PCI/USB hardware IDs and route to known official OEM/chip-vendor support portals with `lookup`.
- Export local device reports as JSON.

**No drivers are downloaded or installed.** `lookup` returns static official support landing pages, not live catalogue results, verified package matches or proof that an update exists. `search` produces lookup guidance, not verified driver URLs or update recommendations.

## Install (Windows 10/11, Python 3.10+)

```powershell
git clone https://github.com/hmazomba/upgr8de.git
cd upgr8de
py -m pip install -e .
upgr8de
upgr8de doctor
upgr8de scan
upgr8de missing
upgr8de inspect "PCI\VEN_"
upgr8de search "Intel"
upgr8de lookup "PCI\\VEN_8086" --oem HP
upgr8de report --output inventory.json
```

The CLI uses `powershell.exe` and `Get-CimInstance` for local hardware inventory. Driver versions and providers are inventory facts, not guarantees of the newest available driver. Hardware identifiers can be sensitive: review reports before sharing.

## Roadmap

1. Inventory and diagnostics (MVP).
2. Hardware-ID parsing and official support portal routing (initial implementation complete); live OEM catalogue adapters still planned.
3. Installed-vs-available version comparisons with provenance, OS and architecture matching.
4. User-reviewed downloads with signature and hash verification, rollback guidance, and explicit confirmation.
5. Linux/macOS adapters, interactive terminal UI, packaging and expanded tests.

## Principles

Read-only by default. Never install unknown drivers or trust generic driver download sites. Prefer computer OEM support and Microsoft Windows Update. No telemetry and no elevated access required for ordinary inventory.

## Development

```powershell
py -m pip install -e .
py -m unittest discover -s tests -v
```

Apache-2.0 licensed.
