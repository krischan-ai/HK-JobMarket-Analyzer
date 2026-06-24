from __future__ import annotations

import io

from src.logger import get_logger

from .utils import ResumeAgentError

logger = get_logger(__name__)

# 抽取后若有效文本过短，判定为扫描件 / 无文本层，拒绝处理（不做 OCR）。
_MIN_TEXT_LENGTH = 30


def extract_resume_text_from_pdf(file_bytes: bytes) -> str:
    """从文本型 PDF 中抽取简历纯文本。

    - 首选 pypdf；扫描件（无文本层）返回明确错误，不做 OCR。
    - 文件内容仅在内存中处理，不落盘。
    """
    if not file_bytes:
        raise ResumeAgentError("PDF 文件为空")

    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - 依赖缺失时的兜底
        raise ResumeAgentError(
            "未安装 PDF 解析依赖，请执行 pip install -r requirements-resume.txt"
        ) from exc

    try:
        reader = PdfReader(io.BytesIO(file_bytes))
    except Exception as exc:
        raise ResumeAgentError(f"无法解析 PDF 文件：{exc}") from exc

    if reader.is_encrypted:
        # 尝试空密码解锁；失败则拒绝。
        try:
            reader.decrypt("")
        except Exception as exc:
            raise ResumeAgentError("PDF 已加密，无法读取") from exc

    parts: list[str] = []
    for index, page in enumerate(reader.pages):
        try:
            parts.append(page.extract_text() or "")
        except Exception as exc:
            logger.warning("PDF 第 %d 页文本抽取失败：%s", index + 1, exc)

    text = "\n".join(part.strip() for part in parts if part.strip()).strip()

    if len(text) < _MIN_TEXT_LENGTH:
        raise ResumeAgentError(
            "未能从 PDF 中抽取到有效文本，可能是扫描件或图片型简历，请改用粘贴文本方式"
        )

    return text
