"""加载 RAG 项目使用的提示词。"""

import os
from typing import Any

import yaml

from utils.logger_handler import logger
from utils.path_tool import get_abs_path


_PROMPTS_CONFIG_PATH = get_abs_path(os.path.join("config", "prompts.yml"))


def _load_prompts_config() -> dict[str, Any]:
    """读取并验证 prompts.yml 配置。"""
    if not os.path.isfile(_PROMPTS_CONFIG_PATH):
        raise FileNotFoundError(
            f"Prompts config file does not exist: {_PROMPTS_CONFIG_PATH}"
        )

    with open(_PROMPTS_CONFIG_PATH, "r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    if not isinstance(config, dict):
        raise ValueError(
            f"Prompts config must be a YAML mapping: {_PROMPTS_CONFIG_PATH}"
        )

    return config


def _load_prompt(config_key: str) -> str:
    """根据配置键读取对应的提示词文件。"""
    try:
        logger.info("Loading prompt with config key: %s", config_key)
        config = _load_prompts_config()

        configured_path = config.get(config_key)
        if not isinstance(configured_path, str) or not configured_path.strip():
            raise KeyError(
                f"Missing or invalid config key '{config_key}' "
                f"in {_PROMPTS_CONFIG_PATH}"
            )

        prompt_path = get_abs_path(configured_path)
        if not os.path.isfile(prompt_path):
            raise FileNotFoundError(
                f"Prompt file configured by '{config_key}' "
                f"does not exist: {prompt_path}"
            )

        with open(prompt_path, "r", encoding="utf-8") as prompt_file:
            prompt = prompt_file.read()

        if not prompt.strip():
            raise ValueError(f"Prompt file is empty: {prompt_path}")

        logger.info("Prompt loaded successfully: %s", prompt_path)
        return prompt
    except Exception:
        logger.exception("Failed to load prompt: %s", config_key)
        raise


def load_main_prompt() -> str:
    """加载主 Agent 提示词。

    :return: 主 Agent 提示词文本。
    """
    return _load_prompt("main_prompt_path")


def load_rag_summarize_prompt() -> str:
    """加载 RAG 检索总结提示词。

    :return: RAG 检索总结提示词文本。
    """
    return _load_prompt("rag_summarize_prompt_path")


def load_report_prompt() -> str:
    """加载报告生成提示词。

    :return: 报告生成提示词文本。
    """
    return _load_prompt("report_prompt_path")
