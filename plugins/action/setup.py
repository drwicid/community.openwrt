# Copyright (c) 2025 Alexei Znamensky
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

from ansible_collections.community.openwrt.plugins.plugin_utils.openwrt_action import OpenwrtActionBase


class ActionModule(OpenwrtActionBase):
    """Enhanced setup action plugin with UCI filtering and sensitive field masking"""

    def run(self, tmp=None, task_vars=None):
        """Execute setup and post-process UCI data"""
        
        # Call parent to execute the shell module
        result = super(ActionModule, self).run(tmp, task_vars)
        
        # If module failed or UCI discovery wasn't enabled, return as-is
        if result.get('failed') or 'ansible_facts' not in result:
            return result
        
        ansible_facts = result.get('ansible_facts', {})
        openwrt_uci = ansible_facts.get('openwrt_uci')
        
        # If no UCI data, return as-is
        if not openwrt_uci or not isinstance(openwrt_uci, dict):
            return result
        
        # Get filtering parameters from task args
        discover_uci_strict = self._task.args.get('discover_uci_strict', False)
        discover_uci_exclude_list = self._task.args.get('discover_uci_exclude_list', [])
        discover_uci_configs = self._task.args.get('discover_uci_configs', [])
        discover_uci_sensitive_fields = self._task.args.get('discover_uci_sensitive_fields', [])
        
        # Apply filtering and masking
        try:
            filtered_uci = self._filter_uci_data(
                openwrt_uci,
                discover_uci_strict,
                discover_uci_exclude_list,
                discover_uci_configs,
                discover_uci_sensitive_fields
            )
            result['ansible_facts']['openwrt_uci'] = filtered_uci
        except Exception as e:
            if discover_uci_strict:
                result['failed'] = True
                result['msg'] = f"UCI filtering failed: {e}"
            # If not strict, just return unfiltered data
        
        return result
    
    def _filter_uci_data(self, uci_data, strict, exclude_list, configs_list, sensitive_fields):
        """Filter and mask UCI data based on parameters
        
        Args:
            uci_data: Raw UCI data from shell script
            strict: Fail on null configs
            exclude_list: Configs to exclude
            configs_list: Specific configs to include (if set)
            sensitive_fields: List of dicts with config/section/field to mask
        
        Returns:
            Filtered UCI data dictionary
        """
        configs = uci_data.get('configs', [])
        states = uci_data.get('states', {})
        
        # Determine which configs to keep
        if configs_list:
            # Whitelist mode - only keep specified configs
            filtered_configs = [c for c in configs if c in configs_list]
        else:
            # Blacklist mode - exclude specified configs
            filtered_configs = [c for c in configs if c not in exclude_list]
        
        # Filter states
        filtered_states = {}
        for config in filtered_configs:
            state = states.get(config)
            
            # Handle strict mode - fail if state is null/missing
            if strict and (state is None or config not in states):
                raise Exception(f"Unable to retrieve state for config '{config}'")
            
            if state is not None:
                # Mask sensitive fields
                masked_state = self._mask_sensitive_fields(config, state, sensitive_fields)
                filtered_states[config] = masked_state
        
        return {
            'configs': filtered_configs,
            'states': filtered_states
        }
    
    def _mask_sensitive_fields(self, config_name, config_state, sensitive_fields):
        """Recursively mask sensitive fields in UCI config state
        
        Args:
            config_name: Name of the config (e.g., 'wireless', 'ddns')
            config_state: The config state dictionary
            sensitive_fields: List of dicts with 'config', 'section', 'field' keys
        
        Returns:
            Config state with sensitive fields masked
        """
        if not isinstance(config_state, dict) or not sensitive_fields:
            return config_state
        
        # Build a lookup for this config's sensitive fields
        # Format: {section_type: [field1, field2, ...]}
        sensitive_lookup = {}
        for item in sensitive_fields:
            if not isinstance(item, dict):
                continue
            if item.get('config') == config_name:
                section = item.get('section', '')
                field = item.get('field', '')
                if section and field:
                    if section not in sensitive_lookup:
                        sensitive_lookup[section] = []
                    sensitive_lookup[section].append(field)
        
        # No sensitive fields for this config
        if not sensitive_lookup:
            return config_state
        
        # Deep copy to avoid modifying original
        import copy
        masked_state = copy.deepcopy(config_state)
        
        # Iterate through sections in the config state
        for section_name, section_data in masked_state.items():
            if not isinstance(section_data, dict):
                continue
            
            # Check if this section has a '.type' field
            section_type = section_data.get('.type', '')
            
            # Mask fields if this section type is in our sensitive lookup
            if section_type in sensitive_lookup:
                for field in sensitive_lookup[section_type]:
                    if field in section_data:
                        section_data[field] = '***MASKED***'
        
        return masked_state
