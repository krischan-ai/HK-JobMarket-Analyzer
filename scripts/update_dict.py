#!/usr/bin/env python
"""从 LLM 提取结果中发现新词，增量更新 tech_dict.json"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.analyzer.llm_engine import LLMExtractor
from src.analyzer.rule_engine import RuleBasedSkillExtractor
from src.analyzer.hybrid import HybridExtractor
from src.logger import get_logger


def load_dict(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_dict(path: str, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"已更新词表: {path}")


def normalize_term(term: str) -> str:
    term = term.strip().lower()
    return term


def main():
    parser = argparse.ArgumentParser(description="增量更新技术栈词表")
    parser.add_argument("--dict", "-d", default="config/tech_dict.json", help="词表路径")
    parser.add_argument("--input", "-i", required=True, help="输入 JSON 文件（岗位列表）")
    parser.add_argument("--min-occurrences", "-m", type=int, default=2, help="最低出现次数")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不写入")
    parser.add_argument("--auto-add", action="store_true", help="自动添加新词到词表")
    args = parser.parse_args()

    logger = get_logger("update_dict")
    tech_dict = load_dict(args.dict)
    existing_terms = set()
    for cat, terms in tech_dict.items():
        for term in terms:
            existing_terms.add(normalize_term(term))

    with open(args.input, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    hybrid = HybridExtractor(dict_path=args.dict)
    suggestions = hybrid.suggest_dict_updates(jobs, min_occurrences=args.min_occurrences)

    if not suggestions or all(len(v) == 0 for v in suggestions.values()):
        print("未发现新词建议。词表已覆盖当前数据中的技能。")
        return

    print(f"扫描 {len(jobs)} 条岗位，发现以下建议新增的词条：")
    print("=" * 60)

    total_new = 0
    for cat, terms in suggestions.items():
        if not terms:
            continue
        print(f"\n  [{cat}]")
        for term, count in terms.items():
            if normalize_term(term) in existing_terms:
                print(f"    {term:<25} (出现 {count} 次) — 已存在词表中")
            else:
                print(f"    {term:<25} (出现 {count} 次) — ✨ 新词")
                total_new += 1

    print("=" * 60)
    print(f"总计: {total_new} 个新词待添加")

    if args.auto_add and not args.dry_run:
        added = 0
        for cat, terms in suggestions.items():
            if cat not in tech_dict:
                continue
            for term in terms:
                if normalize_term(term) not in existing_terms:
                    tech_dict[cat].append(term)
                    existing_terms.add(normalize_term(term))
                    added += 1
        if added > 0:
            save_dict(args.dict, tech_dict)
            print(f"已添加 {added} 个新词到词表")
        else:
            print("无新词需要添加")

    if args.dry_run:
        print("\n(dry-run 模式，未实际写入)")


if __name__ == "__main__":
    main()
