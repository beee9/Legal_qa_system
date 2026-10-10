# -*- coding: utf-8 -*-
"""法条原文解析模块。

读取 legal_data/*.txt 的 6 部法律法条原文，按「第N条」建立索引，
提供精确条文查询（区别于 RAG 检索，直接返回法条原文，快且准确）。

法条原文格式示例（从国家法律法规数据库整理）：
    第一章　总　则
    第一条　为了规范……，制定本法。
    第二条　……
"""
import os
import re
from base import Config

_CN_DIGITS = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
              "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_CN_UNITS = {"十": 10, "百": 100, "千": 1000, "万": 10000}


def chinese_to_int(s: str) -> int:
    """中文数字转阿拉伯数字。支持：十、百、千、万，如 '四十一' -> 41。"""
    s = s.strip()
    if not s:
        return 0
    if s.isdigit():
        return int(s)
    # 处理「X万X千X百X十X」结构
    total = 0
    section = 0  # 万以内的小节累计
    num = 0
    for ch in s:
        if ch in _CN_DIGITS:
            num = _CN_DIGITS[ch]
        elif ch in _CN_UNITS:
            unit = _CN_UNITS[ch]
            if unit == 10000:  # 万
                total = (section + num) * unit
                section = 0
                num = 0
            else:
                section += (num if num > 0 else 1) * unit
                num = 0
        # 忽略其他字符
    section += num
    return total + section


class LawReader:
    """加载并索引 legal_data/ 下的法条原文。"""

    def __init__(self, data_dir=None):
        conf = Config()
        self._data_dir = data_dir or os.path.join(conf._PROJECT_ROOT, "legal_data")
        # 法律名(短名) -> 文件名（无扩展名）
        self._file_map = {
            "民法典": "民法典",
            "劳动法": "劳动法",
            "劳动合同法": "劳动合同法",
            "公司法": "公司法",
            "刑法": "刑法",
            "民事诉讼法": "民事诉讼法",
        }
        # 短名 -> {条号(int): 条文文本}
        self._index = {}
        self._load_all()

    def _load_all(self):
        for short_name, base in self._file_map.items():
            path = os.path.join(self._data_dir, base + ".txt")
            if os.path.exists(path):
                self._index[short_name] = self._parse(path)

    @staticmethod
    def _parse(path: str) -> dict:
        """解析单个法条文件，返回 {条号(int): 条文文本}。"""
        with open(path, encoding="utf-8") as f:
            text = f.read()

        # 条文标记：第N条 / 第N条之一 等；N 支持中文或阿拉伯数字
        article_re = re.compile(r"第([一二三四五六七八九十百千万零]+|[0-9]+)条")
        # 章节标记（用于切断条文正文）
        chapter_re = re.compile(r"^第[一二三四五六七八九十百千万零]+[章编节]\s*$", re.M)

        index = {}
        # 逐行处理，遇条文标记开始新条，遇章节标记结束当前条
        lines = text.splitlines()
        cur_num = None
        cur_buf = []
        cur_pos = 0

        def flush():
            nonlocal cur_num, cur_buf
            if cur_num is not None:
                body = " ".join(x.strip() for x in cur_buf if x.strip())
                if body:
                    # 保留「第N条　」前缀，便于前端展示
                    index[cur_num] = f"第{cur_num}条　{body}"
            cur_num = None
            cur_buf = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            m = article_re.match(stripped)
            if m:
                flush()
                num_str = m.group(1)
                num = int(num_str) if num_str.isdigit() else chinese_to_int(num_str)
                cur_num = num
                cur_pos = m.end()
                rest = stripped[cur_pos:].strip()
                if rest:
                    cur_buf.append(rest)
                continue
            if chapter_re.match(stripped):
                flush()
                continue
            # 普通正文行
            if cur_num is not None:
                cur_buf.append(stripped)
        flush()
        return index

    def lookup(self, law: str, article) -> str:
        """按法律短名 + 条号查询。article 可为 '1179' / '第一千一百七十九条' / '第1179条' 等。"""
        law_key = None
        for short in self._file_map:
            if law == short or law in short or short in law:
                law_key = short
                break
        if law_key is None or law_key not in self._index:
            return None

        # 归一化条号
        art_str = str(article).strip()
        art_str = re.sub(r"^第", "", art_str)
        art_str = re.sub(r"条$", "", art_str)
        art_num = int(art_str) if art_str.isdigit() else chinese_to_int(art_str)

        return self._index[law_key].get(art_num)


# 模块级单例（加载一次，避免每次请求都解析 6 个文件）
_LAW_READER = None


def get_law_reader() -> LawReader:
    global _LAW_READER
    if _LAW_READER is None:
        _LAW_READER = LawReader()
    return _LAW_READER


if __name__ == "__main__":
    r = get_law_reader()
    for q in [("民法典", "第一千一百七十九条"), ("劳动法", "41"), ("公司法", 23)]:
        print(q, "->", (r.lookup(*q) or "未找到")[:60])
