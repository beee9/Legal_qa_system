"""
测试法律意图分类器的效果
"""
import sys
from pathlib import Path

# 添加项目根目录
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from rag_qa.core.legal_query_classifier import LegalQueryClassifier


def test_classifier():
    """测试分类器"""
    print("=" * 70)
    print("法律意图分类器测试")
    print("=" * 70)

    # 加载模型
    classifier_path = project_root / "rag_qa" / "core" / "legal_intent_classifier" / "final_model"

    print(f"\n加载模型: {classifier_path}")
    classifier = LegalQueryClassifier(model_path=classifier_path)

    # 测试样例
    test_cases = [
        # 法条查询
        ("民法典第509条是什么", "法条查询"),
        ("劳动法第36条内容", "法条查询"),
        ("民法典第1179条规定了什么", "法条查询"),
        ("请问劳动合同法第82条", "法条查询"),

        # 法律咨询
        ("老板拖欠工资怎么办", "法律咨询"),
        ("公司不签劳动合同违法吗", "法律咨询"),
        ("被辞退可以要求赔偿吗", "法律咨询"),
        ("离婚财产怎么分割", "法律咨询"),
        ("借钱不还可以起诉吗", "法律咨询"),
        ("什么是善意取得", "法律咨询"),
        ("诉讼时效是多久", "法律咨询"),
        ("合同违约需要承担什么责任", "法律咨询"),

        # 通用问题
        ("今天天气怎么样", "通用问题"),
        ("你好", "通用问题"),
        ("北京到上海多少公里", "通用问题"),
        ("人工智能是什么", "通用问题"),
        ("感冒了吃什么药", "通用问题"),
    ]

    print("\n" + "=" * 70)
    print("开始测试...")
    print("=" * 70)

    correct = 0
    total = len(test_cases)

    for query, expected in test_cases:
        predicted = classifier.predict_category(query)
        is_correct = predicted == expected
        correct += is_correct

        status = "✓" if is_correct else "✗"
        print(f"{status} {query:40s} | 预测: {predicted:10s} | 期望: {expected:10s}")

    accuracy = correct / total * 100
    print("\n" + "=" * 70)
    print(f"准确率: {correct}/{total} = {accuracy:.2f}%")
    print("=" * 70)

    # 详细测试（显示置信度）
    print("\n详细分析（前5个）：")
    for query, expected in test_cases[:5]:
        predicted = classifier.predict_category(query)
        print(f"\n查询: {query}")
        print(f"  预测: {predicted}")
        print(f"  期望: {expected}")


if __name__ == "__main__":
    test_classifier()
