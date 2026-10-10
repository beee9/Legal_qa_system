#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author  : Vincent
@Time    : 2026/6/23 16:55
@File    : bert_csl_0623.py
@Function :
"""
import json
import os
import numpy as np
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
# 1. 数据集定义
# =====================
class JsonlDataset(Dataset):
    def __init__(self, file_path, tokenizer, label2id, max_length=128):
        self.data = []
        self.tokenizer = tokenizer
        self.label2id = label2id
        self.max_length = max_length

        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                item = json.loads(line.strip())
                self.data.append(item)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]
        text = item["query"]
        label = self.label2id[item["label"]]

        encoding = self.tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=self.max_length
        )

        encoding["labels"] = label
        return {k: torch.tensor(v) for k, v in encoding.items()}


# =====================
# 2. 分类器封装
# =====================
class BertTextClassifier:

    def __init__(
            self,
            model_name="bert-base-chinese",
            num_labels=2,
            model_dir="./model",
            device=None
    ):
        self.model_name = model_name
        self.model_dir = model_dir

        self.label2id = {
            "通用知识": 0,
            "专业咨询": 1
        }
        self.id2label = {v: k for k, v in self.label2id.items()}

        # 自动设备选择（支持CPU/GPU/MPS）
        if device:
            self.device = device
        else:
            if torch.cuda.is_available():
                self.device = "cuda"
            elif torch.backends.mps.is_available():
                self.device = "mps"
            else:
                self.device = "cpu"

        print(f"Using device: {self.device}")

        self.tokenizer = BertTokenizer.from_pretrained(model_name)

        self.model = BertForSequenceClassification.from_pretrained(
            model_name,
            num_labels=num_labels,
            id2label=self.id2label,
            label2id=self.label2id
        ).to(self.device)

    # =====================
    # 3. 训练
    # =====================
    def train(
            self,
            train_file,
            eval_file,
            output_dir="./output",
            epochs=3,
            batch_size=16,
            learning_rate=2e-5
    ):

        train_dataset = JsonlDataset(train_file, self.tokenizer, self.label2id)
        eval_dataset = JsonlDataset(eval_file, self.tokenizer, self.label2id)

        training_args = TrainingArguments(
            output_dir=output_dir,
            eval_strategy="epoch",
            save_strategy="epoch",
            logging_dir=f"{output_dir}/logs",
            learning_rate=learning_rate,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            num_train_epochs=epochs,
            load_best_model_at_end=True,
            metric_for_best_model="f1",
            greater_is_better=True,
            save_total_limit=2,
            report_to="tensorboard",  # 启用TensorBoard日志
            logging_steps=10,  # 每10步记录一次日志
        )

        def compute_metrics(eval_pred):
            logits, labels = eval_pred
            preds = np.argmax(logits, axis=1)

            report = classification_report(
                labels,
                preds,
                target_names=list(self.label2id.keys()),
                output_dict=True
            )

            return {
                "accuracy": report["accuracy"],
                "f1": report["weighted avg"]["f1-score"]
            }

        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            # tokenizer=self.tokenizer,
            compute_metrics=compute_metrics
        )

        trainer.train()

        # 保存最佳模型
        trainer.save_model(self.model_dir)
        self.tokenizer.save_pretrained(self.model_dir)

        print("✅ 模型已保存到:", self.model_dir)

    # =====================
    # 4. 加载模型
    # =====================
    def load(self):
        self.tokenizer = BertTokenizer.from_pretrained(self.model_dir)
        self.model = BertForSequenceClassification.from_pretrained(
            self.model_dir
        ).to(self.device)

    # =====================
    # 5. 预测接口
    # =====================
    def predict(self, text):
        self.model.eval()

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=128
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            pred = torch.argmax(logits, dim=1).item()

        return self.id2label[pred]

    # =====================
    # 6. 批量评估
    # =====================
    def evaluate(self, test_file):

        dataset = JsonlDataset(test_file, self.tokenizer, self.label2id)

        preds = []
        labels = []

        self.model.eval()

        for item in dataset:
            label = item["labels"].item()

            inputs = {
                "input_ids": item["input_ids"].unsqueeze(0).to(self.device),
                "attention_mask": item["attention_mask"].unsqueeze(0).to(self.device)
            }

            with torch.no_grad():
                logits = self.model(**inputs).logits
                pred = torch.argmax(logits, dim=1).item()

            preds.append(pred)
            labels.append(label)

        # 分类报告
        report = classification_report(
            labels,
            preds,
            target_names=list(self.label2id.keys())
        )

        # 混淆矩阵
        cm = confusion_matrix(labels, preds)

        print("===== Classification Report =====")
        print(report)

        print("===== Confusion Matrix =====")
        print(cm)

        return report, cm


def main():
    # =====================
    # 1. 参数配置（直接在这里改）
    # =====================
    config = {
        # 数据路径
        "train_file": "../classify_data/model_generate_0623.jsonl",
        "eval_file": "../classify_data/model_generic_5000.json",
        "test_file": "../classify_data/model_generic_5000.json",  # 可选

        # 模型参数
        "model_name": "/Users/chan/projects/models/bert-base-chinese",
        "model_dir": "./query_cls",
        "output_dir": "./output",

        # 训练参数
        "epochs": 5,
        "batch_size": 16,
        "learning_rate": 2e-5,

        # 设备（None=自动选择 cuda/mps/cpu）
        "device": None
    }

    # =====================
    # 2. 初始化模型
    # =====================
    classifier = BertTextClassifier(
        model_name=config["model_name"],
        model_dir=config["model_dir"],
        device=config["device"]
    )

    # =====================
    # 3. 开始训练
    # =====================
    classifier.train(
        train_file=config["train_file"],
        eval_file=config["eval_file"],
        output_dir=config["output_dir"],
        epochs=config["epochs"],
        batch_size=config["batch_size"],
        learning_rate=config["learning_rate"]
    )

    # =====================
    # 4. 训练后评估（可选）
    # =====================
    if config["test_file"]:
        classifier.load()
        classifier.evaluate(config["test_file"])

    # =====================
    # 5. 简单预测测试
    # =====================
    test_query = "黑马程序员课程多少钱？"
    result = classifier.predict(test_query)

    print("\n===== Demo Prediction =====")
    print(f"输入: {test_query}")
    print(f"预测: {result}")

    # =====================
    # 6. TensorBoard启动提示
    # =====================
    print("\n===== TensorBoard 使用说明 =====")
    print(f"运行以下命令查看训练曲线:")
    print(f"tensorboard --logdir={config['output_dir']}/logs")
    print("然后在浏览器中访问: http://localhost:6006")


if __name__ == "__main__":
    main()
