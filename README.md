# Firmware-upgrade

A staged GitLab CI/CD pipeline for upgrading a Citrix ADC (NetScaler)
environment: one path for the SDX platform, one for VPX tenants. Devices
are upgraded in waves with pre/post health checks, checksum-verified
firmware transfer, and (for VPX) a running-config diff, all captured as
pipeline artifacts.

Every script is Python, and every device interaction goes through the
NITRO REST API - no SSH, SCP, or CLI command execution against the
appliances anywhere in this pipeline.

See [`docs/PIPELINE.md`](docs/PIPELINE.md) for how it works and how to run
it, and [`docs/citrix-api-notes.md`](docs/citrix-api-notes.md) for the
vendor-specific NITRO calls worth double-checking against your firmware
version before running this beyond a lab appliance.
