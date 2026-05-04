import argparse
import asyncio
import json
import logging
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import psutil
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse


DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8765
DEFAULT_INTERVAL_SECONDS = 5
DEFAULT_CONFIG_FILE = "monitor_config.json"
API_KEY_HEADER = "X-API-Key"
GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def bytes_to_gb(value: int | float) -> float:
    return round(float(value) / 1024 / 1024 / 1024, 2)


def bytes_to_mb(value: int | float) -> float:
    return round(float(value) / 1024 / 1024, 2)


def seconds_to_human(seconds: int | float) -> str:
    seconds = int(seconds)
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days}d {hours:02d}:{minutes:02d}:{seconds:02d}"


def get_lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def empty_to_none(value: Any) -> Any:
    if isinstance(value, str) and not value.strip():
        return None
    return value


def read_config_file(path: str) -> dict[str, Any]:
    if not path or not os.path.isfile(path):
        return {}

    with open(path, "r", encoding="utf-8") as config_file:
        data = json.load(config_file)

    if not isinstance(data, dict):
        raise RuntimeError(f"Config file must contain a JSON object: {path}")
    return data


def config_value(config: dict[str, Any], env_name: str, key: str, default: Any = None) -> Any:
    env_value = os.getenv(env_name)
    if env_value is not None:
        return empty_to_none(env_value)
    if key in config:
        return empty_to_none(config.get(key))
    return default


def clean_windows_device_name(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if ";" in text:
        text = text.split(";")[-1].strip()
    return text or None


def run_powershell_json(script: str, timeout: int = 4) -> Any | None:
    command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except Exception:
        return None

    if result.returncode != 0 or not result.stdout or not result.stdout.strip():
        return None

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def registry_subkey_names(key: Any) -> list[str]:
    names: list[str] = []
    index = 0
    winreg = __import__("winreg")
    while True:
        try:
            names.append(winreg.EnumKey(key, index))
        except OSError:
            break
        index += 1
    return names


def registry_values(key: Any) -> dict[str, Any]:
    values: dict[str, Any] = {}
    index = 0
    winreg = __import__("winreg")
    while True:
        try:
            name, value, _ = winreg.EnumValue(key, index)
            values[name] = value
        except OSError:
            break
        index += 1
    return values


def read_registry_devices_by_class(class_name: str) -> list[dict[str, Any]]:
    class_guids = {
        "Display": "{4d36e968-e325-11ce-bfc1-08002be10318}",
        "DiskDrive": "{4d36e967-e325-11ce-bfc1-08002be10318}",
    }
    expected_guid = class_guids.get(class_name, "").lower()
    try:
        winreg = __import__("winreg")
        root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Enum")
    except Exception:
        return []

    devices: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def walk(key: Any, path: str, depth: int) -> None:
        if depth > 4:
            return

        values = registry_values(key)
        class_value = str(values.get("Class") or "")
        class_guid = str(values.get("ClassGUID") or "").lower()
        if class_value == class_name or (expected_guid and class_guid == expected_guid):
            name = clean_windows_device_name(values.get("FriendlyName")) or clean_windows_device_name(values.get("DeviceDesc"))
            identity = (name or "", path)
            if name and identity not in seen:
                seen.add(identity)
                devices.append(
                    {
                        "name": name,
                        "manufacturer": clean_windows_device_name(values.get("Mfg")),
                        "class": values.get("Class"),
                        "instance_id": path,
                    }
                )

        for subkey_name in registry_subkey_names(key):
            try:
                subkey = winreg.OpenKey(key, subkey_name)
            except OSError:
                continue
            try:
                walk(subkey, f"{path}\\{subkey_name}" if path else subkey_name, depth + 1)
            finally:
                try:
                    winreg.CloseKey(subkey)
                except OSError:
                    pass

    try:
        walk(root, "", 0)
    finally:
        try:
            winreg.CloseKey(root)
        except OSError:
            pass

    return devices


@dataclass
class Settings:
    host: str
    port: int
    interval_seconds: int
    api_key: str | None
    ssl_certfile: str | None = None
    ssl_keyfile: str | None = None

    @property
    def ssl_enabled(self) -> bool:
        return bool(self.ssl_certfile and self.ssl_keyfile)


@dataclass
class StartupCheckResult:
    hardware: dict[str, Any] | None = None


@dataclass
class MetricState:
    latest: dict[str, Any] | None = None
    hardware: dict[str, Any] | None = None
    previous_net_total: Any | None = None
    previous_net_interfaces: dict[str, Any] | None = None
    previous_disk: dict[str, Any] | None = None
    previous_ts: float | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class WebSocketHub:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)

    async def broadcast(self, data: dict[str, Any]) -> None:
        message = json.dumps(data, ensure_ascii=False)
        async with self._lock:
            clients = list(self._clients)

        broken: list[WebSocket] = []
        for websocket in clients:
            try:
                await websocket.send_text(message)
            except Exception:
                broken.append(websocket)

        if broken:
            async with self._lock:
                for websocket in broken:
                    self._clients.discard(websocket)


def require_windows() -> None:
    if platform.system().lower() != "windows":
        raise RuntimeError("This monitor is designed for Windows servers only.")


def read_nvidia_gpu() -> list[dict[str, Any]]:
    if not shutil.which("nvidia-smi"):
        return []

    command = [
        "nvidia-smi",
        "--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu",
        "--format=csv,noheader,nounits",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3, check=False)
    except Exception:
        return []

    if result.returncode != 0:
        return []

    gpus: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 6:
            continue
        index, name, util, memory_used, memory_total, temperature = parts[:6]
        try:
            gpus.append(
                {
                    "index": int(index),
                    "name": name,
                    "utilization_percent": float(util),
                    "memory_used_mb": float(memory_used),
                    "memory_total_mb": float(memory_total),
                    "temperature_c": float(temperature),
                    "source": "nvidia-smi",
                }
            )
        except ValueError:
            continue
    return gpus


def read_windows_gpu_counter() -> list[dict[str, Any]]:
    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "$ErrorActionPreference='SilentlyContinue'; "
            "$c=(Get-Counter '\\GPU Engine(*)\\Utilization Percentage').CounterSamples | "
            "Where-Object {$_.CookedValue -gt 0} | "
            "Measure-Object -Property CookedValue -Sum; "
            "[math]::Round([double]$c.Sum,2)"
        ),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=4, check=False)
    except Exception:
        return []

    if result.returncode != 0:
        return []

    try:
        utilization = float(result.stdout.strip() or 0)
    except ValueError:
        return []

    return [
        {
            "index": 0,
            "name": "Windows GPU Engine",
            "utilization_percent": min(round(utilization, 2), 100.0),
            "memory_used_mb": None,
            "memory_total_mb": None,
            "temperature_c": None,
            "source": "windows-performance-counter",
        }
    ]


def read_windows_processors() -> list[dict[str, Any]]:
    data = run_powershell_json(
        "Get-CimInstance Win32_Processor | "
        "Select-Object DeviceID,Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed,LoadPercentage | "
        "ConvertTo-Json -Compress"
    )
    if data is None:
        return read_registry_cpu_processors()

    if isinstance(data, dict):
        data = [data]

    processors: list[dict[str, Any]] = []
    for index, processor in enumerate(data):
        processors.append(
            {
                "index": index,
                "device_id": processor.get("DeviceID"),
                "name": clean_windows_device_name(processor.get("Name")),
                "physical_cores": processor.get("NumberOfCores"),
                "logical_processors": processor.get("NumberOfLogicalProcessors"),
                "max_clock_mhz": processor.get("MaxClockSpeed"),
                "load_percent": processor.get("LoadPercentage"),
            }
        )
    return processors


def parse_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def memory_type_name(value: Any) -> str | None:
    type_code = parse_optional_int(value)
    names = {
        20: "DDR",
        21: "DDR2",
        22: "DDR2 FB-DIMM",
        24: "DDR3",
        26: "DDR4",
        27: "LPDDR",
        28: "LPDDR2",
        29: "LPDDR3",
        30: "LPDDR4",
        34: "DDR5",
        35: "LPDDR5",
    }
    return names.get(type_code)


def format_capacity_label(capacity_gb: float | None) -> str | None:
    if capacity_gb is None:
        return None
    if float(capacity_gb).is_integer():
        return f"{int(capacity_gb)}GB"
    return f"{capacity_gb:g}GB"


def build_memory_display_name(capacity_gb: float | None, memory_type: str | None, speed_mhz: Any, fallback: str | None = None) -> str | None:
    parts: list[str] = []
    capacity_label = format_capacity_label(capacity_gb)
    speed = parse_optional_int(speed_mhz)
    if capacity_label:
        parts.append(capacity_label)
    if memory_type:
        parts.append(memory_type)
    if speed:
        parts.append(f"{speed}MHz")
    if parts:
        return " ".join(parts)
    return fallback


def group_memory_capacity_labels(modules: list[dict[str, Any]]) -> str | None:
    groups: dict[str, int] = {}
    for module in modules:
        label = format_capacity_label(module.get("capacity_gb"))
        if not label:
            continue
        groups[label] = groups.get(label, 0) + 1
    if not groups:
        return None
    return " + ".join(f"{count} x {label}" for label, count in groups.items())


def build_memory_summary(modules: list[dict[str, Any]], fallback_total_gb: float | None) -> str | None:
    detected_total = sum(float(module.get("capacity_gb") or 0) for module in modules)
    total_label = format_capacity_label(detected_total if detected_total > 0 else fallback_total_gb)
    memory_types = {module.get("memory_type") for module in modules if module.get("memory_type")}
    speeds = {
        parse_optional_int(module.get("configured_clock_mhz") or module.get("speed_mhz"))
        for module in modules
        if parse_optional_int(module.get("configured_clock_mhz") or module.get("speed_mhz"))
    }
    capacity_group = group_memory_capacity_labels(modules)

    if total_label and len(memory_types) == 1 and len(speeds) == 1:
        summary = f"{total_label} {next(iter(memory_types))} {next(iter(speeds))}MHz"
        if capacity_group:
            summary += f" ({capacity_group})"
        return summary

    if total_label and len(memory_types) == 1:
        summary = f"{total_label} {next(iter(memory_types))}"
        if capacity_group:
            summary += f" ({capacity_group})"
        return summary

    if total_label and len(speeds) == 1:
        summary = f"{total_label} {next(iter(speeds))}MHz"
        if capacity_group:
            summary += f" ({capacity_group})"
        return summary

    module_names = [module.get("display_name") for module in modules if module.get("display_name")]
    if total_label and module_names:
        return f"{total_label} memory ({' + '.join(module_names)})"
    if total_label:
        return total_label
    return None


def read_registry_cpu_processors() -> list[dict[str, Any]]:
    try:
        winreg = __import__("winreg")
        root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor")
    except Exception:
        return []

    logical_entries: list[dict[str, Any]] = []
    try:
        subkey_names = sorted(registry_subkey_names(root), key=lambda name: int(name) if name.isdigit() else name)
        for subkey_name in subkey_names:
            try:
                subkey = winreg.OpenKey(root, subkey_name)
            except OSError:
                continue
            try:
                values = registry_values(subkey)
                logical_entries.append(
                    {
                        "index": int(subkey_name) if subkey_name.isdigit() else len(logical_entries),
                        "device_id": f"CPU{subkey_name}",
                        "name": clean_windows_device_name(values.get("ProcessorNameString")),
                        "identifier": clean_windows_device_name(values.get("Identifier")),
                        "vendor": clean_windows_device_name(values.get("VendorIdentifier")),
                        "physical_cores": None,
                        "logical_processors": None,
                        "max_clock_mhz": values.get("~MHz"),
                        "load_percent": None,
                        "source": "registry",
                    }
                )
            finally:
                try:
                    winreg.CloseKey(subkey)
                except OSError:
                    pass
    finally:
        try:
            winreg.CloseKey(root)
        except OSError:
            pass

    grouped: dict[tuple[str | None, str | None], dict[str, Any]] = {}
    for entry in logical_entries:
        key = (entry.get("name"), entry.get("vendor"))
        if key not in grouped:
            grouped[key] = {
                **entry,
                "index": len(grouped),
                "device_id": f"CPU{len(grouped)}",
                "logical_processors": 0,
                "logical_processor_entries": [],
            }
        grouped[key]["logical_processors"] += 1
        grouped[key]["logical_processor_entries"].append(entry["device_id"])

    processors = list(grouped.values())
    return processors


def read_memory_modules() -> dict[str, Any]:
    data = run_powershell_json(
        "Get-CimInstance Win32_PhysicalMemory | "
        "Select-Object BankLabel,DeviceLocator,Manufacturer,PartNumber,SerialNumber,Capacity,Speed,ConfiguredClockSpeed,MemoryType,SMBIOSMemoryType | "
        "ConvertTo-Json -Compress"
    )
    memory = psutil.virtual_memory()
    result: dict[str, Any] = {
        "total_gb": bytes_to_gb(memory.total),
        "modules": [],
        "module_details_available": False,
    }

    if data is None:
        result["message"] = "Physical memory module details are unavailable. Windows denied CIM/WMI access or no module data was returned."
        return result

    if isinstance(data, dict):
        data = [data]

    modules: list[dict[str, Any]] = []
    for index, module in enumerate(data):
        capacity = module.get("Capacity")
        capacity_gb = bytes_to_gb(capacity) if capacity is not None else None
        configured_clock_mhz = module.get("ConfiguredClockSpeed")
        speed_mhz = module.get("Speed")
        smbios_memory_type = parse_optional_int(module.get("SMBIOSMemoryType"))
        memory_type = memory_type_name(smbios_memory_type) or memory_type_name(module.get("MemoryType"))
        part_number = clean_windows_device_name(module.get("PartNumber"))
        display_name = build_memory_display_name(
            capacity_gb,
            memory_type,
            configured_clock_mhz or speed_mhz,
            part_number,
        )
        modules.append(
            {
                "index": index,
                "name": display_name,
                "display_name": display_name,
                "bank_label": module.get("BankLabel"),
                "device_locator": module.get("DeviceLocator"),
                "manufacturer": clean_windows_device_name(module.get("Manufacturer")),
                "part_number": part_number,
                "serial_number": clean_windows_device_name(module.get("SerialNumber")),
                "capacity_gb": capacity_gb,
                "memory_type": memory_type,
                "memory_type_code": parse_optional_int(module.get("MemoryType")),
                "smbios_memory_type": smbios_memory_type,
                "speed_mhz": speed_mhz,
                "configured_clock_mhz": configured_clock_mhz,
            }
        )

    summary = build_memory_summary(modules, result.get("total_gb"))
    result["name"] = summary
    result["display_name"] = summary
    result["summary"] = summary
    result["modules"] = modules
    result["module_details_available"] = bool(modules)
    return result


def read_gpu_names() -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    seen_names: set[str] = set()

    def add_device(device: dict[str, Any]) -> None:
        name = clean_windows_device_name(device.get("name"))
        if name and name.lower() not in seen_names:
            device["name"] = name
            seen_names.add(name.lower())
            device["index"] = len(devices)
            devices.append(device)

    nvidia_gpus = read_nvidia_gpu()
    for gpu in nvidia_gpus:
        add_device(
            {
                "name": gpu["name"],
                "source": "nvidia-smi",
            }
        )

    data = run_powershell_json(
        "Get-CimInstance Win32_VideoController | "
        "Select-Object Name,AdapterCompatibility,PNPDeviceID,AdapterRAM,VideoProcessor | "
        "ConvertTo-Json -Compress"
    )
    if data is not None:
        if isinstance(data, dict):
            data = [data]
        for gpu in data:
            add_device(
                {
                    "name": clean_windows_device_name(gpu.get("Name")),
                    "manufacturer": clean_windows_device_name(gpu.get("AdapterCompatibility")),
                    "adapter_ram_gb": bytes_to_gb(gpu.get("AdapterRAM")) if gpu.get("AdapterRAM") is not None else None,
                    "video_processor": clean_windows_device_name(gpu.get("VideoProcessor")),
                    "instance_id": gpu.get("PNPDeviceID"),
                    "source": "cim",
                }
            )

    for device in read_registry_devices_by_class("Display"):
        add_device(
            {
                "name": device["name"],
                "manufacturer": device.get("manufacturer"),
                "instance_id": device.get("instance_id"),
                "source": "registry",
            }
        )

    return devices


def read_disk_names() -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    seen_names: set[str] = set()

    def add_device(device: dict[str, Any]) -> None:
        name = clean_windows_device_name(device.get("name"))
        if name and name.lower() not in seen_names:
            device["name"] = name
            seen_names.add(name.lower())
            device["index"] = len(devices)
            devices.append(device)

    data = run_powershell_json(
        "Get-CimInstance Win32_DiskDrive | "
        "Select-Object Index,Model,Manufacturer,SerialNumber,InterfaceType,MediaType,Size,DeviceID | "
        "ConvertTo-Json -Compress"
    )
    if data is not None:
        if isinstance(data, dict):
            data = [data]
        for disk in data:
            add_device(
                {
                    "name": clean_windows_device_name(disk.get("Model")),
                    "manufacturer": clean_windows_device_name(disk.get("Manufacturer")),
                    "serial_number": clean_windows_device_name(disk.get("SerialNumber")),
                    "interface_type": disk.get("InterfaceType"),
                    "media_type": disk.get("MediaType"),
                    "size_gb": bytes_to_gb(disk.get("Size")) if disk.get("Size") is not None else None,
                    "device_id": disk.get("DeviceID"),
                    "source": "cim",
                }
            )

    for device in read_registry_devices_by_class("DiskDrive"):
        add_device(
            {
                "name": device["name"],
                "manufacturer": device.get("manufacturer"),
                "instance_id": device.get("instance_id"),
                "source": "registry",
            }
        )

    return devices


def collect_hardware_info() -> dict[str, Any]:
    processors = read_windows_processors()
    cpu_name = next((processor.get("name") for processor in processors if processor.get("name")), None)
    return {
        "cpu": {
            "name": cpu_name or platform.processor() or None,
            "processors": processors,
        },
        "memory": read_memory_modules(),
        "gpu": {
            "devices": read_gpu_names(),
        },
        "disk": {
            "devices": read_disk_names(),
        },
    }


def collect_gpu() -> dict[str, Any]:
    gpus = read_nvidia_gpu()
    if not gpus:
        gpus = read_windows_gpu_counter()

    if not gpus:
        return {
            "available": False,
            "message": "No NVIDIA GPU or Windows GPU performance counter data was available.",
            "devices": [],
        }

    average = round(sum(gpu["utilization_percent"] for gpu in gpus) / len(gpus), 2)
    return {"available": True, "average_utilization_percent": average, "devices": gpus}


def collect_disk_usage() -> dict[str, Any]:
    drives: dict[str, Any] = {}
    for partition in psutil.disk_partitions(all=False):
        mountpoint = partition.mountpoint
        drive_key = os.path.splitdrive(mountpoint)[0] or mountpoint.rstrip("\\/")
        if not drive_key:
            drive_key = mountpoint

        try:
            usage = psutil.disk_usage(mountpoint)
        except (OSError, PermissionError):
            drives[drive_key] = {
                "device": partition.device,
                "mountpoint": mountpoint,
                "file_system": partition.fstype,
                "options": partition.opts,
                "available": False,
            }
            continue

        drives[drive_key] = {
            "device": partition.device,
            "mountpoint": mountpoint,
            "file_system": partition.fstype,
            "options": partition.opts,
            "available": True,
            "total_gb": bytes_to_gb(usage.total),
            "used_gb": bytes_to_gb(usage.used),
            "free_gb": bytes_to_gb(usage.free),
            "used_percent": usage.percent,
        }
    return drives


def collect_disk_io(state: MetricState, now: float) -> dict[str, Any]:
    current = psutil.disk_io_counters(perdisk=True)
    previous = state.previous_disk
    interval = max(now - state.previous_ts, 0.001) if state.previous_ts else None
    state.previous_disk = current

    disks: dict[str, Any] = {}
    total_read_bps = 0.0
    total_write_bps = 0.0
    busy_values: list[float] = []

    for name, counters in current.items():
        previous_counters = previous.get(name) if previous else None
        if previous_counters and interval:
            read_bps = (counters.read_bytes - previous_counters.read_bytes) / interval
            write_bps = (counters.write_bytes - previous_counters.write_bytes) / interval
            busy_time = getattr(counters, "busy_time", None)
            previous_busy_time = getattr(previous_counters, "busy_time", None)
            busy_percent = None
            if busy_time is not None and previous_busy_time is not None:
                busy_percent = max(0.0, min(((busy_time - previous_busy_time) / (interval * 1000)) * 100, 100.0))
                busy_values.append(busy_percent)
        else:
            read_bps = 0.0
            write_bps = 0.0
            busy_percent = None

        total_read_bps += read_bps
        total_write_bps += write_bps
        disks[name] = {
            "read_mb_per_second": bytes_to_mb(read_bps),
            "write_mb_per_second": bytes_to_mb(write_bps),
            "busy_percent": round(busy_percent, 2) if busy_percent is not None else None,
        }

    return {
        "read_mb_per_second": bytes_to_mb(total_read_bps),
        "write_mb_per_second": bytes_to_mb(total_write_bps),
        "busy_percent": round(sum(busy_values) / len(busy_values), 2) if busy_values else None,
        "devices": disks,
    }


def collect_network(state: MetricState, now: float) -> dict[str, Any]:
    current = psutil.net_io_counters()
    current_interfaces = psutil.net_io_counters(pernic=True)
    stats = psutil.net_if_stats()
    addresses = psutil.net_if_addrs()
    previous = state.previous_net_total
    previous_interfaces = state.previous_net_interfaces
    interval = max(now - state.previous_ts, 0.001) if state.previous_ts else None
    state.previous_net_total = current
    state.previous_net_interfaces = current_interfaces

    if previous and interval:
        sent_bps = (current.bytes_sent - previous.bytes_sent) / interval
        recv_bps = (current.bytes_recv - previous.bytes_recv) / interval
    else:
        sent_bps = 0.0
        recv_bps = 0.0

    interfaces: dict[str, Any] = {}
    for name, counters in current_interfaces.items():
        previous_counters = previous_interfaces.get(name) if previous_interfaces else None
        if previous_counters and interval:
            interface_sent_bps = (counters.bytes_sent - previous_counters.bytes_sent) / interval
            interface_recv_bps = (counters.bytes_recv - previous_counters.bytes_recv) / interval
        else:
            interface_sent_bps = 0.0
            interface_recv_bps = 0.0

        interface_stats = stats.get(name)
        interface_addresses: list[str] = []
        for address in addresses.get(name, []):
            family_name = getattr(address.family, "name", str(address.family))
            if family_name in {"AF_INET", "AF_INET6"}:
                interface_addresses.append(address.address)

        interfaces[name] = {
            "sent_mb_per_second": bytes_to_mb(interface_sent_bps),
            "received_mb_per_second": bytes_to_mb(interface_recv_bps),
            "total_sent_gb": bytes_to_gb(counters.bytes_sent),
            "total_received_gb": bytes_to_gb(counters.bytes_recv),
            "is_up": interface_stats.isup if interface_stats else None,
            "speed_mbps": interface_stats.speed if interface_stats else None,
            "mtu": interface_stats.mtu if interface_stats else None,
            "addresses": interface_addresses,
        }

    return {
        "sent_mb_per_second": bytes_to_mb(sent_bps),
        "received_mb_per_second": bytes_to_mb(recv_bps),
        "total_sent_gb": bytes_to_gb(current.bytes_sent),
        "total_received_gb": bytes_to_gb(current.bytes_recv),
        "interfaces": interfaces,
    }


def collect_task_manager_counts() -> dict[str, Any]:
    process_count = 0
    thread_count = 0
    handle_count = 0
    handle_count_available = True

    for process in psutil.process_iter(["num_threads"]):
        process_count += 1
        try:
            thread_count += process.info.get("num_threads") or process.num_threads()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        try:
            handle_count += process.num_handles()
        except AttributeError:
            handle_count_available = False
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    boot_time = psutil.boot_time()
    uptime_seconds = max(0, int(time.time() - boot_time))
    return {
        "uptime_seconds": uptime_seconds,
        "uptime_human": seconds_to_human(uptime_seconds),
        "boot_time": datetime.fromtimestamp(boot_time, timezone.utc).isoformat(),
        "process_count": process_count,
        "thread_count": thread_count,
        "handle_count": handle_count if handle_count_available else None,
    }


def collect_metrics(state: MetricState) -> dict[str, Any]:
    now = time.time()
    memory = psutil.virtual_memory()
    cpu_usage_per_core = psutil.cpu_percent(interval=None, percpu=True)
    cpu_frequency = psutil.cpu_freq()
    if state.hardware is None:
        state.hardware = collect_hardware_info()
    hardware = state.hardware

    metrics = {
        "timestamp": utc_now_iso(),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "hardware": hardware,
        "system": collect_task_manager_counts(),
        "cpu": {
            "name": hardware["cpu"]["name"],
            "usage_percent": psutil.cpu_percent(interval=None),
            "logical_cores": psutil.cpu_count(logical=True),
            "physical_cores": psutil.cpu_count(logical=False),
            "frequency_mhz": round(cpu_frequency.current, 2) if cpu_frequency else None,
            "processors": hardware["cpu"]["processors"],
            "logical_processors": [
                {"index": index, "usage_percent": usage}
                for index, usage in enumerate(cpu_usage_per_core)
            ],
        },
        "memory": {
            "usage_percent": memory.percent,
            "total_gb": bytes_to_gb(memory.total),
            "used_gb": bytes_to_gb(memory.used),
            "available_gb": bytes_to_gb(memory.available),
            "free_gb": bytes_to_gb(memory.free),
        },
        "network": collect_network(state, now),
        "gpu": collect_gpu(),
        "disk": {
            "io": collect_disk_io(state, now),
            "drives": collect_disk_usage(),
        },
    }
    state.previous_ts = now
    return metrics


def is_authorized(api_key: str | None, provided_key: str | None) -> bool:
    return not api_key or provided_key == api_key


def build_app(settings: Settings, initial_hardware: dict[str, Any] | None = None) -> FastAPI:
    require_windows()
    state = MetricState()
    state.hardware = initial_hardware
    hub = WebSocketHub()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async def monitor_loop() -> None:
            while True:
                metrics = collect_metrics(state)
                async with state.lock:
                    state.latest = metrics
                await hub.broadcast(metrics)
                await asyncio.sleep(settings.interval_seconds)

        task = asyncio.create_task(monitor_loop())
        try:
            yield
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    app = FastAPI(title="Windows Server Monitor API", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=[API_KEY_HEADER, "Content-Type"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logging.info(
            "%s %s -> %s %.2fms from %s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request.client.host if request.client else "-",
        )
        return response

    @app.get("/")
    async def root() -> dict[str, Any]:
        return {
            "name": "Windows Server Monitor API",
            "metrics": "/api/metrics",
            "hardware": "/api/hardware",
            "websocket": "/ws/metrics",
            "docs": "/docs",
            "auth": f"Send {API_KEY_HEADER} header. ?api_key= is supported only for testing/trusted networks.",
        }

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "timestamp": utc_now_iso()}

    @app.get("/api/metrics")
    async def metrics(request: Request, api_key: str | None = Query(default=None)) -> JSONResponse:
        provided_key = request.headers.get(API_KEY_HEADER) or api_key
        if not is_authorized(settings.api_key, provided_key):
            raise HTTPException(status_code=401, detail="Invalid or missing API key.")

        async with state.lock:
            data = state.latest or collect_metrics(state)
            state.latest = data
        return JSONResponse(data)

    @app.get("/api/hardware")
    async def hardware(request: Request, api_key: str | None = Query(default=None)) -> JSONResponse:
        provided_key = request.headers.get(API_KEY_HEADER) or api_key
        if not is_authorized(settings.api_key, provided_key):
            raise HTTPException(status_code=401, detail="Invalid or missing API key.")

        async with state.lock:
            if state.hardware is None:
                state.hardware = collect_hardware_info()
            data = state.hardware
        return JSONResponse(data)

    @app.websocket("/ws/metrics")
    async def metrics_websocket(websocket: WebSocket, api_key: str | None = Query(default=None)) -> None:
        provided_key = websocket.headers.get(API_KEY_HEADER) or api_key
        if not is_authorized(settings.api_key, provided_key):
            await websocket.close(code=1008)
            logging.warning("WS /ws/metrics rejected from %s", websocket.client.host if websocket.client else "-")
            return

        await hub.connect(websocket)
        logging.info("WS /ws/metrics connected from %s", websocket.client.host if websocket.client else "-")
        try:
            async with state.lock:
                if state.latest:
                    await websocket.send_json(state.latest)
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            await hub.disconnect(websocket)
            logging.info("WS /ws/metrics disconnected from %s", websocket.client.host if websocket.client else "-")

    @app.get("/demo", response_class=HTMLResponse)
    async def demo() -> str:
        return f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>Windows Server Monitor</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 24px; background: #f6f7f9; color: #16181d; }}
    pre {{ padding: 16px; background: white; border: 1px solid #d9dde5; border-radius: 6px; overflow: auto; }}
  </style>
</head>
<body>
  <h1>Windows Server Monitor</h1>
  <pre id="out">Connecting...</pre>
  <script>
    const out = document.getElementById("out");
    const apiKeyEnabled = {"true" if settings.api_key else "false"};
    if (apiKeyEnabled) {{
      out.textContent = "Demo page is disabled while API key is enabled. Use /api/metrics with X-API-Key, or connect through your own same-origin proxy.";
    }} else {{
      const proto = location.protocol === "https:" ? "wss" : "ws";
      const ws = new WebSocket(proto + "://" + location.host + "/ws/metrics");
      ws.onmessage = event => {{
        out.textContent = JSON.stringify(JSON.parse(event.data), null, 2);
      }};
      ws.onclose = () => out.textContent = "WebSocket closed";
    }}
  </script>
</body>
</html>
"""

    return app


def parse_args() -> Settings:
    parser = argparse.ArgumentParser(description="Windows server metrics API and WebSocket broadcaster.")
    parser.add_argument("--config", default=os.getenv("MONITOR_CONFIG", DEFAULT_CONFIG_FILE), help="Path to JSON config file.")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument(
        "--interval",
        type=int,
        help="Metric collection and broadcast interval in seconds.",
    )
    parser.add_argument(
        "--api-key",
        help="Optional API key. Prefer X-API-Key; ?api_key= is only for testing/trusted networks.",
    )
    parser.add_argument(
        "--ssl-certfile",
        help="Optional SSL certificate file. Enables HTTPS/WSS when used with --ssl-keyfile.",
    )
    parser.add_argument(
        "--ssl-keyfile",
        help="Optional SSL private key file. Enables HTTPS/WSS when used with --ssl-certfile.",
    )
    args = parser.parse_args()

    config = read_config_file(args.config)

    host = args.host or config_value(config, "MONITOR_HOST", "host", DEFAULT_HOST)
    port = args.port if args.port is not None else int(config_value(config, "MONITOR_PORT", "port", DEFAULT_PORT))
    interval = args.interval if args.interval is not None else int(config_value(config, "MONITOR_INTERVAL_SECONDS", "interval_seconds", DEFAULT_INTERVAL_SECONDS))
    api_key = args.api_key if args.api_key is not None else config_value(config, "MONITOR_API_KEY", "api_key")
    ssl_certfile = args.ssl_certfile if args.ssl_certfile is not None else config_value(config, "MONITOR_SSL_CERTFILE", "ssl_certfile")
    ssl_keyfile = args.ssl_keyfile if args.ssl_keyfile is not None else config_value(config, "MONITOR_SSL_KEYFILE", "ssl_keyfile")

    if api_key is None and sys.stdin.isatty() and os.getenv("MONITOR_SKIP_KEY_PROMPT") != "1":
        print("")
        api_key = input("Set API key now? Press Enter to skip, or type a key: ").strip() or None

    return Settings(
        host=host,
        port=port,
        interval_seconds=max(interval, 1),
        api_key=api_key,
        ssl_certfile=ssl_certfile,
        ssl_keyfile=ssl_keyfile,
    )


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler("server_monitor.log", encoding="utf-8")],
    )


def validate_ssl_settings(settings: Settings) -> None:
    if bool(settings.ssl_certfile) != bool(settings.ssl_keyfile):
        raise RuntimeError("SSL requires both --ssl-certfile and --ssl-keyfile.")

    if not settings.ssl_enabled:
        return

    cert_path = os.path.abspath(settings.ssl_certfile or "")
    key_path = os.path.abspath(settings.ssl_keyfile or "")
    if not os.path.isfile(cert_path):
        raise RuntimeError(f"SSL certificate file was not found: {cert_path}")
    if not os.path.isfile(key_path):
        raise RuntimeError(f"SSL private key file was not found: {key_path}")

    settings.ssl_certfile = cert_path
    settings.ssl_keyfile = key_path


def print_feature_status(name: str, ok: bool, detail: str | None = None) -> None:
    status = f"{GREEN}[True]{RESET}" if ok else f"{RED}[False]{RESET}"
    if ok:
        print(f"{name}{status}" + (f" {detail}" if detail else ""))
    else:
        reason = detail or "Unable to read this feature."
        print(f"{name}{status} {RED}{reason}{RESET}")


def run_startup_feature_checks(settings: Settings) -> StartupCheckResult:
    print("")
    print(f"{CYAN}Startup feature checks{RESET}")
    result = StartupCheckResult()

    try:
        cpu_total = psutil.cpu_percent(interval=None)
        cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)
        print_feature_status("CPU", bool(cpu_per_core), f"total={cpu_total}%, logical={len(cpu_per_core)}")
    except Exception as exc:
        print_feature_status("CPU", False, str(exc))

    try:
        memory = psutil.virtual_memory()
        print_feature_status("Memory", memory.total > 0, f"total={bytes_to_gb(memory.total)}GB, available={bytes_to_gb(memory.available)}GB")
    except Exception as exc:
        print_feature_status("Memory", False, str(exc))

    try:
        hardware = collect_hardware_info()
        result.hardware = hardware
    except Exception as exc:
        hardware = None
        print_feature_status("HardwareInfo", False, str(exc))

    if hardware:
        cpu_name = hardware["cpu"].get("name")
        print_feature_status("CPUName", bool(cpu_name), cpu_name or "CPU name is unavailable from CIM/registry/platform fallback.")

        memory_hardware = hardware["memory"]
        if memory_hardware.get("module_details_available"):
            print_feature_status("MemoryModules", True, f"{len(memory_hardware.get('modules', []))} module(s)")
        else:
            print_feature_status("MemoryModules", False, memory_hardware.get("message", "Memory module model details are unavailable."))

        gpu_names = hardware["gpu"].get("devices", [])
        print_feature_status("GPUNames", bool(gpu_names), f"{len(gpu_names)} device(s)" if gpu_names else "No GPU names were found through nvidia-smi, CIM, or registry.")

        disk_names = hardware["disk"].get("devices", [])
        print_feature_status("DiskNames", bool(disk_names), f"{len(disk_names)} device(s)" if disk_names else "No disk device names were found through CIM or registry.")

    try:
        gpu = collect_gpu()
        print_feature_status("GPUUsage", bool(gpu.get("available")), f"{len(gpu.get('devices', []))} device(s)" if gpu.get("available") else gpu.get("message"))
    except Exception as exc:
        print_feature_status("GPUUsage", False, str(exc))

    try:
        drives = collect_disk_usage()
        print_feature_status("DiskCapacity", bool(drives), f"{len(drives)} mounted volume(s)" if drives else "No mounted disk volumes were returned by Windows.")
    except Exception as exc:
        print_feature_status("DiskCapacity", False, str(exc))

    try:
        disk_state = MetricState()
        disk_io = collect_disk_io(disk_state, time.time())
        disk_devices = disk_io.get("devices", {})
        print_feature_status("DiskReadWrite", bool(disk_devices), f"{len(disk_devices)} device(s)" if disk_devices else "No disk IO counters were returned by Windows.")
    except Exception as exc:
        print_feature_status("DiskReadWrite", False, str(exc))

    try:
        network_state = MetricState()
        network = collect_network(network_state, time.time())
        interfaces = network.get("interfaces", {})
        print_feature_status("NetworkUpDown", bool(interfaces), f"{len(interfaces)} interface(s)" if interfaces else "No network interfaces were returned by Windows.")
    except Exception as exc:
        print_feature_status("NetworkUpDown", False, str(exc))

    try:
        counts = collect_task_manager_counts()
        print_feature_status("TaskManagerCounts", counts["process_count"] > 0, f"processes={counts['process_count']}, threads={counts['thread_count']}")
        print_feature_status("Handles", counts.get("handle_count") is not None, f"handles={counts.get('handle_count')}" if counts.get("handle_count") is not None else "Handle count is unavailable in this Python/Windows environment.")
        print_feature_status("Uptime", counts["uptime_seconds"] >= 0, counts["uptime_human"])
    except Exception as exc:
        print_feature_status("TaskManagerCounts", False, str(exc))

    print_feature_status("HTTPAPI", True, "HTTP runs over TCP.")
    print_feature_status("WebSocketBroadcast", True, "WebSocket runs over TCP after an HTTP Upgrade.")
    print_feature_status(
        "SSL",
        settings.ssl_enabled,
        "HTTPS/WSS enabled." if settings.ssl_enabled else "No certificate/key configured; API will run as HTTP/WS.",
    )
    print_feature_status("APIKey", bool(settings.api_key), "enabled" if settings.api_key else "No key was configured; requests are open.")
    print_feature_status("RequestLog", True, os.path.abspath("server_monitor.log"))
    print("")

    return result


def print_startup_links(settings: Settings) -> None:
    lan_ip = get_lan_ip()
    auth_hint = "enabled" if settings.api_key else "disabled"
    http_scheme = "https" if settings.ssl_enabled else "http"
    ws_scheme = "wss" if settings.ssl_enabled else "ws"
    print("")
    print("Windows Server Monitor API started")
    print(f"Local API:      {http_scheme}://127.0.0.1:{settings.port}/api/metrics")
    print(f"LAN API:        {http_scheme}://{lan_ip}:{settings.port}/api/metrics")
    print(f"Hardware API:   {http_scheme}://{lan_ip}:{settings.port}/api/hardware")
    print(f"WebSocket:      {ws_scheme}://{lan_ip}:{settings.port}/ws/metrics")
    print(f"Demo page:      {http_scheme}://127.0.0.1:{settings.port}/demo")
    print(f"Docs:           {http_scheme}://127.0.0.1:{settings.port}/docs")
    print(f"Protocol:       {'HTTPS and WSS' if settings.ssl_enabled else 'HTTP and WebSocket'} over TCP, not UDP")
    print(f"Interval:       {settings.interval_seconds}s")
    print(f"API key:        {auth_hint}")
    print(f"SSL:            {'enabled' if settings.ssl_enabled else 'disabled'}")
    if settings.ssl_enabled:
        print(f"SSL cert:       {settings.ssl_certfile}")
        print(f"SSL key:        {settings.ssl_keyfile}")
    print(f"Request log:    {os.path.abspath('server_monitor.log')}")
    print("")


def main() -> None:
    configure_logging()
    settings = parse_args()
    validate_ssl_settings(settings)
    check_result = run_startup_feature_checks(settings)
    print_startup_links(settings)
    app = build_app(settings, initial_hardware=check_result.hardware)
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level="info",
        access_log=False,
        ssl_certfile=settings.ssl_certfile,
        ssl_keyfile=settings.ssl_keyfile,
    )


if __name__ == "__main__":
    main()










