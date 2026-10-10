# 数据优化方案实施指南

本文档说明如何使用新创建的数据优化工具对Legal_qa_system项目进行数据升级。

## 一、新增的核心模块

### 1. 数据模型层 (base/)

#### base/law_article.py
- **LawArticle**: 法律条文数据模型，包含完整元数据
  - 法律名称、条文号、层级、版本
  - 生效/失效日期、适用地域
  - 章节结构、来源追溯
  - 时效性判断方法

#### base/law_database.py
- **LawDatabase**: 法律原文MySQL数据库管理
  - 自动创建law_articles表
  - 条文增删改查
  - 版本管理
  - 时效性过滤

#### base/enhanced_qa.py
- **EnhancedQA**: 增强的问答数据模型
  - 补充法律依据、条文引用
  - 适用条件、例外情形
  - 实操指导、证据要求
  - 数据来源追溯

### 2. 数据工具层 (data_tools/)

#### data_tools/data_quality_optimizer.py
- **去重功能**: 完全重复 + 近重复检测
- **验证功能**: 法律引用准确性检查
- **增强功能**: 自动提取法律依据和条文引用
- **报告功能**: 生成数据质量报告

#### data_tools/law_importer.py
- **多格式导入**: 支持CSV、JSON格式
- **结构化入库**: MySQL + Milvus双写
- **元数据完整**: 保留所有法律元数据

#### data_tools/evaluator.py
- **测试集管理**: 创建分层测试集模板
- **多维度评估**: 分类、检索、答案质量
- **评测报告**: 自动生成Markdown报告

### 3. 向量存储增强 (rag_qa/core/)

#### rag_qa/core/vector_store.py
- **元数据扩展**: 支持17个法律相关字段
- **完整回传**: 检索时返回所有元数据
- **可追溯性**: 保留法律名称、条文号、来源URL

#### rag_qa/scripts/init_enhanced_collection.py
- **集合初始化**: 创建支持完整元数据的Milvus集合
- **数据迁移**: 从旧集合迁移到新集合

---

## 二、实施步骤

### 阶段一：数据底座建设（1-2天）

#### 步骤1：初始化法律原文数据库

```bash
cd E:\陈杰\Legal_qa_system

# 测试数据库连接和表创建
python -c "from base import LawDatabase; db = LawDatabase(); print('法律数据库初始化成功')"
```

#### 步骤2：准备法律原文数据

选择以下任一方式：

**方式A：从JSON导入（推荐）**

```bash
# 1. 生成示例模板
python data_tools/law_importer.py --mode sample --output law_sample.json

# 2. 编辑law_sample.json，填写法律条文
# 3. 导入到MySQL
python data_tools/law_importer.py --mode json --input law_sample.json

# 4. 导入到向量数据库
python data_tools/law_importer.py --mode to_vector --law-short-name "民法典" --collection legal_rag_enhanced
```

**方式B：从CSV导入**

CSV格式示例（law_articles.csv）：
```
article_no,article_title,article_content,chapter,section
509,,当事人应当按照约定全面履行自己的义务...,第三编 合同,第一分编 通则
510,,合同生效后...,第三编 合同,第一分编 通则
```

导入命令：
```bash
python data_tools/law_importer.py \
  --mode csv \
  --input law_articles.csv \
  --law-name "中华人民共和国民法典" \
  --law-short-name "民法典" \
  --law-level "法律" \
  --version "v1" \
  --effective-date "2021-01-01"
```

#### 步骤3：创建增强版向量集合

```bash
cd E:\陈杰\Legal_qa_system\rag_qa\scripts

# 创建新集合
python init_enhanced_collection.py --create --collection legal_rag_enhanced

# （可选）从旧集合迁移数据
python init_enhanced_collection.py --migrate --old-collection legal_rag --collection legal_rag_enhanced
```

**注意**：迁移后旧集合的数据元数据字段为空，需要后续补充。

#### 步骤4：验证数据库

```python
# 验证MySQL
from base import LawDatabase
db = LawDatabase()
stats = db.get_law_statistics()
print(stats)

# 验证向量库
from rag_qa.core.vector_store import VectorStore
vs = VectorStore(collection_name="legal_rag_enhanced")
results = vs.hybrid_search_with_rerank("民法典第509条")
print(results[0].metadata)  # 应该包含law_name, article_no等字段
```

---

### 阶段二：现有数据清洗（1天）

#### 步骤1：分析现有问答数据质量

```bash
cd E:\陈杰\Legal_qa_system

python data_tools/data_quality_optimizer.py \
  --input mysql_qa/data/legal_qa_full.csv \
  --output mysql_qa/data/legal_qa_full_enhanced.csv \
  --dedupe \
  --validate \
  --enhance
```

输出结果：
- `legal_qa_full_enhanced.csv`: 清洗后的数据
- 控制台日志：去重报告、引用问题、质量指标

#### 步骤2：人工审核高风险数据

重点检查工具标记的问题：
- 缺少法律名称的条文引用
- 近重复问题（相似度 > 0.9）
- 法律义务词使用不当

建议使用Excel打开`legal_qa_full_enhanced.csv`，按`article_refs`字段过滤：
- 空值：需要补充法律依据
- 非空值：验证准确性

#### 步骤3：分离训练集和测试集

```python
import pandas as pd
from sklearn.model_selection import train_test_split

df = pd.read_csv('mysql_qa/data/legal_qa_full_enhanced.csv')

# 按领域分层抽样，避免某些领域完全缺失
train_df, test_df = train_test_split(
    df, 
    test_size=0.1,  # 10%作为测试集
    stratify=df['subject'],  # 按领域分层
    random_state=42
)

train_df.to_csv('mysql_qa/data/legal_qa_train.csv', index=False)
test_df.to_csv('mysql_qa/data/legal_qa_test.csv', index=False)

print(f"训练集: {len(train_df)} 条")
print(f"测试集: {len(test_df)} 条")
```

**重要**：测试集一旦划分，不能用于训练或调参！

---

### 阶段三：建立评测体系（1天）

#### 步骤1：创建测试集模板

```bash
python data_tools/evaluator.py \
  --mode create_template \
  --output test_set/legal_qa_test_template.json \
  --samples-per-type 10
```

生成120个测试用例框架（12类问题 × 10个）。

#### 步骤2：手工编写测试用例

编辑`test_set/legal_qa_test_template.json`，为每个用例填写：

```json
{
  "id": "法条精确查询_1",
  "question": "民法典第509条的内容是什么？",
  "question_type": "法条精确查询",
  "expected_intent": "法条查询",
  "expected_articles": [
    {"law": "民法典", "article": "509"}
  ],
  "expected_answer_contains": ["当事人应当", "全面履行", "义务"],
  "expected_answer_not_contains": ["第510条", "合同无效"],
  "should_refuse": false,
  "region": "全国",
  "difficulty": "easy",
  "notes": "基础条文查询"
}
```

**重点补充的问题类型**：
1. **已废止条文**：引用《合同法》条文（已被民法典替代）
2. **地方性法规**：询问北京市、上海市的地方法规
3. **口语化问题**：包含错别字、方言、俚语
4. **需要拒答**：信息不足、超出范围、要求违法操作

建议每类问题至少10个，重点关注边界情况。

#### 步骤3：运行评测

```python
# evaluation_runner.py
from data_tools.evaluator import LegalQAEvaluator
from rag_qa.core.rag_system import RAGSystem
import json

# 加载测试集
evaluator = LegalQAEvaluator()
test_cases = evaluator.load_test_set("test_set/legal_qa_test.json")

# 初始化系统
rag_system = RAGSystem()

# 运行测试
predictions = []
retrieved_articles_list = []
answers = []

for case in test_cases:
    query = case["question"]
    
    # 分类预测（需要你的分类器）
    pred_intent = classify(query)  # 替换为实际分类器
    predictions.append(pred_intent)
    
    # 检索
    docs = rag_system.retrieve(query)
    retrieved = [
        {
            "law": doc.metadata.get("law_short_name", ""),
            "article": doc.metadata.get("article_no", "")
        }
        for doc in docs
    ]
    retrieved_articles_list.append(retrieved)
    
    # 生成答案
    answer = rag_system.answer(query)
    answers.append(answer)

# 评估
results = {
    "classification": evaluator.evaluate_classification(test_cases, predictions),
    "retrieval": evaluator.evaluate_retrieval(test_cases, retrieved_articles_list),
    "answer_quality": evaluator.evaluate_answer_quality(test_cases, answers)
}

# 生成报告
evaluator.generate_report(
    "test_set/legal_qa_test.json",
    results,
    "test_set/evaluation_report.md"
)
```

---

### 阶段四：数据扩充与持续优化（长期）

#### 1. 收集真实用户问题

**方式A：日志挖掘**
```python
import pandas as pd

# 从系统日志中提取查询
logs = pd.read_csv("logs/user_queries.csv")
queries = logs['query'].value_counts().head(1000)

# 过滤低频、无效查询
valid_queries = queries[queries > 5]  # 至少出现5次

# 人工标注后加入训练集
```

**方式B：用户反馈**
在系统中增加"答案有用"/"答案无用"按钮，收集负反馈样本。

#### 2. 生成对抗样本

```python
# 生成错别字样本
original = "合同违约怎么办？"
typo_variants = [
    "合同为约怎么办？",  # 违→为
    "合同违约怎么版？",  # 办→版
]

# 生成同义改写
from openai import OpenAI
client = OpenAI(api_key="your-api-key")

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{
        "role": "user",
        "content": f"请将以下法律问题改写为5种不同的口语化表达（保持语义）：{original}"
    }]
)
```

#### 3. 定期回归测试

```bash
# 每次修改代码或数据后运行
python evaluation_runner.py

# 对比前后报告
diff test_set/evaluation_report_v1.md test_set/evaluation_report_v2.md
```

---

## 三、配置文件修改

### 修改 config.ini

```ini
[milvus]
# 使用新的增强版集合
collection_name = legal_rag_enhanced

[data]
# 指定清洗后的数据
qa_data_path = mysql_qa/data/legal_qa_full_enhanced.csv
train_data_path = mysql_qa/data/legal_qa_train.csv
test_data_path = mysql_qa/data/legal_qa_test.csv
```

### 修改代码以使用新元数据

**rag_qa/core/rag_system.py** 修改答案生成，包含法律依据：

```python
def generate_answer(self, query, context_docs):
    # 提取法律依据
    sources = []
    for doc in context_docs:
        law_name = doc.metadata.get("law_short_name", "")
        article_no = doc.metadata.get("article_no", "")
        if law_name and article_no:
            sources.append(f"《{law_name}》第{article_no}条")
    
    # 在prompt中增加来源引用要求
    prompt = f"""
    根据以下法律条文回答问题。

    问题：{query}

    法律条文：
    {context}

    要求：
    1. 回答必须基于提供的法律条文
    2. 明确引用具体条文（如《民法典》第509条）
    3. 如果法律条文不足以回答，说明"根据提供的法律条文无法完全回答"
    4. 说明适用条件和例外情形

    回答：
    """
    
    answer = self.llm.generate(prompt)
    
    # 附加法律来源
    if sources:
        answer += f"\n\n【法律依据】\n" + "、".join(set(sources))
    
    return answer
```

---

## 四、数据质量检查清单

在每次数据更新后，运行以下检查：

### ✅ MySQL数据完整性

```sql
-- 检查必填字段
SELECT COUNT(*) FROM law_articles WHERE article_content = '' OR article_content IS NULL;
-- 应该为0

-- 检查时效性字段
SELECT law_short_name, COUNT(*) FROM law_articles 
WHERE status = '现行有效' AND effective_date IS NULL
GROUP BY law_short_name;
-- 关键法律应该有生效日期

-- 检查重复
SELECT law_id, article_no, version, COUNT(*) 
FROM law_articles 
GROUP BY law_id, article_no, version 
HAVING COUNT(*) > 1;
-- 应该为空
```

### ✅ Milvus元数据完整性

```python
from rag_qa.core.vector_store import VectorStore

vs = VectorStore(collection_name="legal_rag_enhanced")
results = vs.hybrid_search_with_rerank("测试查询", k=10)

# 检查元数据字段
for doc in results:
    assert doc.metadata.get("law_name"), "缺少law_name"
    assert doc.metadata.get("article_no"), "缺少article_no"
    assert doc.metadata.get("status") == "现行有效", "状态字段错误"

print("✅ 元数据完整性检查通过")
```

### ✅ 问答数据质量

```bash
python data_tools/data_quality_optimizer.py \
  --input mysql_qa/data/legal_qa_full_enhanced.csv \
  --validate

# 检查输出中的警告信息
```

---

## 五、常见问题

### Q1: 旧的legal_rag集合数据如何处理？

**A**: 有两种方案：
1. **双集合并行**：暂时保留旧集合，新数据写入legal_rag_enhanced，对比效果后再切换
2. **全量迁移**：使用`init_enhanced_collection.py --migrate`迁移，但元数据字段会为空，需重新入库

### Q2: 如何补充已有问答数据的法律依据？

**A**: 
```bash
# 自动提取
python data_tools/data_quality_optimizer.py --enhance --input xxx.csv --output xxx_enhanced.csv

# 人工审核
# 打开Excel，重点检查article_refs字段非空的记录，验证准确性
```

### Q3: 测试集应该多大？

**A**: 
- 最小规模：每类问题10个，共120个
- 推荐规模：每类问题20-30个，共240-360个
- 关键原则：**质量 > 数量**，边界情况和难例更重要

### Q4: 如何避免测试集泄漏到训练集？

**A**:
1. 先划分测试集，锁定后不再修改
2. 测试集问题不能出现在训练数据中（包括语义相似的改写）
3. 使用`data_quality_optimizer.py --dedupe`检查重复
4. 定期人工抽查

### Q5: 法律条文数据从哪里获取？

**A**: 
- 官方来源：全国人大网站、最高法网站、司法部网站
- 第三方平台：北大法宝、无讼、Alpha法律智能
- **注意**：务必注明来源URL，便于核验和更新

---

## 六、效果预期

完成上述优化后，系统应具备：

### ✅ 数据质量提升
- 去除重复和近重复数据，提升数据多样性
- 法律引用准确，可追溯到具体条文
- 包含时效性和地域信息，避免引用废止法律

### ✅ 检索能力增强
- 元数据丰富，支持按法律、条文号、地域精确过滤
- 检索结果包含完整来源信息
- 支持法条查询和概念咨询的差异化召回

### ✅ 答案可信度提高
- 每个答案附带法律依据和条文出处
- 明确适用条件和例外情形
- 对无法回答的问题能够正确拒答

### ✅ 持续优化闭环
- 独立测试集固定，可重复评测
- 记录错误案例，转化为新训练样本
- 支持A/B测试对比优化效果

---

## 七、后续计划

1. **增加BM25稀疏检索**（当前只有dense向量）
   - 法律名称、条文号对关键词敏感
   - 实现真正的混合检索：BM25 + Dense + RRF

2. **建立法律知识图谱**
   - 条文之间的引用关系
   - 法律概念的层级关系
   - 支持"相关条文推荐"

3. **细粒度意图分类**
   - 当前只有"法条查询"和"法律咨询"
   - 扩展到13类细分意图

4. **用户画像和个性化**
   - 根据用户地域推荐地方法规
   - 根据历史问题推断咨询场景

---

## 联系与支持

如有问题，请检查：
1. `base/logger.py` 中的日志输出
2. MySQL连接配置是否正确
3. Milvus服务是否正常运行

祝数据优化顺利！
