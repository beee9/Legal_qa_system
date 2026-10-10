"""
快速测试意图分类器（命令行版本）
避免依赖问题，直接测试核心功能
"""
import sys
import time
from pathlib import Path

print("=" * 70)
print("法律意图分类器 - 快速测试")
print("=" * 70)

# 直接导入分类器模块
sys.path.insert(0, str(Path(__file__).parent))

import torch
from transformers import BertTokenizer, BertForSequenceClassification

# 加载模型
model_path = Path("rag_qa/core/legal_intent_classifier/final_model")
print(f"\n加载模型: {model_path}")

tokenizer = BertTokenizer.from_pretrained(model_path)
model = BertForSequenceClassification.from_pretrained(model_path)
model.eval()

id2label = {0: "法条查询", 1: "法律咨询", 2: "通用问题"}

print("模型加载成功！\n")

# 测试查询
test_cases = [
    ("今天天气怎么样", "通用问题"),
    ("民法典第509条是什么", "法条查询"),
    ("老板拖欠工资怎么办", "法律咨询"),
    ("劳动法第36条内容", "法条查询"),
    ("你好", "通用问题"),
    ("被辞退可以要求赔偿吗", "法律咨询"),
]

print("开始测试 (包含性能测速)...\n")
print(f"{'查询':<35} | {'意图':<12} | {'耗时':<10} | 状态")
print("-" * 70)

total_time = 0
for query, expected in test_cases:
    start = time.time()

    # 预测
    inputs = tokenizer(query, return_tensors="pt", truncation=True, padding=True, max_length=128)
    with torch.no_grad():
        outputs = model(**inputs)
        prediction_id = torch.argmax(outputs.logits, dim=1).item()

    elapsed = time.time() - start
    total_time += elapsed

    predicted = id2label[prediction_id]
    is_correct = predicted == expected
    status = "OK" if is_correct else "FAIL"

    print(f"{query:<35} | {predicted:<12} | {elapsed*1000:>6.1f}ms | [{status}]")

avg_time = total_time / len(test_cases) * 1000

print("\n" + "=" * 70)
print("测试完成！")
print("=" * 70)
print(f"平均分类耗时: {avg_time:.1f}ms")
print(f"准确率: {sum(1 for q, e in test_cases if id2label[torch.argmax(model(**tokenizer(q, return_tensors='pt', truncation=True, padding=True, max_length=128)).logits, dim=1).item()] == e) / len(test_cases) * 100:.0f}%")

print("\n" + "=" * 70)
print("性能对比（预估）")
print("=" * 70)
print(f"通用问题优化:")
print(f"  优化前: BM25(200ms) + RAG(2000ms) + LLM(500ms) = 2700ms")
print(f"  优化后: 分类({avg_time:.0f}ms) + LLM(500ms) = {avg_time + 500:.0f}ms")
print(f"  提升: {2700 / (avg_time + 500):.1f}倍")
print(f"\n法条查询优化:")
print(f"  优化前: BM25阈值6.0，部分未命中需RAG(2000ms) = ~1500ms平均")
print(f"  优化后: 分类({avg_time:.0f}ms) + BM25阈值3.0(200ms) = {avg_time + 200:.0f}ms")
print(f"  提升: {1500 / (avg_time + 200):.1f}倍")
