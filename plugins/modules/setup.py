#!/usr/bin/python
# Copyright (c) 2017 Markus Weippert
# GNU General Public License v3.0 (see https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations


DOCUMENTATION = r"""
module: setup
short_description: Gather facts about OpenWrt systems
description:
  - The M(community.openwrt.setup) module gathers facts about OpenWrt systems.
  - It collects system information including distribution details, hostname, network interfaces, services, and device
    information through ubus.
  - This module is automatically called by playbooks to gather useful variables about remote hosts.
author: Markus Weippert (@gekmihesg)
extends_documentation_fragment:
  - community.openwrt.attributes
  - community.openwrt.attributes.facts
  - community.openwrt.attributes.facts_module
options:
  discover_uci:
    description:
      - Enable UCI configuration discovery.
      - When enabled, retrieves all UCI configurations and their states.
    type: bool
    default: false
  discover_uci_strict:
    description:
      - Strict mode for UCI discovery.
      - If enabled, fact gathering will fail if unable to retrieve state for any UCI config.
    type: bool
    default: false
  discover_uci_exclude_list:
    description:
      - List of UCI configs to exclude from discovery.
      - Configs in this list will be skipped during discovery.
    type: list
    elements: str
    default: []
  discover_uci_configs:
    description:
      - List of specific UCI configs to discover.
      - If set, only these configs will be discovered.
      - If empty, all available configs will be discovered.
    type: list
    elements: str
    default: []
  discover_uci_sensitive_fields:
    description:
      - List of UCI config/section/field combinations to mask in output.
      - Each item should be a dict with C(config), C(section), and C(field) keys.
      - Sensitive fields will be replaced with C(***MASKED***) to prevent exposure.
      - "Example: C([{config: ddns, section: service, field: password}])"
    type: list
    elements: dict
    default: []
notes:
  - This module gathers OpenWrt-specific facts including C(ubus) data for network interfaces, devices, services, and
    system information.
  - Facts are returned in the C(ansible_facts) namespace.
"""

EXAMPLES = r"""
- name: Gather facts from OpenWrt device
  community.openwrt.setup:

- name: Show distribution version
  ansible.builtin.debug:
    msg: "{{ ansible_distribution_version }}"
"""

RETURN = r"""
ansible_facts:
  description: Facts gathered from the OpenWrt system.
  returned: always
  type: dict
  contains:
    ansible_hostname:
      description: The hostname of the system.
      type: str
      sample: router
    ansible_distribution:
      description: The distribution name.
      type: str
      sample: OpenWrt
    ansible_distribution_version:
      description: The distribution version.
      type: str
      sample: 22.03.5
    ansible_distribution_major_version:
      description: The major version of the distribution.
      type: str
      sample: "22"
    ansible_distribution_release:
      description: The distribution release codename.
      type: str
      sample: ""
    ansible_os_family:
      description: The OS family.
      type: str
      sample: OpenWrt
    ansible_is_chroot:
      description: Whether the system is running in a chroot.
      type: bool
      sample: false
    openwrt_info:
      description: System information from C(ubus).
      returned: when available
      type: dict
    openwrt_devices:
      description: Network device status from C(ubus).
      returned: when available
      type: dict
    openwrt_services:
      description: Service list from C(ubus).
      returned: when available
      type: dict
    openwrt_board:
      description: Board information from C(ubus).
      returned: when available
      type: dict
    openwrt_wireless:
      description: Wireless status from C(ubus).
      returned: when available
      type: dict
    openwrt_interfaces:
      description: Network interface status from C(ubus).
      returned: when available
      type: dict
    openwrt_uci:
      description: UCI configuration discovery results.
      returned: when O(discover_uci=true) and UCI is available
      type: dict
      contains:
        configs:
          description: List of discovered UCI configuration names.
          type: list
          elements: str
        states:
          description: UCI configuration states indexed by config name.
          type: dict
"""
