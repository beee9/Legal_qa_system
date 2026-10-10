"""
法律查询意图分类器 - 基于 BERT

三分类：
1. 法条查询 - 查询具体法条内容（BM25 精确检索）
2. 法律咨询 - 实际法律问题咨询（RAG 语义检索）
3. 通用问题 - 非法律问题（直连 LLM）
"""
import json
import os
import sys
import torch
import numpy as np
from pathlib import Path
from transformers import BertTokenizer, BertForSequenceClassification
from transformers import Trainer, TrainingArguments
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

# 添加项目根目录到 sys.path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

# 尝试导入 logger，如果失败则使用 logging
try:
    from base import logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


class LegalQueryClassifier:
    """法律查询意图分类器"""

    def __init__(self, model_path=None):
        """
        初始化分类器

        Args:
            model_path: 已训练模型路径。如果为 None，则使用默认路径
        """
        # 默认模型路径
        if model_path is None:
            model_path = Path(__file__).parent / "legal_intent_classifier"

        self.model_path = Path(model_path)
        self.tokenizer = None
        self.model = None

        # 确定设备
        self.device = (
            "cuda" if torch.cuda.is_available() else
            "mps" if torch.backends.mps.is_available() else
            "cpu"
        )
        logger.info(f"使用设备: {self.device}")

        # 标签映射
        self.label_map = {
            "法条查询": 0,
            "法律咨询": 1,
            "通用问题": 2
        }
        self.id2label = {v: k for k, v in self.label_map.items()}

        # 尝试加载已有模型
        if self.model_path.exists():
            self.load_model()
        else:
            logger.warning(f"模型路径 {self.model_path} 不存在，需要先训练模型")

    def load_model(self):
        """加载已训练的模型"""
        try:
            self.tokenizer = BertTokenizer.from_pretrained(self.model_path)
            self.model = BertForSequenceClassification.from_pretrained(
                self.model_path,
                num_labels=3
            )
            self.model.to(self.device)
            self.model.eval()
            logger.info(f"成功加载模型: {self.model_path}")
        except Exception as e:
            logger.error(f"加载模型失败: {e}")
            raise

    def save_model(self, output_dir=None):
        """保存模型"""
        if output_dir is None:
            output_dir = self.model_path

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        self.model.save_pretrained(output_dir)
        self.tokenizer.save_pretrained(output_dir)
        logger.info(f"模型已保存到: {output_dir}")

    def preprocess_data(self, texts, labels=None):
        """预处理数据为 BERT 输入格式"""
        encodings = self.tokenizer(
            texts,
            truncation=True,
            padding=True,
            max_length=128,
            return_tensors="pt"
        )

        if labels is not None:
            label_ids = [self.label_map[label] for label in labels]
            return encodings, label_ids
        else:
            return encodings

    def create_dataset(self, encodings, labels):
        """创建 PyTorch 数据集"""
        class Dataset(torch.utils.data.Dataset):
            def __init__(self, encodings, labels):
                self.encodings = encodings
                self.labels = labels

            def __getitem__(self, idx):
                item = {key: val[idx] for key, val in self.encodings.items()}
                item["labels"] = torch.tensor(self.labels[idx])
                return item

            def __len__(self):
                return len(self.labels)

        return Dataset(encodings, labels)

    def load_training_data(self, data_file):
        """加载训练数据"""
        data_path = Path(data_file)
        if not data_path.exists():
            raise FileNotFoundError(f"数据文件不存在: {data_file}")

        with open(data_path, 'r', encoding='utf-8') as f:
            data = [json.loads(line) for line in f]

        texts = [item["query"] for item in data]
        labels = [item["label"] for item in data]

        return texts, labels

    def train_model(self, train_file, val_file=None, epochs=3, batch_size=16, learning_rate=2e-5):
        """
        训练 BERT 分类模型

        Args:
            train_file: 训练数据文件路径
            val_file: 验证数据文件路径（可选）
            epochs: 训练轮数
            batch_size: 批次大小
            learning_rate: 学习率
        """
        logger.info("=" * 60)
        logger.info("开始训练法律意图分类器")
        logger.info("=" * 60)

        # 初始化 tokenizer 和模型
        # 优先使用本地 BERT 模型
        local_bert = Path(r"E:\bert_model")
        if local_bert.exists():
            bert_base = str(local_bert)
            logger.info(f"使用本地 BERT 模型: {bert_base}")
        else:
            bert_base = "bert-base-chinese"
            logger.info(f"使用 Hugging Face BERT 模型: {bert_base}")

        self.tokenizer = BertTokenizer.from_pretrained(bert_base)
        self.model = BertForSequenceClassification.from_pretrained(
            bert_base,
            num_labels=3
        )
        self.model.to(self.device)

        # 加载训练数据
        logger.info(f"加载训练数据: {train_file}")
        train_texts, train_labels = self.load_training_data(train_file)
        logger.info(f"训练样本数: {len(train_texts)}")

        # 预处理
        train_encodings, train_label_ids = self.preprocess_data(train_texts, train_labels)
        train_dataset = self.create_dataset(train_encodings, train_label_ids)

        # 加载验证数据
        if val_file:
            logger.info(f"加载验证数据: {val_file}")
            val_texts, val_labels = self.load_training_data(val_file)
            logger.info(f"验证样本数: {len(val_texts)}")
            val_encodings, val_label_ids = self.preprocess_data(val_texts, val_labels)
            val_dataset = self.create_dataset(val_encodings, val_label_ids)
        else:
            # 如果没有提供验证集，从训练集分割 10%
            logger.info("未提供验证集，从训练集分割 10%")
            train_texts, val_texts, train_labels, val_labels = train_test_split(
                train_texts, train_labels, test_size=0.1, random_state=42
            )
            train_encodings, train_label_ids = self.preprocess_data(train_texts, train_labels)
            val_encodings, val_label_ids = self.preprocess_data(val_texts, val_labels)
            train_dataset = self.create_dataset(train_encodings, train_label_ids)
            val_dataset = self.create_dataset(val_encodings, val_label_ids)

        # 设置训练参数
        output_dir = self.model_path.parent / "training_output"
        training_args = TrainingArguments(
            output_dir=str(output_dir),
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            learning_rate=learning_rate,
            warmup_steps=500,
            weight_decay=0.01,
            logging_dir=str(output_dir / "logs"),
            logging_steps=50,
            eval_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            save_total_limit=2,
            metric_for_best_model="eval_loss",
            fp16=torch.cuda.is_available(),  # 仅在 GPU 可用时启用混合精度
        )

        # 定义评估指标
        def compute_metrics(eval_pred):
            logits, labels = eval_pred
            predictions = np.argmax(logits, axis=-1)
            accuracy = accuracy_score(labels, predictions)
            return {"accuracy": accuracy}

        # 初始化 Trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            compute_metrics=compute_metrics
        )

        # 开始训练
        logger.info("开始训练...")
        trainer.train()

        # 保存最佳模型
        logger.info("训练完成，保存模型...")
        self.save_model()

        # 在验证集上评估
        logger.info("在验证集上评估...")
        self.evaluate_model(val_texts, val_labels)

        logger.info("=" * 60)
        logger.info("训练完成！")
        logger.info("=" * 60)

    def evaluate_model(self, texts, labels):
        """评估模型性能"""
        logger.info("开始评估模型...")

        # 预处理
        encodings = self.preprocess_data(texts)
        label_ids = [self.label_map[label] for label in labels]
        dataset = self.create_dataset(encodings, label_ids)

        # 预测
        trainer = Trainer(model=self.model)
        predictions = trainer.predict(dataset)
        pred_labels = np.argmax(predictions.predictions, axis=-1)

        # 打印分类报告
        logger.info("\n分类报告:")
        report = classification_report(
            label_ids,
            pred_labels,
            target_names=["法条查询", "法律咨询", "通用问题"],
            digits=4
        )
        logger.info(f"\n{report}")

        # 打印混淆矩阵
        logger.info("\n混淆矩阵:")
        cm = confusion_matrix(label_ids, pred_labels)
        logger.info(f"\n{cm}")

        # 计算准确率
        accuracy = accuracy_score(label_ids, pred_labels)
        logger.info(f"\n总体准确率: {accuracy:.4f}")

        return accuracy

    def predict_category(self, query):
        """
        预测查询类别

        Args:
            query: 用户查询文本

        Returns:
            str: 预测的类别（"法条查询" / "法律咨询" / "通用问题"）
        """
        if self.model is None:
            logger.error("模型未加载，请先训练或加载模型")
            return "法律咨询"  # 默认返回法律咨询

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
        self.model.eval()
        with torch.no_grad():
            outputs = self.model(**encoding)
            prediction = torch.argmax(outputs.logits, dim=1).item()

        # 返回类别
        category = self.id2label[prediction]
        logger.debug(f"查询: '{query}' -> 分类: {category}")
        return category

    def batch_predict(self, queries):
        """批量预测"""
        results = []
        for query in queries:
            category = self.predict_category(query)
            results.append({"query": query, "category": category})
        return results


def main():
    """训练脚本"""
    import argparse

    parser = argparse.ArgumentParser(description="法律意图分类器训练")
    parser.add_argument("--train", action="store_true", help="训练模型")
    parser.add_argument("--test", action="store_true", help="测试模型")
    parser.add_argument("--epochs", type=int, default=3, help="训练轮数")
    parser.add_argument("--batch_size", type=int, default=16, help="批次大小")
    args = parser.parse_args()

    # 数据路径
    data_dir = Path(__file__).parent / "training_data"
    train_file = data_dir / "train.jsonl"
    test_file = data_dir / "test.jsonl"

    # 初始化分类器
    classifier = LegalQueryClassifier()

    if args.train:
        # 训练模型
        classifier.train_model(
            train_file=train_file,
            val_file=test_file,
            epochs=args.epochs,
            batch_size=args.batch_size
        )

    if args.test or not args.train:
        # 测试模型
        print("\n" + "=" * 60)
        print("测试模型")
        print("=" * 60)

        test_queries = [
            "民法典第509条是什么",
            "劳动法第36条内容",
            "老板拖欠工资怎么办",
            "被辞退可以要求赔偿吗",
            "今天天气怎么样",
            "你好",
            "什么是善意取得",
            "诉讼时效是多久",
            "合同违约需要承担什么责任",
            "人工智能是什么",
        ]

        for query in test_queries:
            category = classifier.predict_category(query)
            print(f"查询: {query:30s} -> {category}")


if __name__ == "__main__":
    main()
