import logging

from usb_barcode.usb_barcode import BarcodeScannerComms


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    barcode_scanner = BarcodeScannerComms()
    # run() is blocking and never returns
    for s in barcode_scanner.run():
        print(repr(s))


if __name__ == "__main__":
    main()
