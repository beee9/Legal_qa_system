"""
数据质量优化工具
功能：
1. 去重和近重复检测
2. 法律表述纠正与引用提取
3. 元数据补充
4. 数据质量评估与生成增强版数据集
"""
import pandas as pd
import numpy as np
from typing import List, Tuple, Set, Dict, Optional
import re
import hashlib
from collections import defaultdict
import json
import sys, os

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from base import logger


class DataQualityOptimizer:
    """数据质量优化器"""

    def __init__(self):
        self.logger = logger

        # 常见法律正则映射
        self.law_patterns = {
            "中华人民共和国民法典": r"《?中华人民共和国民法典》?|民法典",
            "中华人民共和国刑法": r"《?中华人民共和国刑法》?|刑法",
            "中华人民共和国劳动法": r"《?中华人民共和国劳动法》?|劳动法",
            "中华人民共和国劳动合同法": r"《?中华人民共和国劳动合同法》?|劳动合同法",
            "中华人民共和国民事诉讼法": r"《?中华人民共和国民事诉讼法》?|民事诉讼法|民诉法",
            "中华人民共和国刑事诉讼法": r"《?中华人民共和国刑事诉讼法》?|刑事诉讼法|刑诉法",
            "中华人民共和国公司法": r"《?中华人民共和国公司法》?|公司法",
            "中华人民共和国消费者权益保护法": r"《?中华人民共和国消费者权益保护法》?|消保法|消费者权益保护法",
            "中华人民共和国治安管理处罚法": r"《?中华人民共和国治安管理处罚法》?|治安管理处罚法",
            "中华人民共和国专利法": r"《?中华人民共和国专利法》?|专利法",
            "中华人民共和国著作权法": r"《?中华人民共和国著作权法》?|著作权法|版权法",
            "中华人民共和国商标法": r"《?中华人民共和国商标法》?|商标法",
        }

        # 匹配条文
        self.article_pattern = re.compile(
            r"(?:第\s*)?([一二三四五六七八九十百千零〇0-9]+)\s*条"
        )

        # 义务/规范关键词
        self.obligation_words = ["应当", "必须", "可以", "不得", "禁止"]

    def detect_columns(self, df: pd.DataFrame) -> Tuple[str, str, str]:
        """识别并返回 (领域列名, 问题列名, 答案列名)"""
        col_map = {str(c).strip(): c for c in df.columns}
        
        q_col = col_map.get("问题") or col_map.get("question") or col_map.get("query")
        a_col = col_map.get("答案") or col_map.get("answer") or col_map.get("response")
        s_col = col_map.get("领域") or col_map.get("subject") or col_map.get("category") or col_map.get("domain")

        cols = list(df.columns)
        if not q_col:
            q_col = cols[1] if len(cols) > 1 else cols[0]
        if not a_col:
            a_col = cols[2] if len(cols) > 2 else cols[-1]
        if not s_col:
            s_col = cols[0]

        return s_col, q_col, a_col

    def _normalize_text(self, text: str) -> str:
        """文本规范化，用于近重复检测"""
        if pd.isna(text):
            return ""
        text = str(text).lower()
        # 去除标点和空格
        text = re.sub(r'[^\w\u4e00-\u9fff]', '', text)
        # 同义词替换，提升重复召回
        replacements = {
            "怎么办": "如何处理",
            "怎样": "如何",
            "什么时候": "何时",
            "哪些": "什么",
            "能不能": "是否可以",
            "可不可以": "是否可以",
            "行不行": "是否可以",
            "算不算": "是否属于",
            "是不是": "是否为",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def _chinese_to_arabic(self, chinese_num: str) -> str:
        """中文数字转阿拉伯数字，如：第五百零九条 -> 509"""
        chinese_num = str(chinese_num).strip()
        if chinese_num.isdigit():
            return chinese_num

        digit_map = {
            '零': 0, '〇': 0, '一': 1, '二': 2, '三': 3, '四': 4,
            '五': 5, '六': 6, '七': 7, '八': 8, '九': 9
        }
        unit_map = {'十': 10, '百': 100, '千': 1000, '万': 10000}

        # 处理 "十"、"十一"、"二十"
        if chinese_num == '十':
            return '10'
        if chinese_num.startswith('十'):
            chinese_num = '一' + chinese_num

        total = 0
        temp = 0
        for char in chinese_num:
            if char in digit_map:
                temp = digit_map[char]
            elif char in unit_map:
                unit = unit_map[char]
                if temp == 0:
                    temp = 1
                total += temp * unit
                temp = 0
        total += temp
        return str(total) if total > 0 else chinese_num

    def extract_article_references(self, text: str) -> List[Dict[str, str]]:
        """从文本中抽取法律名称与具体法条"""
        if pd.isna(text):
            return []
        text = str(text)
        references = []

        # 1. 匹配《法律名》第X条
        pattern_book = r"《([^》]+)》[^\n。！？；]*?第\s*([一二三四五六七八九十百千零〇0-9]+)\s*条"
        for match in re.finditer(pattern_book, text):
            law_name = match.group(1).strip()
            art_raw = match.group(2).strip()
            art_no = self._chinese_to_arabic(art_raw)
            ref_item = {"law": law_name, "article": art_no}
            if ref_item not in references:
                references.append(ref_item)

        # 2. 匹配常见简称
        for standard_law, reg_pattern in self.law_patterns.items():
            pattern_short = rf"({reg_pattern})[^\n。！？；]*?第\s*([一二三四五六七八九十百千零〇0-9]+)\s*条"
            for match in re.finditer(pattern_short, text):
                art_raw = match.group(2).strip()
                art_no = self._chinese_to_arabic(art_raw)
                ref_item = {"law": standard_law, "article": art_no}
                if ref_item not in references:
                    references.append(ref_item)

        return references

    def extract_legal_basis(self, text: str) -> str:
        """从文本中抽取法律依据名称"""
        if pd.isna(text):
            return ""
        text = str(text)
        found_laws = []
        for standard_law, reg_pattern in self.law_patterns.items():
            if re.search(reg_pattern, text):
                found_laws.append(f"《{standard_law}》")
        return "、".join(found_laws)

    def optimize_dataset(self, input_path: str, output_path: str) -> Dict:
        """执行完整数据优化流程并写入目标文件"""
        self.logger.info(f"读取原始数据集: {input_path}")
        df = pd.read_csv(input_path, encoding='utf-8')
        orig_count = len(df)
        self.logger.info(f"原始数据总量: {orig_count}")

        s_col, q_col, a_col = self.detect_columns(df)
        self.logger.info(f"识别列名 -> 领域列: [{s_col}], 问题列: [{q_col}], 答案列: [{a_col}]")

        # 1. 空值清洗
        df = df.dropna(subset=[q_col, a_col]).copy()
        valid_count = len(df)

        # 2. 完全去重
        df = df.drop_duplicates(subset=[q_col], keep='first').copy()
        exact_dedup_count = len(df)

        # 3. 近重复检测与过滤
        norm_series = df[q_col].apply(self._normalize_text)
        hash_dict = {}
        keep_indices = []
        near_duplicate_count = 0

        for idx, norm_q in zip(df.index, norm_series):
            if not norm_q:
                continue
            h = hashlib.md5(norm_q.encode('utf-8')).hexdigest()
            if h not in hash_dict:
                hash_dict[h] = idx
                keep_indices.append(idx)
            else:
                near_duplicate_count += 1

        df_cleaned = df.loc[keep_indices].copy()

        # 4. 标准化列名与增强元数据字段
        df_cleaned['subject'] = df_cleaned[s_col].astype(str).str.strip()
        df_cleaned['question'] = df_cleaned[q_col].astype(str).str.strip()
        df_cleaned['answer'] = df_cleaned[a_col].astype(str).str.strip()

        # 提取法律条文依据与法条引用
        df_cleaned['article_refs'] = df_cleaned['answer'].apply(
            lambda x: json.dumps(self.extract_article_references(x), ensure_ascii=False)
        )
        df_cleaned['legal_basis'] = df_cleaned['answer'].apply(self.extract_legal_basis)
        df_cleaned['region'] = '全国'
        df_cleaned['source_type'] = 'curated'
        df_cleaned['verified'] = df_cleaned['article_refs'] != '[]'
        df_cleaned['confidence_score'] = df_cleaned['verified'].apply(lambda v: 0.95 if v else 0.80)

        # 保存优化结果
        target_columns = [
            'subject', 'question', 'answer',
            'legal_basis', 'article_refs',
            'region', 'source_type', 'verified', 'confidence_score'
        ]
        out_df = df_cleaned[target_columns]
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        out_df.to_csv(output_path, index=False, encoding='utf-8-sig')

        refs_detected = (out_df['article_refs'] != '[]').sum()
        basis_detected = (out_df['legal_basis'] != '').sum()

        report = {
            "original_count": orig_count,
            "non_empty_count": valid_count,
            "exact_dedup_removed": orig_count - exact_dedup_count,
            "near_dedup_removed": near_duplicate_count,
            "final_count": len(out_df),
            "refs_extracted_count": int(refs_detected),
            "basis_extracted_count": int(basis_detected),
            "output_path": output_path
        }
        self.logger.info(f"优化完成报告: {report}")
        return report


if __name__ == "__main__":
    input_file = r"E:\陈杰\Legal_qa_system\mysql_qa\data\legal_qa_full.csv"
    output_file = r"E:\陈杰\Legal_qa_system\mysql_qa\data\legal_qa_full_enhanced.csv"
    optimizer = DataQualityOptimizer()
    report = optimizer.optimize_dataset(input_file, output_file)
    print("\n================ 数据优化执行结果 ================")
    for k, v in report.items():
        print(f"{k}: {v}")
