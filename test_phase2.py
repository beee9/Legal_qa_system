"""
Phase 2 功能测试脚本

测试检索策略选择器和增强 RAG 系统
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_qa.core.retrieval_strategy_selector import RetrievalStrategySelector
from rag_qa.core.legal_rag_prompts import LegalRAGPrompts


def test_strategy_selector():
    """测试检索策略选择器"""
    print("=" * 80)
    print("测试 1：检索策略选择器")
    print("=" * 80)

    selector = RetrievalStrategySelector()

    test_cases = [
        ("民法典第509条是什么", "直接检索"),
        ("劳动法关于工资支付的规定", "直接检索"),
        ("民法典关于合同违约的规定，以及劳动法关于工资支付的规定", "子查询检索"),
        ("公司注册需要什么材料？注销又需要什么流程？", "子查询检索"),
        ("什么是侵权责任", "假设问题检索"),
        ("如何理解不可抗力", "假设问题检索"),
        ("股权转让有哪些注意事项", "假设问题检索"),
        ("我想问一下，就是那个，公司把我辞退了但没给赔偿，怎么办", "回溯问题检索"),
        ("昨天我和老板吵架了，他说要扣我工资，请问这样合法吗", "回溯问题检索"),
    ]

    print("\n测试查询：\n")
    correct = 0
    total = len(test_cases)

    for query, expected_strategy in test_cases:
        try:
            strategy = selector.select_strategy(query)
            is_correct = strategy == expected_strategy
            correct += is_correct

            status = "✓" if is_correct else "✗"
            print(f"{status} 查询: {query[:50]}...")
            print(f"  预期策略: {expected_strategy}")
            print(f"  实际策略: {strategy}")
            print()
        except Exception as e:
            print(f"✗ 查询: {query[:50]}...")
            print(f"  错误: {e}")
            print()

    accuracy = (correct / total) * 100
    print(f"\n准确率: {correct}/{total} ({accuracy:.1f}%)")
    print("=" * 80)


def test_prompts():
    """测试 Prompt 模板"""
    print("\n" + "=" * 80)
    print("测试 2：Prompt 模板")
    print("=" * 80)

    prompts = LegalRAGPrompts()

    # 测试子查询分解
    print("\n[子查询分解 Prompt]")
    subquery_prompt = prompts.subquery_prompt()
    test_query = "民法典关于合同违约的规定，以及劳动法关于工资支付的规定"
    formatted = subquery_prompt.format(query=test_query)
    print(formatted[:300] + "...")

    # 测试 HyDE
    print("\n[HyDE Prompt]")
    hyde_prompt = prompts.hyde_prompt()
    test_query = "什么是侵权责任"
    formatted = hyde_prompt.format(query=test_query)
    print(formatted[:300] + "...")

    # 测试回溯问题
    print("\n[回溯问题 Prompt]")
    backtrack_prompt = prompts.backtracking_prompt()
    test_query = "我想问一下，就是那个，公司把我辞退了但没给赔偿"
    formatted = backtrack_prompt.format(query=test_query)
    print(formatted[:300] + "...")

    # 测试 RAG 生成
    print("\n[RAG 答案生成 Prompt]")
    rag_prompt = prompts.rag_prompt()
    context = "民法典第509条：当事人应当按照约定全面履行自己的义务..."
    question = "民法典第509条是什么？"
    formatted = rag_prompt.format(context=context, question=question)
    print(formatted[:300] + "...")

    print("\n✓ 所有 Prompt 模板正常")
    print("=" * 80)


def test_system_integration():
    """测试系统集成"""
    print("\n" + "=" * 80)
    print("测试 3：系统集成检查")
    print("=" * 80)

    checks = []

    # 检查文件是否存在
    files = [
        "rag_qa/core/retrieval_strategy_selector.py",
        "rag_qa/core/legal_rag_prompts.py",
        "rag_qa/core/enhanced_rag_system.py",
        "new_main_v2.py",
    ]

    print("\n文件检查：")
    for file in files:
        exists = os.path.exists(file)
        status = "✓" if exists else "✗"
        print(f"  {status} {file}")
        checks.append(exists)

    # 检查模块导入
    print("\n模块导入检查：")
    try:
        from rag_qa.core.retrieval_strategy_selector import RetrievalStrategySelector
        print("  ✓ RetrievalStrategySelector")
        checks.append(True)
    except ImportError as e:
        print(f"  ✗ RetrievalStrategySelector: {e}")
        checks.append(False)

    try:
        from rag_qa.core.legal_rag_prompts import LegalRAGPrompts
        print("  ✓ LegalRAGPrompts")
        checks.append(True)
    except ImportError as e:
        print(f"  ✗ LegalRAGPrompts: {e}")
        checks.append(False)

    try:
        from rag_qa.core.enhanced_rag_system import EnhancedRAGSystem
        print("  ✓ EnhancedRAGSystem")
        checks.append(True)
    except ImportError as e:
        print(f"  ✗ EnhancedRAGSystem: {e}")
        checks.append(False)

    # 总结
    print("\n" + "=" * 80)
    if all(checks):
        print("✓ 所有检查通过！Phase 2 集成成功")
    else:
        print(f"✗ 部分检查失败：{sum(checks)}/{len(checks)} 通过")
    print("=" * 80)


def main():
    """主测试函数"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "Phase 2 功能测试" + " " * 43 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    try:
        # 测试 1：策略选择器
        test_strategy_selector()

        # 测试 2：Prompt 模板
        test_prompts()

        # 测试 3：系统集成
        test_system_integration()

        print("\n" + "=" * 80)
        print("测试完成！")
        print("=" * 80)

    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
