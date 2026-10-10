# 导入分词库
import jieba
# 导入日志
from base import logger
from typing import List
import re


# 中文数字转阿拉伯数字映射
CN_NUM = {
    '零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
    '〇': 0, '壹': 1, '贰': 2, '叁': 3, '肆': 4, '伍': 5, '陆': 6, '柒': 7, '捌': 8, '玖': 9,
    '十': 10, '百': 100, '千': 1000, '万': 10000, '亿': 100000000,
    '拾': 10, '佰': 100, '仟': 1000, '萬': 10000
}


def chinese_to_arabic(chinese_num: str) -> str:
    """将中文数字转换为阿拉伯数字
    
    示例：
        五百零九 -> 509
        一千一百七十九 -> 1179
        第五百零九条 -> 第509条
    """
    if not chinese_num:
        return chinese_num
    
    # 匹配中文数字模式
    pattern = r'[零一二三四五六七八九十百千万亿壹贰叁肆伍陆柒捌玖拾佰仟萬〇]+'
    
    def convert_match(match):
        cn_str = match.group()
        try:
            # 处理纯数字
            if cn_str in CN_NUM:
                return str(CN_NUM[cn_str])
            
            # 处理复合数字
            result = 0
            temp = 0
            unit = 1
            
            for char in reversed(cn_str):
                if char in ['零', '〇']:
                    continue
                elif char in ['十', '拾']:
                    unit = 10
                    if temp == 0:
                        temp = 1
                elif char in ['百', '佰']:
                    unit = 100
                elif char in ['千', '仟']:
                    unit = 1000
                elif char in ['万', '萬']:
                    result += temp * unit
                    temp = 0
                    unit = 10000
                elif char in ['亿']:
                    result += temp * unit
                    temp = 0
                    unit = 100000000
                else:
                    digit = CN_NUM.get(char, 0)
                    if unit == 1:
                        temp += digit
                    else:
                        temp += digit * unit
                        unit = 1
            
            result += temp * unit
            return str(result)
        except Exception as e:
            logger.warning(f"中文数字转换失败: {cn_str}, 错误: {e}")
            return cn_str
    
    return re.sub(pattern, convert_match, chinese_num)


def normalize_law_reference(text: str) -> str:
    """标准化法条引用格式
    
    将各种法条表达方式统一为标准格式
    示例：
        民法典第五百零九条 -> 民法典第509条
        民法典509条 -> 民法典第509条
        劳动法第10条 -> 劳动法第10条
    """
    # 先转换中文数字
    text = chinese_to_arabic(text)
    
    # 标准化"第X条"格式
    # 匹配：法律名 + 可选的"第" + 数字 + 可选的"条"
    pattern = r'(民法典|劳动法|公司法|合同法|刑法|民事诉讼法|刑事诉讼法|行政诉讼法)(?:第)?(\d+)(?:条)?'
    
    def standardize_match(match):
        law_name = match.group(1)
        article_num = match.group(2)
        return f"{law_name}第{article_num}条"
    
    return re.sub(pattern, standardize_match, text)


def preprocess_text(text: str) -> List[str]:
    """预处理文本（增强版）
    
    改进：
    1. 中文数字转阿拉伯数字
    2. 标准化法条引用格式
    3. 分词
    4. 转小写
    """
    logger.info("开始预处理文本")
    try:
        # 1. 标准化法条引用（包含中文数字转换）
        normalized_text = normalize_law_reference(text)
        logger.debug(f"标准化前: {text}, 标准化后: {normalized_text}")
        
        # 2. 分词并转换为小写
        tokens = jieba.lcut(normalized_text.lower())
        
        return tokens
    except AttributeError as e:
        # 记录预处理失败
        logger.error(f"文本预处理失败: {e}")
        # 返回空列表
        return []


if __name__ == '__main__':
    # 测试用例
    test_cases = [
        "民法典第五百零九条是什么？",
        "民法典509条",
        "民法典第509条",
        "劳动法第十条",
        "公司法一百七十九条",
        "这是一个测试文本，我要吃白切鸡"
    ]
    
    for text in test_cases:
        print(f"原文: {text}")
        print(f"标准化: {normalize_law_reference(text)}")
        print(f"分词: {preprocess_text(text)}")
        print("-" * 50)
