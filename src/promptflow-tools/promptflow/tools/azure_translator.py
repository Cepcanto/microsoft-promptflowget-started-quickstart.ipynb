import traceback

from promptflow.core.tool import ToolProvider, tool
from promptflow.connections import CustomConnection
from promptflow.core.tools_manager import register_builtins

debug = False


class AzureTranslator(ToolProvider):
    """
    Doc reference :
    https://learn.microsoft.com/en-us/azure/cognitive-services/translator/text-sdk-overview?tabs=python
    """

    def __init__(self, connection: CustomConnection):
        super().__init__()
        self.connection = connection

    @tool
    def get_translation(self, input_text: str, source_language: str, target_language: str = "en"):
        import uuid

        traceId = str(uuid.uuid4())
        try:
            import uuid

            import requests

            # If you encounter any issues with the base_url or path, make sure
            # that you are using the latest endpoint:
            # https://docs.microsoft.com/azure/cognitive-services/translator/reference/v3-0-translate
            print(f"{traceId}: Translate from {source_language} to {target_language}")
            path = "/translate?api-version=3.0"
            params = f"&from={source_language}&to={target_language}"
            constructed_url = self.connection.api_endpoint + path + params
            if debug:
                print(f"{traceId} {constructed_url}")

            headers = {
                "Ocp-Apim-Subscription-Key": self.connection.api_key,
                "Ocp-Apim-Subscription-Region": self.connection.api_region,
                "Content-type": "application/json",
                "X-ClientTraceId": traceId,
            }
            if debug:
                print(f"{traceId} {headers}")
            # You can pass more than one object in body.
            body = [{"text": input_text}]
            request = requests.post(constructed_url, headers=headers, json=body)
            response = request.json()
            if debug:
                print(f"{traceId} {response}")

            translated_text = response[0]["translations"][0]["text"]
            print(f"{traceId} Completed")
            return translated_text
        except Exception:
            error_msg = traceback.format_exc()
            return f"{traceId} Exception {error_msg}"


register_builtins(AzureTranslator)
