import time
import usb
from usb.core import Device

# 0x18d1 used by devices in accessory mode but also pixels in unconfigured state
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


def get_unconfigured() -> list[Device]:
    res = usb.core.find(find_all=True, custom_match=is_unconfigured_scanner)
    return list(res)


def is_configured_scanner(dev: Device) -> bool:
    if not dev.idVendor in VENDORS:
        return False
    if dev.idProduct in CONFIGURED_PRODUCT_ID:
        return True

    return False


def get_configured() -> list[Device]:
    res = usb.core.find(find_all=True, custom_match=is_configured_scanner)
    return list(res)


def try_configure(dev: Device) -> bool:
    # command: get protocol version
    protocol_version = dev.ctrl_transfer(
        bmRequestType=0xc0, bRequest=51, data_or_wLength=2)
    protocol_version = (protocol_version[0] | protocol_version[1] << 8)
    if protocol_version == 0:
        print("Device does not support android accessory mode")
        return None
    print(f"Device talks version {protocol_version}")
    # command: transmit property information of this system to phone.
    # this enables Android to decide which app to open for example
    for i, data in enumerate((MANUFACTURE, MODEL, DESCRIPTION, VERSION, URI, SERIAL)):
        dev.ctrl_transfer(bmRequestType=0x40, bRequest=52, wIndex=i, data_or_wLength=data)

    # command: start accessory mode
    dev.ctrl_transfer(bmRequestType=0x40, bRequest=53) == 0

    old_bus = dev.bus
    old_addr = dev.address
    usb.util.dispose_resources(dev)

    attempts_left = 5
    while attempts_left:
        print(f"Waitring for reconnect {attempts_left}")
        configured = get_configured()
        for dev in configured:
            if dev.bus == old_bus and dev.address == old_addr:
                return dev

        time.sleep(1)
        attempts_left -= 1

    print("Device did not came back configured. Replug to try again.")
    return None


def main() -> None:
    configured = get_configured()
    print(f"Got {len(configured)} configured.")
    unconfigured = get_unconfigured()
    if unconfigured:
        print(f"Got {len(unconfigured)} unconfigured. Trying to start accessory mode ...")
        for dev in unconfigured:
            new_dev = try_configure(dev)
            if new_dev:
                configured.append(new_dev)

    dev = configured[0]
    print("Using first device")
    configuration = dev.get_active_configuration()
    interface = configuration[(0, 0)]
    endpoint_in = usb.util.find_descriptor(
            interface, custom_match= lambda e: usb.util.endpoint_direction(e.bEndpointAddress)
                    == usb.util.ENDPOINT_IN)

    while True:
        size_bytes = endpoint_in.read(2, timeout=-1)
        size = (size_bytes[0] << 8) | size_bytes[1]
        print(endpoint_in.read(size, timeout=-1).tobytes().decode('utf-8'))

if __name__ == "__main__":
    main()
