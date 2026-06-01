from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from src.logger import get_logger

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "llm_config.json"

_DEFAULT_CONFIG: dict[str, Any] = {
    "api_key": "",
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat",
    "timeout": 30,
    "enabled": False,
}


def _default_config_path() -> Path:
    return _DEFAULT_CONFIG_PATH


class LLMConfigManager:
    """管理 LLM 配置的持久化读写，支持面板配置优先于 .env 文件

    配置优先级：面板保存的配置 > .env / environment
    """

    def __init__(self, config_path: str | Path | None = None):
        self.config_path = Path(config_path) if config_path else _default_config_path()
        self.logger = get_logger(self.__class__.__name__)

    def load(self) -> dict[str, Any]:
        config = dict(_DEFAULT_CONFIG)
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                config.update(saved)
            except (json.JSONDecodeError, OSError) as e:
                self.logger.warning("Failed to load LLM config from %s: %s", self.config_path, e)
        return config

    def save(self, **kwargs) -> bool:
        config = self.load()
        config.update(kwargs)
        config["enabled"] = bool(config.get("api_key", ""))
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self.logger.info("LLM config saved to %s", self.config_path)
            return True
        except OSError as e:
            self.logger.error("Failed to save LLM config: %s", e)
            return False

    def clear(self) -> bool:
        try:
            if self.config_path.exists():
                os.remove(self.config_path)
            self.logger.info("LLM config cleared")
            return True
        except OSError as e:
            self.logger.error("Failed to clear LLM config: %s", e)
            return False

    @property
    def configured(self) -> bool:
        config = self.load()
        return bool(config.get("api_key")) and bool(config.get("base_url"))

    def build_kwargs(self) -> dict[str, Any]:
        config = self.load()
        return {
            "api_key": config.get("api_key", ""),
            "api_base": config.get("base_url", "https://api.deepseek.com/v1"),
            "model": config.get("model", "deepseek-chat"),
            "timeout": config.get("timeout", 30),
        }

    def test_connection(self, timeout: int = 10) -> tuple[bool, str]:
        if not self.configured:
            return False, "API Key 或 Base URL 未配置"
        kwargs = self.build_kwargs()
        try:
            import requests
            headers = {
                "Authorization": f"Bearer {kwargs['api_key']}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": kwargs["model"],
                "messages": [{"role": "user", "content": "Hello, respond with OK."}],
                "max_tokens": 10,
            }
            url = f"{kwargs['api_base'].rstrip('/')}/chat/completions"
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            resp.raise_for_status()
            return True, f"连接成功！模型: {kwargs['model']}"
        except ImportError:
            return False, "缺少 requests 库"
        except Exception as e:
            return False, f"连接失败: {e}"
