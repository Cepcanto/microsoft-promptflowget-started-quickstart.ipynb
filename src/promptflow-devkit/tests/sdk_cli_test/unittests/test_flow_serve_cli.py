import os
import sys
from pathlib import Path

import pytest
from mock import mock

from promptflow._cli._pf.entry import main

FLOWS_DIR = Path("./tests/test_configs/flows")
EAGER_FLOWS_DIR = Path("./tests/test_configs/eager_flows")


# TODO: move this to a shared utility module
def run_pf_command(*args, cwd=None):
    """Run a pf command with the given arguments and working directory.

    There have been some unknown issues in using subprocess on CI, so we use this function instead, which will also
    provide better debugging experience.
    """
    origin_argv, origin_cwd = sys.argv, os.path.abspath(os.curdir)
    try:
        sys.argv = ["pf"] + list(args)
        if cwd:
            os.chdir(cwd)
        main()
    finally:
        sys.argv = origin_argv
        os.chdir(origin_cwd)


@pytest.mark.sdk_test
@pytest.mark.unittest
class TestRun:
    @pytest.mark.parametrize(
        "source",
        [
            pytest.param(EAGER_FLOWS_DIR / "simple_with_yaml", id="simple_with_yaml_dir"),
            pytest.param(EAGER_FLOWS_DIR / "simple_with_yaml" / "flow.flex.yaml", id="simple_with_yaml_file"),
            pytest.param(FLOWS_DIR / "simple_hello_world", id="simple_hello_world_dir"),
            pytest.param(FLOWS_DIR / "simple_hello_world" / "flow.dag.yaml", id="simple_hello_world_file"),
        ],
    )
    def test_eager_flow_load(self, source: Path):
        with mock.patch("flask.app.Flask.run"):
            run_pf_command(
                "flow",
                "serve",
                "--source",
                source.as_posix(),
                "--skip-open-browser",
            )
