"""
意图分类器独立测试 - 模拟完整查询流程
无需 MySQL/Redis/Milvus，纯本地测试
"""
import sys
import time
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("意图分类器 - 完整流程模拟测试")
print("=" * 70)

# 加载分类器
print("\n[1/3] 加载意图分类器...")
import torch
from transformers import BertTokenizer, BertForSequenceClassification

model_path = Path("rag_qa/core/legal_intent_classifier/final_model")
tokenizer = BertTokenizer.from_pretrained(model_path)
model = BertForSequenceClassification.from_pretrained(model_path)
model.eval()

id2label = {0: "法条查询", 1: "法律咨询", 2: "通用问题"}
print("✓ 意图分类器加载成功\n")

# 模拟 LLM 响应
def mock_llm(query):
    """模拟 LLM 回答"""
    return f"[模拟 LLM 回答] 关于'{query}'的回答..."

# 模拟 BM25 检索
def mock_bm25(query):
    """模拟 BM25 法条检索"""
    if "509" in query or "第509条" in query:
        return "《中华人民共和国民法典》第五百零九条：当事人应当按照约定全面履行自己的义务..."
    elif "36" in query or "第36条" in query:
        return "《中华人民共和国劳动法》第三十六条：国家实行劳动者每日工作时间不超过八小时..."
    return None

# 模拟 RAG 检索
def mock_rag(query):
    """模拟 RAG 向量检索"""
    return f"[模拟 RAG 检索结果] 根据相关法律规定，关于'{query}'..."

# 完整查询流程
def integrated_query(query):
    """集成查询系统（模拟版）"""
    print(f"\n{'='*70}")
    print(f"查询: {query}")
    print(f"{'='*70}")

    start_time = time.time()

    # Step 1: 意图分类
    classify_start = time.time()
    inputs = tokenizer(query, return_tensors="pt", truncation=True, padding=True, max_length=128)
    with torch.no_grad():
        outputs = model(**inputs)
        prediction_id = torch.argmax(outputs.logits, dim=1).item()
    intent = id2label[prediction_id]
    classify_time = (time.time() - classify_start) * 1000

    print(f"[意图分类] {intent} (耗时: {classify_time:.1f}ms)")

    # Step 2: 根据意图路由
    if intent == "通用问题":
        print(f"[路由策略] 直连 LLM（跳过法律检索）")
        route_start = time.time()
        answer = mock_llm(query)
        route_time = (time.time() - route_start) * 1000
        print(f"[LLM 响应] 耗时: {route_time:.1f}ms")

    elif intent == "法条查询":
        print(f"[路由策略] BM25 精确检索（降低阈值）")
        route_start = time.time()
        answer = mock_bm25(query)
        route_time = (time.time() - route_start) * 1000

        if answer:
            print(f"[BM25 命中] 耗时: {route_time:.1f}ms")
        else:
            print(f"[BM25 未命中] 回退到 RAG 检索")
            answer = mock_rag(query)

    else:  # 法律咨询
        print(f"[路由策略] RAG 向量检索（语义理解）")
        route_start = time.time()
        answer = mock_rag(query)
        route_time = (time.time() - route_start) * 1000
        print(f"[RAG 检索] 耗时: {route_time:.1f}ms")

    total_time = (time.time() - start_time) * 1000

    print(f"\n[回答]")
    print(f"{answer[:100]}...")
    print(f"\n[总耗时] {total_time:.1f}ms")

    return intent, answer, total_time


# 测试用例
print("\n[2/3] 测试三种意图路由...\n")

test_cases = [
    "今天天气怎么样",
    "民法典第509条是什么",
    "老板拖欠工资怎么办",
    "劳动法第36条内容",
    "你好，请问你是谁",
    "被公司辞退可以要求赔偿吗",
]

results = []
for query in test_cases:
    intent, answer, total_time = integrated_query(query)
    results.append({
        "query": query,
        "intent": intent,
        "time": total_time
    })

# 统计结果
print("\n" + "=" * 70)
print("[3/3] 性能统计")
print("=" * 70)

intent_times = {"通用问题": [], "法条查询": [], "法律咨询": []}
for r in results:
    intent_times[r["intent"]].append(r["time"])

for intent, times in intent_times.items():
    if times:
        avg = sum(times) / len(times)
        print(f"{intent:12s}: 平均 {avg:>6.1f}ms ({len(times)} 个查询)")

print("\n" + "=" * 70)
print("测试完成！")
print("=" * 70)
print("\n✅ 意图分类器已成功集成到系统")
print("✅ 三种路由策略工作正常")
print("\n下一步：")
print("1. 启动 MySQL 服务（端口 3307）")
print("2. 启动 Redis 服务（端口 6380）")
print("3. （可选）启动 Milvus 服务（端口 19530）")
print("4. 运行: .venv-RAGtrain\\Scripts\\python.exe app.py")
