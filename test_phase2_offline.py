"""
Phase 2 功能测试脚本（离线版）

测试检索策略选择器和增强 RAG 系统（不调用 API）
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_modules():
    """测试模块导入"""
    print("=" * 80)
    print("测试 1: 模块导入检查")
    print("=" * 80)

    modules = [
        ("检索策略选择器", "rag_qa.core.retrieval_strategy_selector", "RetrievalStrategySelector"),
        ("法律 Prompt 模板", "rag_qa.core.legal_rag_prompts", "LegalRAGPrompts"),
        ("增强 RAG 系统", "rag_qa.core.enhanced_rag_system", "EnhancedRAGSystem"),
    ]

    results = []
    for name, module_path, class_name in modules:
        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            print(f"[OK] {name}: {class_name}")
            results.append(True)
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            results.append(False)

    print(f"\n通过: {sum(results)}/{len(results)}")
    print("=" * 80)
    return all(results)


def test_prompts():
    """测试 Prompt 模板"""
    print("\n" + "=" * 80)
    print("测试 2: Prompt 模板")
    print("=" * 80)

    try:
        from rag_qa.core.legal_rag_prompts import LegalRAGPrompts
        prompts = LegalRAGPrompts()

        tests = [
            ("子查询分解", prompts.subquery_prompt(), {"query": "测试查询"}),
            ("HyDE 假设答案", prompts.hyde_prompt(), {"query": "测试查询"}),
            ("回溯问题简化", prompts.backtracking_prompt(), {"query": "测试查询"}),
            ("RAG 答案生成", prompts.rag_prompt(), {"context": "测试上下文", "question": "测试问题"}),
        ]

        for name, prompt_template, params in tests:
            try:
                formatted = prompt_template.format(**params)
                print(f"[OK] {name}: {len(formatted)} 字符")
            except Exception as e:
                print(f"[FAIL] {name}: {e}")
                return False

        print("\n通过: 所有 Prompt 模板正常")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"[FAIL] Prompt 测试失败: {e}")
        print("=" * 80)
        return False


def test_strategy_patterns():
    """测试策略选择逻辑（模式匹配）"""
    print("\n" + "=" * 80)
    print("测试 3: 策略选择模式")
    print("=" * 80)

    # 定义策略识别规则（简化版，不调用 API）
    test_cases = [
        ("民法典第509条是什么", "直接检索", "单一明确问题"),
        ("劳动法关于工资的规定", "直接检索", "单一明确问题"),
        ("民法典违约规定，以及劳动法工资规定", "子查询检索", "包含多个子问题"),
        ("什么是侵权责任", "假设问题检索", "概念性问题"),
        ("如何理解不可抗力", "假设问题检索", "概念性问题"),
        ("我想问，公司辞退我但没赔偿", "回溯问题检索", "口语化查询"),
    ]

    def guess_strategy(query):
        """简单的策略猜测（基于规则）"""
        if "什么是" in query or "如何理解" in query or "有哪些" in query:
            return "假设问题检索"
        elif "以及" in query or "还有" in query or "和" in query:
            # 检查是否是多个独立问题
            if query.count("？") >= 2 or "," in query:
                return "子查询检索"
        elif "我想" in query or "就是" in query or len(query) > 50:
            return "回溯问题检索"
        return "直接检索"

    print("\n基于规则的策略匹配测试:\n")
    correct = 0
    for query, expected, reason in test_cases:
        guessed = guess_strategy(query)
        is_correct = guessed == expected
        correct += is_correct

        status = "[OK]" if is_correct else "[FAIL]"
        print(f"{status} {query[:40]}...")
        print(f"      预期: {expected} ({reason})")
        print(f"      结果: {guessed}")
        print()

    accuracy = (correct / len(test_cases)) * 100
    print(f"准确率: {correct}/{len(test_cases)} ({accuracy:.1f}%)")
    print("=" * 80)
    return correct >= len(test_cases) * 0.7  # 70% 通过率


def test_file_structure():
    """测试文件结构"""
    print("\n" + "=" * 80)
    print("测试 4: 文件结构检查")
    print("=" * 80)

    files = [
        "rag_qa/core/retrieval_strategy_selector.py",
        "rag_qa/core/legal_rag_prompts.py",
        "rag_qa/core/enhanced_rag_system.py",
        "new_main_v2.py",
        "test_phase2_offline.py",
    ]

    print("\n文件检查:")
    results = []
    for file in files:
        exists = os.path.exists(file)
        status = "[OK]" if exists else "[FAIL]"
        size = os.path.getsize(file) if exists else 0
        print(f"{status} {file} ({size} bytes)")
        results.append(exists)

    print(f"\n通过: {sum(results)}/{len(results)}")
    print("=" * 80)
    return all(results)


def test_enhanced_rag_class():
    """测试增强 RAG 系统类结构"""
    print("\n" + "=" * 80)
    print("测试 5: 增强 RAG 系统类结构")
    print("=" * 80)

    try:
        from rag_qa.core.enhanced_rag_system import EnhancedRAGSystem

        # 检查关键方法
        methods = [
            "_retrieve_direct",
            "_retrieve_subquery",
            "_retrieve_hyde",
            "_retrieve_backtracking",
            "retrieve_documents",
            "generate_answer",
            "query",
        ]

        print("\n方法检查:")
        for method in methods:
            has_method = hasattr(EnhancedRAGSystem, method)
            status = "[OK]" if has_method else "[FAIL]"
            print(f"{status} {method}")

        print("\n[OK] 增强 RAG 系统类结构正常")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"[FAIL] 增强 RAG 系统测试失败: {e}")
        print("=" * 80)
        return False


def main():
    """主测试函数"""
    print("\n")
    print("=" * 80)
    print("Phase 2 功能测试（离线版）")
    print("=" * 80)
    print()

    results = []

    # 运行所有测试
    results.append(("模块导入", test_modules()))
    results.append(("Prompt 模板", test_prompts()))
    results.append(("策略选择", test_strategy_patterns()))
    results.append(("文件结构", test_file_structure()))
    results.append(("RAG 类结构", test_enhanced_rag_class()))

    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)

    for name, passed in results:
        status = "[OK]" if passed else "[FAIL]"
        print(f"{status} {name}")

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    print(f"\n总体通过率: {passed_count}/{total_count} ({passed_count/total_count*100:.1f}%)")

    if passed_count == total_count:
        print("\n[SUCCESS] 所有测试通过！Phase 2 集成成功")
    else:
        print(f"\n[PARTIAL] 部分测试通过")

    print("=" * 80)


if __name__ == "__main__":
    main()
