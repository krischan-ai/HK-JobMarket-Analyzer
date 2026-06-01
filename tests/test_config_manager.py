from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.llm_config_manager import LLMConfigManager


class TestLLMConfigManager:
    def test_default_config(self, temp_dir):
        mgr = LLMConfigManager(config_path=temp_dir / "test_llm.json")
        assert not mgr.configured
        assert mgr.load()["api_key"] == ""

    def test_save_and_load(self, temp_dir):
        config_path = temp_dir / "test_llm.json"
        mgr = LLMConfigManager(config_path=config_path)
        mgr.save(api_key="test-key", base_url="https://test.api.com/v1", model="test-model")
        assert mgr.configured
        config = mgr.load()
        assert config["api_key"] == "test-key"
        assert config["base_url"] == "https://test.api.com/v1"
        assert config["model"] == "test-model"

    def test_clear(self, temp_dir):
        config_path = temp_dir / "test_llm.json"
        mgr = LLMConfigManager(config_path=config_path)
        mgr.save(api_key="key")
        assert config_path.exists()
        mgr.clear()
        assert not config_path.exists()

    def test_build_kwargs(self, temp_dir):
        config_path = temp_dir / "test_llm.json"
        mgr = LLMConfigManager(config_path=config_path)
        mgr.save(api_key="key", base_url="https://test.api.com/v1", model="m", timeout=60)
        kwargs = mgr.build_kwargs()
        assert kwargs["api_key"] == "key"
        assert kwargs["api_base"] == "https://test.api.com/v1"
        assert kwargs["model"] == "m"
        assert kwargs["timeout"] == 60

    def test_test_connection_no_config(self, temp_dir):
        mgr = LLMConfigManager(config_path=temp_dir / "test_llm.json")
        ok, msg = mgr.test_connection()
        assert not ok
        assert "未配置" in msg

    def test_save_enables_flag(self, temp_dir):
        config_path = temp_dir / "test_llm.json"
        mgr = LLMConfigManager(config_path=config_path)
        mgr.save(api_key="key")
        config = mgr.load()
        assert config["enabled"] is True
