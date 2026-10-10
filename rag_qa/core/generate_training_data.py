"""
法律查询意图分类训练数据生成器

三分类：
1. 法条查询 - 查询具体法条内容（适合 BM25 精确检索）
2. 法律咨询 - 实际法律问题咨询（需要 RAG 语义检索）
3. 通用问题 - 非法律相关的通用问题（直连 LLM）
"""
import json
import pandas as pd
import random
from pathlib import Path

# 设置随机种子
random.seed(42)


def generate_from_existing_data():
    """从现有的 legal_qa_full_enhanced.csv 中提取训练数据"""
    csv_path = Path(__file__).parent.parent.parent / "mysql_qa" / "data" / "legal_qa_full_enhanced.csv"
    df = pd.read_csv(csv_path)

    training_data = []

    # 遍历现有数据，自动分类
    for _, row in df.iterrows():
        question = row['question']

        # 分类规则
        if any(keyword in question for keyword in ['第', '条', '款', '项', '编', '章']):
            if '是什么' in question or '内容' in question or '规定' in question:
                label = "法条查询"
            else:
                label = "法律咨询"
        elif any(keyword in question for keyword in ['怎么办', '如何', '能不能', '可以', '应该', '需要']):
            label = "法律咨询"
        else:
            # 默认为法律咨询
            label = "法律咨询"

        training_data.append({
            "query": question,
            "label": label
        })

    return training_data


def generate_manual_samples():
    """手动生成高质量样本（覆盖边界情况）"""
    samples = [
        # === 法条查询（明确查询具体法条内容）===
        {"query": "民法典第509条是什么", "label": "法条查询"},
        {"query": "劳动法第36条内容", "label": "法条查询"},
        {"query": "民法典第1179条规定了什么", "label": "法条查询"},
        {"query": "公司法第三条的具体内容", "label": "法条查询"},
        {"query": "刑法第234条怎么规定的", "label": "法条查询"},
        {"query": "婚姻法关于离婚冷静期的条文", "label": "法条查询"},
        {"query": "合同法第52条原文", "label": "法条查询"},
        {"query": "劳动合同法第82条说的是什么", "label": "法条查询"},
        {"query": "民法典总则编第一百八十八条", "label": "法条查询"},
        {"query": "著作权法第十条的内容是什么", "label": "法条查询"},
        {"query": "请问民法典509条", "label": "法条查询"},
        {"query": "查一下劳动法第44条", "label": "法条查询"},
        {"query": "民法典第一千零七十七条讲的什么", "label": "法条查询"},
        {"query": "物权法第106条的规定", "label": "法条查询"},
        {"query": "消费者权益保护法第55条", "label": "法条查询"},

        # === 法律咨询（实际问题）===
        {"query": "老板拖欠工资怎么办", "label": "法律咨询"},
        {"query": "公司不签劳动合同违法吗", "label": "法律咨询"},
        {"query": "被辞退可以要求赔偿吗", "label": "法律咨询"},
        {"query": "试用期被辞退有补偿吗", "label": "法律咨询"},
        {"query": "离婚财产怎么分割", "label": "法律咨询"},
        {"query": "交通事故对方全责怎么赔偿", "label": "法律咨询"},
        {"query": "房东不退押金怎么办", "label": "法律咨询"},
        {"query": "借钱不还可以起诉吗", "label": "法律咨询"},
        {"query": "公司强制加班合法吗", "label": "法律咨询"},
        {"query": "怀孕期间被辞退能要求赔偿吗", "label": "法律咨询"},
        {"query": "合同违约需要承担什么责任", "label": "法律咨询"},
        {"query": "遗产继承需要什么手续", "label": "法律咨询"},
        {"query": "高空抛物砸到人谁负责", "label": "法律咨询"},
        {"query": "什么情况下可以解除劳动合同", "label": "法律咨询"},
        {"query": "签了合同可以反悔吗", "label": "法律咨询"},
        {"query": "经济补偿金怎么算", "label": "法律咨询"},
        {"query": "双倍工资怎么计算", "label": "法律咨询"},
        {"query": "工伤认定需要什么材料", "label": "法律咨询"},
        {"query": "加班费应该怎么算", "label": "法律咨询"},
        {"query": "什么是善意取得", "label": "法律咨询"},
        {"query": "诉讼时效是多久", "label": "法律咨询"},
        {"query": "竞业限制补偿标准", "label": "法律咨询"},
        {"query": "离职需要提前多久通知", "label": "法律咨询"},
        {"query": "试用期最长多久", "label": "法律咨询"},
        {"query": "定金和订金的区别", "label": "法律咨询"},
        {"query": "合同无效的情形有哪些", "label": "法律咨询"},
        {"query": "见义勇为受伤谁赔偿", "label": "法律咨询"},
        {"query": "不当得利如何处理", "label": "法律咨询"},
        {"query": "居住权是什么意思", "label": "法律咨询"},
        {"query": "格式条款什么时候无效", "label": "法律咨询"},

        # === 通用问题（非法律相关）===
        {"query": "今天天气怎么样", "label": "通用问题"},
        {"query": "北京到上海多少公里", "label": "通用问题"},
        {"query": "你好", "label": "通用问题"},
        {"query": "你是谁", "label": "通用问题"},
        {"query": "现在几点了", "label": "通用问题"},
        {"query": "人工智能是什么", "label": "通用问题"},
        {"query": "Python怎么学", "label": "通用问题"},
        {"query": "推荐一本书", "label": "通用问题"},
        {"query": "怎么做红烧肉", "label": "通用问题"},
        {"query": "感冒了吃什么药", "label": "通用问题"},
        {"query": "最近有什么好看的电影", "label": "通用问题"},
        {"query": "2+3等于多少", "label": "通用问题"},
        {"query": "在吗", "label": "通用问题"},
        {"query": "你能做什么", "label": "通用问题"},
        {"query": "谢谢", "label": "通用问题"},
        {"query": "再见", "label": "通用问题"},
        {"query": "讲个笑话", "label": "通用问题"},
        {"query": "中国有多少人口", "label": "通用问题"},
        {"query": "地球为什么是圆的", "label": "通用问题"},
        {"query": "怎么学英语", "label": "通用问题"},
        {"query": "明天会下雨吗", "label": "通用问题"},
        {"query": "哪个手机好用", "label": "通用问题"},
        {"query": "股票怎么买", "label": "通用问题"},
        {"query": "如何减肥", "label": "通用问题"},
        {"query": "什么是区块链", "label": "通用问题"},
        {"query": "帮我写一首诗", "label": "通用问题"},
        {"query": "翻译一下这段话", "label": "通用问题"},
        {"query": "周杰伦的新歌", "label": "通用问题"},
        {"query": "怎么去故宫", "label": "通用问题"},
        {"query": "一加一等于几", "label": "通用问题"},
    ]

    return samples


def augment_data(samples, augment_ratio=2):
    """数据增强：同义改写、添加噪声"""
    augmented = []

    # 同义词替换字典
    synonyms = {
        "怎么办": ["如何处理", "怎么解决", "该怎么做", "应该怎么办"],
        "是什么": ["的内容", "指什么", "是啥", "讲的什么"],
        "可以吗": ["行吗", "能不能", "可不可以", "是否可以"],
        "违法吗": ["合法吗", "犯法吗", "是否违法", "有没有问题"],
        "第": ["第", ""],  # 有些查询可能省略"第"
    }

    for sample in samples:
        query = sample['query']
        label = sample['label']

        # 原样本
        augmented.append(sample)

        # 生成变体
        for _ in range(augment_ratio - 1):
            new_query = query

            # 随机同义词替换
            for original, replacements in synonyms.items():
                if original in new_query:
                    new_query = new_query.replace(original, random.choice(replacements))

            # 添加常见前缀
            if random.random() > 0.5 and label != "通用问题":
                prefixes = ["请问", "咨询一下", "想问", ""]
                new_query = random.choice(prefixes) + new_query

            augmented.append({
                "query": new_query,
                "label": label
            })

    return augmented


def balance_dataset(data):
    """平衡数据集（确保三类数量相近）"""
    from collections import Counter

    label_counts = Counter([item['label'] for item in data])
    print(f"原始数据分布: {dict(label_counts)}")

    # 找到最大类别数量
    max_count = max(label_counts.values())

    # 对每个类别进行过采样
    balanced_data = []
    for label in label_counts.keys():
        samples = [item for item in data if item['label'] == label]

        # 如果样本不足，进行复制+轻微变化
        while len(samples) < max_count:
            sample = random.choice(samples)
            # 轻微变化（添加标点、空格等）
            new_query = sample['query']
            if random.random() > 0.5:
                new_query = new_query.rstrip('？?') + random.choice(['？', '?', ''])
            samples.append({"query": new_query, "label": sample['label']})

        balanced_data.extend(samples[:max_count])

    # 打乱顺序
    random.shuffle(balanced_data)

    final_counts = Counter([item['label'] for item in balanced_data])
    print(f"平衡后数据分布: {dict(final_counts)}")

    return balanced_data


def save_training_data(data, output_path):
    """保存为 JSONL 格式"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    print(f"[OK] 训练数据已保存到: {output_path}")
    print(f"  总样本数: {len(data)}")

    # 统计
    from collections import Counter
    label_counts = Counter([item['label'] for item in data])
    for label, count in label_counts.items():
        print(f"  - {label}: {count}")


def main():
    print("=" * 60)
    print("法律 BERT 意图分类器 - 训练数据生成")
    print("=" * 60)

    # 1. 从现有数据生成
    print("\n[1/4] 从现有 CSV 数据生成样本...")
    csv_samples = generate_from_existing_data()
    print(f"  生成 {len(csv_samples)} 个样本")

    # 2. 添加手动标注的高质量样本
    print("\n[2/4] 添加手动标注的高质量样本...")
    manual_samples = generate_manual_samples()
    print(f"  添加 {len(manual_samples)} 个样本")

    # 合并
    all_samples = csv_samples + manual_samples

    # 3. 数据增强
    print("\n[3/4] 数据增强...")
    augmented_samples = augment_data(manual_samples, augment_ratio=3)
    all_samples.extend(augmented_samples)
    print(f"  增强后总样本数: {len(all_samples)}")

    # 4. 平衡数据集
    print("\n[4/4] 平衡数据集...")
    balanced_samples = balance_dataset(all_samples)

    # 保存
    output_dir = Path(__file__).parent / "training_data"
    save_training_data(
        balanced_samples,
        output_dir / "legal_intent_training_data.jsonl"
    )

    # 生成测试集（10%）
    random.shuffle(balanced_samples)
    split_idx = int(len(balanced_samples) * 0.9)
    train_data = balanced_samples[:split_idx]
    test_data = balanced_samples[split_idx:]

    save_training_data(train_data, output_dir / "train.jsonl")
    save_training_data(test_data, output_dir / "test.jsonl")

    print("\n" + "=" * 60)
    print("[OK] 数据生成完成！")
    print("=" * 60)
    print(f"\n训练集: {len(train_data)} 样本")
    print(f"测试集: {len(test_data)} 样本")


if __name__ == "__main__":
    main()
