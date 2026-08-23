#   导入 PromptTemplate 类，用于创建 Prompt 模板
from langchain_core.prompts import PromptTemplate


#   定义 RAGPrompts 类，用于管理所有 Prompt 模板
class RAGPrompts:
    #   定义 RAG 提示模板（法律化）
    @staticmethod
    def rag_prompt():
        return PromptTemplate(
            template="""
        你是一个专业的法律信息问答助手，提供基于中国法律法规的信息服务。
        请严格遵守以下规则：

        1. **只基于提供的上下文回答，不编造法条内容**：回答中引用法条时必须标注法条编号（如"《民法典》第X条"、"根据《劳动合同法》第X条"）。

        2. **检索不足时如实说明**：如果检索到的上下文不足以准确回答问题，明确回复："依据现有知识库无法准确回答，建议咨询执业律师。"不得凭想象编造法条内容。

        3. **免责声明**：本回答仅为法律信息参考，不构成法律意见；涉及具体纠纷请咨询执业律师。

        4. **结合对话历史**：对话历史与当前问题相关时结合历史回答，否则忽略历史。

        **上下文**: {context}
        **对话历史**:
        {history}
        **问题**: {question}

        **回答**:
        """,
            input_variables=["context", "history", "question"],
        )

    #   定义假设问题生成的 Prompt 模板（法律化）
    @staticmethod
    def hyde_prompt():
        return PromptTemplate(
            template="""
            假设你是用户，想咨询以下法律问题，请用专业法律术语生成一个简短的假设答案（可含法条编号）：
            问题: {query}
            假设答案:
            """,
            input_variables=["query"],
        )

    #   定义子查询生成的 Prompt 模板（法律化）
    @staticmethod
    def subquery_prompt():
        return PromptTemplate(
            template="""
            将以下复杂的法律咨询分解为多个简单的法律子问题，每行一个子问题：
            查询: {query}
            子问题:
            """,
            input_variables=["query"],
        )

    #   定义回溯问题生成的 Prompt 模板（法律化）
    @staticmethod
    def backtracking_prompt():
        return PromptTemplate(
            template="""
            将以下复杂的法律咨询简化为一个更基础、更便于检索的法律问题：
            查询: {query}
            简化问题:
            """,
            input_variables=["query"],
        )
