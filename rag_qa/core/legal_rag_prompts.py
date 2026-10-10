"""
法律领域专用 Prompt 模板

包含各种检索策略所需的 Prompt：
- 子查询分解
- HyDE 假设答案生成
- 回溯问题简化
- RAG 答案生成
"""

from langchain_core.prompts import PromptTemplate


class LegalRAGPrompts:
    """法律 RAG Prompt 模板集合"""

    @staticmethod
    def rag_prompt():
        """RAG 答案生成 Prompt"""
        return PromptTemplate(
            template="""
你是一个专业的法律助手，负责根据检索到的法律文档回答用户的法律问题。

**指导原则**：
1. 如果上下文中包含相关法律条文，请基于法条准确回答
2. 引用具体的法律条文时，请注明法律名称和条文编号
3. 如果上下文不足以回答问题，请明确告知用户
4. 回答要专业、严谨，但语言要通俗易懂
5. 对于复杂的法律问题，建议咨询专业律师

**检索到的法律文档**：
{context}

**用户问题**：
{question}

**回答要求**：
- 如果找到相关法条，请完整引用并解释
- 如果没有找到相关信息，回复："根据检索到的法律文档，暂未找到直接相关的规定。建议您咨询专业律师获取更准确的法律意见。"
- 不要编造法律条文或提供不确定的信息

**回答**：
            """,
            input_variables=["context", "question"]
        )

    @staticmethod
    def subquery_prompt():
        """子查询分解 Prompt"""
        return PromptTemplate(
            template="""
将以下复杂的法律查询分解为多个简单的子查询，每个子查询应该是一个独立的法律问题。

**原始查询**：
{query}

**要求**：
1. 识别查询中的所有独立法律问题
2. 每个子查询应该清晰、简洁
3. 保留原查询的核心意图
4. 每行一个子查询，不要编号

**子查询**：
            """,
            input_variables=["query"]
        )

    @staticmethod
    def hyde_prompt():
        """HyDE 假设答案生成 Prompt"""
        return PromptTemplate(
            template="""
针对以下法律问题，生成一个假设性的、详细的答案。这个假设答案将用于语义检索，帮助找到相关的法律文档。

**问题**：
{query}

**要求**：
1. 假设你知道答案，生成一个详细、专业的法律解答
2. 包含可能相关的法律条文、法律概念、关键术语
3. 使用法律专业语言
4. 长度控制在 200-300 字
5. 不要说"假设"、"可能"等不确定词汇，直接生成答案

**假设答案**：
            """,
            input_variables=["query"]
        )

    @staticmethod
    def backtracking_prompt():
        """回溯问题简化 Prompt"""
        return PromptTemplate(
            template="""
将以下口语化或冗长的法律查询，简化为一个清晰、简洁的核心问题。

**原始查询**：
{query}

**要求**：
1. 提取核心法律问题
2. 去除无关的背景描述和口语化表达
3. 保留关键的法律要素（如时间、金额、关系等）
4. 使用专业的法律术语
5. 一句话表达，不超过 30 字

**简化问题**：
            """,
            input_variables=["query"]
        )

    @staticmethod
    def direct_retrieval_prompt():
        """直接检索的查询优化 Prompt（可选）"""
        return PromptTemplate(
            template="""
将以下法律查询转换为更适合检索的形式，提取关键法律术语和要素。

**原始查询**：
{query}

**要求**：
1. 保留法律名称和条文编号（如果有）
2. 提取核心法律概念和关键词
3. 保持简洁，不超过 50 字

**优化后的查询**：
            """,
            input_variables=["query"]
        )

    @staticmethod
    def strategy_selection_prompt():
        """检索策略选择 Prompt（从 retrieval_strategy_selector 移过来，统一管理）"""
        return PromptTemplate(
            template="""
你是一个法律问答系统的检索策略选择器。根据用户查询的特点，选择最合适的检索策略。

可选策略：

1. **直接检索**
   - 适用场景：单一、明确的法律问题
   - 示例："民法典第509条的内容是什么？"
   - 示例："劳动合同试用期最长多久？"
   - 特点：问题清晰，可以直接检索

2. **子查询检索**
   - 适用场景：包含多个独立子问题的复杂查询
   - 示例："民法典关于合同违约的规定，以及劳动法关于工资支付的规定，分别是什么？"
   - 示例："公司注册需要什么材料？注销又需要什么流程？"
   - 特点：包含"和"、"以及"、"还有"等连接词，涉及多个独立话题

3. **假设问题检索 (HyDE)**
   - 适用场景：概念性问题、假设性问题、开放性问题
   - 示例："什么是侵权责任？"
   - 示例："如何理解不可抗力？"
   - 示例："股权转让有哪些注意事项？"
   - 特点：询问概念、原理、方法，需要先生成假设答案再检索

4. **回溯问题检索**
   - 适用场景：口语化、冗长、包含无关信息的查询
   - 示例："我想问一下，就是那个，公司把我辞退了，但是没给我赔偿，这种情况下我应该怎么办？"
   - 示例："昨天我和老板吵架了，他说要扣我工资，请问这样合法吗？"
   - 特点：包含大量口语化表达、背景叙述，需要提炼核心问题

当前用户查询：{query}

请根据查询特点，直接返回最适合的策略名称（只返回策略名称，不要任何解释）：
- "直接检索"
- "子查询检索"
- "假设问题检索"
- "回溯问题检索"
            """,
            input_variables=["query"]
        )


# 测试代码
if __name__ == "__main__":
    # 测试各种 Prompt
    prompts = LegalRAGPrompts()

    print("=" * 80)
    print("RAG Prompt 模板测试")
    print("=" * 80)

    # 1. RAG 生成 Prompt
    print("\n1. RAG 答案生成 Prompt:")
    rag_prompt = prompts.rag_prompt()
    print(rag_prompt.format(
        context="民法典第509条：当事人应当按照约定全面履行自己的义务...",
        question="民法典第509条是什么？"
    )[:200])

    # 2. 子查询分解
    print("\n2. 子查询分解 Prompt:")
    subquery_prompt = prompts.subquery_prompt()
    print(subquery_prompt.format(
        query="民法典关于合同违约的规定，以及劳动法关于工资支付的规定"
    )[:200])

    # 3. HyDE
    print("\n3. HyDE 假设答案生成 Prompt:")
    hyde_prompt = prompts.hyde_prompt()
    print(hyde_prompt.format(query="什么是侵权责任？")[:200])

    # 4. 回溯问题
    print("\n4. 回溯问题简化 Prompt:")
    backtrack_prompt = prompts.backtracking_prompt()
    print(backtrack_prompt.format(
        query="我想问一下，就是那个，公司把我辞退了但没给赔偿"
    )[:200])

    print("\n" + "=" * 80)
    print("Prompt 模板测试完成")
    print("=" * 80)
