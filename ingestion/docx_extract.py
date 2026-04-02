from __future__ import annotations

import io
import zipfile
from typing import List
from xml.etree import ElementTree as ET


def _localname(tag: str) -> str:
    # {namespace}local -> local
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def docx_bytes_to_text(docx_bytes: bytes) -> str:
    """
    基于 docx 内部 XML 提取文本（无需额外依赖 python-docx）：
    - 读取 word/document.xml
    - 以段落 (w:p) 为单位拼接 w:t
    """
    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as z:  # type: ignore[name-defined]
        xml_bytes = z.read("word/document.xml")

    root = ET.fromstring(xml_bytes)
    paragraphs: List[str] = []

    # 逐段落解析，尽量保持换行语义
    for p in root.iter():
        if _localname(p.tag) != "p":
            continue
        texts: List[str] = []
        for t in p.iter():
            if _localname(t.tag) == "t" and t.text:
                texts.append(t.text)
        if texts:
            paragraphs.append("".join(texts).strip())

    # 避免过多空行
    return "\n".join([para for para in paragraphs if para])


__all__ = ["docx_bytes_to_text"]

