"""
法律意图分类器训练脚本（独立版本，避免复杂依赖）
"""
import json
import torch
import numpy as np
from pathlib import Path
from transformers import BertTokenizer, BertForSequenceClassification
from transformers import Trainer, TrainingArguments, TrainerCallback
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score


class LegalIntentTrainer:
    """法律意图分类器训练器"""

    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"使用设备: {self.device}")

        self.label_map = {
            "法条查询": 0,
            "法律咨询": 1,
            "通用问题": 2
        }
        self.id2label = {v: k for k, v in self.label_map.items()}

    def load_data(self, file_path):
        """加载训练数据"""
        print(f"加载数据: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = [json.loads(line) for line in f]

        texts = [item["query"] for item in data]
        labels = [self.label_map[item["label"]] for item in data]

        print(f"  样本数: {len(texts)}")
        return texts, labels

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

    def train(self, train_file, test_file, output_dir, epochs=2, batch_size=8):
        """训练模型"""
        print("=" * 70)
        print("开始训练法律意图分类器")
        print("=" * 70)

        # 1. 加载 BERT 模型
        local_bert = Path(r"E:\bert_model")
        if local_bert.exists():
            print(f"使用本地 BERT: {local_bert}")
            bert_path = str(local_bert)
        else:
            print("使用在线 bert-base-chinese")
            bert_path = "bert-base-chinese"

        print("初始化 tokenizer...")
        tokenizer = BertTokenizer.from_pretrained(bert_path)

        print("初始化模型...")
        model = BertForSequenceClassification.from_pretrained(
            bert_path,
            num_labels=3,
            problem_type="single_label_classification"
        )
        model.to(self.device)

        # 2. 加载训练数据
        train_texts, train_labels = self.load_data(train_file)
        test_texts, test_labels = self.load_data(test_file)

        # 3. 预处理
        print("\n预处理数据...")
        train_encodings = tokenizer(
            train_texts,
            truncation=True,
            padding=True,
            max_length=128,
            return_tensors="pt"
        )
        test_encodings = tokenizer(
            test_texts,
            truncation=True,
            padding=True,
            max_length=128,
            return_tensors="pt"
        )

        train_dataset = self.create_dataset(train_encodings, train_labels)
        test_dataset = self.create_dataset(test_encodings, test_labels)

        # 4. 训练配置
        output_path = Path(output_dir)
        training_args = TrainingArguments(
            output_dir=str(output_path / "checkpoints"),
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            learning_rate=2e-5,
            warmup_steps=500,
            weight_decay=0.01,
            logging_dir=str(output_path / "logs"),
            logging_steps=50,
            eval_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            save_total_limit=2,
            metric_for_best_model="accuracy",
            fp16=torch.cuda.is_available(),
        )

        # 5. 定义评估指标
        def compute_metrics(eval_pred):
            logits, labels = eval_pred
            predictions = np.argmax(logits, axis=-1)
            accuracy = accuracy_score(labels, predictions)
            return {"accuracy": accuracy}

        # 6. 创建 Trainer
        print("\n开始训练...")
        print(f"  训练轮数: {epochs}")
        print(f"  批次大小: {batch_size}")
        print(f"  训练样本: {len(train_texts)}")
        print(f"  测试样本: {len(test_texts)}")
        print("-" * 70)

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=test_dataset,
            compute_metrics=compute_metrics
        )

        # 7. 开始训练
        trainer.train()

        # 8. 评估
        print("\n" + "=" * 70)
        print("在测试集上评估...")
        print("=" * 70)

        predictions_output = trainer.predict(test_dataset)
        pred_labels = np.argmax(predictions_output.predictions, axis=-1)

        # 分类报告
        print("\n分类报告:")
        print(classification_report(
            test_labels,
            pred_labels,
            target_names=["法条查询", "法律咨询", "通用问题"],
            digits=4
        ))

        # 混淆矩阵
        print("\n混淆矩阵:")
        cm = confusion_matrix(test_labels, pred_labels)
        print(cm)

        # 准确率
        accuracy = accuracy_score(test_labels, pred_labels)
        print(f"\n总体准确率: {accuracy:.4f}")

        # 9. 保存最终模型
        final_model_path = output_path / "final_model"
        final_model_path.mkdir(parents=True, exist_ok=True)

        print(f"\n保存模型到: {final_model_path}")
        model.save_pretrained(final_model_path)
        tokenizer.save_pretrained(final_model_path)

        print("\n" + "=" * 70)
        print("训练完成！")
        print("=" * 70)
        print(f"模型已保存到: {final_model_path}")

        return final_model_path


def main():
    # 数据路径
    script_dir = Path(__file__).parent
    data_dir = script_dir / "training_data"
    train_file = data_dir / "train.jsonl"
    test_file = data_dir / "test.jsonl"
    output_dir = script_dir / "legal_intent_classifier"

    # 训练
    trainer = LegalIntentTrainer()
    trainer.train(
        train_file=train_file,
        test_file=test_file,
        output_dir=output_dir,
        epochs=2,
        batch_size=8
    )


if __name__ == "__main__":
    main()
