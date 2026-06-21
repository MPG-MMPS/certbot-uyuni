"""Uyuni installer plugin for Certbot."""
import logging
import shutil
import subprocess
import time
from typing import Callable, Iterable, List, Optional, Union

from certbot import errors, interfaces
from certbot.display import util as display_util
from certbot.plugins import common

logger = logging.getLogger(__name__)

UYUNI_CONTAINER = "uyuni-server"
DEFAULT_RESTART_TIMEOUT = 300


class UyuniInstaller(common.Plugin, interfaces.Installer):
    """Deploy certificates to Uyuni via podman secrets."""

    description = "Uyuni Server plugin"

    @classmethod
    def add_parser_arguments(cls, add: Callable[..., None]) -> None:
        add(
            "restart-timeout",
            default=DEFAULT_RESTART_TIMEOUT, type=int,
            help="Seconds to wait for the Uyuni server to "
                 "come back after restart. "
                 "(default: %d)" % DEFAULT_RESTART_TIMEOUT)

    def prepare(self) -> None:
        for cmd in ("podman", "mgradm"):
            if not self._cmd_exists(cmd):
                raise errors.NoInstallationError(
                    "Could not find a usable '%s' binary. "
                    "Ensure %s exists, the binary is "
                    "executable, and your PATH is set "
                    "correctly." % (cmd, cmd))
        if not self._container_running():
            raise errors.NoInstallationError(
                "Uyuni server container is not running.")

    def more_info(self) -> str:
        return ("Deploys certificates to Uyuni "
                "as podman secrets and restarts the server.")

    def get_all_names(self) -> Iterable[str]:
        fqdn = self._get_uyuni_fqdn()
        if fqdn:
            return [fqdn]
        return []

    def deploy_cert(self, domain: str, cert_path: str, key_path: str,
                    chain_path: str, fullchain_path: str) -> None:
        secrets = {
            "uyuni-ca": chain_path,
            "uyuni-cert": fullchain_path,
            "uyuni-key": key_path,
        }
        for name, path in secrets.items():
            proc = subprocess.run(
                ["podman", "secret", "create", "--replace", name, path],
                capture_output=True, check=False,
            )
            if proc.returncode != 0:
                raise errors.PluginError(
                    "Error updating secret %s:\n%s"
                    % (name, proc.stderr.decode().strip()))
        display_util.notify(
            "Successfully deployed certificate for %s to Uyuni podman secrets"
            % domain)

    def enhance(self, domain: str, enhancement: str,
                options: Optional[Union[List[str], str]] = None) -> None:
        raise errors.PluginError(
            "Enhancements are not supported for Uyuni.")

    def supported_enhancements(self) -> List[str]:
        return []

    def save(self, title: Optional[str] = None,
             temporary: bool = False) -> None:
        # No checkpoint system; secrets are replaced in-place.
        pass

    def rollback_checkpoints(self, rollback: int = 1) -> None:
        # No checkpoint system; secrets are replaced in-place.
        pass

    def recovery_routine(self) -> None:
        # No checkpoint system; secrets are replaced in-place.
        pass

    def config_test(self) -> None:
        # No config files to validate.
        pass

    def restart(self) -> None:
        proc = subprocess.run(
            ["mgradm", "restart"], capture_output=True, check=False,
        )
        if proc.returncode != 0:
            raise errors.MisconfigurationError(
                "Uyuni restart failed:\n%s" % proc.stderr.decode().strip())

        timeout = self.conf("restart-timeout")
        if timeout > 0:
            self._wait_for_healthy(timeout)

    def _wait_for_healthy(self, timeout: int) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._container_healthy():
                return
            time.sleep(1)
        raise errors.MisconfigurationError(
            "Uyuni server did not become healthy within %d seconds." % timeout)

    def _get_uyuni_fqdn(self) -> Optional[str]:
        proc = subprocess.run(
            ["podman", "exec", UYUNI_CONTAINER, "sh", "-c",
             "cat /etc/rhn/rhn.conf 2>/dev/null"
             " | grep 'java.hostname'"
             " | cut -d' ' -f3"],
            capture_output=True, check=False,
        )
        if proc.returncode != 0:
            logger.debug("Could not read Uyuni FQDN: %s",
                         proc.stderr.decode().strip())
            return None
        fqdn = proc.stdout.decode().strip()
        return fqdn or None

    @staticmethod
    def _container_running() -> bool:
        proc = subprocess.run(
            ["podman", "inspect", "--format",
             "{{.State.Running}}", UYUNI_CONTAINER],
            capture_output=True, check=False,
        )
        return proc.returncode == 0 and proc.stdout.decode().strip() == "true"

    @staticmethod
    def _container_healthy() -> bool:
        proc = subprocess.run(
            ["podman", "inspect", "--format",
             "{{ .State.Health.Status }}",
             UYUNI_CONTAINER],
            capture_output=True, check=False,
        )
        status = proc.stdout.decode().strip()
        return proc.returncode == 0 and status in ("healthy", "running")

    @staticmethod
    def _cmd_exists(cmd: str) -> bool:
        return shutil.which(cmd) is not None
