# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# ---------------------------------------------------------
from pathlib import Path

import pytest
from marshmallow import ValidationError

from promptflow import load_flow
from promptflow._sdk.entities._flows import FlexFlow, Flow
from promptflow.exceptions import ValidationException

FLOWS_DIR = Path("./tests/test_configs/flows")
EAGER_FLOWS_DIR = Path("./tests/test_configs/eager_flows")


@pytest.mark.sdk_test
@pytest.mark.unittest
class TestRun:
    @pytest.mark.parametrize(
        "kwargs",
        [
            {"source": EAGER_FLOWS_DIR / "simple_with_yaml"},
            {"source": EAGER_FLOWS_DIR / "simple_with_yaml" / "flow.flex.yaml"},
        ],
    )
    def test_eager_flow_load(self, kwargs):
        flow = load_flow(**kwargs)
        assert isinstance(flow, FlexFlow)

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"source": FLOWS_DIR / "print_input_flow"},
            {"source": FLOWS_DIR / "print_input_flow" / "flow.dag.yaml"},
        ],
    )
    def test_dag_flow_load(self, kwargs):
        flow = load_flow(**kwargs)
        assert isinstance(flow, Flow)

    def test_flow_load_advanced(self):
        flow = load_flow(source=EAGER_FLOWS_DIR / "flow_with_environment")
        assert isinstance(flow, FlexFlow)
        assert flow._data["environment"] == {"python_requirements_txt": "requirements.txt"}

    @pytest.mark.parametrize(
        "kwargs, error_message, exception_type",
        [
            (
                {"source": EAGER_FLOWS_DIR / "invalid_extra_fields_nodes"},
                "{'nodes': ['Unknown field.']}",
                ValidationError,
            ),
            (
                {
                    "source": EAGER_FLOWS_DIR / "invalid_illegal_path",
                },
                "{'path': ['Unknown field.']}",
                ValidationError,
            ),
        ],
    )
    def test_flow_load_invalid(self, kwargs, error_message, exception_type):
        with pytest.raises(exception_type) as e:
            load_flow(**kwargs)

        assert error_message in str(e.value)

    def test_multiple_flow_load(self):
        with pytest.raises(ValidationException) as e:
            load_flow(EAGER_FLOWS_DIR / "multiple_flow_yaml")

        assert "Both flow.dag.yaml/flow.dag.yml and flow.flex.yaml/flow.flex.yml exist in " in str(e.value)

    def test_multiple_flex_load(self):
        with pytest.raises(ValidationException) as e:
            load_flow(EAGER_FLOWS_DIR / "multiple_flex_yaml")

        assert "Both flow.dag.yaml/flow.dag.yml and flow.flex.yaml/flow.flex.yml exist in " in str(e.value)

    def test_specify_flow_load(self):
        load_flow(EAGER_FLOWS_DIR / "multiple_flow_yaml" / "flow.dag.yaml")
        load_flow(EAGER_FLOWS_DIR / "multiple_flow_yaml" / "flow.flex.yaml")
