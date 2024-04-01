import tempfile
from unittest.mock import MagicMock, patch

import pytest
from azure.ai.ml import ManagedIdentityConfiguration
from azure.ai.ml.entities import IdentityConfiguration
from pytest_mock import MockerFixture

from promptflow._sdk._errors import RunOperationParameterError
from promptflow._sdk._utils import parse_otel_span_status_code
from promptflow._sdk.entities import Run
from promptflow.azure import PFClient
from promptflow.exceptions import UserErrorException

FLOWS_DIR = "./tests/test_configs/flows"
DATAS_DIR = "./tests/test_configs/datas"
EAGER_FLOWS_DIR = "./tests/test_configs/eager_flows"


@pytest.mark.unittest
class TestRunOperations:
    def test_download_run_with_invalid_workspace_datastore(self, pf: PFClient, mocker: MockerFixture):
        # test download with invalid workspace datastore
        mocker.patch.object(pf.runs, "_validate_for_run_download")
        mocker.patch.object(pf.runs, "_workspace_default_datastore", "test")
        with tempfile.TemporaryDirectory() as tmp_dir:
            with pytest.raises(UserErrorException, match="workspace default datastore is not supported"):
                pf.runs.download(run="fake_run_name", output=tmp_dir)

    def test_run_with_identity(self, pf: PFClient, mocker: MockerFixture):
        mock_workspace = MagicMock()
        mock_workspace.identity = IdentityConfiguration(
            type="managed",
            user_assigned_identities=[
                ManagedIdentityConfiguration(client_id="fake_client_id", resource_id="fake_resource_id")
            ],
        )
        mocker.patch.object(pf.runs, "_workspace", mock_workspace)
        run = Run(
            flow=f"{FLOWS_DIR}/print_env_var",
            data=f"{DATAS_DIR}/env_var_names.jsonl",
            name="test_run",
            identity={"type": "managed", "client_id": "fake_client_id"},
        )
        pf.runs._resolve_identity(run)
        rest_run = run._to_rest_object()
        assert rest_run.identity == "fake_resource_id"

        mock_workspace = MagicMock()
        mock_workspace.primary_user_assigned_identity = "fake_primary_user_assigned_identity"
        mocker.patch.object(pf.runs, "_workspace", mock_workspace)
        run = Run(
            flow=f"{FLOWS_DIR}/print_env_var",
            data=f"{DATAS_DIR}/env_var_names.jsonl",
            name="test_run",
            identity={"type": "managed"},
        )
        pf.runs._resolve_identity(run)
        rest_run = run._to_rest_object()
        assert rest_run.identity == "fake_primary_user_assigned_identity"

    @pytest.mark.parametrize(
        "identity, error_msg",
        [
            # no primary_user_assigned_identity
            ({"type": "managed"}, "Primary user assigned identity not found in workspace"),
            # no user_assigned_identities
            ({"type": "managed", "client_id": "xxx"}, "Failed to get identities with id"),
            # unsupported type
            ({"type": "managed_identity"}, "is not supported"),
        ],
    )
    def test_run_with_identity_illegal_cases(self, pf: PFClient, identity, error_msg):
        mock_workspace = MagicMock(primary_user_assigned_identity=None)
        with patch.object(pf.runs, "_workspace", mock_workspace):
            run = Run(
                flow=f"{FLOWS_DIR}/print_env_var",
                data=f"{DATAS_DIR}/env_var_names.jsonl",
                name="test_run",
                identity=identity,
            )
            with pytest.raises(UserErrorException) as e:
                pf.runs._resolve_identity(run)
            assert error_msg in str(e)

    def test_flex_flow_with_imported_func(self, pf: PFClient):
        # TODO(3017093): won't support this for now
        with pytest.raises(UserErrorException) as e:
            pf.run(
                flow=parse_otel_span_status_code,
                data=f"{DATAS_DIR}/simple_eager_flow_data.jsonl",
                # set code folder to avoid snapshot too big
                code=f"{EAGER_FLOWS_DIR}/multiple_entries",
                column_mapping={"value": "${data.input_val}"},
            )
        assert "not supported" in str(e)

    def test_wrong_workspace_type(
        self, mocker: MockerFixture, subscription_id: str, resource_group_name: str, workspace_name: str
    ):
        from sdk_cli_azure_test._azure_utils import get_cred

        from promptflow.recording.azure import get_pf_client_for_replay

        # the test target "_workspace_default_datastore" is a cached property so the pf client needs to be recreated
        # otherwise the test may fail due to the cached value
        if pytest.is_replay:
            pf = get_pf_client_for_replay()
        else:
            pf = PFClient(
                credential=get_cred(),
                subscription_id=subscription_id,
                resource_group_name=resource_group_name,
                workspace_name=workspace_name,
            )
        # test wrong workspace type "hub"
        mocker.patch.object(pf.runs._workspace, "_kind", "hub")
        with pytest.raises(RunOperationParameterError, match="Failed to get default workspace datastore"):
            datastore = pf.runs._workspace_default_datastore
            assert datastore
