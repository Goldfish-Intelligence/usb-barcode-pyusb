import base64
import json
import logging
import multiprocessing as mp
from pprint import pprint
from typing import Generator

import pyudev
import usb
from usb.core import Device

from usb_barcode.barcode_event import (BarcodeEvent, DeviceConnectedEvent,
                                       DeviceDisconnectedEvent)

# see: https://source.android.com/devices/accessories/aoa

# 0x18d1 used by devices in accessory mode but also pixel or nexus devices in unconfigured state
VENDORS = [0x18d1]

CONFIGURED_PRODUCT_ID = [0x2D00, 0x2D01]

MANUFACTURE = 'Goldfish-Intelligence'
MODEL = 'CompanionScanner'
DESCRIPTION = 'UnifestWhoopWhoop'
VERSION = 1
URI = 'https://unifest-karlsruhe.de/'
SERIAL = 'none'


def is_unconfigured_scanner(dev: Device) -> bool:
    if not dev.idVendor in VENDORS:
        return False
    if dev.idProduct in CONFIGURED_PRODUCT_ID:
        return False

    return True


def is_configured_scanner(dev: Device) -> bool:
    if not dev.idVendor in VENDORS:
        return False
    if dev.idProduct in CONFIGURED_PRODUCT_ID:
        return True

    return False


def _try_configure(dev: Device) -> bool:
    # command: get protocol version
    protocol_version = dev.ctrl_transfer(
        bmRequestType=0xc0, bRequest=51, data_or_wLength=2)
    protocol_version = (protocol_version[0] | protocol_version[1] << 8)
    if protocol_version == 0:
        logging.error(
            f"{repr(dev)}: Device does not support android accessory mode, {dev}")
        return
    logging.debug(
        f"{repr(dev)}: Device talks AOA protocol version {protocol_version}")
    # command: transmit property information of this system to phone.
    # this enables Android to decide which app to open for example
    for i, data in enumerate((MANUFACTURE, MODEL, DESCRIPTION, VERSION, URI, SERIAL)):
        dev.ctrl_transfer(bmRequestType=0x40, bRequest=52,
                          wIndex=i, data_or_wLength=data)

    # command: start accessory mode
    dev.ctrl_transfer(bmRequestType=0x40, bRequest=53) == 0

    usb.util.dispose_resources(dev)


class BarcodeScannerComms:
    def __init__(self) -> None:
        self._eventbus = mp.Queue()

    def _device_loop(self, dev: Device, kernel_path: str):
        self._eventbus.put(DeviceConnectedEvent(kernel_path))

        try:
            configuration = dev.get_active_configuration()
            interface = configuration[(0, 0)]
            endpoint_in = usb.util.find_descriptor(
                interface, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)

            while True:
                size_bytes = endpoint_in.read(2, timeout=-1)
                size = (size_bytes[0] << 8) | size_bytes[1]
                payload = json.loads(endpoint_in.read(
                    size, timeout=-1).tobytes().decode('utf-8'))
                raw_data = None
                if "rawBase64" in payload:
                    raw_data = payload["rawBase64"]
                    raw_data = base64.standard_b64decode(raw_data)
                raw_string = None
                if "rawUTF8" in payload:
                    raw_string = payload["rawUTF8"]
                self._eventbus.put(BarcodeEvent(
                    kernel_path, raw_data=raw_data, string_data=raw_string))
        # todo: reread error handling an device disconnects
        except usb.core.USBError:
            self._eventbus.put(DeviceDisconnectedEvent(kernel_path))

    def _connect_usb(self, bus_num: int, dev_num: int, kernel_path: str):
        new_device = usb.core.find(bus=bus_num, address=dev_num)
        if not new_device:
            # race condition between bind event and pyusb query
            logging.warn(
                f'<{bus_num}:{dev_num}>: Not found by pyusb. Flaky usb connection?')
            return

        if is_unconfigured_scanner(new_device):
            logging.info(
                f"{repr(new_device)}: Device not in accessory mode. reconfigure...")
            # will come back again via udev event
            _try_configure(new_device)
            return
        elif is_configured_scanner(new_device):
            p = mp.Process(target=self._device_loop, args=(new_device, kernel_path, ))
            p.start()
        else:
            logging.debug(
                f'{repr(new_device)}: Vendor / Product ID not in recognition list.')

    def _handle_device_connect(self, udev_device: pyudev.Device):
        if udev_device.device_type != 'usb_device':  # 'usb' filter also provides 'usb_interface'
            return

        # BUSNUM and DEVNUM (libusb lingo: address) used by pyusb for device identity
        bus_num, dev_num = (int(udev_device.get('BUSNUM')),
                            int(udev_device.get('DEVNUM')))
        if udev_device.action == 'bind':
            logging.info(f'<{bus_num}:{dev_num}>: udev reported usb bind')
            self._connect_usb(bus_num, dev_num, udev_device.device_path)

        if udev_device.action == 'unbind':
            logging.debug(
                f'<{bus_num}:{dev_num}>: udev reported usb unbind (should be detected by pyusb as well)')

    def _monitor_thread(self):
        udev_context = pyudev.Context()
        usb_monitor = pyudev.Monitor.from_netlink(udev_context)
        usb_monitor.filter_by('usb')
        for udev_device in iter(usb_monitor.poll, None):
            self._handle_device_connect(udev_device)

    def run(self) -> Generator[BarcodeEvent, None, None]:
        monitor_thread = mp.Process(target=self._monitor_thread)
        monitor_thread.start()

        while True:
            try:
                yield self._eventbus.get()
            except ValueError:
                monitor_thread.kill()
                return  # this represents shutting down, which is not implemented. As such run() never returns atm
