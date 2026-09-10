# Citrix ADC/SDX command and API notes

This pipeline talks to NetScaler appliances over SSH (nscli/shell) and, for
the SDX platform upgrade, the SVM's NITRO REST API. Most of the commands
used are stable and well documented across firmware versions. A few are
not, and are called out here so they get checked against your specific
firmware/platform revision before you run this beyond a lab appliance.

## High confidence (should work as-is across recent firmware versions)

- `save ns config` - persists the running configuration to disk.
- `show ns runningConfig` - dumps the full running configuration
  (`scripts/vpx/save_running_config.sh`).
- `show ns hardware` - basic platform/serial info, used as a lightweight
  "is the CLI responding again" probe after a reboot
  (`scripts/lib/wait_for_online.sh`).
- `show interface` and its `flags=0x... <ENABLED, UP, UP, ...>` block
  format (`scripts/checks/parse_interfaces.py`).
- `shell <command>` prefix over nscli SSH to run a raw shell command as
  nsroot (used for `df` and `sha256sum`).
- The standard VPX/MPX upgrade procedure: copy the build tgz to
  `/var/nsinstall`, extract it, run `./installns`, then reboot
  (`scripts/vpx/upgrade_vpx.sh`). This is Citrix's documented standalone
  appliance upgrade procedure.
- NITRO login (`POST /nitro/v1/config/login`) and session-cookie auth.

## Needs confirmation for your environment

- **SDX headless upgrade trigger**
  (`scripts/sdx/trigger_upgrade.sh`, `SDX_UPGRADE_NITRO_PATH`). Unlike the
  VPX `installns` flow, Citrix's SDX Management Service has historically
  driven firmware upgrades primarily through the SVM GUI wizard, and the
  exact NITRO resource/action for a scripted, headless equivalent has
  varied between SVM releases. Before running this against production:
  1. Confirm the correct NITRO endpoint and request payload for your SVM
     version against Citrix's official "Upgrading the Citrix ADC SDX
     Appliance Software" documentation.
  2. Adjust `SDX_UPGRADE_NITRO_PATH` (and the request body in
     `trigger_upgrade.sh` if the resource name itself differs) accordingly.
  3. Validate the firmware upload destination directory
     (`SDX_FIRMWARE_REMOTE_DIR`, default `/var/mps/mps_images`) against
     your SVM version - this is where the GUI places uploaded images, but
     confirm it hasn't moved.

- **Power-supply health check via SNMP**
  (`scripts/checks/check_psu_snmp.py`). The OIDs used
  (`1.3.6.1.4.1.5951.4.1.1.41.1.1.1.2.<n>`) are drawn from the NetScaler
  enterprise sysHealth MIB, which is the standard way to monitor PSU status
  on Citrix hardware (there is no direct nscli "show power" command exposed
  to nsroot). Index numbering and the "healthy" value encoding can differ
  by chassis model - confirm against your platform's MIB/OID reference
  (or an `snmpwalk` against a real appliance) and adjust `PSU_STATUS_OIDS`
  / `OK_VALUES` if needed. If SNMP is disabled in your environment, the
  check reports `UNKNOWN` rather than silently passing, which the pipeline
  treats as non-passing.

- **Disk and interface thresholds/paths.** `df -Pk /flash /var` and the
  interface admin/oper parsing assume the common two-partition layout and
  the interface block format shown above; double-check against your own
  appliance's `show interface` and `shell df` output and adjust
  `scripts/checks/parse_df.py` / `parse_interfaces.py` if your firmware
  version's output differs.

If anything above doesn't match reality for your appliances, the fix is
localized to the one script/constant named - the surrounding pipeline
(staging, gating, artifacts, checksum verification) does not need to
change.
