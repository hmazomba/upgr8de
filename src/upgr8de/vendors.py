"""Conservative hardware-ID parsing and official support routing.

These are manufacturer support landing pages, NOT verified driver download URLs.
No network access, downloads, or update-availability claims.
"""
from __future__ import annotations

import re

PCI_VENDORS = {
    "8086": ("Intel", "https://www.intel.com/content/www/us/en/support/detect.html"),
    "10DE": ("NVIDIA", "https://www.nvidia.com/Download/index.aspx"),
    "1002": ("AMD", "https://www.amd.com/en/support/download/drivers.html"),
    "1022": ("AMD", "https://www.amd.com/en/support/download/drivers.html"),
    "14E4": ("Broadcom", "https://www.broadcom.com/support"),
    "10EC": ("Realtek", "https://www.realtek.com/Download"),
    "168C": ("Qualcomm Atheros", "https://www.qualcomm.com/support"),
}
USB_VENDORS = {
    "046D": ("Logitech", "https://support.logi.com/"),
    "045E": ("Microsoft", "https://support.microsoft.com/windows"),
    "8087": ("Intel", "https://www.intel.com/content/www/us/en/support/detect.html"),
}
OEM_SUPPORT = {
    "dell": ("Dell", "https://www.dell.com/support/home"),
    "hp": ("HP", "https://support.hp.com/drivers"),
    "hewlett-packard": ("HP", "https://support.hp.com/drivers"),
    "lenovo": ("Lenovo", "https://pcsupport.lenovo.com/"),
    "asus": ("ASUS", "https://www.asus.com/support/"),
    "acer": ("Acer", "https://www.acer.com/support"),
    "msi": ("MSI", "https://www.msi.com/support"),
}


def parse_hardware_id(value: str) -> dict:
    """Parse PCI VEN/DEV or USB VID/PID only; do not infer device compatibility."""
    value = value.upper()
    pci = re.search(r"PCI\\\\VEN_([0-9A-F]{4})&DEV_([0-9A-F]{4})(?![0-9A-F])", value)
    if pci:
        return {"bus": "PCI", "vendor_id": pci.group(1), "device_id": pci.group(2)}
    usb = re.search(r"USB\\\\VID_([0-9A-F]{4})&PID_([0-9A-F]{4})(?![0-9A-F])", value)
    if usb:
        return {"bus": "USB", "vendor_id": usb.group(1), "device_id": usb.group(2)}
    return {"bus": "unknown", "vendor_id": None, "device_id": None}


def support_candidates(device: dict, oem: str | None = None) -> dict:
    """Return support entry points, not available updates."""
    parsed = parse_hardware_id(str(device.get("hardware_id") or ""))
    sources = []
    if oem:
        oem_lower = oem.casefold()
        for key, (name, url) in OEM_SUPPORT.items():
            if key in oem_lower:
                sources.append({"name": name, "url": url, "role": "computer_oem"})
                break
    vendors = PCI_VENDORS if parsed["bus"] == "PCI" else USB_VENDORS if parsed["bus"] == "USB" else {}
    vendor = vendors.get(parsed["vendor_id"])
    if vendor:
        sources.append({"name": vendor[0], "url": vendor[1], "role": "chip_vendor"})
    return {
        "name": device.get("name"),
        "hardware_id": device.get("hardware_id"),
        "parsed_id": parsed,
        "installed_version": device.get("driver_version"),
        "sources": sources,
        "update_status": "not_checked",
        "verified_package": None,
        "note": "Support portals only. Match exact model, OS, architecture, and hardware ID before installing.",
    }
