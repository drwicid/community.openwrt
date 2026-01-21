#!/bin/sh
# shellcheck shell=ash
# Copyright (c) 2017 Markus Weippert
# GNU General Public License v3.0 (see https://www.gnu.org/licenses/gpl-3.0.txt)

NO_EXIT_JSON="1"
PARAMS="discover_uci/b discover_uci_strict/b discover_uci_exclude_list/a discover_uci_configs/a"

JSHN_BIN="${JSHN_BIN:-/usr/bin/jshn}"

discover_uci_configs() {
    local configs cfg_json cfg params states values skip ex
    
    # Check if UCI discovery is enabled
    [ "$discover_uci" = "1" ] || return 1
    
    # Build configs list
    if [ -n "$_discover_uci_configs" ]; then
        configs=""
        json_set_namespace params
        json_select "$_discover_uci_configs"
        local idx=1
        while json_get_var cfg "$idx" 2>/dev/null; do
            configs="$configs $cfg"
            idx=$((idx + 1))
        done
        json_set_namespace result
    else
        cfg_json="$(ubus -S call uci configs 2>/dev/null)" || return 1
        configs="$(echo "$cfg_json" | jsonfilter -e '@.configs[*]' 2>/dev/null || true)"
        [ -n "$configs" ] || return 1
    fi
    
    json_set_namespace uci
    json_init
    
    json_add_array "configs"
    for cfg in $configs; do
        json_add_string "" "$cfg"
    done
    json_close_array
    
    json_add_object "states"
    for cfg in $configs; do
        # Exclude filtering
        if [ -n "$_discover_uci_exclude_list" ]; then
            skip=false
            json_set_namespace params
            json_select "$_discover_uci_exclude_list"
            local idx=1
            local ex_item
            while json_get_var ex_item "$idx" 2>/dev/null; do
                [ "$cfg" = "$ex_item" ] && skip=true && break
                idx=$((idx + 1))
            done
            json_set_namespace uci
            [ "$skip" = "true" ] && continue
        fi
        
        params="$(json_init; json_add_string config "$cfg"; json_dump)"
        
        if ! states="$(ubus -S call uci state "$params" 2>/dev/null)"; then
            if [ "$discover_uci_strict" = "1" ]; then
                json_cleanup
                json_set_namespace result
                return 1
            fi
            json_add_null "$cfg"
            continue
        fi
        
        values="$(echo "$states" | jsonfilter -e '@.values' 2>/dev/null || true)"
        [ -n "$values" ] || values='{}'
        
        # Add config object and inline values
        json_add_object "$cfg"
        eval "$(
            "$JSHN_BIN" -r "$values" 2>/dev/null | sed '1{/^json_init;$/d;}'
        )"
        json_close_object
    done
    json_close_object
    
    local uci_data="$(json_dump)"
    json_cleanup
    json_set_namespace result
    echo -n "$uci_data"
}

DISCOVER_UCI_STRICT="${discover_uci_strict:-false}"
DISCOVER_UCI_EXCLUDE_LIST="${_discover_uci_exclude_list:-}"
DISCOVER_UCI_CONFIGS="${_discover_uci_configs:-}"

discover_uci_configs() {
    local configs cfg_json cfg params states values skip ex
    
    # Build configs list
    if [ -n "$DISCOVER_UCI_CONFIGS" ]; then
        configs="$DISCOVER_UCI_CONFIGS"
    else
        cfg_json="$(ubus -S call uci configs 2>/dev/null)" || return 1
        configs="$(echo "$cfg_json" | jsonfilter -e '@.configs[*]' 2>/dev/null || true)"
        [ -n "$configs" ] || return 1
    fi
    
    json_set_namespace uci
    json_init
    
    json_add_array "configs"
    for cfg in $configs; do
        json_add_string "" "$cfg"
    done
    json_close_array
    
    json_add_object "states"
    for cfg in $configs; do
        # Exclude filtering
        if [ -n "$DISCOVER_UCI_EXCLUDE_LIST" ]; then
            skip=false
            for ex in $DISCOVER_UCI_EXCLUDE_LIST; do
                [ "$cfg" = "$ex" ] && skip=true && break
            done
            [ "$skip" = "true" ] && continue
        fi
        
        params="$(json_init; json_add_string config "$cfg"; json_dump)"
        
        if ! states="$(ubus -S call uci state "$params" 2>/dev/null)"; then
            if [ "$DISCOVER_UCI_STRICT" = "true" ]; then
                json_cleanup
                json_set_namespace result
                return 1
            fi
            json_add_null "$cfg"
            continue
        fi
        
        values="$(echo "$states" | jsonfilter -e '@.values' 2>/dev/null || true)"
        [ -n "$values" ] || values='{}'
        
        # Add config object and inline values
        json_add_object "$cfg"
        eval "$(
            "$JSHN_BIN" -r "$values" 2>/dev/null | sed '1{/^json_init;$/d;}'
        )"
        json_close_object
    done
    json_close_object
    
    local uci_data="$(json_dump)"
    json_cleanup
    json_set_namespace result
    echo -n "$uci_data"
}

add_ubus_fact() {
    set -- ${1//!/ }
    ubus list "$2" > /dev/null 2>&1 || return
    local json="$($ubus call "$2" "$3" 2>/dev/null)"
    echo -n "$delimiter\"$1\":$json"
    delimiter=","
}

main() {
    ubus="/bin/ubus"
    delimiter=","
    echo '{"changed":false,"ansible_facts":'
    dist="OpenWrt"
    dist_version="NA"
    dist_release="NA"
    test -f /etc/openwrt_release && {
        . /etc/openwrt_release
        dist="${DISTRIB_ID:-$dist}"
        dist_version="${DISTRIB_RELEASE:-$dist_version}"
        dist_release="${DISTRIB_CODENAME:-$dist_release}"
    } || test ! -f /etc/os-release || {
        . /etc/os-release
        dist="${NAME:-$dist}"
        dist_version="${VERSION_ID:-$dist_version}"
    }
    dist_major="${dist_version%%.*}"
    json_set_namespace facts
    json_init
    json_add_string ansible_hostname "$(cat /proc/sys/kernel/hostname)"
    json_add_string ansible_distribution "$dist"
    json_add_string ansible_distribution_major_version "$dist_major"
    json_add_string ansible_distribution_release "$dist_release"
    json_add_string ansible_distribution_version "$dist_version"
    json_add_string ansible_os_family OpenWrt
    json_add_boolean ansible_is_chroot "$([ -r /proc/1/root/. ] &&
        { [ / -ef /proc/1/root/. ]; echo $?; } ||
        { [ "$(ls -di / | awk '{print $1}')" -eq 2 ]; echo $?; }
        )"
    dist_facts="$(json_dump)"
    json_cleanup
    json_set_namespace result
    echo "${dist_facts%\}*}"
    for fact in \
            info!system!info \
            devices!network.device!status \
            services!service!list \
            board!system!board \
            wireless!network.wireless!status \
            ; do
        add_ubus_fact "openwrt_$fact"
    done
    echo "$delimiter"'"openwrt_interfaces":{'
    delimiter=""
    for net in $($ubus list); do
        [ "${net#network.interface.}" = "$net" ] ||
            add_ubus_fact "${net##*.}!$net!status"
    done
    echo '}'
    
    # Add UCI configuration discovery if available
    if uci_data="$(discover_uci_configs 2>/dev/null)"; then
        echo "$delimiter"'"openwrt_uci":'
        echo -n "$uci_data"
    fi
    
    echo '}'
}

[ -n "$_ANSIBLE_PARAMS" ] || main
