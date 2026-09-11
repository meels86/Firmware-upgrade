# NetScaler firmware upgrade pipeline

Two independent GitLab CI paths for staged Citrix ADC/NetScaler upgrades:

- **SDX** - upgrades the SDX platform (Management Service / SVM) itself.
- **VPX** - upgrades VPX tenant instances, plus saves/compares the running
  configuration around the upgrade.

Every script is Python, and every device interaction goes through the
**NITRO REST API** over HTTPS (plus one read-only SNMP GET for the SDX
power-supply check) - there is no SSH, SCP, or CLI command execution
against the appliances anywhere in this pipeline. See
`scripts/lib/nitro_client.py` for the API client and
`docs/citrix-api-notes.md` for which NITRO calls are well documented and
which need confirming against your firmware version.

Both paths share the same shape: fetch + checksum the firmware once, then
roll it out in **waves** (canary -> DR -> production). Each wave:

1. **Precheck** - disk space, interface up/up, power supply health (SDX
   only) captured to a JSON artifact. VPX also captures the running config.
2. **Upgrade** - uploads the firmware to each device in the wave (in
   parallel) via the NITRO `systemfile` resource and triggers the upgrade.
3. **Postcheck** - re-runs the same checks, produces a pre/post
   **compare** artifact, and (VPX only) diffs the running config.
4. **Gate** - a manual "promote" job that must be clicked before the next
   wave starts. This is on top of the automatic gate: if postcheck or the
   compare finds a regression, the job fails and the pipeline stops before
   the gate is even reachable.

## Running it

In GitLab, use **Run pipeline** and set:

- `UPGRADE_TARGET`: `sdx` or `vpx` - selects which of the two paths runs.
  Jobs for the other path are skipped entirely via `rules`.
- `FIRMWARE_SOURCE`: `s3` or `smb` - see "Firmware source" below.
- `EXPECTED_SHA256`: the known-good checksum for the build, if you have one.

This pipeline intentionally does **not** run on every `git push`
(`workflow:rules` only allows `web`, `trigger`, `api`, and `schedule`
sources) - it upgrades production hardware and should be started
deliberately.

Required CI/CD variables (credentials, share/bucket details) are listed in
`config/pipeline.env.example`. Mark every secret as **Masked** and
**Protected** in Settings > CI/CD > Variables. `NS_API_USERNAME` /
`NS_API_PASSWORD` authenticate to the NITRO API on both the SDX SVM and
VPX instances (stateless per-request headers - see
`scripts/lib/nitro_client.py`).

## Firmware source: S3 vs. a Windows share

Both are implemented, in pure Python (boto3 for S3, the `smbclient`
package for SMB - no external CLI tools); pick with `FIRMWARE_SOURCE`. As
a rule of thumb:

- **S3** is the better default when your runners have outbound access to
  AWS - it gives you versioning, IAM-scoped access, and no dependency on
  line-of-sight to an internal file server.
- **SMB** makes more sense when your GitLab runners live on-prem next to
  the existing Windows share and have no route to S3/the internet, or your
  organization already manages firmware distribution that way.

## Device inventory and waves

`config/waves.sdx.yml` and `config/tenants.vpx.yml` are the human-readable
inventory. The actual device lists the pipeline runs against are the
`parallel:matrix` YAML anchors near the top of `ci/sdx-pipeline.yml` /
`ci/vpx-pipeline.yml` (GitLab requires matrix values to be static at
pipeline-compile time, so they can't be read from an external file
directly). Keep both in sync.

To add a wave or more devices per wave: copy one of the `*_deviceN`
anchors, add entries, and copy the four wave jobs (`precheck`, `upgrade`,
`postcheck`, `promote`) with the new stage names added to the `stages:`
list in `.gitlab-ci.yml`.

If the fleet grows large enough that hand-maintaining these matrices is
painful, the natural next step is a "generate pipeline" job that reads the
YAML inventory and emits a child-pipeline YAML consumed via
`trigger: include: artifact:` - not implemented here to keep this pipeline
straightforward to read and adapt.

## Artifacts

Every job writes into `artifacts/<device-name>/`, kept for 90 days:

- `health-pre.json` / `health-post.json` - disk, interface, and (SDX)
  power-supply results, pulled directly from NITRO as structured JSON.
- `health-compare.json` / `.md` - pass/fail verdict and findings.
- `upload-checksum.json` - local SHA256 and local-vs-remote file size for
  the firmware transfer (see "No remote checksum verification" in
  `docs/citrix-api-notes.md` for why this isn't a remote SHA256 compare).
- VPX only: `running-config.pre.txt`, `running-config.post.txt`,
  `running-config.diff.full.txt` (full unified diff), and
  `running-config.diff.summary.txt` (consolidated - only lines actually
  added/removed, ignoring re-ordering and blank/comment noise).

A running-config diff does not fail the pipeline by itself (NetScaler
config is expected to survive a VPX upgrade unchanged, but isn't guaranteed
to byte-for-byte); it's surfaced as an artifact for review. Health-check
regressions (e.g., an interface that was up going down) do fail the job and
block promotion to the next wave.

## Project layout

```
scripts/
  lib/            # NitroClient (the only thing that talks to appliances),
                   # logging/env helpers, validate_env.py
  firmware/       # fetch from S3 (boto3) or SMB (smbclient), checksum
  checks/         # disk/interface/psu checks (NITRO + SNMP), compare
  common/         # upload_firmware.py + trigger_upgrade.py - shared by
                   # both SDX and VPX, since both go through the same
                   # NITRO systemfile-upload-then-upgrade-action pattern
  vpx/            # running-config save/compare (VPX-only)
```

Every script reads its target device from `DEVICE_NAME`/`MGMT_IP`/
`PLATFORM` (set per-job by the CI `parallel:matrix`) rather than taking
them as arguments, so the same script works unmodified for any device in
any wave. Run one locally with, e.g.:

```
export PYTHONPATH="$(pwd)/scripts"
export DEVICE_NAME=sdx-lab-01 MGMT_IP=10.10.1.11 PLATFORM=sdx
export NS_API_USERNAME=nsroot NS_API_PASSWORD=...
python3 scripts/checks/health_check.py pre
```

## Important: confirm vendor-specific NITRO calls for your firmware version

This pipeline is a working scaffold, not a turnkey solution - a few of the
NITRO calls are version- and platform-specific enough that they should be
validated against your actual NetScaler firmware version before running
anything beyond a lab appliance. See `docs/citrix-api-notes.md` for
exactly which calls to check and why - most notably the upgrade-trigger
action itself.
