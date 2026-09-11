# Citrix ADC/SDX NITRO API notes

This pipeline talks to NetScaler appliances/SVMs exclusively through the
NITRO REST API over HTTPS (plus one read-only SNMP GET for SDX
power-supply status) - there is no SSH, SCP, or CLI command execution
anywhere in this pipeline. A few of the NITRO calls used are well
documented and stable; a few others are not uniformly documented across
firmware versions and should be checked against your specific
appliance/firmware release before running this beyond a lab appliance.

## High confidence (documented, stable NITRO resources)

- `POST /nitro/v1/config/login` and the `X-NITRO-USER`/`X-NITRO-PASS`
  stateless header auth used instead of session cookies
  (`scripts/lib/nitro_client.py`).
- `POST /nitro/v1/config/nsconfig?action=save` - persists the running
  configuration to disk.
- `GET /nitro/v1/config/nsrunningconfig` - returns the full running
  configuration as text (`scripts/vpx/save_running_config.py`).
- `GET /nitro/v1/config/nsversion` - lightweight "is NITRO responding"
  probe, used to detect when an appliance has come back up after a reboot
  (`NitroClient.wait_online`).
- `POST /nitro/v1/config/systemfile` (base64 `filecontent` +
  `fileencoding: BASE64`) and `GET .../systemfile?args=...` to upload a
  file and read back its metadata - the standard NITRO pattern for
  transferring files (certs, license files, and firmware builds) to an
  appliance without shell access.
- `POST /nitro/v1/config/reboot` - triggers an appliance reboot.

## Needs confirmation for your environment

- **The upgrade trigger action**
  (`NitroClient.trigger_upgrade`, `scripts/common/trigger_upgrade.py`,
  `NS_UPGRADE_ACTION`, default `"upgrade"`). Citrix's NITRO API does not
  uniformly document a single, version-stable "install this uploaded
  systemfile as the new firmware" action across ADC/SDX firmware releases
  the way it documents, say, `nsconfig?action=save`. Before running this
  against production:
  1. Confirm the correct action name/resource for your firmware version
     against Citrix's official upgrade documentation for your platform
     (SDX SVM vs. standalone ADC/VPX may differ).
  2. Override `NS_UPGRADE_ACTION` (or adjust `trigger_upgrade()` directly
     if the resource name itself differs, not just the action) accordingly.
  3. If your organization manages this fleet through **Citrix
     Application Delivery Management (ADM)**, ADM exposes its own
     NITRO-style API for orchestrating instance upgrades centrally and is
     Citrix's purpose-built, fully-API-driven path for this - worth
     evaluating as the integration target instead of the appliance's own
     NITRO API if you already run ADM. This pipeline targets the
     appliance/SVM's own NITRO API directly, which is the lower-level but
     more universally available option.
  4. Validate the firmware upload destination directory
     (`NS_FIRMWARE_REMOTE_DIR`, default `/var/mps/mps_images` for SDX and
     `/var/nsinstall` for VPX) against your firmware version.

- **No remote checksum verification.** NITRO has no generic "compute a
  hash of an arbitrary remote file" action, so `upload_firmware.py`
  verifies the transfer by comparing the uploaded file's size (read back
  via `GET .../systemfile`) against the local file, not a true remote
  SHA256 comparison. The SHA256 of the build itself is still computed and
  optionally verified against `EXPECTED_SHA256` when it's fetched
  (`scripts/firmware/verify_checksum.py`) and is recorded in
  `upload-checksum.json` as the checksum of record. If your NITRO
  version's `systemfile` GET response includes a hash/checksum field,
  wire it into `NitroClient.get_file_info` / `upload_firmware.py` for a
  true remote-hash comparison.

- **Power-supply health check via SNMP**
  (`scripts/checks/psu_check.py`). The OIDs used
  (`1.3.6.1.4.1.5951.4.1.1.41.1.1.1.2.<n>`) are drawn from the NetScaler
  enterprise sysHealth MIB, the standard way to monitor PSU status on
  Citrix hardware (there is no NITRO resource for chassis power-supply
  status). Index numbering and the "healthy" value encoding can differ by
  chassis model - confirm against your platform's MIB/OID reference and
  adjust `PSU_STATUS_OIDS` / `OK_VALUES` if needed. If SNMP is disabled in
  your environment, the check reports `UNKNOWN` rather than silently
  passing, which the pipeline treats as non-passing.

- **Disk and interface stat field names**
  (`scripts/checks/disk_check.py`, `scripts/checks/interface_check.py`).
  `disk0size`/`disk0perusage`/`disk1size`/`disk1perusage` (from
  `GET /nitro/v1/stat/system`) and the `state`/`linkstate` fields (from
  `GET /nitro/v1/config/Interface` and `GET /nitro/v1/stat/Interface`) are
  the field names most commonly seen in these NITRO payloads, but Citrix
  does not publish a single canonical schema reference for them. The
  quickest way to confirm: run
  `GET https://<mgmt-ip>/nitro/v1/stat/system` and
  `GET https://<mgmt-ip>/nitro/v1/stat/Interface` against a real appliance
  (with `X-NITRO-USER`/`X-NITRO-PASS` headers) and check the JSON keys in
  the response against the constants at the top of each script.

If anything above doesn't match reality for your appliances, the fix is
localized to the one script/constant named - the surrounding pipeline
(staging, gating, artifacts, checksum recording) does not need to change.
