"""Uyuni installer plugin for Certbot."""
from typing import Callable, List, Optional, Union

from certbot import errors, interfaces
from certbot.plugins import common


UYUNI_CONTAINER = "uyuni-server"


class UyuniInstaller(common.Plugin, interfaces.Installer):
    """Deploy certificates to Uyuni via podman secrets."""

    description = "Uyuni Server plugin"

    @classmethod
    def add_parser_arguments(cls, add: Callable[..., None]) -> None:
        pass

    def prepare(self) -> None:
        pass

    def more_info(self) -> str:
        return ("Deploys certificates to Uyuni "
                "as podman secrets and restarts the server.")

    def get_all_names(self) -> List[str]:
        return []

    def deploy_cert(self, domain: str, cert_path: str, key_path: str,
                    chain_path: str, fullchain_path: str) -> None:
        pass

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
