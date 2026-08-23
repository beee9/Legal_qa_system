#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author  : Vincent
@Time    : 2026/3/21 15:29
@File    : chatgpt_train_bert.py
@Function :
"""
import json
import os
import torch
import numpy as np
from torch.utils.data import Dataset
from transformers import (
    BertTokenizer,
    BertForSequenceClassification,
    Trainer,
    TrainingArguments
)
from sklearn.metrics import classification_report, confusion_matrix

# =========================
# 标签映射（法律三分类）
# =========================
LABEL_MAP = {"法条查询": 0, "法律咨询": 1, "通用问题": 2}
ID2LABEL = {0: "法条查询", 1: "法律咨询", 2: "通用问题"}


# =========================
# 数据集
# =========================
class BertClsDataset(Dataset):
    def __init__(self, file_path, tokenizer, max_length=128):
        # 预 tokenize：初始化时一次性编码所有样本，避免每步重复 tokenize 造成的训练瓶颈
        self.input_ids = []
        self.attention_masks = []
        self.labels = []

        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line.strip())
                enc = tokenizer(
                    data["query"],
                    truncation=True,
                    padding="max_length",
                    max_length=max_length
                )
                self.input_ids.append(enc["input_ids"])
                self.attention_masks.append(enc["attention_mask"])
                self.labels.append(LABEL_MAP[data["label"]])

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return {
            "input_ids": torch.tensor(self.input_ids[idx], dtype=torch.long),
            "attention_mask": torch.tensor(self.attention_masks[idx], dtype=torch.long),
            "labels": torch.tensor(self.labels[idx], dtype=torch.long)
        }


# =========================
# 主类（训练 + 推理）
# =========================
class BertClassifier:
    def __init__(self, model_path):
        self.model_path = model_path

        self.tokenizer = BertTokenizer.from_pretrained(model_path)
        # ignore_mismatched_sizes: 初始化模型是2类分类头，重建为3类（encoder 权重正常继承）
        self.model = BertForSequenceClassification.from_pretrained(
            model_path,
            num_labels=3,
            ignore_mismatched_sizes=True
        )

    # =========================
    # 构建数据集
    # =========================
    def load_data(self, train_path, dev_path, test_path):
        self.train_dataset = BertClsDataset(train_path, self.tokenizer)
        self.dev_dataset = BertClsDataset(dev_path, self.tokenizer)
        self.test_dataset = BertClsDataset(test_path, self.tokenizer)

    # =========================
    # 评估指标
    # =========================
    def compute_metrics(self, eval_pred):
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=1)

        report = classification_report(
            labels,
            preds,
            target_names=["法条查询", "法律咨询", "通用问题"],
            output_dict=True
        )

        return {
            "accuracy": report["accuracy"],
            "f1": report["weighted avg"]["f1-score"]
        }

    # =========================
    # 训练
    # =========================
    def train(self, output_dir="./output"):
        training_args = TrainingArguments(
            output_dir=output_dir,
            learning_rate=2e-5,
            per_device_train_batch_size=16,
            per_device_eval_batch_size=16,
            num_train_epochs=3,
            eval_strategy="epoch",
            save_strategy="epoch",
            logging_dir="./logs",
            load_best_model_at_end=True,
            metric_for_best_model="f1"
        )

        self.trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=self.train_dataset,
            eval_dataset=self.dev_dataset,
            tokenizer=self.tokenizer,
            compute_metrics=self.compute_metrics
        )

        self.trainer.train()

        # 保存模型
        self.trainer.save_model(output_dir + "/best_model")
        self.tokenizer.save_pretrained(output_dir + "/best_model")

    # =========================
    # 测试评估
    # =========================
    def evaluate(self):
        preds_output = self.trainer.predict(self.test_dataset)

        logits = preds_output.predictions
        labels = preds_output.label_ids
        preds = np.argmax(logits, axis=1)

        print("\n===== Classification Report =====")
        print(classification_report(labels, preds, target_names=["法条查询", "法律咨询", "通用问题"]))

        print("\n===== Confusion Matrix =====")
        print(confusion_matrix(labels, preds))

    # =========================
    # 加载模型（推理用）
    # =========================
    def load_model(self, model_dir):
        self.tokenizer = BertTokenizer.from_pretrained(model_dir)
        self.model = BertForSequenceClassification.from_pretrained(model_dir)
        self.model.eval()

    # =========================
    # 推理
    # =========================
    def predict(self, text):
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=128
        )

        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            pred = torch.argmax(logits, dim=1).item()

        return ID2LABEL[pred]


# =========================
# 主函数
# =========================
if __name__ == "__main__":
    # 用原项目已训练的教育分类器作为初始化（encoder 继承中文 BERT，分类头重建为3类）
    model_path = r"E:\陈杰\Itcast_qa_system\rag_qa\core\bert_query_classifier"

    classifier = BertClassifier(model_path)

    # 1. 加载数据（法律三分类语料，用绝对路径避免相对路径歧义）
    data_dir = r"E:\陈杰\Legal_qa_system\rag_qa\classify_data"
    classifier.load_data(
        train_path=os.path.join(data_dir, "legal_train.jsonl"),
        dev_path=os.path.join(data_dir, "legal_dev.jsonl"),
        test_path=os.path.join(data_dir, "legal_test.jsonl")
    )

    # 2. 训练（输出到新项目 bert_query_classifier）
    classifier.train(output_dir=r"E:\陈杰\Legal_qa_system\rag_qa\core\bert_query_classifier")

    # 3. 测试评估
    classifier.evaluate()

    # 4. 推理测试
    classifier.load_model(r"E:\陈杰\Legal_qa_system\rag_qa\core\bert_query_classifier\best_model")

    text = "民法典第五百零九条是什么？"
    print("\n预测结果：", classifier.predict(text))
    print("推理测试2 - 合同违约怎么办？：", classifier.predict("合同违约了一般怎么处理？"))
    print("推理测试3 - 你好：", classifier.predict("你好"))
