#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Agent系统测试用例集 - 边界场景和漏洞检测"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agentic.legal_agent_system import LegalAgentSystem
from base import logger

class AgentTester:
    def __init__(self):
        self.agent = LegalAgentSystem()
        self.test_cases = []
        self.failed_cases = []

    def add_test(self, name, scenario, queries, expected_behaviors):
        """添加测试用例

        Args:
            name: 测试名称
            scenario: 场景描述
            queries: 用户输入序列（列表）
            expected_behaviors: 预期行为检查点（字典列表）
        """
        self.test_cases.append({
            "name": name,
            "scenario": scenario,
            "queries": queries,
            "expected": expected_behaviors
        })

    def run_test(self, test_case):
        """执行单个测试"""
        print(f"\n{'='*80}")
        print(f"测试: {test_case['name']}")
        print(f"场景: {test_case['scenario']}")
        print(f"{'='*80}")

        state = None
        passed = True

        for i, query in enumerate(test_case['queries']):
            print(f"\n第 {i+1} 轮输入: {query}")
            result = self.agent.run(query, state)
            state = result

            # 显示响应
            if result.get('need_clarify'):
                print(f"系统追问: {result.get('missing_info', [])}")
            elif result.get('final_answer'):
                print(f"系统回答: {result['final_answer'][:200]}...")

            # 检查预期行为
            if i < len(test_case['expected']):
                checks = test_case['expected'][i]
                for key, expected_value in checks.items():
                    actual_value = result.get(key)

                    if key == "should_clarify":
                        if result.get('need_clarify') != expected_value:
                            print(f"❌ 检查失败: need_clarify 应为 {expected_value}, 实际为 {result.get('need_clarify')}")
                            passed = False
                        else:
                            print(f"✅ need_clarify = {expected_value}")

                    elif key == "should_contain":
                        content = result.get('final_answer', '') + str(result.get('missing_info', []))
                        if expected_value not in content:
                            print(f"❌ 检查失败: 响应应包含 '{expected_value}'")
                            passed = False
                        else:
                            print(f"✅ 响应包含: {expected_value}")

                    elif key == "should_not_contain":
                        content = result.get('final_answer', '') + str(result.get('missing_info', []))
                        if expected_value in content:
                            print(f"❌ 检查失败: 响应不应包含 '{expected_value}'")
                            passed = False
                        else:
                            print(f"✅ 响应不包含: {expected_value}")

                    elif key == "clarified_facts_should_have":
                        clarified = result.get('clarified_facts', {})
                        if expected_value not in clarified:
                            print(f"❌ 检查失败: clarified_facts 应包含字段 '{expected_value}'")
                            passed = False
                        else:
                            print(f"✅ clarified_facts 包含: {expected_value} = {clarified[expected_value]}")

        if not passed:
            self.failed_cases.append(test_case['name'])

        print(f"\n{'='*80}")
        print(f"测试结果: {'✅ 通过' if passed else '❌ 失败'}")
        print(f"{'='*80}")

        return passed

    def run_all(self):
        """运行所有测试"""
        print(f"\n开始测试，共 {len(self.test_cases)} 个用例\n")

        passed_count = 0
        for test_case in self.test_cases:
            if self.run_test(test_case):
                passed_count += 1

        print(f"\n{'='*80}")
        print(f"测试总结")
        print(f"{'='*80}")
        print(f"通过: {passed_count}/{len(self.test_cases)}")
        if self.failed_cases:
            print(f"失败用例: {', '.join(self.failed_cases)}")
        print(f"{'='*80}\n")


def main():
    tester = AgentTester()

    # ========== 测试1: 模糊数字表达 ==========
    tester.add_test(
        name="模糊数字表达",
        scenario="用户说'几千块'、'好几万'等模糊金额",
        queries=[
            "公司欠我好几万工资，怎么办？",
            "签了，深圳，有"
        ],
        expected=[
            {"should_clarify": True, "should_contain": "拖欠金额"},
            {"should_contain": "深圳"}
        ]
    )

    # ========== 测试2: 否定回答识别 ==========
    tester.add_test(
        name="否定回答识别",
        scenario="用户回答'没有'、'否'",
        queries=[
            "公司拖欠我1万工资",
            "没有签合同，在北京，有转账记录"
        ],
        expected=[
            {"should_clarify": True},
            {"clarified_facts_should_have": "labor_contract", "should_contain": "双倍工资"}
        ]
    )

    # ========== 测试3: 重复提问检测 ==========
    tester.add_test(
        name="重复提问检测",
        scenario="用户重复问同一个问题",
        queries=[
            "公司拖欠工资怎么办？",
            "公司拖欠工资怎么办？"  # 完全重复
        ],
        expected=[
            {"should_clarify": True},
            {"should_not_contain": "请重复"}  # 不应该让用户觉得系统没理解
        ]
    )

    # ========== 测试4: 不完整回答 ==========
    tester.add_test(
        name="不完整回答",
        scenario="用户只回答了部分问题",
        queries=[
            "公司拖欠我2万工资",
            "签了合同"  # 只回答了合同，没说地区和证据
        ],
        expected=[
            {"should_clarify": True},
            {"should_clarify": True, "should_contain": "省市"}  # 应该继续追问
        ]
    )

    # ========== 测试5: 反问句处理 ==========
    tester.add_test(
        name="反问句处理",
        scenario="用户用反问句回答",
        queries=[
            "公司拖欠工资1万5",
            "合同肯定签了啊，在广州，证据当然有"
        ],
        expected=[
            {"should_clarify": True},
            {"clarified_facts_should_have": "labor_contract", "should_contain": "广州"}
        ]
    )

    # ========== 测试6: 情绪化表达 ==========
    tester.add_test(
        name="情绪化表达",
        scenario="用户带情绪抱怨",
        queries=[
            "老板是个王八蛋，拖欠我工资不给，气死我了！",
            "当然签了合同，深圳的公司，证据我都留着呢"
        ],
        expected=[
            {"should_clarify": True},
            {"should_contain": "深圳", "should_not_contain": "王八蛋"}
        ]
    )

    # ========== 测试7: 口语化数字 ==========
    tester.add_test(
        name="口语化数字",
        scenario="用户用口语表达数字",
        queries=[
            "公司欠我一万多块钱",
            "签了，上海，有的"
        ],
        expected=[
            {"should_clarify": True},
            {"should_contain": "上海", "should_contain": "1.0万"}
        ]
    )

    # ========== 测试8: 多轮对话中途放弃 ==========
    tester.add_test(
        name="中途放弃",
        scenario="用户追问到一半不想继续了",
        queries=[
            "公司欠我工资",
            "算了，不问了"
        ],
        expected=[
            {"should_clarify": True},
            {"should_contain": "欢迎随时咨询"}
        ]
    )

    # ========== 测试9: 地区简称/别名 ==========
    tester.add_test(
        name="地区简称",
        scenario="用户用地区简称",
        queries=[
            "公司拖欠工资8000",
            "签了，在帝都，有证据"  # 帝都=北京
        ],
        expected=[
            {"should_clarify": True},
            {"should_contain": "劳动"}  # 应该能生成答案，即使没识别出"帝都"
        ]
    )

    # ========== 测试10: 一次性回答所有问题 ==========
    tester.add_test(
        name="一次性回答",
        scenario="用户在第一轮就给出所有信息",
        queries=[
            "我在深圳的公司签了劳动合同，但是拖欠我1.5万工资已经2个月了，我有工资条和转账记录，怎么维权？"
        ],
        expected=[
            {"should_clarify": False, "should_contain": "深圳", "should_contain": "1.5万"}
        ]
    )

    # 运行所有测试
    tester.run_all()


if __name__ == "__main__":
    main()
