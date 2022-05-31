from abc import ABC
from dataclasses import dataclass


@dataclass
class ScannerEvent(ABC):
    device_id: str


@dataclass
class DeviceConnectedEvent(ScannerEvent):
    pass


@dataclass
class DeviceDisconnectedEvent(ScannerEvent):
    pass


@dataclass
class BarcodeEvent(ScannerEvent):
    raw_data: bytes
    string_data: str
