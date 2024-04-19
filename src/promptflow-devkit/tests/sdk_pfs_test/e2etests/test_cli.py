# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# ---------------------------------------------------------

import os
import platform
import subprocess
import sys

import pytest
import requests

from promptflow._cli._pf.entry import main
from promptflow._sdk._service.utils.utils import get_pfs_port, get_port_from_config, kill_exist_service


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

    def test_start_service(self, capsys):
        try:
            # force start pfs
            self._test_start_service(force=True)
            # Start pfs by specified port
            port = get_pfs_port()
            self._test_start_service(port=port, force=True)

            # start pfs
            start_pfs = subprocess.Popen("pf service start", shell=True)
            # Wait for service to be started
            start_pfs.wait()
            assert self._is_service_healthy()

            # show-status
            self._run_pfs_command("status")
            output, _ = capsys.readouterr()
            assert str(port) in output

            self._test_start_service(force=True)
            # previous pfs is killed
            assert start_pfs.poll() is not None
            python_dir = os.path.dirname(sys.executable)
            executable_dir = os.path.join(python_dir, "Scripts") if platform.system() == "Windows" else python_dir
            assert executable_dir in os.environ["PATH"].split(os.pathsep)
        finally:
            port = get_port_from_config()
            kill_exist_service(port=port)
            with pytest.raises(SystemExit):
                self._run_pfs_command("status")
