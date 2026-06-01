from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from src.logger import get_logger
from src.utils import ensure_dir

plt.rcParams["axes.unicode_minus"] = False


class TechTrendAnalyzer:
    """技术趋势分析器"""

    def __init__(self, df: pd.DataFrame, output_dir: str | Path = "output/charts"):
        self.df = df
        self.output_dir = ensure_dir(output_dir)
        self.logger = get_logger(self.__class__.__name__)

    def _flatten_skills(self) -> pd.DataFrame:
        records = []
        for _, row in self.df.dropna(subset=["skills"]).iterrows():
            skills = row["skills"]
            if isinstance(skills, dict):
                for category, skill_list in skills.items():
                    if isinstance(skill_list, list):
                        for skill in skill_list:
                            records.append({"job_id": row.get("job_id"), "skill": skill, "category": category})
        return pd.DataFrame(records)

    def top_skills(self, top_n: int = 20) -> pd.Series:
        skill_df = self._flatten_skills()
        if skill_df.empty:
            return pd.Series()
        return skill_df["skill"].value_counts().head(top_n)

    def plot_top_skills(self, top_n: int = 15, save: bool = True) -> Optional[str]:
        top = self.top_skills(top_n)
        if top.empty:
            self.logger.warning("No skills data to plot")
            return None

        fig, ax = plt.subplots(figsize=(12, 7))
        colors = sns.color_palette("Blues_d", len(top))
        bars = ax.barh(range(len(top)), top.values, color=colors)
        ax.set_yticks(range(len(top)))
        ax.set_yticklabels(top.index)
        ax.invert_yaxis()
        ax.set_xlabel("Number of Job Postings", fontsize=12)
        ax.set_title(f"Top {top_n} In-Demand IT Skills in Hong Kong", fontsize=14, fontweight="bold")

        for bar, val in zip(bars, top.values):
            ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                    str(val), va="center", fontsize=9)

        plt.tight_layout()

        if save:
            path = self.output_dir / "top_skills.png"
            plt.savefig(path, dpi=150, bbox_inches="tight")
            plt.close(fig)
            self.logger.info("Saved top skills chart to %s", path)
            return str(path)
        plt.show()
        return None

    def plot_category_distribution(self, save: bool = True) -> Optional[str]:
        skill_df = self._flatten_skills()
        if skill_df.empty:
            return None

        cat_counts = skill_df["category"].value_counts()
        fig, ax = plt.subplots(figsize=(8, 8))
        colors = ["#ff9999", "#66b3ff", "#99ff99", "#ffcc99", "#c2c2f0"]
        ax.pie(cat_counts.values, labels=cat_counts.index, autopct="%1.1f%%",
               colors=colors[:len(cat_counts)], startangle=90)
        ax.set_title("Technical Skill Category Distribution", fontsize=14, fontweight="bold")
        plt.tight_layout()

        if save:
            path = self.output_dir / "category_distribution.png"
            plt.savefig(path, dpi=150, bbox_inches="tight")
            plt.close(fig)
            return str(path)
        plt.show()
        return None

    def plot_salary_by_skill(self, top_skills: int = 10, save: bool = True) -> Optional[str]:
        records = []
        for _, row in self.df.dropna(subset=["salary_min", "skills"]).iterrows():
            avg_salary = (row["salary_min"] + (row.get("salary_max") or row["salary_min"])) / 2
            skills = row["skills"]
            if isinstance(skills, dict):
                for skill_list in skills.values():
                    if isinstance(skill_list, list):
                        for skill in skill_list:
                            records.append({"skill": skill, "salary": avg_salary})

        skill_salary_df = pd.DataFrame(records)
        if skill_salary_df.empty:
            return None

        top = skill_salary_df["skill"].value_counts().head(top_skills).index
        plot_df = skill_salary_df[skill_salary_df["skill"].isin(top)]

        fig, ax = plt.subplots(figsize=(14, 7))
        sns.boxplot(data=plot_df, x="salary", y="skill", ax=ax, palette="Blues_d", hue="skill", legend=False)
        ax.set_xlabel("Monthly Salary (HKD)", fontsize=12)
        ax.set_ylabel("")
        ax.set_title("Salary Distribution by Technical Skill", fontsize=14, fontweight="bold")
        plt.tight_layout()

        if save:
            path = self.output_dir / "salary_by_skill.png"
            plt.savefig(path, dpi=150, bbox_inches="tight")
            plt.close(fig)
            return str(path)
        plt.show()
        return None

    def plot_location_distribution(self, top_n: int = 15, save: bool = True) -> Optional[str]:
        if "location" not in self.df.columns:
            return None

        loc_counts = self.df["location"].value_counts().head(top_n)
        if loc_counts.empty:
            return None

        fig, ax = plt.subplots(figsize=(10, 8))
        colors = plt.cm.Reds(loc_counts.values / loc_counts.max())
        bars = ax.barh(loc_counts.index, loc_counts.values, color=colors)
        ax.invert_yaxis()
        ax.set_xlabel("Number of Job Postings")
        ax.set_title("Job Distribution by Location in Hong Kong", fontsize=14, fontweight="bold")

        for bar, val in zip(bars, loc_counts.values):
            ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                    str(val), va="center", fontsize=9)

        plt.tight_layout()

        if save:
            path = self.output_dir / "location_distribution.png"
            plt.savefig(path, dpi=150, bbox_inches="tight")
            plt.close(fig)
            return str(path)
        plt.show()
        return None

    def generate_all_charts(self) -> dict:
        return {
            "top_skills": self.plot_top_skills(),
            "category_distribution": self.plot_category_distribution(),
            "salary_by_skill": self.plot_salary_by_skill(),
            "location_distribution": self.plot_location_distribution(),
        }
