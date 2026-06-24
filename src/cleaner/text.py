from __future__ import annotations

import re
import warnings

from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning

from src.logger import get_logger

_logger = get_logger(__name__)

# spaCy 懒加载（可选增强）
_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is not None:
        return _nlp
    try:
        import spacy
        _nlp = spacy.load("en_core_web_sm")
        _logger.info("spaCy en_core_web_sm loaded")
    except Exception:
        _nlp = False
        _logger.info("spaCy not available, skipping NLP features")
    return _nlp if _nlp is not False else None


class JDTextCleaner:
    """JD 文本清洗器，按管道顺序执行多步清洗"""

    @staticmethod
    def remove_html_tags(text: str) -> str:
        if not text:
            return ""
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)
            return BeautifulSoup(text, "html.parser").get_text(separator=" ")

    @staticmethod
    def normalize_unicode(text: str) -> str:
        if not text:
            return ""
        replacements = {
            "聽": " ",
            "鈥檚": "'s",
            "鈥檙e": "'re",
            "鈥檒l": "'ll",
            "鈥檝e": "'ve",
            "鈥檇": "'d",
            "鈥檛": "n't",
            "鈥?": " ",
            "鈥": "'",
            "鈩": "",
            "路": "\n",
        }
        for bad, good in replacements.items():
            text = text.replace(bad, good)
        text = text.replace("\u3000", " ")
        text = text.replace("\xa0", " ")
        return text

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def remove_special_chars(text: str) -> str:
        if not text:
            return ""
        return re.sub(r"[^\w\s@.,;:!?()\-+/%#]", " ", text)

    @staticmethod
    def remove_email_urls(text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"\S+@\S+", "", text)
        text = re.sub(r"https?://\S+", "", text)
        return text

    def clean(self, raw_text: str) -> str:
        if not raw_text:
            return ""
        text = self.remove_html_tags(raw_text)
        text = self.remove_email_urls(text)
        text = self.normalize_unicode(text)
        text = self.remove_special_chars(text)
        text = self.normalize_whitespace(text)
        return text

    @staticmethod
    def extract_entities(text: str) -> list[dict]:
        """抽取命名實體（組織、地點、技能），依賴 spaCy"""
        nlp = _get_nlp()
        if nlp is None:
            return []
        doc = nlp(text[:100000])
        entities = []
        for ent in doc.ents:
            if ent.label_ in ("ORG", "GPE", "LOC", "PRODUCT", "TECH"):
                entities.append({"text": ent.text, "label": ent.label_})
        return entities
