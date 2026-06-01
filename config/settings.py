from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Settings:
    env_file: Path = Path(__file__).resolve().parent.parent / ".env"

    proxy_http: Optional[str] = field(default=None)
    proxy_https: Optional[str] = field(default=None)

    llm_api_key: Optional[str] = field(default=None)
    llm_base_url: str = field(default="https://api.deepseek.com/v1")
    llm_model: str = field(default="deepseek-chat")

    mongodb_uri: str = field(default="mongodb://localhost:27017")
    mongodb_db_name: str = field(default="hk_job_market")

    crawl_delay_min: float = field(default=2.5)
    crawl_delay_max: float = field(default=5.0)
    crawl_max_pages: int = field(default=10)
    crawl_timeout: int = field(default=15)

    log_level: str = field(default="INFO")
    log_file: Optional[str] = field(default=None)

    data_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent / "data")
    output_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent / "output")

    def __post_init__(self):
        self._load_env()

    def _load_env(self):
        try:
            from dotenv import load_dotenv
            load_dotenv(self.env_file)
        except ImportError:
            pass

        for field_name in self.__dataclass_fields__:
            env_val = os.getenv(field_name.upper())
            if env_val is not None:
                current = getattr(self, field_name)
                if isinstance(current, bool):
                    setattr(self, field_name, env_val.lower() in ("true", "1", "yes"))
                elif isinstance(current, int):
                    setattr(self, field_name, int(env_val))
                elif isinstance(current, float):
                    setattr(self, field_name, float(env_val))
                elif isinstance(current, Path):
                    setattr(self, field_name, Path(env_val))
                else:
                    setattr(self, field_name, env_val)

    @property
    def proxies(self) -> Optional[dict]:
        if self.proxy_http or self.proxy_https:
            proxies = {}
            if self.proxy_http:
                proxies["http"] = self.proxy_http
            if self.proxy_https:
                proxies["https"] = self.proxy_https
            return proxies
        return None


settings = Settings()
