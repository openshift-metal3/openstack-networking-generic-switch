==============
Juniper Junos
==============

The Juniper Junos implementation supports L2VNI configuration on QFX and EX
series switches with EVPN control plane support. VLANs are referenced by name
(automatically created during network setup), and VNI mappings use the
``vxlan vni`` command.

Configuration Parameters
========================

- ``device_type``: ``netmiko_juniper``
- ``ngs_evpn_vni_config``: Enable EVPN VRF target configuration (default:
  false)
- ``ngs_bgp_asn``: BGP AS number (required when ``ngs_evpn_vni_config`` is
  enabled)

The driver automatically queries the switch to map VLAN IDs to VLAN names for
VNI configuration.

EVPN VRF Target Configuration
==============================

When ``ngs_evpn_vni_config=true`` and ``ngs_bgp_asn`` is set, the driver
configures per-VLAN VRF targets for EVPN Type-2 route import/export:

.. code-block:: bash

   set vlans <vlan-name> vrf-target target:<asn>:<vni>

Configuration Examples
======================

**Scenario 1: Basic L2VNI (no EVPN VRF target)**

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

Without ``ngs_evpn_vni_config``, the VRF target configuration is omitted and
only the VXLAN map is applied.

Prerequisites
=============

* VXLAN configured on QFX or EX series switch
* Switch configured as a VTEP
* BGP EVPN configured for VTEP discovery and BUM traffic replication
* Optional: EVPN VRF target per-VLAN (via ``ngs_evpn_vni_config``)

Example switch configuration:

.. code-block:: text

   ! Configure BGP EVPN
   set protocols bgp group EVPN_OVERLAY type internal
   set protocols bgp group EVPN_OVERLAY local-address 10.0.0.1
   set protocols bgp group EVPN_OVERLAY family evpn signaling
   set protocols bgp group EVPN_OVERLAY neighbor 10.0.0.2

   ! Configure VTEP source interface
   set switch-options vtep-source-interface lo0.0
