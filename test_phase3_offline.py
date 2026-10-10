"""
Phase 3 功能测试脚本（离线版）

测试内容：
1. 上下文管理器
2. 对话摘要管理器
3. 优化的 Prompt 模板
4. 最终 RAG 系统集成
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_context_manager():
    """测试上下文管理器"""
    print("=" * 80)
    print("测试 1: RAG 上下文管理器")
    print("=" * 80)

    try:
        from rag_qa.core.rag_context_manager import RAGContextManager

        # 模拟文档
        class MockDoc:
            def __init__(self, content, subject):
                self.page_content = content
                self.metadata = {'subject': subject}

        manager = RAGContextManager(max_context_length=1000)

        # 创建测试文档
        docs = [
            MockDoc("第五百零九条 当事人应当按照约定全面履行自己的义务。" * 5, "民法典"),
            MockDoc("第五十条 工资应当以货币形式按月支付给劳动者本人。" * 5, "劳动法"),
            MockDoc("第五百七十七条 当事人一方不履行合同义务。" * 5, "民法典"),
            MockDoc("第四十八条 用人单位违反本法规定解除劳动合同。" * 5, "劳动合同法"),
        ]

        print(f"\n原始文档: {len(docs)} 个")

        # 测试截断
        truncated = manager.truncate_documents(docs)
        print(f"截断后: {len(truncated)} 个")

        # 测试压缩
        context = manager.compress_context(truncated)
        print(f"压缩后上下文长度: {len(context)} 字符")

        print("\n[OK] 上下文管理器测试通过")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n[FAIL] 上下文管理器测试失败: {e}")
        print("=" * 80)
        return False


def test_conversation_summary():
    """测试对话摘要管理器"""
    print("\n" + "=" * 80)
    print("测试 2: 对话摘要管理器")
    print("=" * 80)

    try:
        from rag_qa.core.conversation_summary_manager import ConversationSummaryManager

        manager = ConversationSummaryManager(keep_recent_turns=2)

        # 测试历史
        test_history = [
            {"question": "民法典第509条是什么？", "answer": "第五百零九条..."},
            {"question": "合同违约怎么处理？", "answer": "根据民法典..."},
            {"question": "违约金有上限吗？", "answer": "根据民法典..."},
            {"question": "试用期最长多久？", "answer": "根据劳动合同法..."},
            {"question": "试用期可以随意解除吗？", "answer": "不可以..."},
        ]

        print(f"\n总对话轮数: {len(test_history)}")

        # 测试管理（不调用 API）
        if len(test_history) > manager.keep_recent_turns:
            old_history = test_history[:-manager.keep_recent_turns]
            recent_history = test_history[-manager.keep_recent_turns:]

            print(f"历史对话: {len(old_history)} 轮（需要摘要）")
            print(f"最近对话: {len(recent_history)} 轮（保留完整）")

            # 测试简单摘要
            simple_summary = manager._simple_summary(old_history)
            print(f"\n简单摘要长度: {len(simple_summary)} 字符")
            print(f"摘要预览: {simple_summary[:100]}...")

        print("\n[OK] 对话摘要管理器测试通过")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n[FAIL] 对话摘要管理器测试失败: {e}")
        print("=" * 80)
        return False


def test_enhanced_prompts():
    """测试优化的 Prompt 模板"""
    print("\n" + "=" * 80)
    print("测试 3: 优化的 Prompt 模板")
    print("=" * 80)

    try:
        from rag_qa.core.enhanced_legal_prompts import EnhancedLegalPrompts

        prompts = EnhancedLegalPrompts()

        tests = [
            ("RAG (支持历史)", prompts.rag_prompt_with_history(),
             {"conversation_context": "历史", "context": "法条", "question": "问题"}),
            ("RAG (简化版)", prompts.rag_prompt_simple(),
             {"context": "法条", "question": "问题"}),
            ("RAG (Few-Shot)", prompts.rag_prompt_with_examples(),
             {"context": "法条", "question": "问题"}),
            ("子查询分解", prompts.subquery_prompt_enhanced(),
             {"query": "测试查询"}),
            ("HyDE", prompts.hyde_prompt_enhanced(),
             {"query": "测试查询"}),
            ("回溯简化", prompts.backtracking_prompt_enhanced(),
             {"query": "测试查询"}),
        ]

        print("\nPrompt 模板测试:")
        for name, template, params in tests:
            try:
                formatted = template.format(**params)
                print(f"  [OK] {name}: {len(formatted)} 字符")
            except Exception as e:
                print(f"  [FAIL] {name}: {e}")
                return False

        print("\n[OK] 所有 Prompt 模板测试通过")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n[FAIL] Prompt 模板测试失败: {e}")
        print("=" * 80)
        return False


def test_ultimate_rag():
    """测试最终 RAG 系统类结构"""
    print("\n" + "=" * 80)
    print("测试 4: 最终 RAG 系统")
    print("=" * 80)

    try:
        from rag_qa.core.ultimate_rag_system import UltimateRAGSystem

        # 检查关键方法
        methods = [
            "retrieve_documents",
            "generate_answer",
            "query_with_history",
            "query",
        ]

        print("\n方法检查:")
        for method in methods:
            has_method = hasattr(UltimateRAGSystem, method)
            status = "[OK]" if has_method else "[FAIL]"
            print(f"  {status} {method}")
            if not has_method:
                return False

        print("\n[OK] 最终 RAG 系统类结构正常")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n[FAIL] 最终 RAG 系统测试失败: {e}")
        print("=" * 80)
        return False


def test_system_integration():
    """测试系统集成"""
    print("\n" + "=" * 80)
    print("测试 5: 系统集成检查")
    print("=" * 80)

    files = [
        "rag_qa/core/rag_context_manager.py",
        "rag_qa/core/conversation_summary_manager.py",
        "rag_qa/core/enhanced_legal_prompts.py",
        "rag_qa/core/ultimate_rag_system.py",
        "new_main_v3.py",
    ]

    print("\n文件检查:")
    results = []
    for file in files:
        exists = os.path.exists(file)
        status = "[OK]" if exists else "[FAIL]"
        size = os.path.getsize(file) if exists else 0
        print(f"  {status} {file} ({size} bytes)")
        results.append(exists)

    print(f"\n通过: {sum(results)}/{len(results)}")
    print("=" * 80)
    return all(results)


def test_module_imports():
    """测试模块导入"""
    print("\n" + "=" * 80)
    print("测试 6: 模块导入")
    print("=" * 80)

    modules = [
        ("RAG 上下文管理器", "rag_qa.core.rag_context_manager", "RAGContextManager"),
        ("对话摘要管理器", "rag_qa.core.conversation_summary_manager", "ConversationSummaryManager"),
        ("优化 Prompt", "rag_qa.core.enhanced_legal_prompts", "EnhancedLegalPrompts"),
        ("最终 RAG 系统", "rag_qa.core.ultimate_rag_system", "UltimateRAGSystem"),
    ]

    print("\n导入检查:")
    results = []
    for name, module_path, class_name in modules:
        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            print(f"  [OK] {name}")
            results.append(True)
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            results.append(False)

    print(f"\n通过: {sum(results)}/{len(results)}")
    print("=" * 80)
    return all(results)


def main():
    """主测试函数"""
    print("\n")
    print("=" * 80)
    print("Phase 3 功能测试（离线版）")
    print("=" * 80)
    print()

    results = []

    # 运行所有测试
    results.append(("模块导入", test_module_imports()))
    results.append(("上下文管理器", test_context_manager()))
    results.append(("对话摘要", test_conversation_summary()))
    results.append(("Prompt 模板", test_enhanced_prompts()))
    results.append(("最终 RAG", test_ultimate_rag()))
    results.append(("系统集成", test_system_integration()))

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
        print("\n[SUCCESS] 所有测试通过！Phase 3 集成成功")
        print("\nPhase 3 新增功能:")
        print("  - 智能上下文管理（截断 + 压缩）")
        print("  - 对话历史摘要（保留最近 N 轮 + 历史摘要）")
        print("  - 优化 Prompt 模板（结构化 + Few-Shot + 专业表达）")
        print("  - 最终增强 RAG 系统（整合所有优化）")
    else:
        print(f"\n[PARTIAL] 部分测试通过")

    print("=" * 80)


if __name__ == "__main__":
    main()
