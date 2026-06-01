from __future__ import annotations

import re
import warnings

from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning


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
