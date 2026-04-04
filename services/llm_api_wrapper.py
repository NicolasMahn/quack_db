from openai import AzureOpenAI
import tiktoken

from app_config import AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, MODELS

WHITE = "\033[97m"
BLUE = "\033[34m"
GREEN = "\033[32m"
ORANGE = "\033[38;5;208m"
PINK = "\033[38;5;205m"
RESET = "\033[0m"

MAX_TOKENS = {
    "gpt-5-nano": 128000,
    "default": 128000,
}

# Azure deployment name used for OpenAI models.
model_owner = {
    "azure": ["gpt-5-nano"],
    "non_azure_stub": [],
}

DEFAULT_MODEL = "gpt-5-nano"


def count_context_length(prompt: str, model: str = "default") -> int:
    if model not in MAX_TOKENS or model == "default":
        model = DEFAULT_MODEL
    if model == "gpt-5-nano":
        return len(prompt.split())
    else:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(prompt))


def model_max_context_length(model: str) -> int:
    if model in MAX_TOKENS:
        return MAX_TOKENS[model]
    return MAX_TOKENS["default"]


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

    if debug:
        print(f"-------------Model: {model}-------------")
        print(f"{PINK}ROLE:\n{role}{RESET}")
        print(f"{BLUE}PROMPT:\n{prompt}{RESET}")

    if model in model_owner["non_azure_stub"]:
        response = _basic_prompt_non_azure_stub(prompt, role, temperature, model)
    else:
        response = _basic_prompt_azure(prompt, role, temperature, model)

    if debug:
        print(f"{GREEN}RESPONSE:\n{response}{RESET}")
        print("---")
    return response


def _basic_prompt_azure(prompt: str, role: str, temperature: float, model: str) -> str:
    model_cfg = MODELS.get(model, MODELS[DEFAULT_MODEL])
    client = AzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        api_version=model_cfg["api_version"],
        azure_endpoint=AZURE_OPENAI_ENDPOINT.rstrip("/"),
    )
    create_kwargs = dict(
        model=model_cfg.get("deployment", model),
        messages=[
            {"role": "system", "content": role},
            {"role": "user", "content": prompt},
        ],
    )
    if model_cfg.get("temperature_setable", True):
        create_kwargs["temperature"] = temperature
    response = client.chat.completions.create(**create_kwargs)
    return response.choices[0].message.content


def _basic_prompt_non_azure_stub(
    prompt: str, role: str, temperature: float, model: str
) -> str:
    # Stub intentionally kept for future non-Azure providers.
    raise NotImplementedError(
        f"Non-Azure model provider for '{model}' is currently disabled."
    )


