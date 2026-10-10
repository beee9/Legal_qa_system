"""
独立测试法律意图分类器
"""
import torch
from pathlib import Path
from transformers import BertTokenizer, BertForSequenceClassification


def test_classifier():
    # 加载模型
    model_path = Path("rag_qa/core/legal_intent_classifier/final_model")

    print("=" * 70)
    print("法律意图分类器测试")
    print("=" * 70)
    print(f"\n加载模型: {model_path}\n")

    tokenizer = BertTokenizer.from_pretrained(model_path)
    model = BertForSequenceClassification.from_pretrained(model_path)
    model.eval()

    # 标签映射
    id2label = {
        0: "法条查询",
        1: "法律咨询",
        2: "通用问题"
    }

    # 测试样例
    test_cases = [
        # 法条查询
        ("民法典第509条是什么", "法条查询"),
        ("劳动法第36条内容", "法条查询"),
        ("查一下合同法第52条", "法条查询"),
        ("民法典第1179条规定", "法条查询"),

        # 法律咨询
        ("老板拖欠工资怎么办", "法律咨询"),
        ("被公司辞退能要求赔偿吗", "法律咨询"),
        ("什么是善意取得", "法律咨询"),
        ("诉讼时效是多久", "法律咨询"),
        ("离婚财产怎么分割", "法律咨询"),
        ("借钱不还可以起诉吗", "法律咨询"),

        # 通用问题
        ("今天天气怎么样", "通用问题"),
        ("你好", "通用问题"),
        ("Python怎么学", "通用问题"),
        ("北京到上海多少公里", "通用问题"),
    ]

    print("开始测试...\n")
    print(f"{'查询':<35} | {'预测':<12} | {'期望':<12} | 结果")
    print("-" * 70)

    correct = 0
    for query, expected in test_cases:
        # 预测
        inputs = tokenizer(query, return_tensors="pt", truncation=True, padding=True, max_length=128)
        with torch.no_grad():
            outputs = model(**inputs)
            prediction_id = torch.argmax(outputs.logits, dim=1).item()

        predicted = id2label[prediction_id]
        is_correct = predicted == expected
        correct += is_correct

        status = "[OK]" if is_correct else "[X]"
        print(f"{query:<35} | {predicted:<12} | {expected:<12} | {status}")

    accuracy = correct / len(test_cases) * 100
    print("\n" + "=" * 70)
    print(f"测试完成！准确率: {accuracy:.1f}% ({correct}/{len(test_cases)})")
    print("=" * 70)

    return accuracy


if __name__ == "__main__":
    test_classifier()
