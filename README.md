# Python Module for Android USB barcode scanner

Created for [Unifest 2022]

## Usage

Either import as module (see [`__main__.py`](usb_barcode/__main__.py) for example) or execute `usb-barcode` command.

Please note that you probably need to configure your udev system to allow access to raw usb devices.
Otherwise you need to run the python process with elevated privileges.

## A note on recognizing devices

We need a list of usb vendor ids to recognize android phones.
These need to be added to [`usb_barcode.py`](usb_barcode/usb_barcode.py).

[Unifest 2022]: https://unifest-karlsruhe.de/