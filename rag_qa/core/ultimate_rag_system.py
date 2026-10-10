"""
Phase 3: 最终增强版 RAG 系统

整合所有优化：
1. 智能上下文管理（截断 + 压缩）
2. 对话历史摘要
3. 优化的 Prompt 模板
4. Phase 2 的检索策略
"""

import time
from typing import List, Optional, Dict
from base import logger, Config
from .enhanced_rag_system import EnhancedRAGSystem
from .rag_context_manager import RAGContextManager
from .conversation_summary_manager import ConversationSummaryManager
from .enhanced_legal_prompts import EnhancedLegalPrompts


class UltimateRAGSystem(EnhancedRAGSystem):
    """Phase 3 最终增强版 RAG 系统"""

    def __init__(self, vector_store, llm_callable, strategy_selector=None):
        """
        初始化最终版 RAG 系统

        Args:
            vector_store: 向量存储对象
            llm_callable: LLM 调用函数
            strategy_selector: 检索策略选择器（可选）
        """
        # 继承 Phase 2 的增强 RAG 系统
        super().__init__(vector_store, llm_callable, strategy_selector)

        # Phase 3 新增组件
        self.context_manager = RAGContextManager(max_context_length=4000)
        self.summary_manager = ConversationSummaryManager(
            keep_recent_turns=3,
            max_history_length=2000
        )
        self.enhanced_prompts = EnhancedLegalPrompts()

        logger.info("✓ Phase 3 最终增强版 RAG 系统已启动")
        logger.info("  - 智能上下文管理")
        logger.info("  - 对话历史摘要")
        logger.info("  - 优化 Prompt 模板")

    def retrieve_documents(
        self,
        query: str,
        strategy: Optional[str] = None,
        apply_context_management: bool = True
    ) -> List:
        """
        检索文档（Phase 2 + Phase 3 优化）

        Args:
            query: 用户查询
            strategy: 检索策略
            apply_context_management: 是否应用上下文管理

        Returns:
            List: 检索到的文档列表
        """
        # 1. Phase 2: 使用策略检索
        docs = super().retrieve_documents(query, strategy)

        # 2. Phase 3: 上下文管理（截断 + 压缩）
        if apply_context_management and docs:
            docs = self.context_manager.truncate_documents(docs, query)
            logger.info(f"[Phase 3] 上下文管理后保留 {len(docs)} 个文档")

        return docs

    def generate_answer(
        self,
        query: str,
        context_docs: List,
        conversation_history: List[Dict] = None,
        stream: bool = True,
        use_enhanced_prompt: bool = True
    ):
        """
        生成答案（Phase 3 优化）

        Args:
            query: 用户查询
            context_docs: 检索到的文档
            conversation_history: 对话历史 [{"question": "...", "answer": "..."}]
            stream: 是否流式输出
            use_enhanced_prompt: 是否使用增强 Prompt

        Returns:
            生成器（流式）或字符串（非流式）
        """
        # 1. 处理对话历史
        conversation_context = ""
        if conversation_history:
            summary, recent_turns = self.summary_manager.manage_conversation_history(
                conversation_history
            )
            conversation_context = self.summary_manager.format_context_with_summary(
                summary, recent_turns, query
            )
            logger.info(f"[Phase 3] 对话上下文：摘要 {len(summary)} 字符，最近 {len(recent_turns)} 轮")

        # 2. 格式化文档上下文
        if context_docs:
            doc_context = self.context_manager.compress_context(context_docs, query)
        else:
            doc_context = "未检索到相关法律文档"

        # 3. 选择 Prompt 模板
        if use_enhanced_prompt:
            if conversation_history:
                # 有对话历史，使用支持历史的 Prompt
                prompt_template = self.enhanced_prompts.rag_prompt_with_history()
                full_prompt = prompt_template.format(
                    conversation_context=conversation_context,
                    context=doc_context,
                    question=query
                )
            else:
                # 无对话历史，使用简化版 Prompt
                prompt_template = self.enhanced_prompts.rag_prompt_simple()
                full_prompt = prompt_template.format(
                    context=doc_context,
                    question=query
                )
            logger.info("[Phase 3] 使用增强版 Prompt 模板")
        else:
            # 使用 Phase 2 的基础 Prompt
            prompt_template = self.prompts.rag_prompt()
            full_prompt = prompt_template.format(
                context=doc_context,
                question=query
            )

        # 4. 调用 LLM 生成答案
        if stream:
            return self.llm(full_prompt)
        else:
            return self._call_llm_sync(full_prompt)

    def query_with_history(
        self,
        query: str,
        conversation_history: List[Dict] = None,
        strategy: Optional[str] = None,
        stream: bool = True
    ):
        """
        完整查询流程（Phase 3 完整版）

        Args:
            query: 用户查询
            conversation_history: 对话历史
            strategy: 检索策略（可选）
            stream: 是否流式输出

        Returns:
            生成器（流式）或字符串（非流式）
        """
        start_time = time.time()

        logger.info(f"[Phase 3 查询] '{query}' (历史 {len(conversation_history or [])} 轮)")

        # 1. Phase 2: 检索文档
        docs = self.retrieve_documents(
            query,
            strategy=strategy,
            apply_context_management=True
        )

        # 2. Phase 3: 生成答案（支持对话历史）
        answer = self.generate_answer(
            query,
            docs,
            conversation_history=conversation_history,
            stream=stream,
            use_enhanced_prompt=True
        )

        elapsed = time.time() - start_time
        logger.info(f"[Phase 3 查询] 检索完成，耗时 {elapsed:.2f}s")

        return answer

    def query(
        self,
        query: str,
        strategy: Optional[str] = None,
        stream: bool = True,
        conversation_history: List[Dict] = None
    ):
        """
        统一查询接口（兼容 Phase 2 和 Phase 3）

        Args:
            query: 用户查询
            strategy: 检索策略（可选）
            stream: 是否流式输出
            conversation_history: 对话历史（可选，Phase 3 特性）

        Returns:
            生成器（流式）或字符串（非流式）
        """
        if conversation_history:
            # Phase 3 模式：支持对话历史
            return self.query_with_history(
                query,
                conversation_history=conversation_history,
                strategy=strategy,
                stream=stream
            )
        else:
            # Phase 2 模式：兼容旧接口
            return super().query(query, strategy=strategy, stream=stream)


# 测试代码
if __name__ == "__main__":
    print("=" * 80)
    print("Phase 3 最终增强版 RAG 系统")
    print("=" * 80)
    print("\n集成功能：")
    print("  ✓ Phase 1: 意图分类")
    print("  ✓ Phase 2: 检索策略选择（4种策略）")
    print("  ✓ Phase 3: 上下文管理 + 对话摘要 + 优化 Prompt")
    print("\n系统架构：")
    print("  用户查询")
    print("    ↓")
    print("  [意图分类] → 路由决策")
    print("    ↓")
    print("  [策略选择] → 4 种检索策略")
    print("    ↓")
    print("  [上下文管理] → 智能截断 + 压缩")
    print("    ↓")
    print("  [对话摘要] → 历史上下文整合")
    print("    ↓")
    print("  [优化 Prompt] → 结构化生成")
    print("    ↓")
    print("  [LLM 生成] → 专业法律回答")
    print("=" * 80)
