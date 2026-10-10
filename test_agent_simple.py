#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""简化版Agent测试 - 边界场景检测"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agentic.legal_agent_system import LegalAgentSystem

def test_scenario(name, queries, description):
    """测试单个场景"""
    print(f"\n{'='*80}")
    print(f"测试场景: {name}")
    print(f"描述: {description}")
    print(f"{'='*80}\n")

    agent = LegalAgentSystem()
    state = None

    for i, query in enumerate(queries, 1):
        print(f"【第{i}轮】用户: {query}")
        result = agent.run(query, state)
        state = result

        if result.get('need_clarify'):
            print(f"系统追问: {result.get('missing_info', [])}")
        elif result.get('final_answer'):
            answer = result['final_answer']
            print(f"系统回答: {answer[:150]}...")

        print(f"clarified_facts: {result.get('clarified_facts', {})}")
        print()

def main():
    print("\n开始Agent边界场景测试\n")

    # 测试1: 模糊金额
    test_scenario(
        "模糊金额表达",
        [
            "公司欠我好几万工资，怎么办？",
            "签了，深圳，有"
        ],
        "用户说'好几万'这种模糊表达，系统应该追问具体金额"
    )

    # 测试2: 否定回答
    test_scenario(
        "否定回答识别",
        [
            "公司拖欠我1万工资",
            "没有签合同，北京，有转账记录"
        ],
        "用户明确说'没有签合同'，应识别为未签订并提及双倍工资"
    )

    # 测试3: 不完整回答
    test_scenario(
        "不完整回答",
        [
            "公司拖欠我2万工资",
            "签了"
        ],
        "用户只回答了合同，没说地区和证据，应该继续追问"
    )

    # 测试4: 反问句
    test_scenario(
        "反问句处理",
        [
            "公司拖欠工资1万5",
            "合同肯定签了啊，广州的，证据当然有啊"
        ],
        "用户用反问语气，应该能正确识别'肯定签了'='已签订'"
    )

    # 测试5: 情绪化表达
    test_scenario(
        "情绪化表达",
        [
            "老板太过分了，拖欠我工资不给！",
            "签了合同，深圳，都有证据"
        ],
        "用户带情绪抱怨，系统应该过滤情绪词，正常处理"
    )

    # 测试6: 口语化数字
    test_scenario(
        "口语化数字",
        [
            "公司欠我一万多块钱工资",
            "签了，上海，有的"
        ],
        "用户说'一万多'，系统应识别为约1万并计算赔偿"
    )

    # 测试7: 中途放弃
    test_scenario(
        "中途放弃对话",
        [
            "公司欠我工资",
            "算了，不想问了"
        ],
        "用户中途放弃，系统应优雅结束而不是继续追问"
    )

    # 测试8: 一次性给全
    test_scenario(
        "一次性回答所有信息",
        [
            "我在深圳的公司签了劳动合同，但是拖欠我1.5万工资已经2个月了，我有工资条和转账记录，怎么维权？"
        ],
        "用户第一轮就给出所有信息，应该直接生成答案而不追问"
    )

    # 测试9: 地区别名
    test_scenario(
        "地区简称/别名",
        [
            "公司拖欠工资8000",
            "签了，在魔都，有证据"
        ],
        "用户说'魔都'（上海），系统可能识别不出但不应报错"
    )

    # 测试10: 数字+万混合
    test_scenario(
        "数字万元混合",
        [
            "公司拖欠我3w块钱",
            "签了劳动合同，杭州，有证据"
        ],
        "用户说'3w'，系统应识别为3万并正确计算赔偿"
    )

    print("\n" + "="*80)
    print("测试完成！请检查以上场景是否符合预期")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
