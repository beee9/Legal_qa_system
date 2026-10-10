"""
检索策略选择器 - Phase 2 优化

根据查询复杂度，自动选择最优检索策略：
1. 直接检索 - 单一明确的法律问题
2. 子查询检索 - 包含多个子问题的复杂查询
3. HyDE 检索 - 假设性问题或概念查询
4. 回溯检索 - 口语化或冗长的查询
"""

from langchain_core.prompts import PromptTemplate
from base import logger, Config
from openai import OpenAI


class RetrievalStrategySelector:
    """检索策略选择器"""

    def __init__(self):
        self.config = Config()
        # 初始化 OpenAI 客户端（DashScope）
        self.client = OpenAI(
            api_key=self.config.DASHSCOPE_API_KEY,
            base_url=self.config.DASHSCOPE_BASE_URL
        )
        # 获取策略选择提示模板
        self.strategy_prompt = self._get_strategy_prompt()

    def _call_llm(self, prompt):
        """调用 DashScope LLM"""
        try:
            completion = self.client.chat.completions.create(
                model=self.config.LLM_MODEL,
                messages=[
                    {"role": "system", "content": "你是一个专业的法律助手。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # 低温度保证稳定输出
                max_tokens=500
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"调用 LLM 失败: {e}")
            return "直接检索"  # 默认策略

    def _get_strategy_prompt(self):
        """获取策略选择的 Prompt 模板"""
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

    def select_strategy(self, query):
        """
        选择检索策略

        Args:
            query: 用户查询

        Returns:
            str: 策略名称
        """
        try:
            # 调用 LLM 获取策略
            strategy = self._call_llm(self.strategy_prompt.format(query=query))

            # 标准化策略名称
            strategy = strategy.strip().replace('"', '').replace("'", '')

            # 验证策略有效性
            valid_strategies = ["直接检索", "子查询检索", "假设问题检索", "回溯问题检索"]
            if strategy not in valid_strategies:
                logger.warning(f"无效的策略 '{strategy}'，使用默认策略")
                strategy = "直接检索"

            logger.info(f"为查询 '{query}' 选择的检索策略：{strategy}")
            return strategy

        except Exception as e:
            logger.error(f"策略选择失败: {e}，使用默认策略")
            return "直接检索"


# 测试代码
if __name__ == "__main__":
    selector = RetrievalStrategySelector()

    # 测试不同类型的查询
    test_queries = [
        "民法典第509条是什么",  # 直接检索
        "民法典关于合同违约的规定，以及劳动法关于工资支付的规定",  # 子查询检索
        "什么是侵权责任",  # HyDE
        "我想问一下，就是那个，公司把我辞退了但没给赔偿，怎么办",  # 回溯检索
    ]

    for query in test_queries:
        strategy = selector.select_strategy(query)
        print(f"\n查询: {query}")
        print(f"策略: {strategy}")
