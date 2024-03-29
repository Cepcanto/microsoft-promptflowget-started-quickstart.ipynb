# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# ---------------------------------------------------------

import subprocess
import sys

import pytest
import requests

from promptflow._cli._pf.entry import main
from promptflow._sdk._service.utils.utils import get_port_from_config, get_random_port, kill_exist_service


@pytest.mark.e2etest
class TestPromptflowServiceCLI:
    def _run_pfs_command(self, *args):
        """Run a pfs command with the given arguments."""
        origin_argv = sys.argv
        try:
            sys.argv = ["pf", "service"] + list(args)
            main()
        finally:
            sys.argv = origin_argv

    def _test_start_service(self, port=None, force=False):
        command = f"pf service start --port {port}" if port else "pf service start"
        if force:
            command = f"{command} --force"
        start_pfs = subprocess.Popen(command, shell=True)
        # Wait for service to be started
        start_pfs.wait()
        assert self._is_service_healthy()
        stop_command = "pf service stop"
        stop_pfs = subprocess.Popen(stop_command, shell=True)
        stop_pfs.wait()

    def _is_service_healthy(self, port=None):
        port = port or get_port_from_config()
        response = requests.get(f"http://localhost:{port}/heartbeat")
        return response.status_code == 200

    def test_start_service(self):
        try:
            # start pfs by pf.yaml
            self._test_start_service()
            # Start pfs by specified port
            random_port = get_random_port()
            self._test_start_service(port=random_port, force=True)

            # start pfs
            start_pfs = subprocess.Popen("pf service start", shell=True)
            # Wait for service to be started
            start_pfs.wait()
            assert self._is_service_healthy()
            self._test_start_service(force=True)
            # previous pfs is killed
            assert start_pfs.poll() is not None
        finally:
            port = get_port_from_config()
            kill_exist_service(port=port)

    def test_show_service_status(self, capsys):
        with pytest.raises(SystemExit):
            self._run_pfs_command("show-status")
        start_pfs = subprocess.Popen("pf service start", shell=True)
        # Wait for service to be started
        start_pfs.wait()
        # assert self._is_service_healthy()
        self._run_pfs_command("show-status")
        output, _ = capsys.readouterr()
        assert str(get_port_from_config()) in output
        self._run_pfs_command("stop")
        output, _ = capsys.readouterr()
        assert str(get_port_from_config()) in output
