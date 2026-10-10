"""
Phase 3: RAG 上下文管理器

优化功能：
1. 智能截断逻辑（基于相关性和重要性）
2. 上下文压缩（去除冗余信息）
3. 分层组织（按法律来源和相关性排序）
"""

from typing import List, Dict, Any
from base import logger


class RAGContextManager:
    """RAG 上下文管理器"""

    def __init__(self, max_context_length: int = 4000):
        """
        初始化上下文管理器

        Args:
            max_context_length: 最大上下文字符数（考虑 LLM token 限制）
        """
        self.max_context_length = max_context_length

    def truncate_documents(self, docs: List, query: str = None) -> List:
        """
        智能截断文档列表

        策略：
        1. 优先保留高相关性文档
        2. 每个法律来源至少保留 1 个文档
        3. 考虑文档多样性

        Args:
            docs: 文档列表（已按相关性排序）
            query: 原始查询（可选，用于二次筛选）

        Returns:
            List: 截断后的文档列表
        """
        if not docs:
            return []

        # 1. 按法律来源分组
        docs_by_source = {}
        for doc in docs:
            source = doc.metadata.get('subject', '未知')
            if source not in docs_by_source:
                docs_by_source[source] = []
            docs_by_source[source].append(doc)

        # 2. 每个来源保留最相关的文档
        selected_docs = []
        for source, source_docs in docs_by_source.items():
            # 至少保留 1 个，最多保留 3 个
            top_docs = source_docs[:min(3, len(source_docs))]
            selected_docs.extend(top_docs)

        # 3. 按原始相关性重新排序
        selected_docs = sorted(
            selected_docs,
            key=lambda d: docs.index(d) if d in docs else float('inf')
        )

        # 4. 按长度截断
        truncated = self._truncate_by_length(selected_docs)

        logger.info(
            f"[上下文管理] 原始 {len(docs)} 个文档 → "
            f"截断为 {len(truncated)} 个文档（来源数：{len(docs_by_source)}）"
        )

        return truncated

    def _truncate_by_length(self, docs: List) -> List:
        """
        按长度截断，确保不超过最大上下文长度

        Args:
            docs: 文档列表

        Returns:
            List: 截断后的文档列表
        """
        total_length = 0
        truncated_docs = []

        for doc in docs:
            doc_length = len(doc.page_content)

            # 预留空间给格式化（【法律名】标签、换行等）
            estimated_length = total_length + doc_length + 100

            if estimated_length > self.max_context_length:
                # 如果已经有至少 2 个文档，停止添加
                if len(truncated_docs) >= 2:
                    logger.info(
                        f"[上下文管理] 达到长度限制 {self.max_context_length}，"
                        f"保留 {len(truncated_docs)} 个文档"
                    )
                    break

                # 如果只有 0-1 个文档，截断当前文档的内容
                remaining_space = self.max_context_length - total_length - 100
                if remaining_space > 200:  # 至少保留 200 字符
                    truncated_content = doc.page_content[:remaining_space] + "..."
                    doc.page_content = truncated_content
                    truncated_docs.append(doc)
                    logger.info(
                        f"[上下文管理] 截断文档内容：{doc_length} → {len(truncated_content)} 字符"
                    )
                break

            truncated_docs.append(doc)
            total_length = estimated_length

        return truncated_docs

    def compress_context(self, docs: List, query: str = None) -> str:
        """
        压缩并格式化上下文

        Args:
            docs: 文档列表
            query: 原始查询（可选）

        Returns:
            str: 格式化的上下文字符串
        """
        if not docs:
            return "未检索到相关法律文档"

        # 构建格式化上下文
        context_parts = []

        # 按法律来源分组
        docs_by_source = {}
        for doc in docs:
            source = doc.metadata.get('subject', '未知')
            if source not in docs_by_source:
                docs_by_source[source] = []
            docs_by_source[source].append(doc)

        # 格式化输出
        for source, source_docs in docs_by_source.items():
            context_parts.append(f"【{source}】")
            for i, doc in enumerate(source_docs, 1):
                # 去除多余空白
                content = self._clean_content(doc.page_content)
                context_parts.append(content)

            context_parts.append("")  # 来源间空行

        context = "\n".join(context_parts).strip()

        # 记录统计信息
        total_chars = len(context)
        logger.info(
            f"[上下文管理] 最终上下文：{total_chars} 字符，"
            f"{len(docs)} 个文档，{len(docs_by_source)} 个法律来源"
        )

        return context

    def _clean_content(self, content: str) -> str:
        """
        清理文档内容

        Args:
            content: 原始内容

        Returns:
            str: 清理后的内容
        """
        # 1. 去除多余空白
        content = " ".join(content.split())

        # 2. 去除重复的法律名称前缀（如果已经在【】标签中）
        # 例如："民法典第509条" → "第509条"（如果已有【民法典】标签）
        # 这里简化处理，实际可以更复杂

        return content

    def format_context_with_metadata(self, docs: List) -> List[Dict[str, Any]]:
        """
        格式化上下文，保留元数据（用于引用溯源）

        Args:
            docs: 文档列表

        Returns:
            List[Dict]: 包含内容和元数据的字典列表
        """
        formatted = []
        for doc in docs:
            formatted.append({
                'content': doc.page_content,
                'source': doc.metadata.get('subject', '未知'),
                'metadata': doc.metadata
            })
        return formatted


# 测试代码
if __name__ == "__main__":
    print("=" * 80)
    print("RAG 上下文管理器测试")
    print("=" * 80)

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
        MockDoc("第五百七十七条 当事人一方不履行合同义务或者履行合同义务不符合约定的。" * 5, "民法典"),
        MockDoc("第四十八条 用人单位违反本法规定解除或者终止劳动合同。" * 5, "劳动合同法"),
    ]

    print("\n1. 原始文档数量:", len(docs))
    print("   来源分布:", {doc.metadata['subject'] for doc in docs})

    # 测试截断
    truncated = manager.truncate_documents(docs)
    print("\n2. 截断后文档数量:", len(truncated))

    # 测试压缩
    context = manager.compress_context(truncated)
    print("\n3. 压缩后上下文长度:", len(context))
    print("\n4. 上下文预览:")
    print(context[:300] + "...")

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
