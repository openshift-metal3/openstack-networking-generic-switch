#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import json
import re

from oslo_log import log as logging

from networking_generic_switch.devices.netconf_devices import netconf_switch
from networking_generic_switch.netconf_models import constants as ncconst
from networking_generic_switch.netconf_models.openconfig import (
    constants as oc_constants)
from networking_generic_switch.netconf_models.openconfig.interfaces \
    .interfaces import Interfaces
from networking_generic_switch.netconf_models.openconfig \
    .network_instance.network_instance import NetworkInstances
from networking_generic_switch.netconf_models.openconfig.vlan \
    .vlan import VlanSwitchedVlan

LOG = logging.getLogger(__name__)


class NetconfOpenConfigSwitch(netconf_switch.NetconfSwitch):
    """NETCONF OpenConfig switch driver.

    Manages network and port operations using OpenConfig YANG models
    over NETCONF transport.  Callable class variables (ADD_NETWORK,
    DELETE_NETWORK, ADD_NETWORK_TO_TRUNK, REMOVE_NETWORK_FROM_TRUNK,
    PLUG_PORT_TO_NETWORK, DELETE_PORT, ENABLE_PORT, DISABLE_PORT) build
    OpenConfig model objects that the base class serialises to XML and
    pushes via ``send_config_to_device``.
    """

    def __init__(self, device_cfg, *args, **kwargs):
        super().__init__(device_cfg, *args, **kwargs)

        self._network_instance = self.ngs_config.get(
            'ngs_openconfig_network_instance', 'default')

        port_id_re_sub_raw = self.ngs_config.get(
            'ngs_port_id_re_sub', '')
        if isinstance(port_id_re_sub_raw, dict):
            self._port_id_re_sub = port_id_re_sub_raw
        elif port_id_re_sub_raw:
            self._port_id_re_sub = json.loads(port_id_re_sub_raw)
        else:
            self._port_id_re_sub = {}

        disabled_raw = self.ngs_config.get(
            'ngs_openconfig_disabled_properties', '')
        if isinstance(disabled_raw, list):
            self._disabled_properties = disabled_raw
        elif disabled_raw:
            self._disabled_properties = [
                p.strip() for p in disabled_raw.split(',')]
        else:
            self._disabled_properties = []

    def _port_id_resub(self, port_id):
        """Apply configured regex substitution to a port ID.

        Some devices do not use the port description from LLDP in
        NETCONF configuration.  When ``ngs_port_id_re_sub`` is set
        the port_id is modified before building device configuration.

        :param port_id: Original port identifier from local link info.
        :returns: Possibly modified port identifier.
        """
        if self._port_id_re_sub:
            pattern = self._port_id_re_sub.get('pattern')
            repl = self._port_id_re_sub.get('repl')
            if pattern and repl is not None:
                port_id = re.sub(pattern, repl, port_id)
        return port_id

    # ------------------------------------------------------------------
    # Callable class variables invoked by NetconfSwitch dispatch methods.
    # Wrapped in staticmethod() so that attribute access on an instance
    # returns the raw function rather than a bound method — the base
    # class passes ``self`` explicitly.
    # ------------------------------------------------------------------

    def _add_network(self, segmentation_id, network_name, **kwargs):
        """Build OpenConfig objects to create a VLAN.

        :param segmentation_id: VLAN ID.
        :param network_name: Name to assign to the VLAN on the device.
        :returns: list of OpenConfig model objects.
        """
        segmentation_id = int(segmentation_id)
        net_instances = NetworkInstances()
        net_inst = net_instances.add(self._network_instance)
        _vlan = net_inst.vlans.add(segmentation_id)
        _vlan.config.name = network_name
        _vlan.config.status = oc_constants.VLAN_ACTIVE
        return [net_instances]

    def _delete_network(self, segmentation_id, network_name, **kwargs):
        """Build OpenConfig objects to remove a VLAN.

        Not all devices support outright VLAN removal, so the VLAN is
        also set to SUSPENDED with a ``neutron-DELETED-`` name prefix
        as a fallback.

        :param segmentation_id: VLAN ID.
        :param network_name: Original network name (unused in the
            delete payload but accepted for signature compatibility).
        :returns: list of OpenConfig model objects.
        """
        segmentation_id = int(segmentation_id)
        net_instances = NetworkInstances()
        net_inst = net_instances.add(self._network_instance)
        _vlan = net_inst.vlans.remove(segmentation_id)
        _vlan.config.name = f'neutron-DELETED-{segmentation_id}'
        _vlan.config.status = oc_constants.VLAN_SUSPENDED
        return [net_instances]

    def _add_network_to_trunk(self, segmentation_id, trunk_ports, **kwargs):
        """Build OpenConfig objects to tag trunk ports with a VLAN.

        When *physnet_vlans* is provided the complete set of trunk VLANs
        is written with ``operation="replace"`` so that the device
        converges to the desired state.  Falls back to a single-VLAN
        merge when *physnet_vlans* is ``None``.

        :param segmentation_id: VLAN ID to add to trunk ports.
        :param trunk_ports: List of switch interface names.
        :param physnet_vlans: (kwarg) Complete set of VLAN IDs on the
            physical network, or ``None``.
        :returns: list of OpenConfig model objects.
        """
        physnet_vlans = kwargs.get('physnet_vlans')
        segmentation_id = int(segmentation_id)
        ifaces = Interfaces()
        for port in trunk_ports:
            port = self._port_id_resub(port)
            iface = ifaces.add(port)
            switched_vlan = VlanSwitchedVlan()
            switched_vlan.config.interface_mode = (
                oc_constants.VLAN_MODE_TRUNK)
            if physnet_vlans is not None:
                switched_vlan.config.operation = (
                    ncconst.NetconfEditConfigOperation.REPLACE)
                for vlan_id in sorted(physnet_vlans):
                    switched_vlan.config.trunk_vlans = vlan_id
            else:
                switched_vlan.config.trunk_vlans = segmentation_id
            iface.ethernet.switched_vlan = switched_vlan
        return [ifaces]

    def _remove_network_from_trunk(self, segmentation_id, trunk_ports,
                                   **kwargs):
        """Build OpenConfig objects to untag trunk ports from a VLAN.

        When *physnet_vlans* is provided the complete set (which already
        excludes the deleted VLAN) is written with
        ``operation="replace"``.  Falls back to per-element
        ``operation="remove"`` when *physnet_vlans* is ``None``.

        :param segmentation_id: VLAN ID to remove from trunk ports.
        :param trunk_ports: List of switch interface names.
        :param physnet_vlans: (kwarg) Complete set of VLAN IDs on the
            physical network after deletion, or ``None``.
        :returns: list of OpenConfig model objects.
        """
        physnet_vlans = kwargs.get('physnet_vlans')
        segmentation_id = int(segmentation_id)
        ifaces = Interfaces()
        for port in trunk_ports:
            port = self._port_id_resub(port)
            iface = ifaces.add(port)
            switched_vlan = VlanSwitchedVlan()
            switched_vlan.config.interface_mode = (
                oc_constants.VLAN_MODE_TRUNK)
            if physnet_vlans is not None:
                switched_vlan.config.operation = (
                    ncconst.NetconfEditConfigOperation.REPLACE)
                for vlan_id in sorted(physnet_vlans):
                    switched_vlan.config.trunk_vlans = vlan_id
            else:
                switched_vlan.config.trunk_vlans.remove(segmentation_id)
            iface.ethernet.switched_vlan = switched_vlan
        return [ifaces]

    def _plug_port_to_network(self, port_id, segmentation_id, **kwargs):
        """Build OpenConfig objects to assign an access VLAN to a port.

        :param port_id: Switch interface name.
        :param segmentation_id: VLAN ID.
        :returns: list of OpenConfig model objects.
        """
        segmentation_id = int(segmentation_id)
        port_id = self._port_id_resub(port_id)

        ifaces = Interfaces()
        iface = ifaces.add(port_id)

        switched_vlan = VlanSwitchedVlan()
        switched_vlan.config.operation = (
            ncconst.NetconfEditConfigOperation.REPLACE)
        switched_vlan.config.interface_mode = oc_constants.VLAN_MODE_ACCESS
        switched_vlan.config.access_vlan = segmentation_id
        iface.ethernet.switched_vlan = switched_vlan

        return [ifaces]

    def _delete_port(self, port_id, segmentation_id, **kwargs):
        """Build OpenConfig objects to remove VLAN config from a port.

        :param port_id: Switch interface name.
        :param segmentation_id: VLAN ID.
        :returns: list of OpenConfig model objects.
        """
        port_id = self._port_id_resub(port_id)

        ifaces = Interfaces()
        iface = ifaces.add(port_id)
        iface.config.operation = ncconst.NetconfEditConfigOperation.REMOVE
        iface.config.description = ''
        iface.ethernet.switched_vlan.config.operation = (
            ncconst.NetconfEditConfigOperation.REMOVE)

        return [ifaces]

    def _enable_port(self, port_id, **kwargs):
        """Build OpenConfig objects to enable an interface.

        :param port_id: Switch interface name.
        :returns: list of OpenConfig model objects.
        """
        port_id = self._port_id_resub(port_id)

        ifaces = Interfaces()
        iface = ifaces.add(port_id)
        iface.config.enabled = True

        return [ifaces]

    def _disable_port(self, port_id, **kwargs):
        """Build OpenConfig objects to disable an interface.

        :param port_id: Switch interface name.
        :returns: list of OpenConfig model objects.
        """
        port_id = self._port_id_resub(port_id)

        ifaces = Interfaces()
        iface = ifaces.add(port_id)
        iface.config.enabled = False

        return [ifaces]

    ADD_NETWORK = staticmethod(_add_network)
    DELETE_NETWORK = staticmethod(_delete_network)
    ADD_NETWORK_TO_TRUNK = staticmethod(_add_network_to_trunk)
    REMOVE_NETWORK_FROM_TRUNK = staticmethod(_remove_network_from_trunk)
    PLUG_PORT_TO_NETWORK = staticmethod(_plug_port_to_network)
    DELETE_PORT = staticmethod(_delete_port)
    ENABLE_PORT = staticmethod(_enable_port)
    DISABLE_PORT = staticmethod(_disable_port)
