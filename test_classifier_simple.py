"""
测试法律意图分类器（独立版本）
"""
import torch
from pathlib import Path
from transformers import BertTokenizer, BertForSequenceClassification


def test_classifier():
    """测试分类器"""
    print("=" * 70)
    print("法律意图分类器测试")
    print("=" * 70)

    # 加载模型
    model_path = Path(__file__).parent / "rag_qa" / "core" / "legal_intent_classifier" / "final_model"

    print(f"\n加载模型: {model_path}")
    tokenizer = BertTokenizer.from_pretrained(model_path)
    model = BertForSequenceClassification.from_pretrained(model_path)
    model.eval()

    # 标签映射（注意：Itcast 模型是二分类，我们需要调整）
    # Itcast: 0=通用知识, 1=专业咨询
    # 我们改为三分类逻辑
    id2label = {
        0: "通用问题",
        1: "专业咨询（法律）"
    }

    # 测试样例
    test_cases = [
        # 法条查询类
        "民法典第509条是什么",
        "劳动法第36条内容",
        "民法典第1179条规定了什么",

        # 法律咨询类
        "老板拖欠工资怎么办",
        "公司不签劳动合同违法吗",
        "被辞退可以要求赔偿吗",
        "离婚财产怎么分割",
        "借钱不还可以起诉吗",
        "什么是善意取得",

        # 通用问题类
        "今天天气怎么样",
        "你好",
        "北京到上海多少公里",
        "人工智能是什么",
        "感冒了吃什么药",
    ]

    print("\n" + "=" * 70)
    print("开始测试（Itcast 二分类模型）...")
    print("=" * 70)

    for query in test_cases:
        # 分词
        inputs = tokenizer(query, return_tensors="pt", truncation=True, padding=True, max_length=128)

        # 预测
        with torch.no_grad():
            outputs = model(**inputs)
            prediction = torch.argmax(outputs.logits, dim=1).item()
            probs = torch.softmax(outputs.logits, dim=1)[0]

        category = id2label[prediction]
        confidence = probs[prediction].item() * 100

        print(f"{query:40s} | {category:20s} | 置信度: {confidence:.1f}%")

    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)
    print("\n注意：Itcast 模型是二分类（通用/专业），需要重新训练三分类模型")
    print("      法条查询 和 法律咨询 目前都归为'专业咨询'")


if __name__ == "__main__":
    test_classifier()
