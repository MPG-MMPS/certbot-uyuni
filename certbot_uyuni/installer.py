"""Uyuni installer plugin for Certbot."""
import shutil
import subprocess
from typing import Callable, List, Optional, Union

from certbot import errors, interfaces
from certbot.display import util as display_util
from certbot.plugins import common


UYUNI_CONTAINER = "uyuni-server"


class UyuniInstaller(common.Plugin, interfaces.Installer):
    """Deploy certificates to Uyuni via podman secrets."""

    description = "Uyuni Server plugin"

    @classmethod
    def add_parser_arguments(cls, add: Callable[..., None]) -> None:
        pass

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

    def get_all_names(self) -> List[str]:
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
        pass

    @staticmethod
    def _container_running() -> bool:
        proc = subprocess.run(
            ["podman", "inspect", "--format",
             "{{.State.Running}}", UYUNI_CONTAINER],
            capture_output=True, check=False,
        )
        return proc.returncode == 0 and proc.stdout.decode().strip() == "true"

    @staticmethod
    def _cmd_exists(cmd: str) -> bool:
        return shutil.which(cmd) is not None
