"""
法律意图分类器 - 集成到 Legal_qa_system

三分类：
1. 法条查询 (label_id=0) → BM25 精确检索
2. 法律咨询 (label_id=1) → RAG 向量检索
3. 通用问题 (label_id=2) → 直连 LLM
"""
import sys
import torch
from pathlib import Path
from transformers import BertTokenizer, BertForSequenceClassification

# 添加项目根目录到 sys.path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from base import logger


class LegalIntentClassifier:
    """法律意图分类器（生产版）"""

    def __init__(self, model_path=None):
        """
        初始化分类器

        Args:
            model_path: 训练好的模型路径。如果为 None，使用默认路径
        """
        if model_path is None:
            model_path = Path(__file__).parent / "legal_intent_classifier" / "final_model"

        self.model_path = Path(model_path)

        # 确定设备
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"法律意图分类器使用设备: {self.device}")

        # 标签映射
        self.label_map = {
            "法条查询": 0,
            "法律咨询": 1,
            "通用问题": 2
        }
        self.id2label = {
            0: "法条查询",
            1: "法律咨询",
            2: "通用问题"
        }

        # 加载模型
        self.tokenizer = None
        self.model = None
        self.load_model()

    def load_model(self):
        """加载已训练的模型"""
        try:
            if not self.model_path.exists():
                logger.warning(f"模型路径不存在: {self.model_path}")
                logger.warning("分类器将禁用，所有查询默认为'法律咨询'")
                return

            logger.info(f"加载法律意图分类器: {self.model_path}")
            self.tokenizer = BertTokenizer.from_pretrained(self.model_path)
            self.model = BertForSequenceClassification.from_pretrained(self.model_path)
            self.model.to(self.device)
            self.model.eval()
            logger.info("法律意图分类器加载成功")

        except Exception as e:
            logger.error(f"加载模型失败: {e}")
            logger.warning("分类器将禁用，所有查询默认为'法律咨询'")
            self.model = None
            self.tokenizer = None

    def predict_intent(self, query):
        """
        预测查询意图

        Args:
            query: 用户查询文本

        Returns:
            str: "法条查询" / "法律咨询" / "通用问题"
        """
        # 如果模型未加载，默认返回法律咨询
        if self.model is None or self.tokenizer is None:
            logger.debug(f"分类器未加载，查询'{query}'默认为'法律咨询'")
            return "法律咨询"

        try:
            # 预处理
            encoding = self.tokenizer(
                query,
                truncation=True,
                padding=True,
                max_length=128,
                return_tensors="pt"
            )
            encoding = {k: v.to(self.device) for k, v in encoding.items()}

            # 预测
            with torch.no_grad():
                outputs = self.model(**encoding)
                prediction = torch.argmax(outputs.logits, dim=1).item()

            # 返回类别
            intent = self.id2label[prediction]
            logger.debug(f"查询: '{query}' -> 意图: {intent}")
            return intent

        except Exception as e:
            logger.error(f"意图分类失败: {e}")
            return "法律咨询"  # 失败时默认返回法律咨询

    def batch_predict(self, queries):
        """批量预测"""
        results = []
        for query in queries:
            intent = self.predict_intent(query)
            results.append({"query": query, "intent": intent})
        return results


# 全局单例（避免重复加载模型）
_classifier_instance = None


def get_classifier():
    """获取全局分类器单例"""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = LegalIntentClassifier()
    return _classifier_instance


if __name__ == "__main__":
    # 测试分类器
    classifier = LegalIntentClassifier()

    test_cases = [
        # 法条查询
        ("民法典第509条是什么", "法条查询"),
        ("劳动法第36条内容", "法条查询"),
        ("查一下合同法第52条", "法条查询"),

        # 法律咨询
        ("老板拖欠工资怎么办", "法律咨询"),
        ("被公司辞退能要求赔偿吗", "法律咨询"),
        ("什么是善意取得", "法律咨询"),
        ("诉讼时效是多久", "法律咨询"),

        # 通用问题
        ("今天天气怎么样", "通用问题"),
        ("你好", "通用问题"),
        ("Python怎么学", "通用问题"),
    ]

    print("=" * 70)
    print("法律意图分类器测试")
    print("=" * 70)

    correct = 0
    for query, expected in test_cases:
        predicted = classifier.predict_intent(query)
        is_correct = predicted == expected
        correct += is_correct

        status = "✓" if is_correct else "✗"
        print(f"{status} {query:30s} -> {predicted:10s} (期望: {expected})")

    accuracy = correct / len(test_cases) * 100
    print("=" * 70)
    print(f"准确率: {accuracy:.1f}% ({correct}/{len(test_cases)})")
