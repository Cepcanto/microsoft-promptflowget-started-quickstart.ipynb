# flake8: noqa: E402
import os
import sys

from promptflow import tool

# append chat_with_pdf to sys.path so code inside it can discover its modules
sys.path.append(f"{os.path.dirname(__file__)}/chat_with_pdf")
from chat_with_pdf.rewrite_question import rewrite_question


@tool
def rewrite_question_tool(question: str, history: list):
    return rewrite_question(question, history)
