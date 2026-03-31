from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LegalNode:
    level: str
    heading: str
    content: str = ""
    children: List["LegalNode"] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "level": self.level,
            "heading": self.heading,
            "content": self.content.strip(),
            "children": [child.to_dict() for child in self.children],
        }


@dataclass
class ClauseRecord:
    law: Optional[str] = None
    bian: Optional[str] = None
    zhang: Optional[str] = None
    jie: Optional[str] = None
    tiao: Optional[str] = None
    kuan: Optional[str] = None
    xiang: Optional[str] = None
    text: str = ""

    def to_dict(self) -> Dict:
        return {
            "law": self.law,
            "bian": self.bian,
            "zhang": self.zhang,
            "jie": self.jie,
            "tiao": self.tiao,
            "kuan": self.kuan,
            "xiang": self.xiang,
            "text": self.text.strip(),
        }


class FineGrainedLegalParser:
    """
    细粒度法律文本解析器：
    - 支持识别到 编、章、节、条、款、项
    - 兼容中文全角空格与常见编号样式
    """

    BIAN_RE = re.compile(r"^\s*第[一二三四五六七八九十百千万0-9]+编[^\n]*$")
    ZHANG_RE = re.compile(r"^\s*第[一二三四五六七八九十百千万0-9]+章[^\n]*$")
    JIE_RE = re.compile(r"^\s*第[一二三四五六七八九十百千万0-9]+节[^\n]*$")
    TIAO_RE = re.compile(r"^\s*第[一二三四五六七八九十百千万0-9]+条[^\n]*$")
    # 款通常表现为：一、…… / （一）…… / 1.……
    KUAN_RE = re.compile(
        r"^\s*(?:[一二三四五六七八九十百千万]+、|（[一二三四五六七八九十百千万]+）|\([一二三四五六七八九十百千万]+\)|\d+[\.、])\s*.+$"
    )
    # 项通常表现为：1. / （1） / (1)
    XIANG_RE = re.compile(r"^\s*(?:\d+[\.、]|（\d+）|\(\d+\))\s*.+$")

    LEVEL_ORDER = {
        "law": 0,
        "bian": 1,
        "zhang": 2,
        "jie": 3,
        "tiao": 4,
        "kuan": 5,
        "xiang": 6,
    }

    def parse(self, text: str, law_title: Optional[str] = None) -> Dict:
        normalized_lines = self._normalize_lines(text)
        tree_root = LegalNode(level="law", heading=law_title or "未命名法律")
        self._build_tree(normalized_lines, tree_root)
        clauses = self._extract_clause_records(normalized_lines, law_title)
        return {
            "law_title": law_title,
            "tree": tree_root.to_dict(),
            "clauses": [item.to_dict() for item in clauses],
        }

    def _normalize_lines(self, text: str) -> List[str]:
        # 统一空白并去掉空行，减少正则判断误差
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
        return [line for line in lines if line]

    def _build_tree(self, lines: List[str], root: LegalNode) -> None:
        stack: List[LegalNode] = [root]

        for line in lines:
            level = self._detect_level(line)
            if not level:
                stack[-1].content += f"\n{line}"
                continue

            node = LegalNode(level=level, heading=line)
            node_order = self.LEVEL_ORDER[level]

            while len(stack) > 1 and self.LEVEL_ORDER[stack[-1].level] >= node_order:
                stack.pop()

            stack[-1].children.append(node)
            stack.append(node)

    def _extract_clause_records(
        self, lines: List[str], law_title: Optional[str]
    ) -> List[ClauseRecord]:
        records: List[ClauseRecord] = []
        current = ClauseRecord(law=law_title)

        for line in lines:
            level = self._detect_level(line)

            if level == "bian":
                current.bian = line
                current.zhang = None
                current.jie = None
                current.tiao = None
                current.kuan = None
                current.xiang = None
                continue

            if level == "zhang":
                current.zhang = line
                current.jie = None
                current.tiao = None
                current.kuan = None
                current.xiang = None
                continue

            if level == "jie":
                current.jie = line
                current.tiao = None
                current.kuan = None
                current.xiang = None
                continue

            if level == "tiao":
                current.tiao = line
                current.kuan = None
                current.xiang = None
                # 条标题本身作为一个独立记录
                records.append(
                    ClauseRecord(
                        law=current.law,
                        bian=current.bian,
                        zhang=current.zhang,
                        jie=current.jie,
                        tiao=current.tiao,
                        text=line,
                    )
                )
                continue

            if level == "kuan":
                current.kuan = line
                current.xiang = None
                records.append(
                    ClauseRecord(
                        law=current.law,
                        bian=current.bian,
                        zhang=current.zhang,
                        jie=current.jie,
                        tiao=current.tiao,
                        kuan=current.kuan,
                        text=line,
                    )
                )
                continue

            if level == "xiang":
                current.xiang = line
                records.append(
                    ClauseRecord(
                        law=current.law,
                        bian=current.bian,
                        zhang=current.zhang,
                        jie=current.jie,
                        tiao=current.tiao,
                        kuan=current.kuan,
                        xiang=current.xiang,
                        text=line,
                    )
                )
                continue

            # 普通正文归入当前最深层级对象
            if records:
                records[-1].text = f"{records[-1].text}\n{line}".strip()
            else:
                records.append(ClauseRecord(law=current.law, text=line))

        return records

    def _detect_level(self, line: str) -> Optional[str]:
        if self.BIAN_RE.match(line):
            return "bian"
        if self.ZHANG_RE.match(line):
            return "zhang"
        if self.JIE_RE.match(line):
            return "jie"
        if self.TIAO_RE.match(line):
            return "tiao"
        if self.XIANG_RE.match(line):
            return "xiang"
        if self.KUAN_RE.match(line):
            return "kuan"
        return None


__all__ = ["FineGrainedLegalParser", "LegalNode", "ClauseRecord"]

