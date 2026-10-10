# Legal QA System - AI-Native 改造路线图

> **项目备份位置**: `E:\陈杰\Legal_qa_system_backup_20260825`  
> **改造开始时间**: 2026-08-25  
> **目标**: 从传统问答系统升级为 AI-Native 法律智能体系统

---

## 📊 改造全景流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI-Native 改造三阶段路线图                      │
└─────────────────────────────────────────────────────────────────┘

阶段一：Agentic Workflow (智能体工作流)      [2-3周] ⭐⭐⭐
┌──────────────────────────────────────────────────────┐
│  ✅ 数据优化 (已完成)                                  │
│  □ 安装依赖                                           │
│  □ 测试工具集                                         │
│  □ 运行演示脚本                                       │
│  □ 集成到现有系统                                     │
│  □ Web 界面适配                                       │
│  □ 测试与优化                                         │
└──────────────────────────────────────────────────────┘
              ↓
阶段二：GraphRAG / 知识图谱                   [3-4周] ⭐⭐
┌──────────────────────────────────────────────────────┐
│  □ 设计法律知识图谱 Schema                            │
│  □ 构建法律条文关系图                                 │
│  □ 集成 Neo4j                                         │
│  □ 实现混合检索（向量 + 图谱）                         │
│  □ 优化检索效果                                       │
└──────────────────────────────────────────────────────┘
              ↓
阶段三：LLMOps / 数据飞轮                     [持续进行] ⭐
┌──────────────────────────────────────────────────────┐
│  □ 建立 Trace 记录系统                                │
│  □ 用户反馈收集                                       │
│  □ 自动化评测流水线                                   │
│  □ Bad Case 沉淀机制                                  │
│  □ 持续优化闭环                                       │
└──────────────────────────────────────────────────────┘
```

---

## 🎯 阶段一：Agentic Workflow（当前阶段）

### 核心目标
将"单次问答"升级为"智能体多步推理"，具备：
- ✅ 主动追问缺失信息
- ✅ 调用工具（计算金额、生成文书）
- ✅ 自我审查与验证
- ✅ 多步推理与规划

---

### 1.1 环境准备 ⏳

#### 任务清单

- [ ] **安装 LangGraph 依赖**
  ```bash
  cd E:\陈杰\Legal_qa_system
  pip install langgraph==0.0.50 langchain-core==0.1.40
  ```
  
  **验证方式**:
  ```bash
  python -c "import langgraph; print('LangGraph version:', langgraph.__version__)"
  ```
  
  **预期输出**: `LangGraph version: 0.0.50`

- [ ] **检查现有依赖**
  ```bash
  pip list | findstr "langchain pymilvus"
  ```
  
  **确保已安装**:
  - `langchain-core >= 0.1.0`
  - `pymilvus >= 2.3.0`

---

### 1.2 测试工具集 ⏳

#### 任务清单

- [ ] **测试法律工具集**
  ```bash
  python agentic\legal_tools.py
  ```
  
  **预期输出**:
  - ✅ 双倍工资计算结果
  - ✅ 经济补偿金计算结果
  - ✅ 已废止法律检测
  - ✅ 劳动仲裁申请书生成
  - ✅ 诉讼时效计算

  **验证要点**:
  - [ ] 计算金额准确
  - [ ] 法条引用正确
  - [ ] 文书格式完整

---

### 1.3 运行演示脚本 ⏳

#### 任务清单

- [ ] **运行 AI-Native 演示**
  ```bash
  python agentic\demo.py
  ```
  
  **预期场景**:
  1. **场景1**: 劳动争议 → 主动追问 → 工具调用 → 生成方案
  2. **场景2**: 法条查询 → 时效性检查 → 自动纠正已废止法律
  3. **场景3**: 文书生成 → 催告函 + 证据清单

  **验证要点**:
  - [ ] 能识别缺失信息并追问
  - [ ] 工具调用成功（金额计算、文书生成）
  - [ ] 检测到《合同法》已废止并提示

  **成功标志**: 三个场景都能正常运行并输出完整答案

---

### 1.4 集成到现有系统 ⏳

#### 架构设计

```
┌─────────────────────────────────────────────────────┐
│                  Web 接口层 (app.py)                  │
│  ┌──────────────┐          ┌──────────────┐         │
│  │ /api/query   │          │ /api/agent   │         │
│  │ (传统模式)    │          │ (Agent模式)   │←── 新增 │
│  └──────────────┘          └──────────────┘         │
└─────────────────────────────────────────────────────┘
           ↓                          ↓
┌─────────────────────┐    ┌─────────────────────────┐
│  传统 RAG 系统       │    │  Agent 智能体系统        │
│  (new_main.py)      │    │  (legal_agent_system.py)│
│                     │    │                         │
│  BM25 → Vector      │    │  意图分类 → 事实澄清     │
│    ↓                │    │     ↓                   │
│  生成答案           │    │  工具调用 → 生成答案     │
│                     │    │     ↓                   │
│                     │    │  质量审查 → 最终输出     │
└─────────────────────┘    └─────────────────────────┘
```

#### 任务清单

- [ ] **步骤1: 修改 app.py 增加 Agent 接口**
  
  **文件位置**: `E:\陈杰\Legal_qa_system\app.py`
  
  **修改内容**:
  ```python
  # 在文件开头增加导入
  from agentic.legal_agent_system import LegalAgentSystem
  
  # 初始化 Agent 系统
  agent_system = LegalAgentSystem()
  
  # 增加新接口
  @app.route('/api/agent/query', methods=['POST'])
  def agent_query():
      """智能体模式：支持多步推理和工具调用"""
      data = request.get_json()
      query = data.get('query', '')
      
      # 调用 Agent 系统
      result = agent_system.run(query)
      
      return jsonify({
          'success': True,
          'intent': result['intent'],
          'need_clarify': result['need_clarify'],
          'missing_info': result['missing_info'],
          'tools_called': result['tools_called'],
          'answer': result.get('final_answer', result['draft_answer'])
      })
  ```
  
  **验证方式**:
  ```bash
  # 启动服务
  python app.py
  
  # 测试 Agent 接口
  curl -X POST http://localhost:5001/api/agent/query \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"老板拖欠我工资怎么办\"}"
  ```

- [ ] **步骤2: 修改 new_main.py 增加 Agent 模式开关**
  
  **文件位置**: `E:\陈杰\Legal_qa_system\new_main.py`
  
  **修改内容**:
  ```python
  from agentic.legal_agent_system import LegalAgentSystem
  
  class IntegratedQASystem:
      def __init__(self):
          # 原有初始化...
          
          # 新增：Agent 系统
          self.agent_system = LegalAgentSystem()
          self.use_agent = False  # 默认关闭，可通过参数控制
      
      def query(self, query, session_id=None, use_agent=False):
          """
          query: 用户问题
          session_id: 会话ID
          use_agent: 是否使用 Agent 模式
          """
          if use_agent:
              return self._query_with_agent(query, session_id)
          else:
              return self._query_traditional(query, session_id)
      
      def _query_with_agent(self, query, session_id):
          """使用 Agent 模式处理"""
          result = self.agent_system.run(query)
          
          if result['need_clarify']:
              return {
                  'type': 'clarification',
                  'missing_info': result['missing_info'],
                  'message': '为了更准确地回答，我需要了解：\n' + 
                            '\n'.join(f'{i+1}. {info}' 
                                     for i, info in enumerate(result['missing_info']))
              }
          
          return {
              'type': 'answer',
              'answer': result.get('final_answer', result['draft_answer']),
              'tools_used': result['tools_called']
          }
      
      def _query_traditional(self, query, session_id):
          """原有的传统模式"""
          # 保持原有逻辑不变
          ...
  ```

- [ ] **步骤3: 前端增加 Agent 模式开关**
  
  **文件位置**: `E:\陈杰\Legal_qa_system\static\index.html`
  
  **修改内容**: 在查询输入框旁边增加开关
  ```html
  <div class="mode-switch">
      <label>
          <input type="checkbox" id="agentMode" onchange="toggleAgentMode()">
          启用智能体模式 (AI 主动追问)
      </label>
  </div>
  
  <script>
  let isAgentMode = false;
  
  function toggleAgentMode() {
      isAgentMode = document.getElementById('agentMode').checked;
      console.log('Agent 模式:', isAgentMode ? '开启' : '关闭');
  }
  
  function sendQuery() {
      const query = document.getElementById('queryInput').value;
      const endpoint = isAgentMode ? '/api/agent/query' : '/api/query';
      
      fetch(endpoint, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({query: query})
      })
      .then(response => response.json())
      .then(data => {
          if (data.type === 'clarification') {
              // 显示追问信息
              displayClarification(data.missing_info);
          } else {
              // 显示答案
              displayAnswer(data.answer);
          }
      });
  }
  
  function displayClarification(missing_info) {
      let html = '<div class="clarification-box">';
      html += '<p>为了更准确地回答您的问题，我需要了解：</p><ul>';
      missing_info.forEach(info => {
          html += `<li>${info}</li>`;
      });
      html += '</ul></div>';
      document.getElementById('answerArea').innerHTML = html;
  }
  </script>
  ```

---

### 1.5 测试与验证 ⏳

#### 测试用例清单

| 测试ID | 测试场景 | 输入 | 预期输出 | 状态 |
|--------|---------|------|---------|------|
| T1-1 | 简单法条查询 | "民法典第509条是什么" | 直接返回法条内容 | [ ] |
| T1-2 | 缺信息咨询 | "老板拖欠我工资怎么办" | 追问：是否签合同、金额、地点、证据 | [ ] |
| T1-3 | 补充信息后 | 用户回答追问 | 调用计算工具 + 生成完整方案 | [ ] |
| T1-4 | 已废止法律 | "合同法第94条是什么" | 提示已废止，引导查民法典 | [ ] |
| T1-5 | 工具调用 | "未签合同11个月月薪8000" | 自动计算双倍工资88000元 | [ ] |
| T1-6 | 文书生成 | "帮我生成劳动仲裁申请书" | 生成完整申请书模板 | [ ] |

#### 验证步骤

- [ ] **本地测试**
  ```bash
  # 1. 启动服务
  python app.py
  
  # 2. 浏览器访问
  http://localhost:5001
  
  # 3. 勾选"启用智能体模式"
  # 4. 输入测试用例
  # 5. 验证预期输出
  ```

- [ ] **性能测试**
  ```bash
  # 使用 locust 进行压力测试
  python scripts/locust_test.py
  
  # 验证指标:
  # - 响应时间 < 5秒
  # - 并发 10人时成功率 > 95%
  ```

- [ ] **对比测试**
  
  **测试方法**: 同一问题分别用传统模式和 Agent 模式回答
  
  | 问题 | 传统模式答案 | Agent 模式答案 | 优势 |
  |-----|------------|--------------|------|
  | "老板拖欠工资" | 机械回答法条 | 追问信息→计算金额→生成文书 | [ ] |
  | "合同法第94条" | 直接返回 | 检测废止→引导民法典 | [ ] |

---

### 1.6 上线与监控 ⏳

#### 灰度发布计划

- [ ] **第1周**: 10% 流量使用 Agent 模式（内部测试）
- [ ] **第2周**: 30% 流量使用 Agent 模式
- [ ] **第3周**: 50% 流量使用 Agent 模式
- [ ] **第4周**: 全量切换

#### 监控指标

- [ ] **关键指标看板**
  ```
  Agent 模式核心指标:
  - 追问率: ___% (目标: 30-50%)
  - 工具调用成功率: ___% (目标: >95%)
  - 平均响应时间: ___ 秒 (目标: <5秒)
  - 用户满意度: ___分 (目标: >4.0/5.0)
  ```

- [ ] **每日检查项**
  - [ ] 查看错误日志
  - [ ] 检查工具调用失败率
  - [ ] 收集用户反馈
  - [ ] 记录 Bad Case

---

## 🔄 阶段二：GraphRAG / 知识图谱（预计3-4周后启动）

### 准备工作清单

- [ ] 学习 Neo4j 基础
- [ ] 设计法律知识图谱 Schema
- [ ] 准备法律条文关系数据
- [ ] 安装 Neo4j 数据库

### 核心任务

- [ ] 构建法律层级关系图
- [ ] 构建法条引用关系图
- [ ] 实现混合检索（向量 + 图谱）
- [ ] 优化检索准确率

**详细计划**: 待阶段一完成后制定

---

## 🔁 阶段三：LLMOps / 数据飞轮（持续进行）

### 准备工作清单

- [ ] 设计 Trace 数据结构
- [ ] 建立用户反馈表
- [ ] 搭建自动化评测流水线

### 核心任务

- [ ] 记录每次推理的完整 Trace
- [ ] 收集用户点赞/点踩反馈
- [ ] 每周自动跑回归测试
- [ ] Bad Case 自动沉淀为测试集

**详细计划**: 待阶段一完成后制定

---

## 📈 进度追踪

### 整体进度

```
阶段一：Agentic Workflow    [████░░░░░░] 40% (数据优化完成)
阶段二：GraphRAG            [░░░░░░░░░░]  0% (未开始)
阶段三：LLMOps              [░░░░░░░░░░]  0% (未开始)
```

### 里程碑

- [x] **M1**: 数据优化完成 (2026-08-25)
- [ ] **M2**: Agent 工具集测试通过 (目标: _______)
- [ ] **M3**: 集成到现有系统 (目标: _______)
- [ ] **M4**: 灰度发布 10% (目标: _______)
- [ ] **M5**: 全量上线 (目标: _______)

---

## 🚨 风险与应对

### 已识别风险

| 风险项 | 影响 | 概率 | 应对措施 | 状态 |
|--------|------|------|---------|------|
| LangGraph 依赖冲突 | 高 | 中 | 单独虚拟环境测试 | [ ] |
| Agent 响应时间过长 | 中 | 高 | 异步处理 + 超时限制 | [ ] |
| 用户不习惯追问模式 | 低 | 中 | 提供传统模式开关 | [ ] |
| 工具调用失败率高 | 高 | 低 | 增加异常处理和重试 | [ ] |

---

## 📝 每日工作日志

### 2026-08-25
- [x] 完成项目备份
- [x] 完成数据优化（2632条 → 2632条，去重+增强）
- [x] 创建 Agent 框架和工具集
- [x] 编写改造路线图

### 2026-08-26
- [ ] 安装 LangGraph 依赖
- [ ] 测试工具集
- [ ] 运行演示脚本
- [ ] ___________

### 2026-08-27
- [ ] ___________
- [ ] ___________

---

## 🎓 学习资源

### 必读文档
- [ ] [LangGraph 官方文档](https://python.langchain.com/docs/langgraph)
- [ ] [项目内部文档] `agentic/README.md`
- [ ] [数据优化指南] `docs/DATA_OPTIMIZATION_GUIDE.md`

### 视频教程
- [ ] LangGraph 快速入门（推荐：B站搜索）
- [ ] AI Agent 原理讲解

---

## 🤝 协作与支持

### 团队成员

| 角色 | 姓名 | 职责 | 联系方式 |
|------|------|------|---------|
| 技术负责人 | ___ | 整体架构设计 | ___ |
| 开发工程师 | ___ | 代码实现 | ___ |
| 测试工程师 | ___ | 测试验证 | ___ |

### 沟通机制
- 每日站会：___点
- 每周复盘：周___
- 问题反馈：___

---

## ✅ 验收标准

### 阶段一验收标准

- [ ] **功能完整性**
  - [ ] Agent 能识别缺失信息并追问
  - [ ] 至少5个工具能正常调用
  - [ ] 质量审查机制生效

- [ ] **性能指标**
  - [ ] 响应时间 < 5秒
  - [ ] 工具调用成功率 > 95%
  - [ ] 并发10人时成功率 > 95%

- [ ] **用户体验**
  - [ ] 用户满意度 > 4.0/5.0
  - [ ] 追问信息命中率 > 80%
  - [ ] 答案完整性评分 > 4.0/5.0

---

## 📞 问题反馈

遇到问题时，请按以下顺序排查：

1. **查看日志**: `logs/app.log`
2. **检查文档**: `agentic/README.md`
3. **运行测试**: `python agentic/demo.py`
4. **提交 Issue**: 项目仓库

---

**最后更新**: 2026-08-25  
**下次更新**: ___________  
**当前负责人**: ___________
