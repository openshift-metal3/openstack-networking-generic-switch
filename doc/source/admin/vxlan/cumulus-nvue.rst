============
Cumulus NVUE
============

The Cumulus NVUE implementation supports L2VNI configuration on the default
bridge domain ``br_default`` with three modes for BUM (Broadcast, Unknown
unicast, Multicast) traffic replication:

1. **Ingress-replication** (default) - Uses EVPN-learned VTEPs for dynamic
   BUM replication
2. **Head-end-replication** - Uses static VTEP flood lists for BUM
   replication
3. **Multicast** - Uses ASM multicast groups with PIM Sparse Mode

Configuration Parameters
========================

BUM Replication Mode Configuration:

* ``ngs_bum_replication_mode`` - BUM traffic replication mode. Options:
  ``ingress-replication`` (default), ``head-end-replication``, ``multicast``

Ingress-Replication Mode (EVPN-learned VTEPs):

* No additional configuration required - VTEPs are learned via EVPN

Head-End-Replication Mode (Static VTEP Lists):

* ``ngs_her_flood_list`` - Global HER flood list (comma-separated VTEP IPs)
* ``ngs_physnet_her_flood`` - Per-physnet HER flood lists (format:
  ``physnet1:ip1,ip2;physnet2:ip3,ip4``)

Multicast Mode:

* ``ngs_mcast_group_map`` - Explicit VNI-to-multicast-group mappings (format:
  ``vni1:group1,vni2:group2``)
* ``ngs_mcast_group_base`` - Base multicast group address for automatic
  derivation (e.g., ``239.1.1.0``)
* ``ngs_mcast_group_increment`` - Derivation method (default:
  ``vni_last_octet``)

EVPN Control Plane Configuration:

* ``ngs_evpn_vni_config`` - Enable EVPN VNI control plane configuration
  (default: false)
* ``ngs_bgp_asn`` - BGP AS number (required when ``ngs_evpn_vni_config`` is
  enabled)

BUM Replication Mode Auto-Detection
====================================

The driver automatically selects the appropriate BUM replication mode:

1. If ``ngs_bum_replication_mode`` is explicitly set, use that mode
2. Else if ``ngs_her_flood_list`` or ``ngs_physnet_her_flood`` is configured,
   auto-detect ``head-end-replication`` mode (backward compatibility)
3. Else default to ``ingress-replication`` mode

This ensures backward compatibility with existing deployments using HER flood
lists while defaulting new deployments to EVPN-learned VTEPs.

EVPN VNI Control Plane
========================

When ``ngs_evpn_vni_config=true`` and ``ngs_bgp_asn`` is set, the driver
configures per-VNI EVPN in FRRouting (FRR) using vtysh commands:

.. code-block:: bash

   vtysh -c "configure terminal" \
         -c "router bgp <asn>" \
         -c "address-family l2vpn evpn" \
         -c "vni <vni>" \
         -c "rd auto" \
         -c "route-target import auto" \
         -c "route-target export auto"

Configuration Examples
======================

**Scenario 1: Ingress-Replication (EVPN-learned VTEPs, Default)**

.. code-block:: ini

   [genericswitch:cumulus-switch]
   device_type = netmiko_cumulus_nvue

Generated commands:

.. code-block:: bash

   nv set bridge domain br_default vlan 100 vni 10100
   nv set bridge domain br_default vlan 100 vni 10100 flooding \
       head-end-replication evpn

**Scenario 2: Head-End-Replication with Global HER Flood List**

.. code-block:: ini

   [genericswitch:cumulus-switch]
   device_type = netmiko_cumulus_nvue
   ngs_her_flood_list = 10.0.1.1,10.0.1.2

Generated commands:

.. code-block:: bash

   nv set bridge domain br_default vlan 100 vni 10100
   nv set nve vxlan flooding head-end-replication 10.0.1.1
   nv set nve vxlan flooding head-end-replication 10.0.1.2

**Scenario 3: Head-End-Replication with Per-Physnet HER Flood Lists**

.. code-block:: ini

   [genericswitch:cumulus-switch]
   device_type = netmiko_cumulus_nvue
   ngs_physnet_her_flood = physnet1:10.0.1.1,10.0.1.2;physnet2:10.0.2.1

For physnet1, generated commands:

.. code-block:: bash

   nv set bridge domain br_default vlan 100 vni 10100
   nv set nve vxlan flooding head-end-replication 10.0.1.1
   nv set nve vxlan flooding head-end-replication 10.0.1.2

**Scenario 4: Multicast Mode with Base Address**

.. code-block:: ini

   [genericswitch:cumulus-switch]
   device_type = netmiko_cumulus_nvue
   ngs_bum_replication_mode = multicast
   ngs_mcast_group_base = 239.1.1.0

For VNI 10100, generated commands:

.. code-block:: bash

   nv set bridge domain br_default vlan 100 vni 10100
   nv set bridge domain br_default vlan 100 vni 10100 flooding \
       multicast-group 239.1.1.116

**Scenario 5: Multicast Mode with Explicit Mapping**

.. code-block:: ini

   [genericswitch:cumulus-switch]
   device_type = netmiko_cumulus_nvue
   ngs_bum_replication_mode = multicast
   ngs_mcast_group_map = 10100:239.5.5.100,10200:239.5.5.200

For VNI 10100, generated commands:

.. code-block:: bash

   nv set bridge domain br_default vlan 100 vni 10100
   nv set bridge domain br_default vlan 100 vni 10100 flooding \
       multicast-group 239.5.5.100

**Scenario 6: EVPN VNI Configuration with Ingress-Replication**

.. code-block:: ini

   [genericswitch:cumulus-switch]
   device_type = netmiko_cumulus_nvue
   ngs_evpn_vni_config = true
   ngs_bgp_asn = 65000

Generated commands:

.. code-block:: bash

   vtysh -c "configure terminal" \
         -c "router bgp 65000" \
         -c "address-family l2vpn evpn" \
         -c "vni 10100" \
         -c "rd auto" \
         -c "route-target import auto" \
         -c "route-target export auto"
   nv set bridge domain br_default vlan 100 vni 10100
   nv set bridge domain br_default vlan 100 vni 10100 flooding \
       head-end-replication evpn

Prerequisites
=============

**Ingress-replication mode:**

* BGP EVPN configured (optional per-VNI config via
  ``ngs_evpn_vni_config``)

Example FRR configuration for EVPN:

.. code-block:: bash

   nv set router bgp 65000 neighbor 10.0.0.2 type external
   nv set router bgp 65000 neighbor 10.0.0.2 \
       address-family l2vpn-evpn enable on
   nv set nve vxlan source address 10.0.0.1

**Head-end-replication mode:**

* Static VTEP flood lists configured
* No BGP EVPN required (optional for MAC/IP learning)

**Multicast mode:**

* PIM Sparse Mode and Rendezvous Point for BUM traffic replication
  (data plane)
* BGP EVPN optional but recommended for MAC/IP learning (control
  plane)

Example PIM configuration:

.. code-block:: bash

   # Configure PIM on interfaces
   nv set interface swp1 router pim
   nv set interface lo router pim

   # Configure RP
   nv set router pim address-family ipv4-unicast \
       rp 10.255.255.254 group-range 239.0.0.0/8

   # Configure EVPN (for MAC/IP learning)
   nv set router bgp 65000 neighbor 10.0.0.2 type external
   nv set router bgp 65000 neighbor 10.0.0.2 \
       address-family l2vpn-evpn enable on
   nv set nve vxlan source address 10.0.0.1
