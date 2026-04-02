from __future__ import annotations

import re
from typing import Optional


_TAG_RE = re.compile(r"<[^>]+>")


def clean_html_content(content: str) -> str:
    """
    剥离 HTML 标签，返回纯文本。
    说明：当前 ingestion 可能遇到 HTML 或富文本段落，因此提供统一清洗入口。
    """
    if not content:
        return ""
    # 先快速去标签
    text = _TAG_RE.sub(" ", content)
    # 统一空白
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_text(text: str) -> str:
    """
    轻度文本规范化：去控制字符、合并空白、保留换行用于后续 ^第X条 切分。
    """
    if not text:
        return ""
    # 控制字符替换为空格
    text = re.sub(r"[\x00-\x1f]+", " ", text)
    # 统一空白但保留换行
    text = re.sub(r"[ \t]+", " ", text)
    # 清理连续空行
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def infer_status_display(sxx: Optional[int]) -> str:
    if sxx == 3:
        return "【有效】"
    if sxx == 2:
        return "【已修改】"
    if sxx == 1:
        return "【已废止】"
    if sxx == 4:
        return "【尚未生效】"
    return "【有效】"


__all__ = ["clean_html_content", "normalize_text", "infer_status_display"]

