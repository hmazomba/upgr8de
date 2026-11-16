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
- Query configured Windows Update Agent for applicable, not-installed driver offers without downloading or installing.
- Match offers to local devices using exact hardware IDs and compare strictly numeric driver versions, flagging ambiguous matches for manual review.

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
upgr8de updates
upgr8de updates --json
upgr8de check
upgr8de check --json
```

The CLI uses `powershell.exe` and `Get-CimInstance` for local hardware inventory. Driver versions and providers are inventory facts, not guarantees of the newest available driver. Hardware identifiers can be sensitive: review reports before sharing.

## Roadmap

1. Inventory and diagnostics (MVP).
2. Hardware-ID parsing and official support portal routing (initial implementation complete); live OEM catalogue adapters still planned.
3. Windows Update Agent driver offer discovery, exact hardware-ID matching and numeric version comparison (implemented). Live independent OEM catalogue verification remains planned.
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

## Live update detection

`upgr8de updates` calls Windows Update Agent's read-only `Search` API with `IsInstalled=0 and Type='Driver' and IsHidden=0`. It uses your system's configured Windows Update or WSUS service; the scan may use the network and take several minutes. `--json` includes update identifiers, revision and metadata. An offered driver is **not proof of a newer version** and may not be a complete list of OEM updates. No packages are downloaded or installed. A scan failure is reported as an error rather than as zero updates.

## Device-to-offer matching

`upgr8de check` inventories local PnP hardware IDs, retrieves applicable driver offers from the configured Windows Update service, then assigns an offer to a device only when exactly one device has an identical hardware ID. Missing and ambiguous IDs remain unmatched. `version_comparison` can be `newer`, `same`, `older`, or `unknown` and only compares numeric dotted versions. **A newer number is not proof of a safer or more compatible driver.** All matches are for manual review; the tool does not download, verify package signatures, or install. Windows Update is not a complete manufacturer catalogue, and OEM-specific adapters are not yet implemented.

## Phase 5: Offline OEM catalogue review and file integrity

This phase adds **local catalogue ingestion**, not live Dell/HP/Lenovo API integration. Catalogue JSON must be obtained and reviewed independently. An HTTPS URL in metadata is **not** proof of an official vendor source. No network downloads or installation occur.

Example schema (`catalogue.json`):

```json
{"schema_version":1,"packages":[{"vendor":"Example OEM","model":"Model X","hardware_id":"PCI\\VEN_8086&DEV_1234","version":"2.0","os":"Windows 11","architecture":"x64","url":"https://example.com/driver.zip","sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}]}
```

```powershell
upgr8de catalogue catalogue.json --model "Model X" --os "Windows 11" --arch x64
upgr8de verify .\driver.zip --sha256 <expected-64-character-sha256>
```

Only exact model, OS, architecture and hardware-ID matches are reported. Results remain **unverified catalogue entries**. `verify` checks local SHA-256 bytes only; it does not verify Authenticode signatures, publisher trust, or installation safety. The example hash and URL are placeholders, not real driver metadata. Live OEM catalogue adapters, trusted vendor source validation, package download, signature verification and rollback remain future work.

## Phase 6: Local Authenticode inspection

On Windows, inspect a downloaded driver package **without running it**:

```powershell
upgr8de signature .\driver.exe
upgr8de verify .\driver.exe --sha256 YOUR_EXPECTED_SHA256
```

`signature` calls Windows `Get-AuthenticodeSignature` and reports status, certificate subject and thumbprint. A `Valid` result means Windows accepted the file's Authenticode signature under local trust policy; **it does not prove the signer is an approved OEM**, that the file is safe, or that it matches the device. Check publisher against independently sourced OEM information. Unsigned or invalid signatures return exit code 2. No installation occurs.

**Remaining work:** Live authenticated OEM catalogue adapters (Dell/HP/Lenovo), safe vendor-specific download endpoints, allowlisted redirects, verified release metadata, OS/build applicability, rollback strategy and Windows integration testing. Avoid downloading from arbitrary URLs in untrusted catalogue JSON.

## Phase 7: Automatic OEM identity

```powershell
upgr8de oem
```

Uses read-only Windows CIM queries to identify manufacturer, model, SKU, OS version/build and architecture. Reports known official support portal links. It deliberately does **not** collect serial numbers or device UUIDs. This is a prerequisite for trustworthy OEM-specific catalogue queries, **not** a live catalogue adapter. Driver downloads and installation remain disabled.

## Phase 8: Live HP OEM catalogue metadata (opt-in)

On supported HP Windows systems, install the **HP Client Management Script Library (CMSL)** separately from HP's official distribution. upgr8de does not install dependencies automatically. Then run:

```powershell
upgr8de oem
upgr8de oem-catalog --provider hp
```

This calls HP CMSL `Get-SoftpaqList` for the current platform and displays returned SoftPaq metadata. It can contact HP's services; no SoftPaq packages are downloaded or installed by upgr8de. Metadata fields depend on CMSL version. Treat the result as a catalogue listing, **not** a verified driver update or device-level compatibility decision. No silent fallback to generic driver sites.

Dell's current commercial client catalogues use CAB index/platform catalogues, while Lenovo's Update Retriever uses its own repository/update metadata workflow. Neither is wired up as a live adapter yet. Secure package downloading, trusted metadata verification and rollback remain pending.

## Phase 9: Standalone OEM catalogue direction

**No vendor utility installation required.** The live `oem-catalog` command now supports a direct Dell catalogue pilot:

```powershell
upgr8de oem-catalog --provider dell
```

The command retrieves Dell's official `DriverPackCatalog.cab` from `downloads.dell.com`, uses Windows' built-in `expand.exe`, and attempts exact model-name matching against the catalogue. This is **model-level deployment pack discovery**, not device-by-device driver matching or verified individual updates. Dell catalogue structures may use system IDs rather than full model names; some systems can therefore return zero matches. No packages are downloaded or installed. HP CMSL is no longer required by the active CLI. HP and Lenovo direct catalogue adapters and verified package downloads are pending. The legacy `hp.py` module is unused and should be removed in a cleanup.
