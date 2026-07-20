===========
Arista EOS
===========

The Arista EOS implementation supports two modes for BUM (Broadcast, Unknown
unicast, Multicast) traffic replication: ingress-replication (default) and
multicast.

Configuration Parameters
========================

* ``ngs_vxlan_interface`` - VXLAN interface name (default: ``Vxlan1``)
* ``ngs_bgp_asn`` - BGP AS number (required)
* ``ngs_evpn_route_target`` - Route-target value (default: ``auto``)
* ``ngs_bum_replication_mode`` - BUM traffic replication mode (default:
  ``ingress-replication``). Options: ``ingress-replication``, ``multicast``
* ``ngs_mcast_group_map`` - Explicit VNI-to-multicast-group mappings as
  comma-separated ``VNI:group`` pairs. Used for pre-existing multicast group
  assignments. Example: ``10100:239.1.1.100, 10200:239.1.1.200``
* ``ngs_mcast_group_base`` - Base ASM multicast group address for automatic
  derivation of unmapped VNIs (optional when ``ngs_mcast_group_map`` is used,
  required otherwise when ``ngs_bum_replication_mode=multicast``).
  Example: ``239.1.1.0``
* ``ngs_mcast_group_increment`` - Multicast group derivation method (default:
  ``vni_last_octet``)

Configuration Examples
======================

**Ingress-Replication Mode (Default)**

.. code-block:: ini

   [genericswitch:arista-switch]
   device_type = netmiko_arista_eos
   ip = 192.0.2.30
   username = admin
   password = password
   ngs_physical_networks = datacenter1,datacenter2
   ngs_vxlan_interface = Vxlan1
   ngs_bgp_asn = 65000

**Multicast Mode with Base IP**

.. code-block:: ini

   [genericswitch:arista-leaf02]
   device_type = netmiko_arista_eos
   ip = 192.0.2.31
   username = admin
   password = password
   ngs_physical_networks = datacenter1,datacenter2
   ngs_bum_replication_mode = multicast
   ngs_mcast_group_base = 239.1.1.0
   ngs_vxlan_interface = Vxlan1
   ngs_bgp_asn = 65000

**Multicast Mode with Explicit Mapping**

.. code-block:: ini

   [genericswitch:arista-leaf03]
   device_type = netmiko_arista_eos
   ip = 192.0.2.32
   username = admin
   password = password
   ngs_physical_networks = datacenter1,datacenter2
   ngs_bum_replication_mode = multicast
   ngs_mcast_group_map = 10100:239.1.1.100, 10200:239.1.1.200
   ngs_mcast_group_base = 239.1.1.0
   ngs_bgp_asn = 65000

Prerequisites
=============

Both modes require BGP EVPN configured and a VXLAN interface configured
as a VTEP.

Ingress-Replication Mode
-------------------------

Example switch configuration:

.. code-block:: text

   ! Configure BGP EVPN
   router bgp 65000
     router-id 10.0.0.1
     neighbor 10.0.0.2 remote-as 65000
     neighbor 10.0.0.2 update-source Loopback0
     address-family evpn
       neighbor 10.0.0.2 activate

   ! Configure VXLAN interface
   interface Vxlan1
     vxlan source-interface Loopback0
     vxlan udp-port 4789

Multicast Mode
---------------

For multicast mode, in addition to BGP EVPN (used for MAC/IP learning), your
fabric must have PIM Sparse Mode with Anycast RP configured.

Example switch configuration:

.. code-block:: text

   ! Configure PIM on underlay interfaces
   interface Ethernet1-48
     ip pim sparse-mode

   ! Loopback for VTEP
   interface Loopback0
     ip address 10.0.0.1/32
     ip pim sparse-mode

   ! Anycast RP configuration
   ip pim rp-address 10.255.255.254 239.0.0.0/8

   ! Configure Anycast RP set
   ip pim anycast-rp 10.255.255.254 10.0.0.1
   ip pim anycast-rp 10.255.255.254 10.0.0.2

   ! Configure BGP EVPN (for MAC/IP learning)
   router bgp 65000
     router-id 10.0.0.1
     neighbor 10.0.0.2 remote-as 65000
     neighbor 10.0.0.2 update-source Loopback0
     address-family evpn
       neighbor 10.0.0.2 activate

   ! Configure VXLAN interface
   interface Vxlan1
     vxlan source-interface Loopback0
     vxlan udp-port 4789

Generated Configuration
========================

For each VXLAN network, the driver automatically generates the following
configuration on the switch.

**Ingress-Replication Mode:**

.. code-block:: text

   ! BGP EVPN control plane
   router bgp 65000
     vlan 100
       rd auto
       route-target both auto

   ! Data plane with ingress-replication
   interface Vxlan1
     vxlan vlan 100 vni 10100

**Multicast Mode:**

.. code-block:: text

   ! BGP EVPN control plane (MAC/IP learning only)
   router bgp 65000
     vlan 100
       rd auto
       route-target both auto

   ! Data plane with multicast group
   interface Vxlan1
     vxlan vlan 100 vni 10100
     vxlan vlan 100 flood vtep 239.1.1.116
