import pytest

from promptflow.contracts.run_info import Status
from promptflow.executor._result import LineResult
from promptflow.executor.flow_executor import FlowExecutor

from ..utils import get_flow_inputs, get_yaml_file


@pytest.mark.e2etest
class TestExecutorSkip:
    def test_skip(self):
        flow_folder = "conditional_flow_with_skip"
        executor = FlowExecutor.create(get_yaml_file(flow_folder), connections={})
        results = executor.exec_line(get_flow_inputs(flow_folder))
        self.assert_skip_flow_result(results)

    def assert_skip_flow_result(self, result: LineResult):
        # Validate the flow status
        assert result.run_info.status == Status.Completed
        # Validate the flow output
        assert isinstance(result.output, dict)
        assert result.output == {"string": "Result: 10 is even number, skip the next node"}
        # Validate the flow node run infos
        assert len(result.node_run_infos) == 3

        node_run_info = result.node_run_infos["is_even"]
        assert node_run_info.status == Status.Completed
        assert node_run_info.output == {"is_even": True, "message": "10 is even number, skip the next node"}

        node_run_info = result.node_run_infos["conditional_node"]
        assert node_run_info.status == Status.Bypassed
        assert node_run_info.output == "10 is even number, skip the next node"

        node_run_info = result.node_run_infos["print_result"]
        assert node_run_info.status == Status.Completed
        assert node_run_info.output == "Result: 10 is even number, skip the next node"
