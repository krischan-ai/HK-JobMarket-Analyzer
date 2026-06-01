from __future__ import annotations

from pathlib import Path

from src.logger import get_logger


class PerformanceOptimizer:
    """性能优化工具集"""

    @staticmethod
    def get_codebase_stats() -> dict:
        src_dir = Path(__file__).resolve().parent / "src"
        py_files = list(src_dir.rglob("*.py"))
        total_lines = sum(len(f.read_text(encoding="utf-8").splitlines()) for f in py_files)
        return {
            "py_files": len(py_files),
            "total_lines": total_lines,
        }

    @staticmethod
    def get_crawler_stats(crawler) -> dict:
        stats = {"success_count": 0, "fail_count": 0}
        if hasattr(crawler, "delay_controller"):
            stats["success_rate"] = crawler.delay_controller.success_rate
            stats["current_delay"] = crawler.delay_controller._current_delay
        return stats

    @staticmethod
    def clear_all_caches():
        """清空所有模块的缓存，用于测试或热重载"""
        import src.analyzer.rule_engine as re_mod
        import src.cleaner.salary as sal_mod
        import src.i18n.translator as i18n_mod

        for mod in [re_mod, sal_mod, i18n_mod]:
            for name in dir(mod):
                obj = getattr(mod, name)
                if hasattr(obj, "cache_clear"):
                    obj.cache_clear()
                    get_logger("cache").info("Cleared cache for %s.%s", mod.__name__, name)
