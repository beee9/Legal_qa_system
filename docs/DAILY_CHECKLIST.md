# AI-Native 改造每日执行清单

> **快速开始**: 每天执行此清单，逐步完成 AI-Native 改造  
> **完整路线图**: 参考 `AI_NATIVE_ROADMAP.md`

---

## 🚀 快速启动

```bash
# 运行自动化执行助手
python scripts\roadmap_executor.py
```

这个脚本会自动：
- ✅ 检查环境依赖
- ✅ 测试工具集
- ✅ 运行演示
- ✅ 更新进度到路线图

---

## 📋 第1周任务清单（环境准备 + 测试）

### Day 1: 环境搭建 ⏳

- [ ] **安装 LangGraph**
  ```bash
  pip install langgraph==0.0.50 langchain-core==0.1.40
  ```

- [ ] **测试安装**
  ```bash
  python -c "import langgraph; print('OK')"
  ```

- [ ] **阅读文档**
  - [ ] `agentic/README.md` (30分钟)
  - [ ] `AI_NATIVE_ROADMAP.md` (20分钟)

**今日目标**: 完成环境搭建，理解 AI-Native 架构

---

### Day 2: 测试工具集 ⏳

- [ ] **运行工具测试**
  ```bash
  python agentic\legal_tools.py
  ```

- [ ] **验证功能**
  - [ ] 双倍工资计算
  - [ ] 经济补偿金计算
  - [ ] 已废止法律检测
  - [ ] 文书生成

- [ ] **记录问题**
  - 问题1: ___________
  - 问题2: ___________

**今日目标**: 确保所有工具正常运行

---

### Day 3: 运行演示脚本 ⏳

- [ ] **运行完整演示**
  ```bash
  python agentic\demo.py
  ```

- [ ] **体验3个场景**
  - [ ] 场景1: 劳动争议（主动追问）
  - [ ] 场景2: 法条查询（时效检查）
  - [ ] 场景3: 文书生成

- [ ] **对比传统模式**
  - [ ] 记录 Agent 模式的优势
  - [ ] 识别可能的问题

**今日目标**: 理解 AI-Native 的核心价值

---

### Day 4: 集成准备 ⏳

- [ ] **备份当前代码**
  ```bash
  # 已有备份: Legal_qa_system_backup_20260825
  # 可以继续修改
  ```

- [ ] **创建测试分支**
  ```bash
  cd E:\陈杰\Legal_qa_system
  git checkout -b feature/ai-native
  ```

- [ ] **设计集成方案**
  - [ ] 确定接口路径: `/api/agent/query`
  - [ ] 设计前端开关位置
  - [ ] 规划灰度发布策略

**今日目标**: 完成集成前准备

---

### Day 5: 后端集成 ⏳

- [ ] **修改 `app.py`**
  
  在文件开头增加：
  ```python
  from agentic.legal_agent_system import LegalAgentSystem
  agent_system = LegalAgentSystem()
  ```
  
  增加新接口：
  ```python
  @app.route('/api/agent/query', methods=['POST'])
  def agent_query():
      data = request.get_json()
      query = data.get('query', '')
      result = agent_system.run(query)
      
      return jsonify({
          'success': True,
          'need_clarify': result['need_clarify'],
          'missing_info': result['missing_info'],
          'answer': result.get('final_answer', result['draft_answer'])
      })
  ```

- [ ] **测试接口**
  ```bash
  # 启动服务
  python app.py
  
  # 测试（新开终端）
  curl -X POST http://localhost:5001/api/agent/query ^
    -H "Content-Type: application/json" ^
    -d "{\"query\": \"老板拖欠我工资\"}"
  ```

**今日目标**: 后端接口可用

---

### Day 6: 前端集成 ⏳

- [ ] **修改 `static/index.html`**
  
  增加模式开关：
  ```html
  <div class="mode-switch" style="margin: 10px 0;">
      <label>
          <input type="checkbox" id="agentMode">
          启用智能体模式 (AI主动追问)
      </label>
  </div>
  ```
  
  修改查询函数：
  ```javascript
  function sendQuery() {
      const isAgent = document.getElementById('agentMode').checked;
      const endpoint = isAgent ? '/api/agent/query' : '/api/query';
      // ... 其余代码
  }
  ```

- [ ] **测试界面**
  - [ ] 访问 http://localhost:5001
  - [ ] 勾选"智能体模式"
  - [ ] 输入测试问题
  - [ ] 验证追问功能

**今日目标**: 前端可切换模式

---

### Day 7: 本地测试 ⏳

- [ ] **功能测试**
  
  | 测试用例 | 传统模式 | Agent模式 | 通过 |
  |---------|---------|----------|------|
  | "民法典509条" | __ | __ | [ ] |
  | "老板拖欠工资" | __ | __ | [ ] |
  | "合同法94条" | __ | __ | [ ] |

- [ ] **性能测试**
  - [ ] 响应时间: ___ 秒 (目标: <5秒)
  - [ ] 工具调用成功率: ___% (目标: >95%)

- [ ] **问题记录**
  - 问题1: ___________
  - 解决方案: ___________

**今日目标**: 完成第一周任务，系统可本地运行

---

## 📋 第2周任务清单（优化 + 灰度发布）

### Day 8: 异常处理 ⏳

- [ ] 增加超时处理
- [ ] 增加工具调用失败重试
- [ ] 增加错误日志记录

### Day 9: 性能优化 ⏳

- [ ] 异步处理长耗时操作
- [ ] 增加缓存机制
- [ ] 压力测试

### Day 10: 监控埋点 ⏳

- [ ] 记录 Agent 调用次数
- [ ] 记录工具调用情况
- [ ] 记录响应时间

### Day 11-12: 灰度发布准备 ⏳

- [ ] 设计灰度策略
- [ ] 准备回滚方案
- [ ] 编写上线文档

### Day 13-14: 灰度发布 ⏳

- [ ] 10% 流量 Agent 模式
- [ ] 监控关键指标
- [ ] 收集用户反馈

---

## 📊 每日检查项（每天都要做）

### 开始工作前（5分钟）

- [ ] 拉取最新代码
- [ ] 查看昨日进度
- [ ] 确定今日目标

### 工作中（随时）

- [ ] 遇到问题立即记录
- [ ] 重要决策写入文档
- [ ] 代码提交带清晰注释

### 结束工作前（10分钟）

- [ ] 提交今日代码
- [ ] 更新路线图进度
- [ ] 记录明日计划

---

## 🎯 里程碑检查

### 里程碑1: 本地环境可用 ✓

- [x] 依赖安装完成
- [ ] 工具集测试通过
- [ ] 演示脚本运行正常

### 里程碑2: 集成完成 ⏳

- [ ] 后端接口可用
- [ ] 前端界面可切换
- [ ] 本地测试通过

### 里程碑3: 灰度发布 ⏳

- [ ] 10% 流量上线
- [ ] 无严重错误
- [ ] 用户反馈正面

### 里程碑4: 全量上线 ⏳

- [ ] 50% 流量稳定运行
- [ ] 核心指标达标
- [ ] 全量切换

---

## 📈 进度可视化

```
本周进度: Day [1][2][3][4][5][6][7]
完成情况: [✓][✓][⏳][░][░][░][░]

整体进度:
环境准备  ████████░░ 80%
工具测试  ██░░░░░░░░ 20%
演示验证  ░░░░░░░░░░  0%
后端集成  ░░░░░░░░░░  0%
前端集成  ░░░░░░░░░░  0%
测试优化  ░░░░░░░░░░  0%
灰度发布  ░░░░░░░░░░  0%
```

---

## 🚨 遇到问题？

### 常见问题速查

1. **LangGraph 安装失败**
   ```bash
   # 尝试指定镜像源
   pip install langgraph -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

2. **工具调用报错**
   - 检查 `base/law_database.py` 中的数据库连接
   - 确认 MySQL 服务正常运行

3. **演示脚本编码错误**
   - 已修复，使用 UTF-8 输出

4. **接口测试失败**
   - 检查端口占用
   - 查看 `logs/app.log` 错误信息

### 求助流程

1. 查看 `agentic/README.md`
2. 搜索 `AI_NATIVE_ROADMAP.md` 中的"风险与应对"
3. 查看项目 Issue
4. 向团队成员求助

---

## 📝 今日工作记录

**日期**: ___________  
**今日目标**: ___________

**完成情况**:
- [x] ___________
- [ ] ___________
- [ ] ___________

**遇到的问题**:
1. ___________
2. ___________

**解决方案**:
1. ___________
2. ___________

**明日计划**:
1. ___________
2. ___________

**工作时长**: ___ 小时

---

**💡 提示**: 
- 使用 `python scripts\roadmap_executor.py` 自动检查进度
- 每天更新此清单，保持进度可见
- 遇到困难不要卡住，先记录问题继续下一项

**🎯 目标**: 
- 第1周完成环境搭建和本地测试
- 第2周完成集成和灰度发布
- 持续优化，提升用户体验

---

**最后更新**: 2026-08-25  
**当前负责人**: ___________
