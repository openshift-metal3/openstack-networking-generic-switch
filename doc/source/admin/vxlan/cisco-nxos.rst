===================
Cisco Nexus (NX-OS)
===================

The Cisco Nexus implementation supports two modes for BUM (Broadcast, Unknown
unicast, Multicast) traffic replication: ingress-replication (default) and
multicast.

Configuration Parameters
========================

* ``ngs_nve_interface`` - NVE interface name (default: ``nve1``)
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

   [genericswitch:leaf01]
   device_type = netmiko_cisco_nxos
   ip = 192.0.2.10
   username = admin
   password = password
   ngs_physical_networks = datacenter1,datacenter2
   ngs_nve_interface = nve1

**Multicast Mode with Base IP**

.. code-block:: ini

   [genericswitch:leaf02]
   device_type = netmiko_cisco_nxos
   ip = 192.0.2.11
   username = admin
   password = password
   ngs_physical_networks = datacenter1,datacenter2
   ngs_bum_replication_mode = multicast
   ngs_mcast_group_base = 239.1.1.0

**Multicast Mode with Explicit Mapping**

.. code-block:: ini

   [genericswitch:leaf03]
   device_type = netmiko_cisco_nxos
   ip = 192.0.2.12
   username = admin
   password = password
   ngs_physical_networks = datacenter1,datacenter2
   ngs_bum_replication_mode = multicast
   ngs_mcast_group_map = 10100:239.1.1.100, 10200:239.1.1.200
   ngs_mcast_group_base = 239.1.1.0

Prerequisites
=============

Both modes require VXLAN and NV overlay features enabled with the switch
configured as a VTEP.

Ingress-Replication Mode
-------------------------

Your Cisco NX-OS switches must have BGP EVPN configured. This is required
for both MAC/IP learning and BUM traffic replication.

Example switch configuration:

.. code-block:: text

   ! Enable required features
   feature bgp
   feature vxlan
   feature nv overlay

   ! Configure BGP EVPN
   router bgp 65000
     neighbor 192.0.2.1 remote-as 65000
     address-family l2vpn evpn
       neighbor 192.0.2.1 activate
       advertise-pip

   ! Configure NVE interface
   interface nve1
     no shutdown
     source-interface loopback0
     host-reachability protocol bgp

Multicast Mode
---------------

For multicast mode, in addition to BGP EVPN (used for MAC/IP learning), your
fabric must have PIM Sparse Mode with Anycast RP configured.

Example switch configuration:

.. code-block:: text

   ! Enable required features
   feature bgp
   feature pim
   feature vxlan
   feature nv overlay

   ! Configure PIM on underlay interfaces
   interface Ethernet1/1-48
     ip pim sparse-mode

   ! Loopback for VTEP
   interface loopback0
     ip address 10.0.0.1/32
     ip pim sparse-mode

   ! Anycast RP configuration (same on all RP switches)
   ip pim rp-address 10.255.255.254 group-list 239.0.0.0/8

   ! Configure Anycast RP set (repeat for each RP)
   ip pim anycast-rp 10.255.255.254 10.0.0.1
   ip pim anycast-rp 10.255.255.254 10.0.0.2

   ! Configure BGP EVPN (for MAC/IP learning)
   router bgp 65000
     neighbor 192.0.2.1 remote-as 65000
     address-family l2vpn evpn
       neighbor 192.0.2.1 activate
       advertise-pip

   ! Configure NVE interface
   interface nve1
     no shutdown
     source-interface loopback0
     host-reachability protocol bgp

Generated Configuration
========================

For each VXLAN network, the driver automatically generates the following
configuration on the switch.

**Ingress-Replication Mode:**

.. code-block:: text

   ! BGP EVPN control plane
   evpn
     vni 10100 l2
     rd auto
     route-target both auto

   ! Data plane with ingress-replication
   vlan 100
     vn-segment 10100
   interface nve1
     member vni 10100
       ingress-replication protocol bgp

**Multicast Mode:**

.. code-block:: text

   ! BGP EVPN control plane (MAC/IP learning only)
   evpn
     vni 10100 l2
     rd auto
     route-target both auto

   ! Data plane with multicast group
   vlan 100
     vn-segment 10100
   interface nve1
     member vni 10100
       mcast-group 239.1.1.116
