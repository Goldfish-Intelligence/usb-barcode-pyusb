from abc import ABC, abstractmethod


class ScannerEvent(ABC):
    @abstractmethod
    def get_device_id(self) -> str:
        """
        Identification string determined by USB port
        """
        pass

    @abstractmethod
    def as_dict(self) -> dict:
        pass


class DeviceConnectedEvent(ScannerEvent):
    def __init__(self, device_id):
        self._device_id = device_id

    def get_device_id(self) -> str:
        return self._device_id

    def as_dict(self) -> dict:
        return {"device_id": self._device_id}


class DeviceDisconnectedEvent(ScannerEvent):
    def __init__(self, device_id):
        self._device_id = device_id

    def get_device_id(self) -> str:
        return self._device_id

    def as_dict(self) -> dict:
        return {"device_id": self._device_id}


class BarcodeEvent(ScannerEvent):
    def __init__(self, device_id, raw_data: bytearray, string_data: str):
        self._device_id = device_id
        self._raw_data = raw_data
        self._string_data = string_data

    def get_device_id(self) -> str:
        return self._device_id

    def get_raw_data(self) -> str:
        return self._raw_data

    def get_string_data(self) -> str:
        return self._string_data

    def as_dict(self) -> dict:
        return {"device_id": self._device_id, "raw_data": self._raw_data, "string_data": self._string_data}
