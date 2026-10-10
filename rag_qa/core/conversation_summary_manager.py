"""
Phase 3: 对话历史摘要管理器

优化功能：
1. 智能摘要历史对话（避免上下文过长）
2. 保留关键信息（法律要点、用户问题）
3. 滑动窗口管理（保留最近 N 轮完整对话 + 历史摘要）
"""

from typing import List, Dict, Tuple
from base import logger, Config
from openai import OpenAI


class ConversationSummaryManager:
    """对话历史摘要管理器"""

    def __init__(self, keep_recent_turns: int = 3, max_history_length: int = 2000):
        """
        初始化摘要管理器

        Args:
            keep_recent_turns: 保留最近 N 轮完整对话
            max_history_length: 历史摘要最大长度
        """
        self.keep_recent_turns = keep_recent_turns
        self.max_history_length = max_history_length

        # 初始化 LLM 客户端（用于生成摘要）
        config = Config()
        self.client = OpenAI(
            api_key=config.DASHSCOPE_API_KEY,
            base_url=config.DASHSCOPE_BASE_URL
        )
        self.llm_model = config.LLM_MODEL

    def manage_conversation_history(
        self,
        history: List[Dict[str, str]],
        existing_summary: str = None
    ) -> Tuple[str, List[Dict[str, str]]]:
        """
        管理对话历史

        策略：
        - 最近 N 轮：保留完整对话
        - 历史轮次：生成摘要

        Args:
            history: 对话历史列表 [{"question": "...", "answer": "..."}]
            existing_summary: 已有的历史摘要（可选）

        Returns:
            Tuple[str, List]: (历史摘要, 最近N轮对话)
        """
        if not history:
            return "", []

        # 1. 分离历史和最近对话
        if len(history) <= self.keep_recent_turns:
            # 对话轮次较少，不需要摘要
            return "", history

        # 历史轮次（需要摘要）
        old_history = history[:-self.keep_recent_turns]
        # 最近轮次（保留完整）
        recent_history = history[-self.keep_recent_turns:]

        # 2. 生成或更新摘要
        if old_history:
            summary = self._generate_summary(old_history, existing_summary)
        else:
            summary = existing_summary or ""

        logger.info(
            f"[对话摘要] 历史 {len(old_history)} 轮 → 摘要 {len(summary)} 字符，"
            f"保留最近 {len(recent_history)} 轮完整对话"
        )

        return summary, recent_history

    def _generate_summary(
        self,
        history: List[Dict[str, str]],
        existing_summary: str = None
    ) -> str:
        """
        生成对话摘要

        Args:
            history: 需要摘要的对话历史
            existing_summary: 已有摘要（增量更新）

        Returns:
            str: 生成的摘要
        """
        try:
            # 构建摘要 Prompt
            prompt = self._build_summary_prompt(history, existing_summary)

            # 调用 LLM 生成摘要
            completion = self.client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "你是一个专业的对话摘要助手。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )

            summary = completion.choices[0].message.content.strip()

            # 控制摘要长度
            if len(summary) > self.max_history_length:
                summary = summary[:self.max_history_length] + "..."
                logger.warning(f"[对话摘要] 摘要过长，截断到 {self.max_history_length} 字符")

            logger.info(f"[对话摘要] 生成摘要：{len(summary)} 字符")
            return summary

        except Exception as e:
            logger.error(f"[对话摘要] 生成失败: {e}")
            # 失败时返回简化摘要
            return self._simple_summary(history, existing_summary)

    def _build_summary_prompt(
        self,
        history: List[Dict[str, str]],
        existing_summary: str = None
    ) -> str:
        """
        构建摘要 Prompt

        Args:
            history: 对话历史
            existing_summary: 已有摘要

        Returns:
            str: Prompt 字符串
        """
        # 格式化对话历史
        history_text = ""
        for i, turn in enumerate(history, 1):
            history_text += f"轮次 {i}：\n"
            history_text += f"问：{turn['question']}\n"
            history_text += f"答：{turn['answer'][:200]}{'...' if len(turn['answer']) > 200 else ''}\n\n"

        # 构建 Prompt
        if existing_summary:
            prompt = f"""
你需要更新以下对话摘要，将新的对话轮次整合进去。

**已有摘要**：
{existing_summary}

**新增对话**：
{history_text}

**要求**：
1. 提取关键法律问题和要点
2. 保留重要的法律条文引用
3. 去除冗余和重复信息
4. 使用简洁专业的语言
5. 控制在 300 字以内

**更新后的摘要**：
"""
        else:
            prompt = f"""
请为以下法律咨询对话生成简洁摘要。

**对话历史**：
{history_text}

**要求**：
1. 提取用户咨询的核心法律问题
2. 总结涉及的主要法律条文和要点
3. 保留重要的结论和建议
4. 使用简洁专业的语言
5. 控制在 300 字以内

**摘要**：
"""

        return prompt

    def _simple_summary(
        self,
        history: List[Dict[str, str]],
        existing_summary: str = None
    ) -> str:
        """
        简单摘要（LLM 失败时的回退方案）

        Args:
            history: 对话历史
            existing_summary: 已有摘要

        Returns:
            str: 简化的摘要
        """
        # 提取所有问题
        questions = [turn['question'] for turn in history]

        # 构建简单摘要
        simple_summary = f"用户咨询了 {len(questions)} 个问题："
        for i, q in enumerate(questions[:5], 1):  # 最多显示 5 个
            simple_summary += f"\n{i}. {q[:50]}{'...' if len(q) > 50 else ''}"

        if len(questions) > 5:
            simple_summary += f"\n... 还有 {len(questions) - 5} 个问题"

        # 合并已有摘要
        if existing_summary:
            simple_summary = existing_summary + "\n\n" + simple_summary

        return simple_summary

    def format_context_with_summary(
        self,
        summary: str,
        recent_history: List[Dict[str, str]],
        current_question: str
    ) -> str:
        """
        格式化上下文（摘要 + 最近对话 + 当前问题）

        Args:
            summary: 历史摘要
            recent_history: 最近对话
            current_question: 当前问题

        Returns:
            str: 格式化的上下文
        """
        context_parts = []

        # 1. 历史摘要
        if summary:
            context_parts.append("【对话摘要】")
            context_parts.append(summary)
            context_parts.append("")

        # 2. 最近对话
        if recent_history:
            context_parts.append("【最近对话】")
            for i, turn in enumerate(recent_history, 1):
                context_parts.append(f"Q{i}: {turn['question']}")
                # 答案摘要（避免过长）
                answer_preview = turn['answer'][:150] + "..." if len(turn['answer']) > 150 else turn['answer']
                context_parts.append(f"A{i}: {answer_preview}")
                context_parts.append("")

        # 3. 当前问题
        context_parts.append("【当前问题】")
        context_parts.append(current_question)

        return "\n".join(context_parts)


# 测试代码
if __name__ == "__main__":
    print("=" * 80)
    print("对话历史摘要管理器测试")
    print("=" * 80)

    # 创建测试历史
    test_history = [
        {
            "question": "民法典第509条是什么？",
            "answer": "第五百零九条 当事人应当按照约定全面履行自己的义务。当事人应当遵循诚信原则，根据合同的性质、目的和交易习惯履行通知、协助、保密等义务。"
        },
        {
            "question": "合同违约怎么处理？",
            "answer": "根据民法典第五百七十七条，当事人一方不履行合同义务或者履行合同义务不符合约定的，应当承担继续履行、采取补救措施或者赔偿损失等违约责任。"
        },
        {
            "question": "违约金有上限吗？",
            "answer": "根据民法典第五百八十五条，约定的违约金低于造成的损失的，人民法院或者仲裁机构可以根据当事人的请求予以增加；约定的违约金过分高于造成的损失的，人民法院或者仲裁机构可以根据当事人的请求予以适当减少。"
        },
        {
            "question": "劳动合同试用期最长多久？",
            "answer": "根据劳动合同法第十九条，劳动合同期限三个月以上不满一年的，试用期不得超过一个月；劳动合同期限一年以上不满三年的，试用期不得超过二个月；三年以上固定期限和无固定期限的劳动合同，试用期不得超过六个月。"
        },
        {
            "question": "试用期可以随意解除吗？",
            "answer": "不可以。根据劳动合同法第二十一条，在试用期中，除劳动者有本法第三十九条和第四十条第一项、第二项规定的情形外，用人单位不得解除劳动合同。"
        },
    ]

    manager = ConversationSummaryManager(keep_recent_turns=2)

    print("\n测试场景：5 轮对话，保留最近 2 轮")
    print(f"历史对话数量：{len(test_history)}")

    # 注意：这里会实际调用 LLM API，测试时请确保有可用额度
    print("\n正在生成摘要...")
    print("（提示：此测试会调用 LLM API）")

    # 如果不想调用 API，可以测试简单摘要
    simple_summary = manager._simple_summary(test_history[:3])
    print("\n简单摘要（回退方案）：")
    print(simple_summary)

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
