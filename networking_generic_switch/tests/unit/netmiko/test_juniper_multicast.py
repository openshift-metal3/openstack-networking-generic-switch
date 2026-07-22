#
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

from unittest import mock

from networking_generic_switch.devices.netmiko_devices import juniper
from networking_generic_switch import exceptions as exc
from networking_generic_switch.tests.unit.netmiko import test_netmiko_base


class TestNetmikoJuniperMulticast(test_netmiko_base.NetmikoSwitchTestBase):
    """Tests for Juniper multicast BUM replication mode."""

    def _make_switch_device(self, extra_cfg=None):
        device_cfg = {'device_type': 'netmiko_juniper'}
        if extra_cfg:
            device_cfg.update(extra_cfg)
        return juniper.Juniper(device_cfg)

    # BUM Replication Mode Configuration Tests

    def test_init_default_bum_mode_ingress_replication(self):
        """Test __init__ defaults to ingress-replication."""
        device_cfg = {'device_type': 'netmiko_juniper'}
        switch = juniper.Juniper(device_cfg)
        self.assertEqual(switch.bum_replication_mode, 'ingress-replication')

    def test_init_explicit_multicast_mode(self):
        """Test __init__ with explicitly set multicast mode."""
        device_cfg = {
            'device_type': 'netmiko_juniper',
            'ngs_bum_replication_mode': 'multicast',
            'ngs_mcast_group_base': '239.1.1.0'
        }
        switch = juniper.Juniper(device_cfg)
        self.assertEqual(switch.bum_replication_mode, 'multicast')
        self.assertEqual(switch.mcast_group_base, '239.1.1.0')

    def test_init_explicit_ingress_replication_mode(self):
        """Test __init__ with explicitly set ingress-replication mode."""
        device_cfg = {
            'device_type': 'netmiko_juniper',
            'ngs_bum_replication_mode': 'ingress-replication'
        }
        switch = juniper.Juniper(device_cfg)
        self.assertEqual(switch.bum_replication_mode, 'ingress-replication')

    def test_init_multicast_with_base(self):
        """Test __init__ with multicast base configuration."""
        device_cfg = {
            'device_type': 'netmiko_juniper',
            'ngs_bum_replication_mode': 'multicast',
            'ngs_mcast_group_base': '239.2.2.0'
        }
        switch = juniper.Juniper(device_cfg)
        self.assertEqual(switch.mcast_group_base, '239.2.2.0')

    def test_init_multicast_with_map(self):
        """Test __init__ with multicast group map."""
        device_cfg = {
            'device_type': 'netmiko_juniper',
            'ngs_bum_replication_mode': 'multicast',
            'ngs_mcast_group_map': '10100:239.1.1.100,10200:239.1.1.200'
        }
        switch = juniper.Juniper(device_cfg)
        self.assertEqual(len(switch.mcast_group_map), 2)
        self.assertEqual(switch.mcast_group_map[10100], '239.1.1.100')
        self.assertEqual(switch.mcast_group_map[10200], '239.1.1.200')

    def test_init_multicast_combined_evpn(self):
        """Test __init__ with multicast and EVPN configuration."""
        device_cfg = {
            'device_type': 'netmiko_juniper',
            'ngs_bum_replication_mode': 'multicast',
            'ngs_mcast_group_base': '239.1.1.0',
            'ngs_evpn_vni_config': 'true',
            'ngs_bgp_asn': '65000'
        }
        switch = juniper.Juniper(device_cfg)
        self.assertEqual(switch.bum_replication_mode, 'multicast')
        self.assertEqual(switch.mcast_group_base, '239.1.1.0')
        self.assertTrue(switch.evpn_vni_config)
        self.assertEqual(switch.bgp_asn, '65000')

    # Multicast Group Derivation Tests

    def test_get_multicast_group_from_base(self):
        """Test _get_multicast_group calculates from base."""
        device_cfg = {
            'device_type': 'netmiko_juniper',
            'ngs_bum_replication_mode': 'multicast',
            'ngs_mcast_group_base': '239.1.1.0'
        }
        switch = juniper.Juniper(device_cfg)
        # VNI 10100 % 256 = 116 -> 239.1.1.116
        self.assertEqual(switch._get_multicast_group(10100), '239.1.1.116')
        # VNI 10200 % 256 = 216 -> 239.1.1.216
        self.assertEqual(switch._get_multicast_group(10200), '239.1.1.216')

    def test_get_multicast_group_from_map(self):
        """Test _get_multicast_group uses explicit mapping."""
        device_cfg = {
            'device_type': 'netmiko_juniper',
            'ngs_bum_replication_mode': 'multicast',
            'ngs_mcast_group_map': '10100:239.99.99.99'
        }
        switch = juniper.Juniper(device_cfg)
        self.assertEqual(switch._get_multicast_group(10100), '239.99.99.99')

    def test_get_multicast_group_map_precedence_over_base(self):
        """Test explicit map takes precedence over base derivation."""
        device_cfg = {
            'device_type': 'netmiko_juniper',
            'ngs_bum_replication_mode': 'multicast',
            'ngs_mcast_group_base': '239.1.1.0',
            'ngs_mcast_group_map': '10100:239.99.99.99'
        }
        switch = juniper.Juniper(device_cfg)
        # Explicit mapping should take precedence
        self.assertEqual(switch._get_multicast_group(10100), '239.99.99.99')
        # Unmapped VNI should use base derivation
        self.assertEqual(switch._get_multicast_group(10200), '239.1.1.216')

    def test_get_multicast_group_without_config_raises_error(self):
        """Test _get_multicast_group raises error without config."""
        device_cfg = {
            'device_type': 'netmiko_juniper',
            'ngs_bum_replication_mode': 'multicast'
        }
        switch = juniper.Juniper(device_cfg)
        self.assertRaises(
            exc.GenericSwitchNetmikoConfigError,
            switch._get_multicast_group,
            10100
        )

    # Plug Operations with Multicast Mode Tests

    @mock.patch('networking_generic_switch.devices.netmiko_devices.'
                'NetmikoSwitch.send_commands_to_device',
                return_value='', autospec=True)
    @mock.patch.object(juniper.Juniper, '_get_vlan_name_by_id',
                       return_value='vlan100', autospec=True)
    def test_plug_switch_to_network_multicast_mode(
            self, mock_get_vlan, mock_exec):
        """Test plug_switch_to_network with multicast mode."""
        device_cfg = {
            'device_type': 'netmiko_juniper',
            'ngs_bum_replication_mode': 'multicast',
            'ngs_mcast_group_base': '239.1.1.0'
        }
        switch = juniper.Juniper(device_cfg)
        switch.plug_switch_to_network(10100, 100)

        # VNI 10100 % 256 = 116, so mcast group is 239.1.1.116
        mock_exec.assert_called_with(
            switch,
            ['set vlans vlan100 vxlan vni 10100',
             'set vlans vlan100 vxlan multicast-group 239.1.1.116'])

    @mock.patch('networking_generic_switch.devices.netmiko_devices.'
                'NetmikoSwitch.send_commands_to_device',
                return_value='', autospec=True)
    @mock.patch.object(juniper.Juniper, '_get_vlan_name_by_id',
                       return_value='vlan100', autospec=True)
    def test_plug_switch_to_network_multicast_with_map(
            self, mock_get_vlan, mock_exec):
        """Test plug_switch_to_network multicast with explicit mapping."""
        device_cfg = {
            'device_type': 'netmiko_juniper',
            'ngs_bum_replication_mode': 'multicast',
            'ngs_mcast_group_map': '10100:239.99.99.99'
        }
        switch = juniper.Juniper(device_cfg)
        switch.plug_switch_to_network(10100, 100)

        mock_exec.assert_called_with(
            switch,
            ['set vlans vlan100 vxlan vni 10100',
             'set vlans vlan100 vxlan multicast-group 239.99.99.99'])

    @mock.patch('networking_generic_switch.devices.netmiko_devices.'
                'NetmikoSwitch.send_commands_to_device',
                return_value='', autospec=True)
    @mock.patch.object(juniper.Juniper, '_get_vlan_name_by_id',
                       return_value='vlan50', autospec=True)
    def test_plug_switch_to_network_multicast_with_evpn(
            self, mock_get_vlan, mock_exec):
        """Test plug_switch_to_network multicast with EVPN VNI config."""
        device_cfg = {
            'device_type': 'netmiko_juniper',
            'ngs_bum_replication_mode': 'multicast',
            'ngs_mcast_group_base': '239.2.2.0',
            'ngs_evpn_vni_config': 'true',
            'ngs_bgp_asn': '65000'
        }
        switch = juniper.Juniper(device_cfg)
        switch.plug_switch_to_network(5000, 50)

        # VNI 5000 % 256 = 136 -> 239.2.2.136
        mock_exec.assert_called_with(
            switch,
            ['set vlans vlan50 vxlan vni 5000',
             'set vlans vlan50 vxlan multicast-group 239.2.2.136',
             'set vlans vlan50 vrf-target target:65000:5000'])

    @mock.patch('networking_generic_switch.devices.netmiko_devices.'
                'NetmikoSwitch.send_commands_to_device',
                return_value='', autospec=True)
    @mock.patch.object(juniper.Juniper, '_get_vlan_name_by_id',
                       return_value='vlan100', autospec=True)
    def test_plug_switch_to_network_default_mode(
            self, mock_get_vlan, mock_exec):
        """Test plug_switch_to_network with default mode."""
        device_cfg = {'device_type': 'netmiko_juniper'}
        switch = juniper.Juniper(device_cfg)
        switch.plug_switch_to_network(10100, 100)

        # Default mode (ingress-replication), no explicit BUM config
        mock_exec.assert_called_with(
            switch,
            ['set vlans vlan100 vxlan vni 10100'])

    @mock.patch('networking_generic_switch.devices.netmiko_devices.'
                'NetmikoSwitch.send_commands_to_device',
                return_value='', autospec=True)
    @mock.patch.object(juniper.Juniper, '_get_vlan_name_by_id',
                       return_value='vlan200', autospec=True)
    def test_plug_switch_to_network_ingress_replication_explicit(
            self, mock_get_vlan, mock_exec):
        """Test plug_switch_to_network with explicit ingress mode."""
        device_cfg = {
            'device_type': 'netmiko_juniper',
            'ngs_bum_replication_mode': 'ingress-replication'
        }
        switch = juniper.Juniper(device_cfg)
        switch.plug_switch_to_network(10200, 200)

        # Explicit ingress-replication mode, no BUM config needed
        mock_exec.assert_called_with(
            switch,
            ['set vlans vlan200 vxlan vni 10200'])

    @mock.patch('networking_generic_switch.devices.netmiko_devices.'
                'NetmikoSwitch.send_commands_to_device',
                return_value='', autospec=True)
    @mock.patch.object(juniper.Juniper, '_get_vlan_name_by_id',
                       return_value='vlan150', autospec=True)
    def test_plug_switch_to_network_ingress_replication_with_evpn(
            self, mock_get_vlan, mock_exec):
        """Test plug_switch_to_network ingress mode with EVPN."""
        device_cfg = {
            'device_type': 'netmiko_juniper',
            'ngs_bum_replication_mode': 'ingress-replication',
            'ngs_evpn_vni_config': 'true',
            'ngs_bgp_asn': '65001'
        }
        switch = juniper.Juniper(device_cfg)
        switch.plug_switch_to_network(10150, 150)

        # Ingress mode with EVPN - only VNI and VRF target
        mock_exec.assert_called_with(
            switch,
            ['set vlans vlan150 vxlan vni 10150',
             'set vlans vlan150 vrf-target target:65001:10150'])

    # Unplug Operations Tests

    @mock.patch('networking_generic_switch.devices.netmiko_devices.'
                'NetmikoSwitch.send_commands_to_device',
                return_value='', autospec=True)
    @mock.patch.object(juniper.Juniper, '_get_vlan_name_by_id',
                       return_value='vlan100', autospec=True)
    def test_unplug_switch_from_network_multicast_mode(
            self, mock_get_vlan, mock_exec):
        """Test unplug_switch_from_network with multicast mode."""
        device_cfg = {
            'device_type': 'netmiko_juniper',
            'ngs_bum_replication_mode': 'multicast',
            'ngs_mcast_group_base': '239.1.1.0'
        }
        switch = juniper.Juniper(device_cfg)
        switch.unplug_switch_from_network(10100, 100)

        mock_exec.assert_called_with(
            switch,
            ['delete vlans vlan100 vxlan multicast-group',
             'delete vlans vlan100 vxlan vni'])

    @mock.patch('networking_generic_switch.devices.netmiko_devices.'
                'NetmikoSwitch.send_commands_to_device',
                return_value='', autospec=True)
    @mock.patch.object(juniper.Juniper, '_get_vlan_name_by_id',
                       return_value='vlan50', autospec=True)
    def test_unplug_switch_from_network_multicast_with_evpn(
            self, mock_get_vlan, mock_exec):
        """Test unplug_switch_from_network multicast with EVPN."""
        device_cfg = {
            'device_type': 'netmiko_juniper',
            'ngs_bum_replication_mode': 'multicast',
            'ngs_mcast_group_base': '239.2.2.0',
            'ngs_evpn_vni_config': 'true',
            'ngs_bgp_asn': '65000'
        }
        switch = juniper.Juniper(device_cfg)
        switch.unplug_switch_from_network(5000, 50)

        mock_exec.assert_called_with(
            switch,
            ['delete vlans vlan50 vxlan multicast-group',
             'delete vlans vlan50 vxlan vni',
             'delete vlans vlan50 vrf-target'])

    @mock.patch('networking_generic_switch.devices.netmiko_devices.'
                'NetmikoSwitch.send_commands_to_device',
                return_value='', autospec=True)
    @mock.patch.object(juniper.Juniper, '_get_vlan_name_by_id',
                       return_value='vlan100', autospec=True)
    def test_unplug_switch_from_network_default_mode(
            self, mock_get_vlan, mock_exec):
        """Test unplug_switch_from_network with default mode."""
        device_cfg = {'device_type': 'netmiko_juniper'}
        switch = juniper.Juniper(device_cfg)
        switch.unplug_switch_from_network(10100, 100)

        # Default mode (ingress-replication), no BUM cleanup
        mock_exec.assert_called_with(
            switch,
            ['delete vlans vlan100 vxlan vni'])

    @mock.patch('networking_generic_switch.devices.netmiko_devices.'
                'NetmikoSwitch.send_commands_to_device',
                return_value='', autospec=True)
    @mock.patch.object(juniper.Juniper, '_get_vlan_name_by_id',
                       return_value='vlan150', autospec=True)
    def test_unplug_switch_from_network_ingress_replication_with_evpn(
            self, mock_get_vlan, mock_exec):
        """Test unplug_switch_from_network ingress mode with EVPN."""
        device_cfg = {
            'device_type': 'netmiko_juniper',
            'ngs_bum_replication_mode': 'ingress-replication',
            'ngs_evpn_vni_config': 'true',
            'ngs_bgp_asn': '65001'
        }
        switch = juniper.Juniper(device_cfg)
        switch.unplug_switch_from_network(10150, 150)

        # Ingress mode with EVPN - remove VNI and VRF target
        mock_exec.assert_called_with(
            switch,
            ['delete vlans vlan150 vxlan vni',
             'delete vlans vlan150 vrf-target'])
