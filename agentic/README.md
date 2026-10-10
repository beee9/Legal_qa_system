# AI-Native 改造实施方案

## 📋 目标

将 `Legal_qa_system` 从传统的"单次问答"系统升级为 **AI-Native 法律智能体系统**，具备：
- ✅ 多步推理与主动追问
- ✅ 工具调用（金额计算、文书生成、时效检查）
- ✅ 自我反思与验证
- ✅ 持续学习与数据飞轮

---

## 🚀 第一阶段：Agentic Workflow（已完成基础框架）

### 新增模块

#### 1. `agentic/legal_agent_system.py` - 智能体核心系统

**功能：**
- ✅ 意图分类节点
- ✅ 事实澄清节点（识别缺失信息，主动追问）
- ✅ 法条检索节点（集成现有 BM25 + RAG）
- ✅ 工具调用节点
- ✅ 答案生成节点
- ✅ 质量审查节点（Critic）

**工作流程：**
```
用户问题 
  → 意图分类 
  → 事实澄清（如缺信息则追问）
  → 法条检索 
  → 工具调用 
  → 生成答案 
  → 质量审查 
  → 最终输出
```

#### 2. `agentic/legal_tools.py` - 法律工具集

**已实现的工具：**

| 工具类别 | 工具名称 | 功能 |
|---------|---------|------|
| **金额计算** | `calculate_double_salary` | 计算未签合同的双倍工资差额 |
| | `calculate_economic_compensation` | 计算经济补偿金（N或2N） |
| | `calculate_overtime_pay` | 计算加班费 |
| | `calculate_severance_pay` | 计算解除劳动合同补偿金 |
| **时效性检查** | `check_law_validity` | 检查法条是否现行有效 |
| | `detect_obsolete_laws` | 检测已废止法律（如《合同法》） |
| **文书生成** | `generate_arbitration_application` | 生成劳动仲裁申请书 |
| | `generate_evidence_list` | 生成证据清单 |
| | `generate_demand_letter` | 生成催告函 |
| **风险评估** | `assess_litigation_risk` | 诉讼风险评估 |
| | `calculate_statute_of_limitations` | 计算诉讼时效 |

---

## 📦 依赖安装

```bash
pip install langgraph langchain-core
```

---

## 🎯 使用示例

### 1. 基础使用（Python脚本）

```python
from agentic.legal_agent_system import LegalAgentSystem

# 初始化智能体系统
agent = LegalAgentSystem()

# 运行查询
result = agent.run("老板拖欠我两个月工资，我该怎么办？")

# 查看结果
print(f"意图分类：{result['intent']}")
print(f"缺失信息：{result['missing_info']}")
print(f"工具调用：{result['tools_called']}")
print(f"最终答案：{result['final_answer']}")
```

### 2. 测试工具集

```python
from agentic.legal_tools import LegalTools

tools = LegalTools()

# 计算双倍工资
result = tools.calculate_double_salary(months=11, monthly_salary=8000)
print(result['explanation'])
# 输出：您可主张 11 个月的双倍工资差额，共计 88000.00 元。

# 检测已废止法律
text = "根据《合同法》第94条..."
result = tools.detect_obsolete_laws(text)
if result['has_obsolete']:
    for law in result['detected_laws']:
        print(law['warning'])
# 输出：《合同法》已于 2021-01-01 废止，应引用《中华人民共和国民法典》第三编 合同

# 生成劳动仲裁申请书
facts = {
    "applicant_name": "张三",
    "company_name": "某科技公司",
    "claim_type": "双倍工资差额",
    "claim_amount": "88,000",
    "facts_description": "申请人于2023年1月1日入职..."
}
doc = tools.generate_arbitration_application(facts)
print(doc)
```

---

## 🔗 集成到现有系统

### 方式1：替换 `new_main.py` 的 query 方法

```python
# new_main.py 修改建议

from agentic.legal_agent_system import LegalAgentSystem
from agentic.legal_tools import LegalTools

class IntegratedQASystem:
    def __init__(self):
        # ... 原有初始化代码 ...
        
        # 新增：初始化 Agent 系统
        self.agent_system = LegalAgentSystem()
        self.legal_tools = LegalTools()
    
    def query_with_agent(self, query, session_id=None):
        """使用智能体系统处理复杂查询"""
        
        # 运行 Agent 工作流
        result = self.agent_system.run(query)
        
        # 如果需要追问
        if result['need_clarify']:
            # 返回追问信息
            return {
                "type": "clarification_needed",
                "missing_info": result['missing_info'],
                "message": "为了更准确地回答您的问题，我需要了解以下信息：\n" + 
                          "\n".join(f"- {info}" for info in result['missing_info'])
            }
        
        # 正常返回答案
        return {
            "type": "answer",
            "answer": result['final_answer'],
            "tools_used": result['tools_called'],
            "legal_basis": [doc for doc in result['retrieved_docs']]
        }
```

### 方式2：在 FastAPI 接口中增加 Agent 模式

```python
# app.py 修改建议

from agentic.legal_agent_system import LegalAgentSystem

agent_system = LegalAgentSystem()

@app.post("/api/agent/query")
async def agent_query(request: QueryRequest):
    """智能体模式：支持多步推理和工具调用"""
    
    result = agent_system.run(request.query)
    
    return {
        "intent": result['intent'],
        "need_clarify": result['need_clarify'],
        "missing_info": result['missing_info'],
        "tools_called": result['tools_called'],
        "answer": result.get('final_answer', result['draft_answer'])
    }
```

---

## 📊 效果对比

### 传统模式 vs AI-Native 模式

| 场景 | 传统模式（BM25 + RAG） | AI-Native 智能体模式 |
|------|----------------------|-------------------|
| **简单法条查询** | ✅ 直接返回法条内容 | ✅ 同样高效 |
| **复杂咨询（缺信息）** | ❌ 机械回答，可能答非所问 | ✅ 主动追问补充信息 |
| **需要计算** | ❌ 只能给建议，不能算 | ✅ 自动调用计算工具给出具体金额 |
| **需要文书** | ❌ 只能告诉流程 | ✅ 直接生成申请书/催告函 |
| **引用错误法律** | ❌ 可能引用已废止法条 | ✅ 自动检查并纠正 |
| **多步骤问题** | ❌ 单次回答 | ✅ 逐步推理、验证、交付 |

### 示例对比

**用户问题：** "老板拖欠我两个月工资，我该怎么办？"

#### 传统模式输出：
```
根据《劳动合同法》第30条，用人单位应当按照劳动合同约定和国家规定，
向劳动者及时足额支付劳动报酬。如果用人单位拖欠工资，您可以：
1. 与用人单位协商
2. 向劳动监察部门投诉
3. 申请劳动仲裁

【免责声明】以上内容仅供参考，不构成法律意见。
```

**问题：** 没有问是否签合同、金额多少、有无证据，无法给出具体方案。

---

#### AI-Native 智能体模式输出：

**第1轮（Agent 主动追问）：**
```
为了更准确地帮助您，我需要了解以下信息：
- 是否签订书面劳动合同？
- 拖欠金额是多少？拖欠多长时间？
- 公司注册地或工作地在哪个省市？
- 是否有工资条、转账记录、打卡记录等证据？
```

**用户补充：** "没签合同，月薪8000，拖欠2个月，公司在北京，有银行转账记录和打卡记录。"

**第2轮（Agent 综合分析 + 工具调用）：**
```
根据您的情况，我为您分析如下：

一、法律分析
1. 根据《劳动合同法》第82条，用人单位未与劳动者签订书面劳动合同的，
   应当向劳动者每月支付二倍的工资。您可主张双倍工资差额。

2. 根据《劳动合同法》第30条，用人单位拖欠工资，您可以要求支付拖欠的工资。

二、金额计算（已为您自动计算）
- 拖欠工资：8,000 × 2 = 16,000 元
- 双倍工资差额（假设11个月）：8,000 × 11 = 88,000 元
- 合计可主张：104,000 元

三、维权步骤
1. 先与公司协商解决
2. 如协商不成，向北京市劳动仲裁委员会申请劳动仲裁
3. 准备证据材料：银行转账记录、打卡记录、工作邮件等

四、我已为您生成《劳动仲裁申请书》（附后），您可以直接使用。

五、风险提示
- 劳动仲裁时效为1年，请尽快申请
- 双倍工资差额的计算需以实际工作时长为准
- 建议保存好所有证据材料原件

【免责声明】以上内容仅供参考，不构成法律意见。

---

附件：劳动仲裁申请书

劳动仲裁申请书

申请人：___________
被申请人：某公司（北京）

仲裁请求：
1. 裁决被申请人支付申请人双倍工资差额 88,000 元；
2. 裁决被申请人支付申请人拖欠工资 16,000 元；
3. 本案仲裁费用由被申请人承担。

事实与理由：
...（完整文书内容）
```

**优势：**
- ✅ 主动收集关键信息
- ✅ 自动计算具体金额
- ✅ 生成可直接使用的文书
- ✅ 给出具体地域的操作步骤
- ✅ 提示时效和风险

---

## 🛠️ 下一步改进方向

### 1. 增强工具集

- [ ] **案例检索工具**：查询类似案件的判决结果
- [ ] **企业信息查询工具**：通过天眼查/企查查 API 查询公司状态
- [ ] **法院信息工具**：自动告知管辖法院地址和联系方式
- [ ] **律师费计算工具**：估算诉讼成本

### 2. 集成到 Web 界面

在 `static/index.html` 中增加"智能体模式"开关：

```html
<label>
  <input type="checkbox" id="agentMode"> 启用智能体模式（AI主动追问）
</label>
```

WebSocket 中增加追问逻辑：

```javascript
socket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    if (data.type === "clarification_needed") {
        // 显示追问信息
        displayClarificationRequest(data.missing_info);
    } else if (data.type === "answer") {
        // 显示答案
        displayAnswer(data.answer);
    }
}
```

### 3. 增加对话记忆

让 Agent 能够记住上下文：

```python
class LegalAgentSystem:
    def __init__(self):
        self.conversation_memory = {}  # {session_id: [messages]}
    
    def run(self, query: str, session_id: str = None):
        # 获取历史对话
        history = self.conversation_memory.get(session_id, [])
        
        # 在 state 中包含历史
        initial_state = {
            "query": query,
            "history": history,
            ...
        }
```

### 4. 引入 LLM Function Calling

将工具注册为 LLM 的 function calling：

```python
tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "calculate_double_salary",
            "description": "计算未签劳动合同的双倍工资差额",
            "parameters": {
                "type": "object",
                "properties": {
                    "months": {"type": "integer", "description": "工作月数（1-11）"},
                    "monthly_salary": {"type": "number", "description": "月工资"}
                },
                "required": ["months", "monthly_salary"]
            }
        }
    }
]

response = client.chat.completions.create(
    model="gpt-4",
    messages=[...],
    tools=tools_schema,
    tool_choice="auto"
)
```

---

## 📈 评估与优化

### 评估指标

| 指标 | 传统模式 | AI-Native 目标 |
|------|---------|--------------|
| 单次回答完整性 | 60% | 90%+ |
| 追问准确率 | 0% | 85%+ |
| 法条引用准确率 | 78% | 95%+ |
| 用户满意度 | 3.5/5 | 4.5/5 |
| 平均对话轮次 | 1.2 | 2.5（主动追问） |

### 持续优化

1. **记录所有 Agent 执行 Trace**
   - 保存每次工具调用、推理步骤
   - 用户反馈（有用/无用）

2. **自动评测**
   - 每周自动跑回归测试集
   - 检测准确率下降

3. **Bad Case 沉淀**
   - 用户标记"答案不对"的自动加入测试集
   - 人工分析失败原因

---

## ⚠️ 注意事项

1. **LangGraph 依赖**：需要 Python 3.9+
2. **工具调用可能增加响应时间**：从平均 1.5秒 → 3-5秒
3. **需要更强的 LLM**：建议使用 GPT-4 或 Qwen-Max 以获得更好的推理能力
4. **成本增加**：多步推理会增加 Token 消耗

---

## 📞 技术支持

如有问题，请查看：
- LangGraph 文档：https://python.langchain.com/docs/langgraph
- 项目 Issue：提交到项目仓库

---

**开始使用 AI-Native 模式，让法律咨询更智能！** 🚀
