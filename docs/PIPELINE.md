# NetScaler firmware upgrade pipeline

Two independent GitLab CI paths for staged Citrix ADC/NetScaler upgrades:

- **SDX** - upgrades the SDX platform (Management Service / SVM) itself.
- **VPX** - upgrades VPX tenant instances, plus saves/compares the running
  configuration around the upgrade.

Both paths share the same shape: fetch + checksum the firmware once, then
roll it out in **waves** (canary -> DR -> production). Each wave:

1. **Precheck** - disk space, interface up/up, power supply health (SDX
   only) captured to a JSON artifact. VPX also captures the running config.
2. **Upgrade** - uploads the firmware to each device in the wave (in
   parallel) and triggers the upgrade.
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
**Protected** in Settings > CI/CD > Variables, and prefer an SSH key (a
GitLab "File" type variable, `NS_SSH_PRIVATE_KEY_FILE`) over a password.

## Firmware source: S3 vs. a Windows share

Both are implemented; pick with `FIRMWARE_SOURCE`. As a rule of thumb:

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
  power-supply results.
- `health-compare.json` / `.md` - pass/fail verdict and findings.
- `upload-checksum.json` - local vs. remote SHA256 for the firmware
  transfer.
- VPX only: `running-config.pre.txt`, `running-config.post.txt`,
  `running-config.diff.full.txt` (full unified diff), and
  `running-config.diff.summary.txt` (consolidated - only lines actually
  added/removed, ignoring re-ordering and blank/comment noise).

A running-config diff does not fail the pipeline by itself (NetScaler
config is expected to survive a VPX upgrade unchanged, but isn't guaranteed
to byte-for-byte); it's surfaced as an artifact for review. Health-check
regressions (e.g., an interface that was up going down) do fail the job and
block promotion to the next wave.

## Speeding up the pipeline

Each job installs its CLI tools (`ssh`, `smbclient`, `jq`, `snmp`) via
`apt-get` in `before_script`, which is slow when repeated across many
matrix jobs. Build `docker/tooling.Dockerfile` once, push it to your
project's container registry, and point `.base.image` in `ci/common.yml`
at it (then drop the `apt-get`/`pip install` lines).

## Important: confirm vendor-specific commands for your firmware version

This pipeline is a working scaffold, not a turnkey solution - a few of the
device interactions are version- and platform-specific enough that they
should be validated against your actual NetScaler firmware version before
running anything beyond a lab appliance. See `docs/citrix-api-notes.md` for
exactly which calls to check and why.
