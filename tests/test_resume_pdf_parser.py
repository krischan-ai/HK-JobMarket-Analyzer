from __future__ import annotations

import pytest

from src.resume_agent.pdf_parser import extract_resume_text_from_pdf
from src.resume_agent.utils import ResumeAgentError


def _build_pdf(text: str) -> bytes:
    """构造一个含文本层的最小合法 PDF，xref 偏移动态计算。"""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        None,  # 内容流，下面填充
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    stream = b"BT /F1 24 Tf 72 700 Td (" + text.encode("latin-1") + b") Tj ET"
    objects[3] = b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += str(i).encode() + b" 0 obj\n" + body + b"\nendobj\n"

    xref_pos = len(out)
    out += b"xref\n0 " + str(len(objects) + 1).encode() + b"\n"
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (
        b"trailer\n<< /Size " + str(len(objects) + 1).encode() + b" /Root 1 0 R >>\n"
        b"startxref\n" + str(xref_pos).encode() + b"\n%%EOF"
    )
    return bytes(out)


def test_extract_text_from_text_pdf():
    pdf = _build_pdf("Jane Doe Senior Python Engineer Hong Kong")
    text = extract_resume_text_from_pdf(pdf)
    assert "Jane Doe" in text
    assert "Python" in text


def test_rejects_empty_bytes():
    with pytest.raises(ResumeAgentError):
        extract_resume_text_from_pdf(b"")


def test_rejects_non_pdf_bytes():
    with pytest.raises(ResumeAgentError):
        extract_resume_text_from_pdf(b"this is plain text, not a pdf at all")


def test_rejects_scanned_pdf_without_text_layer():
    # 仅含一个空白页、无文本层 → 应判定为扫描件并拒绝。
    blank = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"trailer\n<< /Root 1 0 R >>\n%%EOF"
    )
    with pytest.raises(ResumeAgentError):
        extract_resume_text_from_pdf(blank)
