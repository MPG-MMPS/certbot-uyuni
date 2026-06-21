"""Tests for certbot_uyuni.installer."""

import unittest
from typing import Any
from unittest import mock

from certbot import errors

from certbot_uyuni.installer import UyuniInstaller


def _mock_proc(
    returncode: int = 0, stdout: bytes = b"", stderr: bytes = b""
) -> mock.MagicMock:
    proc = mock.MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


class UyuniInstallerTest(unittest.TestCase):

    def setUp(self) -> None:
        super().setUp()
        self.config = mock.MagicMock()
        self.config.uyuni_restart_timeout = 0
        self.installer = UyuniInstaller(self.config, "uyuni")
        self.installer.conf = mock.MagicMock(  # type: ignore[method-assign]
            return_value=0
        )

    # -- prepare --

    @mock.patch.object(UyuniInstaller, "_container_running", return_value=True)
    @mock.patch.object(UyuniInstaller, "_cmd_exists", return_value=True)
    def test_prepare(self, _mock_cmd: Any, _mock_running: Any) -> None:
        self.installer.prepare()

    @mock.patch.object(UyuniInstaller, "_cmd_exists", return_value=False)
    def test_prepare_missing_binary(self, _mock_cmd: Any) -> None:
        self.assertRaises(errors.NoInstallationError, self.installer.prepare)

    @mock.patch.object(UyuniInstaller, "_container_running", return_value=False)
    @mock.patch.object(UyuniInstaller, "_cmd_exists", return_value=True)
    def test_prepare_container_not_running(
        self, _mock_cmd: Any, _mock_running: Any
    ) -> None:
        self.assertRaises(errors.NoInstallationError, self.installer.prepare)

    # -- deploy_cert --

    @mock.patch("certbot.display.util.notify")
    @mock.patch("subprocess.run")
    def test_deploy_cert(self, mock_run: Any, _mock_notify: Any) -> None:
        mock_run.return_value = _mock_proc()
        self.installer.deploy_cert(
            "example.com", "/cert.pem", "/key.pem", "/chain.pem", "/fullchain.pem"
        )
        self.assertEqual(mock_run.call_count, 3)
        calls = mock_run.call_args_list
        self.assertEqual(
            calls[0][0][0],
            ["podman", "secret", "create", "--replace", "uyuni-ca", "/chain.pem"],
        )
        self.assertEqual(
            calls[1][0][0],
            ["podman", "secret", "create", "--replace", "uyuni-cert", "/fullchain.pem"],
        )
        self.assertEqual(
            calls[2][0][0],
            ["podman", "secret", "create", "--replace", "uyuni-key", "/key.pem"],
        )

    @mock.patch("subprocess.run")
    def test_deploy_cert_error(self, mock_run: Any) -> None:
        mock_run.return_value = _mock_proc(returncode=1, stderr=b"fail")
        self.assertRaises(
            errors.PluginError,
            self.installer.deploy_cert,
            "example.com",
            "/cert.pem",
            "/key.pem",
            "/chain.pem",
            "/fullchain.pem",
        )

    # -- restart --

    @mock.patch("subprocess.run")
    def test_restart(self, mock_run: Any) -> None:
        mock_run.return_value = _mock_proc()
        self.installer.restart()
        mock_run.assert_called_once_with(
            ["mgradm", "restart"], capture_output=True, check=False
        )

    @mock.patch("subprocess.run")
    def test_restart_failure(self, mock_run: Any) -> None:
        mock_run.return_value = _mock_proc(returncode=1, stderr=b"fail")
        self.assertRaises(errors.MisconfigurationError, self.installer.restart)

    @mock.patch("time.sleep")
    @mock.patch("subprocess.run")
    def test_restart_waits_for_healthy(self, mock_run: Any, _mock_sleep: Any) -> None:
        self.installer.conf = mock.MagicMock(  # type: ignore[method-assign]
            return_value=10
        )
        mock_run.side_effect = [
            _mock_proc(),
            _mock_proc(stdout=b"healthy"),
        ]
        self.installer.restart()
        self.assertEqual(mock_run.call_count, 2)

    @mock.patch("time.monotonic")
    @mock.patch("time.sleep")
    @mock.patch("subprocess.run")
    def test_restart_healthy_timeout(
        self, mock_run: Any, _mock_sleep: Any, mock_time: Any
    ) -> None:
        self.installer.conf = mock.MagicMock(  # type: ignore[method-assign]
            return_value=5
        )
        mock_run.side_effect = [
            _mock_proc(),
            _mock_proc(stdout=b"starting"),
        ]
        mock_time.side_effect = [0, 0, 10]
        self.assertRaises(errors.MisconfigurationError, self.installer.restart)

    # -- get_all_names --

    @mock.patch("subprocess.run")
    def test_get_all_names(self, mock_run: Any) -> None:
        mock_run.return_value = _mock_proc(stdout=b"uyuni.example.com\n")
        self.assertEqual(list(self.installer.get_all_names()), ["uyuni.example.com"])

    @mock.patch("subprocess.run")
    def test_get_all_names_empty(self, mock_run: Any) -> None:
        mock_run.return_value = _mock_proc(returncode=1, stderr=b"err")
        self.assertEqual(list(self.installer.get_all_names()), [])

    # -- _container_running --

    @mock.patch("subprocess.run")
    def test_container_running(self, mock_run: Any) -> None:
        mock_run.return_value = _mock_proc(stdout=b"true")
        self.assertTrue(UyuniInstaller._container_running())

    @mock.patch("subprocess.run")
    def test_container_not_running(self, mock_run: Any) -> None:
        mock_run.return_value = _mock_proc(stdout=b"false")
        self.assertFalse(UyuniInstaller._container_running())

    # -- _container_healthy --

    @mock.patch("subprocess.run")
    def test_container_healthy(self, mock_run: Any) -> None:
        mock_run.return_value = _mock_proc(stdout=b"healthy")
        self.assertTrue(UyuniInstaller._container_healthy())

    @mock.patch("subprocess.run")
    def test_container_healthy_running(self, mock_run: Any) -> None:
        mock_run.return_value = _mock_proc(stdout=b"running")
        self.assertTrue(UyuniInstaller._container_healthy())

    @mock.patch("subprocess.run")
    def test_container_unhealthy(self, mock_run: Any) -> None:
        mock_run.return_value = _mock_proc(stdout=b"starting")
        self.assertFalse(UyuniInstaller._container_healthy())

    # -- _cmd_exists --

    @mock.patch("shutil.which", return_value="/usr/bin/podman")
    def test_cmd_exists(self, _mock_which: Any) -> None:
        self.assertTrue(UyuniInstaller._cmd_exists("podman"))

    @mock.patch("shutil.which", return_value=None)
    def test_cmd_not_exists(self, _mock_which: Any) -> None:
        self.assertFalse(UyuniInstaller._cmd_exists("nonexistent"))

    # -- other interface methods --

    def test_more_info(self) -> None:
        self.assertIsInstance(self.installer.more_info(), str)

    def test_supported_enhancements(self) -> None:
        self.assertEqual(self.installer.supported_enhancements(), [])

    def test_enhance_raises(self) -> None:
        self.assertRaises(
            errors.PluginError, self.installer.enhance, "example.com", "redirect"
        )


if __name__ == "__main__":
    unittest.main()
