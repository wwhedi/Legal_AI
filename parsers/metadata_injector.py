from __future__ import annotations

from typing import Optional


def inject_hierarchical_context(
    chunk_text: str,
    law_title: str,
    bian: Optional[str] = None,
    zhang: Optional[str] = None,
    jie: Optional[str] = None,
    tiao: Optional[str] = None,
    kuan: Optional[str] = None,
    xiang: Optional[str] = None,
) -> str:
    """
    将法律层级上下文注入到切片文本开头。

    示例输出：
    【法律】民法典 > 【编】第三编 > 【条】第617条
    <chunk_text>
    """

    path_parts = [f"【法律】{law_title.strip()}"]

    if bian:
        path_parts.append(f"【编】{bian.strip()}")
    if zhang:
        path_parts.append(f"【章】{zhang.strip()}")
    if jie:
        path_parts.append(f"【节】{jie.strip()}")
    if tiao:
        path_parts.append(f"【条】{tiao.strip()}")
    if kuan:
        path_parts.append(f"【款】{kuan.strip()}")
    if xiang:
        path_parts.append(f"【项】{xiang.strip()}")

    header = " > ".join(path_parts)
    text = (chunk_text or "").strip()
    return f"{header}\n{text}" if text else header


__all__ = ["inject_hierarchical_context"]

