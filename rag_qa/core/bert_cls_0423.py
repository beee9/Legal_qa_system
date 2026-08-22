#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author  : Vincent
@Time    : 2026/4/23 15:44
@File    : bert_cls_0423.py
@Function :
"""
import json
import os
import numpy as np
from typing import List, Dict

import torch
from torch.utils.data import Dataset

from transformers import (
    BertTokenizer,
    BertForSequenceClassification,
    Trainer,
    TrainingArguments
)

from sklearn.metrics import classification_report, confusion_matrix


# =====================
# 数据集定义
# =====================
class JsonDataset(Dataset):
    def __init__(self, data_path, tokenizer, label2id, max_length=128):
        self.data = self.load_data(data_path)
        self.tokenizer = tokenizer
        self.label2id = label2id
        self.max_length = max_length

    def load_data(self, path):
        data = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                data.append(json.loads(line.strip()))
        return data

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]

        encoding = self.tokenizer(
            item["query"],
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_tensors="pt"
        )

        label = self.label2id[item["label"]]

        return {
            "input_ids": encoding["input_ids"].squeeze(),
            "attention_mask": encoding["attention_mask"].squeeze(),
            "labels": torch.tensor(label)
        }


# =====================
# 主模型类
# =====================
class BertTextClassifier:

    def __init__(
            self,
            model_name="bert-base-chinese",
            num_labels=2,
            output_dir="./output",
            label2id=None
    ):
        self.label2id = label2id or {"通用知识": 0, "专业咨询": 1}
        self.id2label = {v: k for k, v in self.label2id.items()}

        self.tokenizer = BertTokenizer.from_pretrained(model_name)

        self.model = BertForSequenceClassification.from_pretrained(
            model_name,
            num_labels=num_labels,
            id2label=self.id2label,
            label2id=self.label2id
        )

        self.output_dir = output_dir

    # =====================
    # 训练
    # =====================
    def train(self, train_path, dev_path, epochs=3, batch_size=16):
        train_dataset = JsonDataset(train_path, self.tokenizer, self.label2id)
        dev_dataset = JsonDataset(dev_path, self.tokenizer, self.label2id)

        training_args = TrainingArguments(
            output_dir=self.output_dir,
            eval_strategy="epoch",
            save_strategy="epoch",
            logging_dir="./logs",
            learning_rate=2e-5,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            num_train_epochs=epochs,
            load_best_model_at_end=True,
            metric_for_best_model="f1",
            save_total_limit=2
        )

        def compute_metrics(eval_pred):
            logits, labels = eval_pred
            preds = np.argmax(logits, axis=1)

            report = classification_report(
                labels, preds,
                target_names=list(self.label2id.keys()),
                output_dict=True
            )

            return {
                "accuracy": report["accuracy"],
                "f1": report["weighted avg"]["f1-score"]
            }

        self.trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=dev_dataset,
            tokenizer=self.tokenizer,
            compute_metrics=compute_metrics
        )

        self.trainer.train()

        # 保存最优模型
        self.trainer.save_model(os.path.join(self.output_dir, "best_model"))
        self.tokenizer.save_pretrained(os.path.join(self.output_dir, "best_model"))

    # =====================
    # 预测
    # =====================
    def predict(self, texts: List[str]):
        inputs = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            return_tensors="pt"
        )

        self.model.eval()
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            preds = torch.argmax(logits, dim=1).cpu().numpy()

        return [self.id2label[p] for p in preds]

    # =====================
    # 评估
    # =====================
    def evaluate(self, test_path):
        dataset = JsonDataset(test_path, self.tokenizer, self.label2id)

        preds = []
        labels = []

        self.model.eval()

        for item in dataset:
            inputs = {
                "input_ids": item["input_ids"].unsqueeze(0),
                "attention_mask": item["attention_mask"].unsqueeze(0)
            }

            with torch.no_grad():
                logits = self.model(**inputs).logits
                pred = torch.argmax(logits, dim=1).item()

            preds.append(pred)
            labels.append(item["labels"].item())

        # 分类报告
        report = classification_report(
            labels, preds,
            target_names=list(self.label2id.keys())
        )

        # 混淆矩阵
        cm = confusion_matrix(labels, preds)

        print("===== 分类报告 =====")
        print(report)

        print("===== 混淆矩阵 =====")
        print(cm)

        return report, cm


# =====================
# 使用示例
# =====================
if __name__ == "__main__":
    classifier = BertTextClassifier(
        model_name="/Users/chan/projects/models/bert-base-chinese",
        output_dir="./model_output"
    )

    # 训练
    classifier.train(
        train_path="../classify_data/chatgpt_generate_200_0423.jsonl",
        dev_path="../classify_data/chatgpt_generate_200_query.jsonl",
        epochs=2
    )

    # 预测
    result = classifier.predict([
        "Python怎么写快速排序？",
        "你们Java培训学费多少？"
    ])
    print(result)

    # 评估
    classifier.evaluate("../classify_data/chatgpt_generate_200_query.jsonl")
