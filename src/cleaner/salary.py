from __future__ import annotations

import re
from typing import Optional, Tuple


class SalaryParser:
    """香港招聘薪资解析器，支持多种薪资格式"""

    PATTERNS = [
        # HK$45,000 - HK$60,000 /month  or /annum
        re.compile(
            r"(?:hk)?\$?\s*([\d,]+)\s*-\s*(?:hk)?\$?\s*([\d,]+)\s*"
            r"(?:/|per\s*)(month|mth|annum|year|yr)",
            re.IGNORECASE,
        ),
        # HK$45,000 - HK$60,000 (no period)
        re.compile(
            r"(?:hk)?\$?\s*([\d,]+)\s*-\s*(?:hk)?\$?\s*([\d,]+)\b",
            re.IGNORECASE,
        ),
        # HK$45,000 up/above/plus
        re.compile(
            r"(?:hk)?\$?\s*([\d,]+)\s*(up|above|plus|以上)",
            re.IGNORECASE,
        ),
        # HK$45,000 /month  or /annum (single value)
        re.compile(
            r"(?:hk)?\$?\s*([\d,]+)\s*(?:/|per\s*)(month|mth|annum|year|yr)",
            re.IGNORECASE,
        ),
        # HK$45,000 (bare number)
        re.compile(
            r"(?:hk)?\$?\s*([\d,]+)\b",
            re.IGNORECASE,
        ),
    ]

    @staticmethod
    def _normalize_period(period: str) -> str:
        period = period.lower().strip()
        if period in ("annum", "year", "yr"):
            return "annual"
        return "monthly"

    @staticmethod
    def parse(raw: str) -> Tuple[Optional[float], Optional[float]]:
        if not raw or not isinstance(raw, str):
            return None, None

        raw = raw.strip()

        for pattern in SalaryParser.PATTERNS:
            match = pattern.search(raw)
            if not match:
                continue

            groups = match.groups()

            if len(groups) >= 2:
                try:
                    min_val = float(groups[0].replace(",", ""))
                except (ValueError, IndexError):
                    continue

                max_val = None
                period = "monthly"

                if len(groups) >= 2:
                    second = groups[1]
                    if second.lower() in ("up", "above", "plus", "以上"):
                        return min_val, None
                    if second.lower() in ("month", "mth", "annum", "year", "yr"):
                        period = SalaryParser._normalize_period(second)
                    else:
                        try:
                            max_val = float(second.replace(",", ""))
                        except ValueError:
                            pass

                if len(groups) >= 3 and max_val is not None:
                    period_str = groups[2]
                    if period_str:
                        period = SalaryParser._normalize_period(period_str)

                if period == "annual":
                    min_val = round(min_val / 12, 0)
                    if max_val is not None:
                        max_val = round(max_val / 12, 0)

                return min_val, max_val

        return None, None
