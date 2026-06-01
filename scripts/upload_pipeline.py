#!/usr/bin/env python
"""
CLI 版上传处理脚本：处理用户上传的招聘数据文件

Usage:
    python scripts/upload_pipeline.py --file data/uploads/sample.csv --source "my_crawl"
    python scripts/upload_pipeline.py --file data/uploads/sample.json --skip-extraction
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.knowledge_base.uploader import Uploader


def main():
    parser = argparse.ArgumentParser(description="上传招聘数据文件到知识库")
    parser.add_argument("--file", "-f", required=True, help="数据文件路径 (CSV/JSON/Excel)")
    parser.add_argument("--source", "-s", default="user_upload", help="数据来源标签")
    parser.add_argument("--skip-cleaning", action="store_true", help="跳过清洗步骤")
    parser.add_argument("--skip-extraction", action="store_true", help="跳过技能提取")
    parser.add_argument("--skip-dedup", action="store_true", help="跳过重复检测")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"错误: 文件不存在 {file_path}")
        sys.exit(1)

    uploader = Uploader(
        file_path=str(file_path),
        source_tag=args.source,
        detect_duplicates=not args.skip_dedup,
        run_cleaning=not args.skip_cleaning,
        run_extraction=not args.skip_extraction,
    )

    print(f"正在处理: {file_path}")
    print(f"  来源标签: {args.source}")
    print(f"  清洗: {'跳过' if args.skip_cleaning else '启用'}")
    print(f"  技能提取: {'跳过' if args.skip_extraction else '启用'}")
    print()

    result = uploader.process()

    print("=" * 50)
    print("处理完成!")
    print(f"  总记录数:   {result.total}")
    print(f"  成功入库:   {result.success}")
    print(f"  跳过:       {result.skipped}")
    print(f"  新增记录:   {result.new_records}")
    print(f"  更新记录:   {result.updated_records}")
    print(f"  耗时:       {result.duration_ms} ms")
    if result.errors:
        print(f"  错误:       {len(result.errors)} 个")
        for e in result.errors:
            print(f"    - {e}")
    print("=" * 50)


if __name__ == "__main__":
    main()
