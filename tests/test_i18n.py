from __future__ import annotations

import pandas as pd
import pytest

from src.i18n.translator import Translator, get_translator


@pytest.fixture(scope="module")
def translator():
    return Translator()


class TestTranslator:
    def test_location_en_to_zh(self, translator):
        assert translator.location_en_to_zh("Central") == "中環"
        assert translator.location_en_to_zh("Quarry Bay") == "鰂魚涌"
        assert translator.location_en_to_zh("Unknown Place") == "Unknown Place"
        assert translator.location_en_to_zh("") == ""
        assert translator.location_en_to_zh(None) is None

    def test_category_en_to_zh(self, translator):
        assert translator.category_en_to_zh("programming_languages") == "编程语言"
        assert translator.category_en_to_zh("frameworks_libraries") == "框架与库"
        assert translator.category_en_to_zh("unknown_cat") == "unknown_cat"

    def test_translate_df(self, translator):
        df = pd.DataFrame({"location": ["Central", "Quarry Bay", "Unknown"]})
        result = translator.translate_df(df)
        assert result["location"].iloc[0] == "中環"
        assert result["location"].iloc[1] == "鰂魚涌"
        assert result["location"].iloc[2] == "Unknown"

    def test_translate_skills(self, translator):
        skills = {
            "programming_languages": ["Python", "Java"],
            "unknown_cat": ["Something"],
        }
        result = translator.translate_skills(skills)
        assert "编程语言" in result
        assert result["编程语言"] == ["Python", "Java"]

    def test_translate_skills_empty(self, translator):
        assert translator.translate_skills({}) == {}
        assert translator.translate_skills(None) is None

    def test_get_translator_singleton(self):
        t1 = get_translator()
        t2 = get_translator()
        assert t1 is t2
