#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PyGATT backend
--------------

.. moduleauthor:: hbldh <henrik.blidh@nedomkull.com>
Created on 2016-04-02

"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import logging

from ctypes import create_string_buffer
try:
    from pygatt import BLEAddressType
    from pygatt.backends.gatttool import gatttool
    _import_failure = None
except ImportError as e:
    _import_failure = e

from pymetawear.exceptions import PyMetaWearException, PyMetaWearConnectionTimeout
from pymetawear.compat import range_
from pymetawear.backends import BLECommunicationBackend

__all__ = ["PyGattBackend"]

log = logging.getLogger(__name__)


class PyGattBackend(BLECommunicationBackend):
    """
    Backend using `pygatt <https://github.com/peplin/pygatt>`_
    for BLE communication.
    """

    def __init__(self, address, interface=None, async=True, timeout=None, debug=False):
        if _import_failure is not None:
            raise PyMetaWearException(
                "pygatt[GATTTOOL] package error: {0}".format(_import_failure))
        self._backend = None
        if debug:
            log.setLevel(logging.DEBUG)

        super(PyGattBackend, self).__init__(
            address, interface, async,
            gatttool.DEFAULT_CONNECT_TIMEOUT_S if timeout is None else timeout,
            debug)

    @property
    def requester(self):
        """Property handling the backend's device instance and its connection.

        :return: A connected ``pygatt`` BLE device instance.
        :rtype: :class:`pygatt.device.BLEDevice`

        """
        if self._requester is None:

            log.info("PyGattBackend: Creating new GATTToolBackend and starting GATTtool process...")
            self._backend = gatttool.GATTToolBackend(hci_device=self._interface)
            self._backend.start(reset_on_start=False)
            log.info("PyGattBackend: Connecting GATTTool...")
            self._requester = self._backend.connect(
                self._address, timeout=self._timeout, address_type=BLEAddressType.random)

            if not self.requester._connected:
                raise PyMetaWearConnectionTimeout(
                    "PyGattBackend: Could not establish a connection to {0}.".format(
                        self._address))

        return self._requester

    def disconnect(self):
        """Disconnect via the GATTTool process and terminate the
        interactive prompt.

        We can use the `stop` method since only one client can be
        connected to one GATTTool backend.

        """
        if self._backend is not None and self._backend:
            self._backend.stop()
        self._backend = None
        self._requester = None

    def _subscribe(self, characteristic_uuid, callback):
        return self.requester.subscribe(str(characteristic_uuid), callback)

    def read_gatt_char_by_uuid(self, characteristic):
        """Read the desired data from the MetaWear board using pygatt backend.

        :param pymetawear.mbientlab.metawear.core.GattCharacteristic
            characteristic: :class:`ctypes.POINTER` to a GattCharacteristic.
        :return: The read data.
        :rtype: str

        """
        return self.requester.char_read(str(self.get_uuid(characteristic)))

    def write_gatt_char_by_uuid(self, characteristic, command, length):
        """Write the desired data to the MetaWear board using pygatt backend.

        :param uuid.UUID characteristic: The UUID to the characteristic
            to write to.
        :param POINTER(c_ubyte) command: Data to send.
        :param int length: Number of characters in the command.

        """
        data_to_send = bytearray([command[i] for i in range_(length)])
        self.requester.char_write(str(self.get_uuid(characteristic)), data_to_send)

    def get_handle(self, characteristic_uuid, notify_handle=False):
        """Get handle from characteristic UUID.

        :param uuid.UUID characteristic_uuid: The UUID to find handle to.
        :param bool notify_handle:
        :return: Integer handle.
        :rtype: int

        """
        return self.requester.get_handle(characteristic_uuid) + int(notify_handle)

    def _response_2_string_buffer(self, response):
        return create_string_buffer(bytes(response), len(response))