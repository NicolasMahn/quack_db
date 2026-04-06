"""LLM calls (ported from llm_api_wrapper)."""

import tiktoken
from openai import AzureOpenAI

from quack_db.config import get_settings

MAX_TOKENS = {
    "gpt-5-mini": 128000,
    "default": 128000,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "o1": 200000,
    "o1-mini": 128000,
    "o3-mini": 200000,
    "gemini-2.0-flash": 1048576,
}

model_owner = {
    "azure": ["gpt-4o", "gpt-4o-mini", "o1", "o1-mini", "o3-mini"],
    "google": [
        "gemini-2.0-flash",
        "gemini-2.0-flash-thinking-exp",
        "gemini-2.0-flash-lite-preview-02-05",
        "learnlm-1.5-pro-experimental",
    ],
}

DEFAULT_MODEL = "gpt-5-mini"


def count_context_length(prompt: str, model: str = "default") -> int:
    if model not in MAX_TOKENS or model == "default":
        model = DEFAULT_MODEL
    if model in model_owner["google"] or model == "gpt-5-mini":
        return len(prompt.split())
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(prompt))


def model_max_context_length(model: str) -> int:
    return MAX_TOKENS.get(model, MAX_TOKENS["default"])


def is_context_too_long(prompt: str, model: str = "default") -> bool:
    return count_context_length(prompt, model) > model_max_context_length(model)


def basic_prompt(
    prompt: str,
    role: str = "You are a helpful assistant.",
    temperature: float = 0.2,
    model: str = "default",
    debug: bool = False,
) -> str:
    if model not in MAX_TOKENS or model == "default":
        model = DEFAULT_MODEL
    if is_context_too_long(prompt, model):
        raise ValueError("Prompt exceeds the maximum token limit.")

    if model in model_owner["google"]:
        return _basic_prompt_gemini(prompt, role, temperature, model)
    return _basic_prompt_azure(prompt, role, temperature, model)


def _basic_prompt_azure(prompt: str, role: str, temperature: float, model: str) -> str:
    s = get_settings()
    client = AzureOpenAI(
        api_key=s.azure_openai_nano_api_key or s.azure_openai_api_key,
        api_version=s.azure_openai_api_version,
        azure_endpoint=(s.azure_openai_nano_endpoint or s.azure_openai_endpoint).rstrip("/"),
    )
    use_fixed = model.startswith("o1") or model.startswith("o3")
    response = client.chat.completions.create(
        model=s.azure_openai_nano_deployment,
        messages=[
            {"role": "system", "content": role},
            {"role": "user", "content": prompt},
        ],
        temperature=float(s.azure_openai_nano_temperature) if use_fixed else temperature,
    )
    return response.choices[0].message.content or ""


def _basic_prompt_gemini(prompt: str, role: str, temperature: float, model: str) -> str:
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise ImportError(
            "Gemini models require the google-genai package: pip install google-genai"
        ) from exc

    s = get_settings()
    client = genai.Client(api_key=s.google_api_key)
    role_prompt = f"TASK: {role} \n---\nPROMPT: {prompt}"
    response = client.models.generate_content(
        model=model,
        contents=role_prompt,
        config=types.GenerateContentConfig(temperature=temperature),
    )
    return response.text or ""
