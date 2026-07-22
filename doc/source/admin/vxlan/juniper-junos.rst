==============
Juniper Junos
==============

The Juniper Junos implementation supports L2VNI configuration on QFX and EX
series switches with EVPN control plane support. It supports two modes for
BUM (Broadcast, Unknown unicast, Multicast) traffic replication:
ingress-replication (default) and multicast. VLANs are referenced by name
(automatically created during network setup), and VNI mappings use the
``vxlan vni`` command.

Configuration Parameters
========================

- ``device_type``: ``netmiko_juniper``
- ``ngs_evpn_vni_config``: Enable EVPN VRF target configuration (default:
  false)
- ``ngs_bgp_asn``: BGP AS number (required when ``ngs_evpn_vni_config`` is
  enabled)
- ``ngs_bum_replication_mode``: BUM traffic replication mode (default:
  ``ingress-replication``). Options: ``ingress-replication``, ``multicast``
- ``ngs_mcast_group_map``: Explicit VNI-to-multicast-group mappings
  (format: ``vni1:group1,vni2:group2``)
- ``ngs_mcast_group_base``: Base multicast group IP for automatic
  derivation (e.g., ``239.1.1.0``)
- ``ngs_mcast_group_increment``: Multicast group derivation method
  (default: ``vni_last_octet``)

The driver automatically queries the switch to map VLAN IDs to VLAN names
for VNI configuration.

EVPN VRF Target Configuration
==============================

When ``ngs_evpn_vni_config=true`` and ``ngs_bgp_asn`` is set, the driver
configures per-VLAN VRF targets for EVPN Type-2 route import/export:

.. code-block:: bash

   set vlans <vlan-name> vrf-target target:<asn>:<vni>

Configuration Examples
======================

**Scenario 1: Basic L2VNI with Ingress-Replication (default)**

.. code-block:: ini

   [genericswitch:juniper-switch]
   device_type = netmiko_juniper

Generated commands:

.. code-block:: bash

   set vlans vlan100 vxlan vni 10100

**Scenario 2: L2VNI with EVPN VRF Target**

.. code-block:: ini

   [genericswitch:juniper-switch]
   device_type = netmiko_juniper
   ngs_evpn_vni_config = true
   ngs_bgp_asn = 65000

Generated commands:

.. code-block:: bash

   set vlans vlan100 vxlan vni 10100
   set vlans vlan100 vrf-target target:65000:10100

**Scenario 3: L2VNI with Multicast Mode**

.. code-block:: ini

   [genericswitch:juniper-switch]
   device_type = netmiko_juniper
   ngs_bum_replication_mode = multicast
   ngs_mcast_group_base = 239.1.1.0

Generated commands (for VNI 10100):

.. code-block:: bash

   set vlans vlan100 vxlan vni 10100
   set vlans vlan100 vxlan multicast-group 239.1.1.116

**Scenario 4: L2VNI with Multicast Mode and EVPN VRF Target**

.. code-block:: ini

   [genericswitch:juniper-switch]
   device_type = netmiko_juniper
   ngs_evpn_vni_config = true
   ngs_bgp_asn = 65000
   ngs_bum_replication_mode = multicast
   ngs_mcast_group_base = 239.1.1.0

Generated commands (for VNI 10100):

.. code-block:: bash

   set vlans vlan100 vxlan vni 10100
   set vlans vlan100 vxlan multicast-group 239.1.1.116
   set vlans vlan100 vrf-target target:65000:10100

**Scenario 5: Multicast Mode with Explicit VNI Mapping**

.. code-block:: ini

   [genericswitch:juniper-switch]
   device_type = netmiko_juniper
   ngs_bum_replication_mode = multicast
   ngs_mcast_group_map = 10100:239.1.1.100, 10200:239.1.1.200

Generated commands (for VNI 10100):

.. code-block:: bash

   set vlans vlan100 vxlan vni 10100
   set vlans vlan100 vxlan multicast-group 239.1.1.100

Without ``ngs_evpn_vni_config``, the VRF target configuration is omitted
and only the VXLAN map is applied.

Prerequisites
=============

Both modes require VXLAN configured on a QFX or EX series switch with a
VTEP and BGP EVPN configured for VTEP discovery.

Ingress-Replication Mode
-------------------------

Example switch configuration:

.. code-block:: text

   ! Configure BGP EVPN
   set protocols bgp group EVPN_OVERLAY type internal
   set protocols bgp group EVPN_OVERLAY local-address 10.0.0.1
   set protocols bgp group EVPN_OVERLAY family evpn signaling
   set protocols bgp group EVPN_OVERLAY neighbor 10.0.0.2

   ! Configure VTEP source interface
   set switch-options vtep-source-interface lo0.0

Multicast Mode
---------------

For multicast mode, in addition to BGP EVPN (used for MAC/IP learning),
your fabric must have PIM Sparse Mode with Rendezvous Point (RP)
configured across all switches.

Example switch configuration:

.. code-block:: text

   ! Configure PIM on underlay interfaces
   set protocols pim interface ge-0/0/0.0 mode sparse
   set protocols pim interface ge-0/0/1.0 mode sparse

   ! Configure loopback for VTEP
   set interfaces lo0 unit 0 family inet address 10.0.0.1/32
   set protocols pim interface lo0.0 mode sparse

   ! Configure RP
   set protocols pim rp static address 10.255.255.254

   ! Configure BGP EVPN (still used for MAC/IP learning)
   set protocols bgp group EVPN_OVERLAY type internal
   set protocols bgp group EVPN_OVERLAY local-address 10.0.0.1
   set protocols bgp group EVPN_OVERLAY family evpn signaling
   set protocols bgp group EVPN_OVERLAY neighbor 10.0.0.2

   ! Configure VTEP source interface
   set switch-options vtep-source-interface lo0.0

Generated Configuration
========================

For each VXLAN network, the driver automatically generates the following
configuration on the switch.

**Ingress-Replication Mode (default):**

.. code-block:: text

   ! VLAN to VNI mapping
   set vlans vlan100 vxlan vni 10100

   ! Optional: EVPN VRF target (if ngs_evpn_vni_config enabled)
   set vlans vlan100 vrf-target target:65000:10100

**Multicast Mode:**

.. code-block:: text

   ! VLAN to VNI mapping
   set vlans vlan100 vxlan vni 10100

   ! Multicast group for BUM traffic
   set vlans vlan100 vxlan multicast-group 239.1.1.116

   ! Optional: EVPN VRF target (if ngs_evpn_vni_config enabled)
   set vlans vlan100 vrf-target target:65000:10100
