import os
import random

import yaml


def extract_code_from_markdown(markdown_text: str, type_: str = None) -> list[str]:
    """
    Extracts code blocks from markdown text.

    Args:
        markdown_text: The markdown text.
        type_: The type of code block to extract (e.g., 'python').

    Returns:
        List of extracted code blocks.
    """
    code_blocks = []
    in_code_block = False
    code_block = []
    for line in markdown_text.split("\n"):
        if line.strip().startswith("```"):
            if in_code_block:
                in_code_block = False
                code_blocks.append("\n".join(code_block))
                code_block = []
            else:
                if type_ is None or line.strip() == f"```{type_}":
                    in_code_block = True
        elif in_code_block:
            code_block.append(line)
    return code_blocks


def load_config(config_file: str | None = None) -> dict:
    if config_file is None:
        config_file = "config.yaml"

    base_path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_path, config_file)

    with open(config_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def pop_random_entry(d: dict):
    key = random.choice(list(d.keys()))
    return key, d.pop(key)
