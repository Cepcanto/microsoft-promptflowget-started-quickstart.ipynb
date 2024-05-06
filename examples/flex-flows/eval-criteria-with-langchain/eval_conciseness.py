from dataclasses import dataclass

from langchain_community.chat_models import AzureChatOpenAI, ChatAnthropic
from langchain.evaluation import load_evaluator

from promptflow.connections import CustomConnection
from promptflow.tracing import trace
from promptflow.client import PFClient


@dataclass
class Result:
    reasoning: str
    value: str
    score: float


class LangChainEvaluator:
    def __init__(self, custom_connection: CustomConnection):
        self.custom_connection = custom_connection

        # create llm according to the secrets in custom connection
        if "anthropic_api_key" in self.custom_connection.secrets:
            self.llm = ChatAnthropic(
                temperature=0, anthropic_api_key=self.custom_connection.secrets["anthropic_api_key"]
            )
        elif "openai_api_key" in self.custom_connection.secrets:
            self.llm = AzureChatOpenAI(
                deployment_name="gpt-35-turbo",
                openai_api_key=self.custom_connection.secrets["openai_api_key"],
                azure_endpoint=self.custom_connection.secrets["azure_endpoint"],
                openai_api_type="azure",
                openai_api_version="2023-07-01-preview",
                temperature=0,
            )
        else:
            raise ValueError("No valid API key found in the connection.")
        # evaluate with langchain evaluator for conciseness
        self.evaluator = load_evaluator("criteria", llm=self.llm, criteria="conciseness")

    @trace
    def __call__(
        self,
        input: str,
        prediction: str,
    ) -> Result:
        """Evaluate with langchain evaluator."""

        eval_result = self.evaluator.evaluate_strings(prediction=prediction, input=input)
        return Result(**eval_result)


if __name__ == "__main__":
    from promptflow.tracing import start_trace

    start_trace()
    pf = PFClient()
    connection = pf.connections.get(name="my_llm_connection", with_secrets=True)
    evaluator = LangChainEvaluator(custom_connection=connection)
    result = evaluator(
        prediction="What's 2+2? That's an elementary question. The answer you're looking for is that two and two is four.",
        input="What's 2+2?",
    )
    print(result)
