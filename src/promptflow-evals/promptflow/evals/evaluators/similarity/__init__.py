# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# ---------------------------------------------------------

__path__ = __import__("pkgutil").extend_path(__path__, __name__)  # type: ignore

from promptflow import load_flow
from promptflow.entities import AzureOpenAIConnection
from pathlib import Path


class SimilarityEvaluator:
    def __init__(self, model_config: AzureOpenAIConnection, deployment_name: str):
        """
        Initialize an evaluator configured for a specific Azure OpenAI model.

        :param model_config: Configuration for the Azure OpenAI model.
        :type model_config: AzureOpenAIConnection
        :param deployment_name: Deployment to be used which has Azure OpenAI model.
        :type deployment_name: AzureOpenAIConnection

        **Usage**

        .. code-block:: python

            eval_fn = SimilarityEvaluator(model_config, deployment_name="gpt-4")
            result = eval_fn(
                question="What is the capital of Japan?",
                answer="The capital of Japan is Tokyo.",
                ground_truth="Tokyo is Japan's capital.")
        """

        # Load the flow as function
        current_dir = Path(__file__).resolve().parent
        flow_dir = current_dir / "flow"
        self._flow = load_flow(source=flow_dir)

        # Override the connection
        self._flow.context.connections = {
            "query_llm": {
                "connection": AzureOpenAIConnection(
                    api_base=model_config.api_base,
                    api_key=model_config.api_key,
                    api_version=model_config.api_version,
                    api_type="azure"
                ),
                "deployment_name": deployment_name,
            }
        }

    def __call__(self, *, question: str, answer: str, ground_truth: str, **kwargs):
        """Evaluate similarity.

        :param question: The question to be evaluated.
        :type question: str
        :param answer: The answer to be evaluated.
        :type answer: str
        :param ground_truth: The ground truth to be evaluated.
        :type ground_truth: str
        :return: The similarity score.
        :rtype: dict
        """

        # Run the evaluation flow
        return self._flow(question=question, answer=answer, ground_truth=ground_truth)