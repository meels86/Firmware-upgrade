"""Minimal client for the Citrix ADC / SDX Management Service (SVM) NITRO
REST API.

Every device interaction in this pipeline goes through this client - no
SSH or SCP is used against the appliances, only HTTPS calls to the NITRO
API. Authentication is stateless (X-NITRO-USER / X-NITRO-PASS headers sent
on every request) rather than session-cookie based, so no login session
needs to be kept alive across separate script invocations or across a
device reboot.

See docs/citrix-api-notes.md for which of the calls below are
well-established across firmware versions and which need confirming
against your specific appliance/firmware version.
"""
from __future__ import annotations

import base64
import time
from typing import Any

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class NitroError(RuntimeError):
    """Raised for any NITRO transport error or non-zero errorcode response."""


class NitroClient:
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        verify_ssl: bool = False,
        timeout: int = 30,
    ) -> None:
        self.host = host
        self.base_url = f"https://{host}/nitro/v1"
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self._headers = {
            "X-NITRO-USER": username,
            "X-NITRO-PASS": password,
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/{path}"
        try:
            resp = requests.request(
                method,
                url,
                headers=self._headers,
                params=params,
                json=json_body,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
        except requests.exceptions.RequestException as exc:
            raise NitroError(f"{method} {url} failed: {exc}") from exc

        try:
            body = resp.json() if resp.content else {}
        except ValueError:
            body = {}

        error_code = body.get("errorcode")
        if error_code not in (None, 0) or resp.status_code >= 400:
            raise NitroError(
                f"{method} {url} -> HTTP {resp.status_code}, errorcode={error_code}, "
                f"message={body.get('message', resp.text[:300])}"
            )
        return body

    # --- generic config/stat access ------------------------------------

    def get_config(self, resource: str, args: dict[str, str] | None = None) -> dict[str, Any]:
        params = None
        if args:
            params = {"args": ",".join(f"{k}:{v}" for k, v in args.items())}
        return self._request("GET", f"config/{resource}", params=params)

    def get_stat(self, resource: str) -> dict[str, Any]:
        return self._request("GET", f"stat/{resource}")

    def post_config(
        self, resource: str, payload: dict[str, Any], action: str | None = None
    ) -> dict[str, Any]:
        params = {"action": action} if action else None
        return self._request("POST", f"config/{resource}", params=params, json_body={resource: payload})

    # --- higher-level operations ----------------------------------------

    def save_config(self) -> None:
        """Persist the running configuration to disk (`save ns config`)."""
        self.post_config("nsconfig", {}, action="save")

    def get_running_config(self) -> str:
        body = self.get_config("nsrunningconfig")
        return body.get("nsrunningconfig", {}).get("response", "")

    def upload_file(self, filelocation: str, filename: str, local_path: str) -> None:
        """Upload a file via the `systemfile` resource (base64 body)."""
        with open(local_path, "rb") as fh:
            encoded = base64.b64encode(fh.read()).decode("ascii")
        self.post_config(
            "systemfile",
            {
                "filename": filename,
                "filelocation": filelocation,
                "filecontent": encoded,
                "fileencoding": "BASE64",
            },
        )

    def get_file_info(self, filelocation: str, filename: str) -> dict[str, Any]:
        body = self.get_config("systemfile", args={"filelocation": filelocation, "filename": filename})
        files = body.get("systemfile", [])
        return files[0] if files else {}

    def trigger_upgrade(self, filelocation: str, filename: str, action: str = "upgrade") -> dict[str, Any]:
        """Trigger an install/upgrade from an already-uploaded systemfile.

        CAVEAT: the exact NITRO action for this is not uniformly documented
        across ADC/SDX firmware versions - confirm it for your environment
        and override via NS_UPGRADE_ACTION if it differs from the default.
        See docs/citrix-api-notes.md.
        """
        return self.post_config(
            "systemfile",
            {"filename": filename, "filelocation": filelocation},
            action=action,
        )

    def reboot(self, warm: bool = True) -> None:
        payload = {"warm": True} if warm else {}
        try:
            self.post_config("reboot", payload)
        except NitroError:
            # The appliance typically drops the connection as part of
            # rebooting before it can send back a clean HTTP response -
            # that is expected here, not a failure.
            pass

    def wait_online(self, timeout: int = 900, poll_interval: int = 15, settle_delay: int = 30) -> bool:
        """Poll NITRO until it responds again after a reboot."""
        time.sleep(settle_delay)
        elapsed = settle_delay
        while elapsed < timeout:
            try:
                self.get_config("nsversion")
                return True
            except NitroError:
                pass
            time.sleep(poll_interval)
            elapsed += poll_interval
        return False
