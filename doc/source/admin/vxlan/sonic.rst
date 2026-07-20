=====
SONiC
=====

The SONiC implementation uses BGP EVPN with ingress-replication for BUM
(Broadcast, Unknown unicast, Multicast) traffic handling.

Configuration Parameters
========================

* ``ngs_vtep_name`` - VXLAN tunnel endpoint interface name (required)
* ``ngs_bgp_asn`` - BGP AS number (required)

Configuration Example
=====================

.. code-block:: ini

   [genericswitch:sonic-switch]
   device_type = netmiko_sonic
   ip = 192.0.2.20
   username = admin
   password = password
   ngs_physical_networks = datacenter1,datacenter2
   ngs_vtep_name = vtep
   ngs_bgp_asn = 65000

Prerequisites
=============

Your SONiC switches must have BGP EVPN pre-configured with
``advertise-all-vni`` enabled in FRR.

Example FRR configuration:

.. code-block:: text

   router bgp 65000
     neighbor 10.0.0.2 remote-as 65000
     neighbor 10.0.0.2 update-source lo
     address-family l2vpn evpn
       neighbor 10.0.0.2 activate
       advertise-all-vni

Generated Configuration
========================

For each VXLAN network, the driver automatically generates:

.. code-block:: text

   # BGP EVPN control plane (via FRR vtysh)
   vtysh -c "configure terminal" \
         -c "router bgp 65000" \
         -c "address-family l2vpn evpn" \
         -c "vni 10100" \
         -c "rd auto" \
         -c "route-target import auto" \
         -c "route-target export auto"

   # VXLAN map
   config vxlan map add vtep 100 10100

Limitations
===========

SONiC does NOT support multicast-based BUM replication. Only
ingress-replication mode is available. If
``ngs_bum_replication_mode=multicast`` is configured, the driver
will raise a ``GenericSwitchNetmikoConfigError``.

According to the SONiC EVPN VXLAN HLD: "Support Ingress
Replication for L2 BUM traffic over VXLAN tunnels. Underlay IP
Multicast is not supported."

For multicast-based BUM replication, consider using Cumulus NVUE,
Arista EOS, or Cisco NX-OS.
