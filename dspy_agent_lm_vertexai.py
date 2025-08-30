import dspy
import os


def get_vertexai_lm(model:str, reasoning_effort:str) -> dspy.LM:
    """
    Make sure to set VERTEXAI_PROJECT, VERTEXAI_LOCATION as environment variables
    """
    if not os.getenv("VERTEXAI_PROJECT") or not os.getenv("VERTEXAI_LOCATION"):
        raise ValueError("VERTEXAI_PROJECT and VERTEXAI_LOCATION must be set as environment variables")

    return dspy.LM(model=model, reasoning_effort=reasoning_effort)
    