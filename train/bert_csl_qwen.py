#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author  : Vincent
@Time    : 2026/4/23 16:31
@File    : bert_csl_qwen.py
@Function :
"""
import json
import os
import torch
import numpy as np
from sklearn.metrics import confusion_matrix, classification_report, accuracy_score, precision_recall_fscore_support
from transformers import (
    BertTokenizer,
    BertForSequenceClassification,
    Trainer,
    TrainingArguments,
    DataCollatorWithPadding
)
from torch.utils.data import Dataset


class TextClassifier:
    def __init__(self, model_name_or_path="bert-base-chinese", num_labels=2, device=None):
        """
        初始化分类器
        :param model_name_or_path: 预训练模型名称或本地路径
        :param num_labels: 分类类别数量
        :param device: 指定设备，默认自动检测
        """
        # 1. 设备自适应逻辑
        if device:
            self.device = torch.device(device)
        else:
            if torch.cuda.is_available():
                self.device = torch.device("cuda")
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self.device = torch.device("mps")  # 适配 Apple Silicon
            else:
                self.device = torch.device("cpu")

        print(f"🚀 使用设备: {self.device}")

        # 2. 加载模型和分词器
        self.tokenizer = BertTokenizer.from_pretrained(model_name_or_path)
        self.model = BertForSequenceClassification.from_pretrained(
            model_name_or_path,
            num_labels=num_labels
        ).to(self.device)

        # 标签映射 (根据实际数据调整)
        self.label_map = {"通用知识": 0, "专业咨询": 1}
        self.id2label = {0: "通用知识", 1: "专业咨询"}

    class CustomDataset(Dataset):
        def __init__(self, data, tokenizer, max_length=128):
            self.data = data
            self.tokenizer = tokenizer
            self.max_length = max_length

        def __len__(self):
            return len(self.data)

        def __getitem__(self, idx):
            item = self.data[idx]
            # 编码文本
            encoding = self.tokenizer(
                item['query'],
                truncation=True,
                padding='max_length',
                max_length=self.max_length,
                return_tensors='pt'
            )
            # 移除批次维度 (Trainer 会自动重新打包)
            item_dict = {key: val.squeeze() for key, val in encoding.items()}
            item_dict['labels'] = torch.tensor(item['label'])
            return item_dict

    def load_data(self, file_path):
        """加载 JSON 数据"""
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        # 确保 label 是数字，如果是字符串则转换
        processed_data = []
        for item in raw_data:
            label = item['label']
            if isinstance(label, str):
                label = self.label_map.get(label, 0)  # 默认归为0类如果找不到
            processed_data.append({"query": item['query'], "label": label})
        return processed_data

    def train(self, train_file, eval_file=None, output_dir="./results", epochs=3, batch_size=16):
        """
        训练模型
        """
        print("📊 正在加载数据...")
        train_data = self.load_data(train_file)
        train_dataset = self.CustomDataset(train_data, self.tokenizer)

        eval_dataset = None
        if eval_file and os.path.exists(eval_file):
            eval_data = self.load_data(eval_file)
            eval_dataset = self.CustomDataset(eval_data, self.tokenizer)

        # 配置训练参数
        training_args = TrainingArguments(
            output_dir=output_dir,
            eval_strategy="epoch" if eval_dataset else "no",
            save_strategy="epoch",
            learning_rate=2e-5,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            num_train_epochs=epochs,
            weight_decay=0.01,
            save_total_limit=1,  # 只保存效果最好的一个检查点
            load_best_model_at_end=True if eval_dataset else False,
            metric_for_best_model="eval_loss" if eval_dataset else None,
            greater_is_better=False if eval_dataset else None,
            logging_dir=f"{output_dir}/logs",
            logging_steps=100,
            report_to="none"  # 关闭 wandb 等报告，避免报错
        )

        # 初始化 Trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            tokenizer=self.tokenizer,
            data_collator=DataCollatorWithPadding(self.tokenizer)
        )

        print("🔥 开始训练...")
        trainer.train()

        # 保存最终模型
        print(f"💾 保存模型到 {output_dir}")
        self.model.save_pretrained(output_dir)
        self.tokenizer.save_pretrained(output_dir)
        print("✅ 训练完成！")

    def predict(self, texts):
        """
        预测接口
        :param texts: 单个字符串或字符串列表
        :return: 预测结果列表
        """
        if isinstance(texts, str):
            texts = [texts]

        self.model.eval()
        results = []

        with torch.no_grad():
            inputs = self.tokenizer(texts, return_tensors="pt", padding=True, truncation=True).to(self.device)
            outputs = self.model(**inputs)
            predictions = torch.argmax(outputs.logits, dim=-1)

            for i, text in enumerate(texts):
                pred_label_id = predictions[i].item()
                results.append({
                    "text": text,
                    "predicted_label": self.id2label[pred_label_id],
                    "label_id": pred_label_id
                })
        return results

    def evaluate(self, eval_file):
        """
        评估模型，输出分类报告和混淆矩阵
        """
        print("📝 正在评估模型...")
        if not os.path.exists(eval_file):
            print("❌ 评估文件不存在")
            return

        data = self.load_data(eval_file)
        texts = [item['query'] for item in data]
        true_labels = [item['label'] for item in data]

        # 获取预测结果
        predictions = self.predict(texts)
        pred_labels = [p['label_id'] for p in predictions]

        # 计算指标
        print("\n--- 分类报告 ---")
        print(classification_report(true_labels, pred_labels,
                                    target_names=[self.id2label[i] for i in sorted(self.id2label.keys())]))

        print("\n--- 混淆矩阵 ---")
        cm = confusion_matrix(true_labels, pred_labels)
        print(cm)

        # 简单可视化混淆矩阵（可选，依赖matplotlib）
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
            plt.figure(figsize=(8, 6))
            sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                        xticklabels=[self.id2label[i] for i in sorted(self.id2label.keys())],
                        yticklabels=[self.id2label[i] for i in sorted(self.id2label.keys())])
            plt.xlabel('预测标签')
            plt.ylabel('真实标签')
            plt.title('混淆矩阵')
            plt.show()
        except ImportError:
            print("提示: 安装 matplotlib 和 seaborn 可查看可视化混淆矩阵")


# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 1. 配置路径 (请修改为你自己的路径)
    MODEL_PATH = "/Users/chan/projects/models/bert-base-chinese"  # 或者本地路径 "./bert-base-chinese"
    TRAIN_DATA = "../classify_data/chatgpt_generate_200_0423.jsonl"
    EVAL_DATA = "../classify_data/chatgpt_generate_200_query.jsonl"
    OUTPUT_DIR = "./my_classifier_model"

    # 2. 准备测试数据 (如果还没有文件，这里创建临时的)
    # 实际使用时请确保 train.json 格式为: [{"query": "...", "label": "通用知识"}, ...]
    if not os.path.exists(TRAIN_DATA):
        dummy_data = [
                         {"query": "Python如何实现快速排序？", "label": "通用知识"},
                         {"query": "今天天气怎么样", "label": "通用知识"},
                         {"query": "Transformer架构中的自注意力机制原理是什么？", "label": "专业咨询"},
                         {"query": "请解释一下量化宽松政策对股市的影响", "label": "专业咨询"}
                     ] * 10  # 复制多份用于演示训练
        with open(TRAIN_DATA, 'w', encoding='utf-8') as f:
            json.dump(dummy_data, f, ensure_ascii=False, indent=2)
        with open(EVAL_DATA, 'w', encoding='utf-8') as f:
            json.dump(dummy_data[:4], f, ensure_ascii=False, indent=2)  # 简单测试集

    # 3. 初始化并训练
    classifier = TextClassifier(model_name_or_path=MODEL_PATH)

    # 开始训练
    classifier.train(
        train_file=TRAIN_DATA,
        eval_file=EVAL_DATA,
        output_dir=OUTPUT_DIR,
        epochs=1,
        batch_size=4
    )

    # 4. 预测测试
    test_text = "Bert模型微调的具体步骤有哪些？"
    result = classifier.predict(test_text)
    print(f"\n🔮 预测结果: {result}")

    # 5. 评估模型
    classifier.evaluate(EVAL_DATA)
