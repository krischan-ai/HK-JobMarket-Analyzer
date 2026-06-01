from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pandas as pd


class Translator:
    """前端中文化翻译器，支持地点、类别的中文转换"""

    def __init__(self):
        i18n_dir = Path(__file__).resolve().parent.parent.parent / "config" / "i18n"
        with open(i18n_dir / "locations_zh.json", "r", encoding="utf-8") as f:
            self.location_map: dict[str, str] = json.load(f)
        with open(i18n_dir / "categories_zh.json", "r", encoding="utf-8") as f:
            self.category_map: dict[str, str] = json.load(f)

    def location_en_to_zh(self, en: str) -> str:
        if not en or not isinstance(en, str):
            return en
        return self.location_map.get(en.strip(), en)

    def category_en_to_zh(self, en: str) -> str:
        if not en or not isinstance(en, str):
            return en
        return self.category_map.get(en, en)

    def translate_df(self, df: pd.DataFrame) -> pd.DataFrame:
        if "location" in df.columns:
            df = df.copy()
            df["location"] = df["location"].apply(self.location_en_to_zh)
        return df

    def translate_skills(self, skills: dict) -> dict:
        if not skills:
            return skills
        return {self.category_en_to_zh(k): v for k, v in skills.items()}


_translator: Optional[Translator] = None


def get_translator() -> Translator:
    global _translator
    if _translator is None:
        _translator = Translator()
    return _translator
