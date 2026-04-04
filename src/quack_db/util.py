"""Small helpers (YAML config, markdown code blocks)."""

from __future__ import annotations

import random
from pathlib import Path

import yaml


def extract_code_from_markdown(markdown_text: str, type_: str | None = None) -> list[str]:
    """Extract fenced code blocks from markdown (optional ```type filter)."""
    code_blocks: list[str] = []
    in_code_block = False
    code_block: list[str] = []
    for line in markdown_text.split("\n"):
        if line.strip().startswith("```"):
            if in_code_block:
                in_code_block = False
                code_blocks.append("\n".join(code_block))
                code_block = []
            elif type_ is None or line.strip() == f"```{type_}":
                in_code_block = True
        elif in_code_block:
            code_block.append(line)
    return code_blocks


def load_config(config_file: str | None = None) -> dict:
    """Load `config.yaml` shipped next to this package (collection defaults)."""
    if config_file is None:
        config_file = "config.yaml"
    base = Path(__file__).resolve().parent
    config_path = base / config_file
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def pop_random_entry(d: dict):
    key = random.choice(list(d.keys()))
    return key, d.pop(key)
