from __future__ import annotations

import base64
import os
from pathlib import Path

from .env import parse_bool_env
from .prompt import MASTER_SYSTEM_PROMPT_TEMPLATE


def invoke_llm_with_full_video(*, video_path: str, answer_key_json: str):
    """Call an LLM via langchain-aws using Bedrock Converse.

    IMPORTANT: Sends the *entire* video as a single file block.
    Model support for video depends on the selected Bedrock model.
    """

    if not parse_bool_env("ENABLE_LLM", default=False):
        raise RuntimeError("LLM is disabled (set ENABLE_LLM=1 to enable)")

    model_id = (os.getenv("BEDROCK_MODEL_ID") or "").strip()
    if not model_id:
        raise RuntimeError("Missing required environment variable: BEDROCK_MODEL_ID")

    # Import inside function so worker can run without Bedrock access when disabled.
    from langchain_aws import ChatBedrockConverse

    # Avoid importing app.* here; runner already does that after env load.
    from app.serializers import VideoExtractionResult

    region_name = (os.getenv("BEDROCK_REGION") or os.getenv("AWS_REGION") or "").strip() or None
    temperature = float(os.getenv("LLM_TEMPERATURE", "0"))
    max_tokens = int(os.getenv("LLM_MAX_TOKENS", "4096"))

    llm = ChatBedrockConverse(
        model_id=model_id,
        region_name=region_name,
        temperature=temperature,
        max_tokens=max_tokens,
    ).with_structured_output(VideoExtractionResult)

    system_prompt = MASTER_SYSTEM_PROMPT_TEMPLATE.format(answer_key_json=answer_key_json)

    video_bytes = Path(video_path).read_bytes()
    max_mb = float(os.getenv("LLM_MAX_VIDEO_MB", "30"))
    if len(video_bytes) > int(max_mb * 1024 * 1024):
        raise RuntimeError(
            f"Video too large for configured limit: {len(video_bytes)} bytes. "
            f"Increase LLM_MAX_VIDEO_MB (currently {max_mb})."
        )

    video_block = {
        "type": "file",
        "mime_type": os.getenv("LLM_VIDEO_MIME_TYPE", "video/mp4"),
        "base64": base64.b64encode(video_bytes).decode("utf-8"),
        "name": Path(video_path).name,
    }

    messages = [
        {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Process the attached video using the rules above and return JSON matching the schema.",
                },
                video_block,
            ],
        },
    ]

    try:
        return llm.invoke(messages)
    except Exception as exc:
        raise RuntimeError(
            "LLM invocation failed. Confirm the selected Bedrock model supports file inputs for the provided mime "
            "type (video) and that payload size is within limits. "
            f"Underlying error: {exc}"
        ) from exc
