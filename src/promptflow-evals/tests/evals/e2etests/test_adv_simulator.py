import asyncio
import os
from typing import Any, Dict, List

import pytest
from azure.identity import DefaultAzureCredential


@pytest.mark.usefixtures("model_config", "recording_injection", "ml_client_config")
@pytest.mark.e2etest
class TestAdvSimulator:
    def test_adv_sim_init_with_prod_url(self, model_config, ml_client_config):
        os.environ.pop("rai_svc_url", None)
        from promptflow.evals.synthetic import AdversarialSimulator

        template = "adv_conversation"
        project_scope = {
            "subscription_id": ml_client_config["subscription_id"],
            "resource_group_name": ml_client_config["resource_group_name"],
            "workspace_name": ml_client_config["project_name"],
            "credential": DefaultAzureCredential(),
        }
        simulator = AdversarialSimulator(template=template, project_scope=project_scope)
        assert callable(simulator)

    def test_incorrect_template_raises_error(self, model_config, ml_client_config):
        os.environ.pop("rai_svc_url", None)
        from promptflow.evals.synthetic import AdversarialSimulator

        project_scope = {
            "subscription_id": ml_client_config["subscription_id"],
            "resource_group_name": ml_client_config["resource_group_name"],
            "workspace_name": ml_client_config["project_name"],
            "credential": DefaultAzureCredential(),
        }

        async def callback(x):
            return x

        simulator = AdversarialSimulator(template="adv_conversation_wrong", project_scope=project_scope)
        with pytest.raises(ValueError):
            asyncio.run(simulator(max_conversation_turns=1, max_simulation_results=1, target=callback))

    def test_adv_qa_sim_responds_with_one_response(self, model_config, ml_client_config):
        os.environ.pop("rai_svc_url", None)
        from promptflow.evals.synthetic import AdversarialSimulator

        template = "adv_qa"
        project_scope = {
            "subscription_id": ml_client_config["subscription_id"],
            "resource_group_name": ml_client_config["resource_group_name"],
            "workspace_name": ml_client_config["project_name"],
            "credential": DefaultAzureCredential(),
        }

        async def callback(
            messages: List[Dict], stream: bool = False, session_state: Any = None, context: Dict[str, Any] = None
        ) -> dict:
            question = messages["messages"][0]["content"]
            response_from_acs, temperature = question, 0.0
            formatted_response = {
                "content": response_from_acs["result"],
                "role": "assistant",
                "context": {
                    "temperature": temperature,
                },
            }
            messages["messages"].append(formatted_response)
            return {
                "messages": messages["messages"],
                "stream": stream,
                "session_state": session_state,
                "context": context,
            }

        simulator = AdversarialSimulator(template=template, project_scope=project_scope)

        outputs = asyncio.run(
            simulator(
                max_conversation_turns=1,
                max_simulation_results=1,
                target=callback,
                api_call_retry_limit=3,
                api_call_retry_sleep_sec=1,
                api_call_delay_sec=30,
                concurrent_async_task=1,
            )
        )
        assert len(outputs) == 1

    def test_adv_conversation_sim_responds_with_responses(self, model_config, ml_client_config):
        os.environ.pop("rai_svc_url", None)
        from promptflow.evals.synthetic import AdversarialSimulator

        template = "adv_conversation"
        project_scope = {
            "subscription_id": ml_client_config["subscription_id"],
            "resource_group_name": ml_client_config["resource_group_name"],
            "workspace_name": ml_client_config["project_name"],
            "credential": DefaultAzureCredential(),
        }

        async def callback(
            messages: List[Dict], stream: bool = False, session_state: Any = None, context: Dict[str, Any] = None
        ) -> dict:
            question = messages["messages"][0]["content"]

            formatted_response = {"content": question, "role": "assistant"}
            messages["messages"].append(formatted_response)
            return {
                "messages": messages["messages"],
                "stream": stream,
                "session_state": session_state,
                "context": context,
            }

        simulator = AdversarialSimulator(template=template, project_scope=project_scope)

        outputs = asyncio.run(
            simulator(
                max_conversation_turns=2,
                max_simulation_results=1,
                target=callback,
                api_call_retry_limit=3,
                api_call_retry_sleep_sec=1,
                api_call_delay_sec=30,
                concurrent_async_task=1,
            )
        )
        assert len(outputs) == 1
        print(outputs)
        assert len(outputs[0]["messages"]) == 4

    def test_adv_summarization_sim_responds_with_responses(self, model_config, ml_client_config):
        os.environ.pop("rai_svc_url", None)
        from promptflow.evals.synthetic import AdversarialSimulator

        template = "adv_summarization"
        project_scope = {
            "subscription_id": ml_client_config["subscription_id"],
            "resource_group_name": ml_client_config["resource_group_name"],
            "workspace_name": ml_client_config["project_name"],
            "credential": DefaultAzureCredential(),
        }

        async def callback(
            messages: List[Dict], stream: bool = False, session_state: Any = None, context: Dict[str, Any] = None
        ) -> dict:
            question = messages["messages"][0]["content"]

            formatted_response = {"content": question, "role": "assistant"}
            messages["messages"].append(formatted_response)
            return {
                "messages": messages["messages"],
                "stream": stream,
                "session_state": session_state,
                "context": context,
            }

        simulator = AdversarialSimulator(template=template, project_scope=project_scope)

        outputs = asyncio.run(
            simulator(
                max_conversation_turns=1,
                max_simulation_results=1,
                target=callback,
                api_call_retry_limit=3,
                api_call_retry_sleep_sec=1,
                api_call_delay_sec=30,
                concurrent_async_task=1,
            )
        )
        print(outputs.to_json_lines())
        print("*****************************")
        assert len(outputs) == 1

        # assert file content exists in request

        # assert len(outputs[0]["messages"]) == 4
