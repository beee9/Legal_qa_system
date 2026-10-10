"""
AI-Native 智能体工作流 - 法律问答 Agent 系统
基于 LangGraph 实现多步推理、工具调用、自我反思
"""
from typing import TypedDict, Annotated, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base import logger, Config
from mysql_qa import BM25Search, MySQLClient, RedisClient


# 定义 Agent 状态
class AgentState(TypedDict):
    query: str  # 用户原始问题
    intent: str  # 意图分类结果
    missing_info: List[str]  # 缺失的关键信息
    clarified_facts: dict  # 用户补充的事实
    need_clarify: bool  # 是否需要追问
    retrieved_docs: List[dict]  # 检索到的法条
    tools_called: List[dict]  # 工具调用记录
    draft_answer: str  # 草稿答案
    validation_issues: List[str]  # 审查发现的问题
    final_answer: str  # 最终答案
    messages: List  # 对话历史
    retry_count: int  # 审查重试次数


class LegalAgentSystem:
    """法律智能体系统"""
    
    def __init__(self):
        self.logger = logger
        self.config = Config()
        self.bm25_search = BM25Search(RedisClient(), MySQLClient())
        
        # 构建工作流图
        self.workflow = self._build_workflow()
    
    def _build_workflow(self):
        """构建智能体工作流图"""
        workflow = StateGraph(AgentState)
        
        # 添加节点
        workflow.add_node("intent_classifier", self.classify_intent)
        workflow.add_node("fact_clarifier", self.clarify_facts)
        workflow.add_node("retriever", self.retrieve_documents)
        workflow.add_node("tool_caller", self.call_tools)
        workflow.add_node("answer_generator", self.generate_answer)
        workflow.add_node("critic", self.validate_answer)
        
        # 定义流转边
        workflow.set_entry_point("intent_classifier")

        # 条件边：检查是否是对话结束
        workflow.add_conditional_edges(
            "intent_classifier",
            lambda state: END if state["intent"] == "对话结束" else "fact_clarifier"
        )

        # 条件边：是否需要追问
        workflow.add_conditional_edges(
            "fact_clarifier",
            lambda state: END if state["need_clarify"] else "retriever"
        )
        
        workflow.add_edge("retriever", "tool_caller")
        workflow.add_edge("tool_caller", "answer_generator")
        workflow.add_edge("answer_generator", "critic")
        
        # 条件边：审查是否通过
        workflow.add_conditional_edges(
            "critic",
            lambda state: "answer_generator" if state["validation_issues"] else END
        )
        
        return workflow.compile()
    
    def classify_intent(self, state: AgentState) -> AgentState:
        """意图分类节点"""
        query = state["query"]

        # 检查是否是礼貌性回复/对话结束
        polite_endings = [
            r"^(好的|好|OK|ok|明白了|知道了|了解了|清楚了)$",
            r"^(谢谢|感谢|多谢).*",
            r"^(没.*问题|不用了|不需要了|就这样吧).*",
            r"(算了|不想.*问|不问了|别.*问|取消|放弃)"  # 中途放弃
        ]
        for pattern in polite_endings:
            if re.search(pattern, query.strip(), re.IGNORECASE):
                intent = "对话结束"
                self.logger.info(f"意图分类结果: {intent}")
                state["intent"] = intent
                # 直接设置最终答案，跳过后续流程
                state["final_answer"] = "好的，如有其他法律问题，欢迎随时咨询！"
                state["need_clarify"] = False
                return state

        # 简单规则判断（实际可用 BERT 分类器）
        if re.search(r"第\s*\d+\s*条", query):
            intent = "法条查询"
        elif any(kw in query for kw in ["怎么办", "如何", "流程"]):
            intent = "法律咨询"
        else:
            intent = "通用问题"

        self.logger.info(f"意图分类结果: {intent}")
        state["intent"] = intent
        return state
    
    def clarify_facts(self, state: AgentState) -> AgentState:
        """事实澄清节点 - 识别缺失信息"""
        query = state["query"]
        intent = state["intent"]
        clarified = state.get("clarified_facts", {})

        missing_info = []

        # 检测是否是多问题咨询
        detected_topics = self._detect_multiple_topics(query)

        if len(detected_topics) > 1:
            # 多问题场景，引导用户选择优先问题
            self.logger.info(f"检测到 {len(detected_topics)} 个法律问题")

            topic_desc = {
                "divorce": "离婚财产分割",
                "lease": "房屋租赁纠纷",
                "labor": "劳动争议",
                "traffic": "交通事故赔偿",
                "contract": "合同纠纷",
                "inheritance": "继承纠纷"
            }

            clarification_text = "您好，我理解您遇到了多个法律问题，包括：\n\n"
            for i, topic in enumerate(detected_topics, 1):
                clarification_text += f"{i}. {topic_desc.get(topic, topic)}\n"

            clarification_text += "\n为了给您更专业、详细的建议，建议我们逐一解答。请问您最紧急、最想先了解的是哪个问题？（请回复数字序号或问题类型）"

            state["missing_info"] = [clarification_text]
            state["need_clarify"] = True
            state["clarified_facts"]["multiple_topics"] = detected_topics

            self.logger.info(f"引导用户选择优先问题")
            return state

        # 单一问题场景 - 原有逻辑
        # 劳动纠纷场景的关键信息检查
        # 判断条件：当前query提到劳动相关 OR 已有劳动相关的clarified信息
        is_labor_case = ("工资" in query or "劳动" in query or "试用期" in query or "社保" in query or
                        "labor_contract" in clarified or "amount" in clarified)

        if is_labor_case:
            # 先从当前query中提取信息（这样可以避免重复追问用户已经说过的信息）
            if re.search(r"签订了|签了|已签|有签|有合同|肯定.*签|当然.*签", query) and "labor_contract" not in clarified:
                clarified["labor_contract"] = "已签订"
            elif re.search(r"没\s*有?\s*签|未\s*签|无\s*合同", query) and "labor_contract" not in clarified:
                clarified["labor_contract"] = "未签订"

            if re.search(r"(\d+\.?\d*)\s*[wW万]\s*\d*|(\d+)\s*元|[一二三四五六七八九十百千]+\s*[万千百]", query) and "amount" not in clarified:
                clarified["amount"] = query

            location_match = re.search(r"(广东|深圳|北京|上海|杭州|成都|重庆|天津|南京|武汉|西安|苏州|长沙|郑州|青岛|大连|厦门|宁波|广州|东莞|佛山)", query)
            if location_match and "location" not in clarified:
                clarified["location"] = location_match.group(0)

            if re.search(r"有.*证据|工资条|转账|打卡|当然有|肯定有|都有|有的", query) and "evidence" not in clarified:
                clarified["evidence"] = "有证据"

            # 然后检查还缺少哪些信息
            if "labor_contract" not in clarified:
                missing_info.append("是否签订书面劳动合同？")
            if "amount" not in clarified:
                missing_info.append("拖欠金额是多少？拖欠多长时间？")
            if "location" not in clarified:
                missing_info.append("公司注册地或工作地在哪个省市？")
            if "evidence" not in clarified:
                missing_info.append("是否有工资条、转账记录、打卡记录等证据？")

        # 合同纠纷场景
        elif "合同" in query and intent == "法律咨询":
            if "违约" in query and "金" not in query:
                missing_info.append("合同中是否约定了违约金条款？")
            if not re.search(r"签订|签字|盖章", query):
                missing_info.append("合同是否已签订生效？")

        state["missing_info"] = missing_info
        state["need_clarify"] = len(missing_info) > 0
        state["clarified_facts"] = clarified  # 保存提取的信息

        if missing_info:
            self.logger.info(f"识别到 {len(missing_info)} 个缺失信息，需要追问")

        return state
    
    def retrieve_documents(self, state: AgentState) -> AgentState:
        """检索法条节点"""
        query = state["query"]
        
        # 先尝试 BM25 精确检索
        answer, need_rag = self.bm25_search.search(query, threshold=6.0)
        
        if answer:
            self.logger.info("BM25 命中精确答案")
            state["retrieved_docs"] = [{"source": "BM25", "content": answer}]
        else:
            self.logger.info("BM25 未命中，需要 RAG 检索")
            # 这里应该调用 vector_store.search()，简化为示例
            state["retrieved_docs"] = [{"source": "RAG", "content": "向量检索结果..."}]
        
        return state
    
    def call_tools(self, state: AgentState) -> AgentState:
        """工具调用节点"""
        query = state["query"]
        tools_called = []
        
        # 工具1：金额计算
        if "双倍工资" in query or "经济补偿" in query:
            # 假设用户补充了：未签合同11个月，月薪8000
            amount = self._calculate_double_salary(months=11, monthly_salary=8000)
            tools_called.append({
                "tool": "calculate_double_salary",
                "result": f"双倍工资差额：{amount}元"
            })
        
        # 工具2：法条查询
        if re.search(r"第\s*(\d+)\s*条", query):
            article_no = re.search(r"第\s*(\d+)\s*条", query).group(1)
            result = self._query_article(article_no)
            tools_called.append({
                "tool": "query_article",
                "result": result
            })
        
        # 工具3：时效性检查
        validation_result = self._check_law_validity(state["retrieved_docs"])
        tools_called.append({
            "tool": "check_law_validity",
            "result": validation_result
        })
        
        state["tools_called"] = tools_called
        self.logger.info(f"调用了 {len(tools_called)} 个工具")
        
        return state
    
    def generate_answer(self, state: AgentState) -> AgentState:
        """答案生成节点"""
        query = state["query"]
        docs = state["retrieved_docs"]
        tools = state["tools_called"]
        clarified = state.get("clarified_facts", {})

        # 根据用户补充的事实，生成针对性答案
        if clarified.get("labor_contract") == "已签订":
            # 已签订合同，关注点是拖欠工资
            # 提取具体信息
            amount_info = clarified.get("amount", "")
            location = clarified.get("location", "工作地")
            evidence = clarified.get("evidence", "")

            # 解析金额
            amount_text = ""
            # 先尝试匹配"1万5"这种格式（X万Y千）
            wan_qian_match = re.search(r"(\d+)\s*[wW万]\s*(\d+)", amount_info)
            if wan_qian_match:
                wan = int(wan_qian_match.group(1))
                qian = int(wan_qian_match.group(2))
                # "1万5" = 1.5万，"2万3" = 2.3万
                amount_value = wan + qian / 10.0
                amount_text = f"约{amount_value}万元"
                compensation_min = amount_value * 0.5
                compensation_text = f"您可主张拖欠工资{amount_text}，以及{compensation_min:.1f}万-{amount_value}万元的赔偿金（按应付金额50%-100%计算）。"
            else:
                # 尝试匹配标准格式"1.5万"或"1万"
                amount_match = re.search(r"(\d+\.?\d*)\s*[wW万]", amount_info)
                if amount_match:
                    amount_value = float(amount_match.group(1))
                    amount_text = f"约{amount_value}万元"
                    compensation_min = amount_value * 0.5
                    compensation_text = f"您可主张拖欠工资{amount_text}，以及{compensation_min:.1f}万-{amount_value}万元的赔偿金（按应付金额50%-100%计算）。"
                else:
                    # 尝试匹配中文数字
                    cn_match = re.search(r"([一二三四五六七八九十百千]+)\s*[万千百]", amount_info)
                    if cn_match:
                        # 简化处理：常见口语表达
                        cn_map = {"一万": 1.0, "二万": 2.0, "三万": 3.0, "五千": 0.5, "八千": 0.8}
                        cn_text = cn_match.group(0).replace(" ", "")
                        for key, value in cn_map.items():
                            if key in cn_text:
                                amount_value = value
                                amount_text = f"约{amount_value}万元" if amount_value >= 1 else f"约{amount_value * 10}千元"
                                compensation_min = amount_value * 0.5
                                compensation_text = f"您可主张拖欠工资{amount_text}，以及{compensation_min:.1f}万-{amount_value}万元的赔偿金（按应付金额50%-100%计算）。"
                                break

            if not amount_text:
                compensation_text = "您可主张拖欠工资及相应的赔偿金。"

            # 解析拖欠时长
            time_text = ""
            time_match = re.search(r"(\d+)\s*个?月", amount_info)
            if time_match:
                months = int(time_match.group(1))
                time_text = f"拖欠{months}个月工资，"

            draft_answer = f"""根据《中华人民共和国劳动合同法》第三十条规定，用人单位应当按照劳动合同约定和国家规定，向劳动者及时足额支付劳动报酬。用人单位拖欠或者未足额支付劳动报酬的，劳动者可以依法向当地人民法院申请支付令，人民法院应当依法发出支付令。

根据《劳动合同法》第八十五条，用人单位未按照劳动合同的约定或者国家规定及时足额支付劳动者劳动报酬的，由劳动行政部门责令限期支付劳动报酬；逾期不支付的，责令用人单位按应付金额百分之五十以上百分之一百以下的标准向劳动者加付赔偿金。

**您的情况分析**：
- 已签订书面劳动合同：✓
- {time_text}金额{amount_text if amount_text else "需明确"}
- 工作地点：{location}
- 证据情况：{"已有工资条、转账记录等证据" if evidence else "建议收集相关证据"}

**可主张权益**：
{compensation_text}

**维权步骤建议**：
1. 整理证据材料：劳动合同、工资条、银行转账记录、考勤打卡记录、工作微信/邮件等；
2. 优先途径：向{location}劳动监察大队投诉（12333热线），要求责令公司支付并加付赔偿金；
3. 备选途径：直接向{location}劳动人事争议仲裁委员会申请劳动仲裁（仲裁时效为1年）；
4. 紧急情况：可向人民法院申请支付令（适用于事实清楚、证据充分的欠薪案件）；
5. 如公司恶意逃避：可向公安机关报案（涉嫌拒不支付劳动报酬罪）。

**{location}具体联系方式**：
- 劳动监察：12333（全国统一热线）或{location}各区劳动监察大队
- 劳动仲裁：{location}各区劳动人事争议仲裁院（需到现场立案）"""

        elif clarified.get("labor_contract") == "未签订":
            # 未签订合同，可主张双倍工资+拖欠工资
            # 提取具体信息
            amount_info = clarified.get("amount", "")
            location = clarified.get("location", "工作地")
            evidence = clarified.get("evidence", "")

            # 解析金额
            amount_text = ""
            amount_match = re.search(r"(\d+\.?\d*)\s*[wW万]", amount_info)
            if amount_match:
                amount_value = float(amount_match.group(1))
                amount_text = f"约{amount_value}万元"

            draft_answer = f"""根据《中华人民共和国劳动合同法》第十条、第八十二条规定：

1. 建立劳动关系，应当订立书面劳动合同；用人单位自用工之日起超过一个月不满一年未与劳动者订立书面劳动合同的，应当向劳动者每月支付二倍的工资。

2. 根据《劳动合同法》第三十条、第八十五条，用人单位拖欠工资的，劳动者可以申请支付令或申请劳动仲裁，逾期不支付的，责令用人单位加付赔偿金。

**您的情况分析**：
- 劳动合同状态：未签订 ⚠️
- 拖欠金额：{amount_text if amount_text else "需明确"}
- 工作地点：{location}
- 证据情况：{"已有转账记录等证据" if evidence else "建议收集相关证据"}

**可主张权益**：
1. 未签订书面劳动合同的**双倍工资差额**（自用工满1个月至满1年期间，最多11个月）；
2. 被拖欠的工资{amount_text if amount_text else ""}；
3. 经济补偿金（如被违法解除劳动关系）。

**维权步骤建议**：
1. 收集能证明劳动关系的证据：工资转账记录、考勤打卡记录、工作证、工作服、同事证言、工作微信/邮件往来等；
2. 优先途径：向{location}劳动监察大队投诉（12333热线）；
3. 备选途径：直接向{location}劳动人事争议仲裁委员会申请劳动仲裁（仲裁时效为1年，双倍工资时效为离职后1年内）；
4. 在仲裁申请中明确主张：拖欠工资 + 双倍工资差额 + 经济补偿金；
5. 如公司恶意逃避：可向公安机关报案（涉嫌拒不支付劳动报酬罪）。

**{location}具体联系方式**：
- 劳动监察：12333（全国统一热线）或各区劳动监察大队
- 劳动仲裁：各区劳动人事争议仲裁院（需到现场立案，携带身份证、证据材料）"""

        else:
            # 没有补充信息，生成通用答案
            draft_answer = f"""针对您的问题"{query}"，建议：

1. 保留好劳动关系和工资支付的相关证据；
2. 向当地劳动监察大队投诉；
3. 或申请劳动争议仲裁，主张相关权益。

如需进一步协助，请补充具体情况。"""

        state["draft_answer"] = draft_answer
        return state
    
    def validate_answer(self, state: AgentState) -> AgentState:
        """答案审查节点（Critic）"""
        draft = state["draft_answer"]
        retry_count = state.get("retry_count", 0)
        issues = []

        # 检查1：是否包含法条引用
        if not re.search(r"第\s*\d+\s*条", draft):
            issues.append("缺少具体法条引用")

        # 检查2：是否包含免责声明（如果缺少，直接添加而不重试）
        if "仅供参考" not in draft and "不构成法律意见" not in draft:
            self.logger.info("自动添加免责声明")
            draft += "\n\n本回答仅为法律信息参考，不构成法律意见；涉及具体纠纷请咨询执业律师。"
            state["draft_answer"] = draft

        # 检查3：是否存在常见错误引用
        if "《合同法》" in draft:
            issues.append("引用了已废止的《合同法》，应引用《民法典》合同编")

        state["validation_issues"] = issues
        state["retry_count"] = retry_count + 1

        # 如果没有问题，或者重试次数过多，直接通过
        if not issues or retry_count >= 2:
            state["final_answer"] = draft
            if retry_count >= 2:
                self.logger.warning(f"答案审查重试 {retry_count} 次后强制通过")
            else:
                self.logger.info("答案审查通过")
            state["validation_issues"] = []  # 清空问题，避免重试
        else:
            self.logger.warning(f"答案审查发现 {len(issues)} 个问题: {issues}，重试第 {retry_count + 1} 次")
        
        return state

    # ========== 工具函数 ==========

    def _detect_multiple_topics(self, query: str) -> List[str]:
        """检测查询中包含的多个法律主题"""
        topics = []

        # 离婚财产分割
        if any(kw in query for kw in ["离婚", "前夫", "前妻", "夫妻共同财产", "财产分割", "协议离婚"]):
            topics.append("divorce")

        # 房屋租赁
        if any(kw in query for kw in ["租赁", "租客", "房东", "出租", "漏水", "租期"]):
            topics.append("lease")

        # 劳动争议
        if any(kw in query for kw in ["劳动", "工资", "社保", "试用期", "劳动合同", "仲裁", "降薪", "辞退"]):
            topics.append("labor")

        # 交通事故
        if any(kw in query for kw in ["追尾", "交通事故", "车辆", "保险", "理赔", "贬值费", "误工费"]):
            topics.append("traffic")

        # 合同纠纷
        if any(kw in query for kw in ["合同", "违约", "违约金", "解除合同"]) and "劳动合同" not in query:
            topics.append("contract")

        # 继承纠纷
        if any(kw in query for kw in ["继承", "遗产", "遗嘱", "遗赠"]):
            topics.append("inheritance")

        return topics

    def _is_answering_clarification(self, query: str) -> bool:
        """检测用户是否在回答追问（通过关键词和格式判断）"""
        # 包含追问关键词
        clarification_keywords = [
            "签订书面劳动合同", "拖欠金额", "拖欠多长时间",
            "注册地或工作地", "工资条", "转账记录", "打卡记录"
        ]

        # 如果包含追问关键词+问号，说明用户在回答
        for keyword in clarification_keywords:
            if keyword in query and "？" in query:
                return True

        # 如果包含明确的回答格式（关键词后跟答案）
        if re.search(r"(签订了|没签|未签|已签|有签|无合同)", query):
            return True
        if re.search(r"\d+\s*[wW万元].*[年月天]", query):
            return True
        if re.search(r"(广东|深圳|北京|上海|省|市)", query):
            return True
        if re.search(r"(有的|都有|有证据|有工资条|有转账)", query):
            return True

        return False

    def _calculate_double_salary(self, months: int, monthly_salary: float) -> float:
        """计算双倍工资差额"""
        return months * monthly_salary
    
    def _query_article(self, article_no: str) -> str:
        """查询具体法条内容"""
        # 实际应查询 law_articles 表
        return f"第{article_no}条的内容..."
    
    def _check_law_validity(self, docs: List[dict]) -> str:
        """检查法律时效性"""
        # 实际应查询 law_articles 表的 status 字段
        return "所有引用法条均为现行有效"
    
    def run(self, query: str, previous_state: dict = None) -> dict:
        """运行 Agent 工作流

        Args:
            query: 用户当前问题
            previous_state: 上一轮的状态（用于多轮对话）
        """
        # 检查用户是否在回答追问（即使没有 previous_state）
        is_answering = self._is_answering_clarification(query)

        if previous_state and (is_answering or previous_state.get("need_clarify")):
            # 继续之前的对话，更新 query
            self.logger.info(f"🔄 继续对话，加载上一轮状态")
            initial_state = previous_state.copy()
            initial_state["query"] = query

            # 解析用户回答，更新 clarified_facts
            clarified = initial_state.get("clarified_facts", {})
            missing = initial_state.get("missing_info", [])

            self.logger.info(f"📋 上一轮缺失信息: {missing}")
            self.logger.info(f"📝 用户回答: {query}")

            # 根据之前的缺失信息，解析用户回答
            if missing or is_answering:
                # 先检查用户是否在选择多问题中的某个主题
                multiple_topics = clarified.get("multiple_topics", [])
                if multiple_topics:
                    self.logger.info(f"🔍 检测到之前有多问题: {multiple_topics}")
                    # 检查用户选择了哪个主题（数字序号或关键词）
                    selected_topic = None
                    if re.search(r"[3三]|劳动|工资|拖欠|劳动争议", query):
                        selected_topic = "labor"
                    elif re.search(r"[1一]|离婚|财产|分割", query):
                        selected_topic = "divorce"
                    elif re.search(r"[2二]|租|租赁|房屋|房东", query):
                        selected_topic = "lease"
                    elif re.search(r"[4四]|交通|事故|赔偿", query):
                        selected_topic = "traffic"

                    if selected_topic:
                        self.logger.info(f"✅ 用户选择了主题: {selected_topic}")
                        clarified["selected_topic"] = selected_topic
                        # 清空 multiple_topics，表示已经选择完成
                        clarified.pop("multiple_topics", None)
                        # 清空之前从多问题中提取的可能混乱的信息
                        # 只保留与当前主题相关的字段
                        clarified.pop("amount", None)
                        clarified.pop("location", None)
                        clarified.pop("evidence", None)
                        clarified.pop("labor_contract", None)
                        self.logger.info(f"🧹 清空之前的混杂信息，重新收集")
                        # 重新构建聚焦的query
                        topic_keywords = {
                            "labor": "劳动争议",
                            "divorce": "离婚财产分割",
                            "lease": "房屋租赁纠纷",
                            "traffic": "交通事故赔偿"
                        }
                        initial_state["query"] = f"{topic_keywords.get(selected_topic, '')} {query}"
                        self.logger.info(f"🔄 重构query: {initial_state['query']}")

                # 检查劳动合同（支持多种回答格式）
                # 重要：否定判断必须优先于肯定判断，避免"没有签"被"有签"误匹配
                # 格式1: "没有签合同"、"未签订"、"没签"
                if re.search(r"没\s*有?\s*签|未\s*签|无\s*合同|没\s*签", query):
                    clarified["labor_contract"] = "未签订"
                    self.logger.info(f"✅ 识别: 未签订劳动合同")
                # 格式2: "是否签订？是"、"签订了"、"有合同"
                elif re.search(r"合同[？?]\s*是|签订[？?]\s*是|^是[，,、；]|，是[，,、；]", query) or \
                     re.search(r"签订了|签了|已签|(?<!没)有\s*签|(?<!无)合同", query):
                    clarified["labor_contract"] = "已签订"
                    self.logger.info(f"✅ 识别: 已签订劳动合同")

                # 检查拖欠金额和时间
                amount_match = re.search(r"(\d+\.?\d*)\s*[wW万]|(\d+)\s*元", query)
                time_match = re.search(r"(\d+)\s*年|(\d+)\s*个?月|(\d+)\s*天", query)
                if amount_match or time_match:
                    clarified["amount"] = query
                    self.logger.info(f"✅ 识别: 金额和时间")

                # 检查地区（限定常见城市名，避免误匹配）
                location_match = re.search(r"(广东|深圳|北京|上海|杭州|成都|重庆|天津|南京|武汉|西安|苏州|长沙|郑州|青岛|大连|厦门|宁波|广州|东莞|佛山|珠海|中山|江门|惠州|肇庆|韶关|湛江|茂名|汕头|潮州|揭阳|梅州|河源|清远|阳江|云浮|汕尾|[一-龥]{2,}省)", query)
                if location_match:
                    clarified["location"] = location_match.group(0)
                    self.logger.info(f"✅ 识别: 地区 - {location_match.group(0)}")

                # 检查证据
                if re.search(r"有的|都有|有证据|有工资条|有转账|有打卡", query):
                    clarified["evidence"] = "有证据"
                    self.logger.info(f"✅ 识别: 有证据")

            initial_state["clarified_facts"] = clarified
            # 清空 need_clarify，让工作流重新判断
            initial_state["need_clarify"] = False

            self.logger.info(f"📦 更新后的 clarified_facts: {clarified}")
        else:
            # 新对话，创建初始状态
            initial_state = {
                "query": query,
                "intent": "",
                "missing_info": [],
                "clarified_facts": {},
                "need_clarify": False,
                "retrieved_docs": [],
                "tools_called": [],
                "draft_answer": "",
                "validation_issues": [],
                "final_answer": "",
                "messages": [],
                "retry_count": 0
            }

        result = self.workflow.invoke(initial_state)
        return result


if __name__ == "__main__":
    agent = LegalAgentSystem()
    
    # 测试用例
    test_queries = [
        "老板拖欠我两个月工资，我该怎么办？",
        "民法典第509条是什么？",
        "合同违约需要承担什么责任？"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"用户问题：{query}")
        print(f"{'='*60}")
        
        result = agent.run(query)
        
        print(f"\n意图分类：{result['intent']}")
        if result['missing_info']:
            print(f"需要追问：{result['missing_info']}")
        print(f"\n工具调用：{len(result['tools_called'])} 个")
        for tool in result['tools_called']:
            print(f"  - {tool['tool']}: {tool['result']}")
        print(f"\n最终答案：\n{result.get('final_answer', result['draft_answer'])}")
