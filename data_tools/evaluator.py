"""
法律问答评测工具
提供独立的测试集管理和多维度评估
"""
import pandas as pd
import json
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import sys, os

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from base import logger


class LegalQAEvaluator:
    """法律问答评测器"""
    
    def __init__(self):
        self.logger = logger
        
        # 问题类型定义
        self.question_types = [
            "法条精确查询",      # "民法典第509条是什么？"
            "法律概念解释",      # "什么是定金？"
            "事实场景咨询",      # "老板拖欠工资怎么办？"
            "纠纷处理建议",      # "合同违约如何处理？"
            "诉讼程序咨询",      # "起诉需要什么材料？"
            "合同审查",          # "这个合同条款有效吗？"
            "多轮追问",          # 需要补充事实
            "跨法条问题",        # 涉及多个法律
            "已废止条文",        # 测试时效性判断
            "地方性法规",        # 测试地域判断
            "口语化问题",        # 测试鲁棒性
            "需要拒答",          # 信息不足或越界
        ]
        
        # 评估维度
        self.eval_dimensions = [
            "分类准确性",
            "检索召回率",
            "条文号准确性",
            "法律依据正确性",
            "答案完整性",
            "时效性判断",
            "地域判断",
            "拒答准确性",
        ]
    
    def create_test_set_template(self, output_path: str, samples_per_type: int = 10):
        """
        创建测试集模板
        输出JSON格式，包含各类问题的示例
        """
        test_cases = []
        
        for q_type in self.question_types:
            for i in range(samples_per_type):
                test_case = {
                    "id": f"{q_type}_{i+1}",
                    "question": "",  # 待填写
                    "question_type": q_type,
                    "expected_intent": "",  # 期望的意图分类
                    "expected_articles": [],  # 期望检索到的条文 [{"law": "民法典", "article": "509"}]
                    "expected_answer_contains": [],  # 答案应包含的关键词
                    "expected_answer_not_contains": [],  # 答案不应包含的内容
                    "should_refuse": False,  # 是否应该拒答
                    "region": "全国",  # 适用地域
                    "effective_date": None,  # 期望判断的时效性
                    "difficulty": "medium",  # easy/medium/hard
                    "notes": "",  # 备注
                }
                test_cases.append(test_case)
        
        # 保存为JSON
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(test_cases, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"已生成测试集模板：{output_path}，包含 {len(test_cases)} 个测试用例")
        self.logger.info("请手工填写question、expected_*等字段")
    
    def load_test_set(self, test_set_path: str) -> List[Dict]:
        """加载测试集"""
        with open(test_set_path, 'r', encoding='utf-8') as f:
            test_cases = json.load(f)
        
        # 过滤掉question为空的用例
        valid_cases = [case for case in test_cases if case.get("question", "").strip()]
        
        self.logger.info(f"加载测试集：{len(valid_cases)} 个有效用例")
        return valid_cases
    
    def evaluate_classification(self, test_cases: List[Dict], 
                               predictions: List[str]) -> Dict:
        """
        评估分类准确性
        predictions: 预测的意图分类结果列表
        """
        if len(test_cases) != len(predictions):
            raise ValueError("测试用例数量与预测结果数量不匹配")
        
        correct = 0
        confusion = {}  # 混淆矩阵
        
        for case, pred in zip(test_cases, predictions):
            expected = case["expected_intent"]
            
            if expected not in confusion:
                confusion[expected] = {}
            if pred not in confusion[expected]:
                confusion[expected][pred] = 0
            
            confusion[expected][pred] += 1
            
            if expected == pred:
                correct += 1
        
        accuracy = correct / len(test_cases)
        
        return {
            "accuracy": accuracy,
            "correct": correct,
            "total": len(test_cases),
            "confusion_matrix": confusion
        }
    
    def evaluate_retrieval(self, test_cases: List[Dict],
                          retrieved_articles: List[List[Dict]]) -> Dict:
        """
        评估检索效果
        retrieved_articles: [[{"law": "民法典", "article": "509"}], ...]
        """
        if len(test_cases) != len(retrieved_articles):
            raise ValueError("测试用例数量与检索结果数量不匹配")
        
        recall_scores = []
        precision_scores = []
        mrr_scores = []
        
        for case, retrieved in zip(test_cases, retrieved_articles):
            expected = case["expected_articles"]
            
            if not expected:
                continue
            
            # Recall: 期望的条文中有多少被检索到
            expected_set = set(f"{a['law']}_{a['article']}" for a in expected)
            retrieved_set = set(f"{a['law']}_{a['article']}" for a in retrieved)
            
            recall = len(expected_set & retrieved_set) / len(expected_set) if expected_set else 0
            recall_scores.append(recall)
            
            # Precision: 检索到的条文中有多少是期望的
            precision = len(expected_set & retrieved_set) / len(retrieved_set) if retrieved_set else 0
            precision_scores.append(precision)
            
            # MRR: 第一个正确结果的排名倒数
            for i, r in enumerate(retrieved):
                key = f"{r['law']}_{r['article']}"
                if key in expected_set:
                    mrr_scores.append(1.0 / (i + 1))
                    break
            else:
                mrr_scores.append(0.0)
        
        return {
            "avg_recall": sum(recall_scores) / len(recall_scores) if recall_scores else 0,
            "avg_precision": sum(precision_scores) / len(precision_scores) if precision_scores else 0,
            "mrr": sum(mrr_scores) / len(mrr_scores) if mrr_scores else 0,
            "evaluated_cases": len(recall_scores)
        }
    
    def evaluate_answer_quality(self, test_cases: List[Dict],
                               answers: List[str]) -> Dict:
        """
        评估答案质量
        检查答案是否包含/不包含期望的内容
        """
        if len(test_cases) != len(answers):
            raise ValueError("测试用例数量与答案数量不匹配")
        
        contain_correct = 0
        not_contain_correct = 0
        refuse_correct = 0
        
        detailed_errors = []
        
        for i, (case, answer) in enumerate(zip(test_cases, answers)):
            case_errors = []
            
            # 检查应包含的关键词
            expected_contains = case.get("expected_answer_contains", [])
            for keyword in expected_contains:
                if keyword in answer:
                    contain_correct += 1
                else:
                    case_errors.append(f"缺少关键词：{keyword}")
            
            # 检查不应包含的内容
            expected_not_contains = case.get("expected_answer_not_contains", [])
            for keyword in expected_not_contains:
                if keyword not in answer:
                    not_contain_correct += 1
                else:
                    case_errors.append(f"不应包含：{keyword}")
            
            # 检查拒答判断
            should_refuse = case.get("should_refuse", False)
            is_refused = any(kw in answer for kw in ["无法回答", "信息不足", "需要补充", "超出范围"])
            
            if should_refuse == is_refused:
                refuse_correct += 1
            else:
                if should_refuse:
                    case_errors.append("应该拒答但没有拒答")
                else:
                    case_errors.append("不应拒答但进行了拒答")
            
            if case_errors:
                detailed_errors.append({
                    "id": case["id"],
                    "question": case["question"],
                    "errors": case_errors
                })
        
        total_contain_checks = sum(len(case.get("expected_answer_contains", [])) for case in test_cases)
        total_not_contain_checks = sum(len(case.get("expected_answer_not_contains", [])) for case in test_cases)
        
        return {
            "contain_accuracy": contain_correct / total_contain_checks if total_contain_checks > 0 else 1.0,
            "not_contain_accuracy": not_contain_correct / total_not_contain_checks if total_not_contain_checks > 0 else 1.0,
            "refuse_accuracy": refuse_correct / len(test_cases),
            "detailed_errors": detailed_errors[:20]  # 只返回前20个错误
        }
    
    def generate_report(self, test_set_path: str, 
                       results: Dict,
                       output_path: str):
        """
        生成评测报告
        results包含：classification_result, retrieval_result, answer_quality_result
        """
        report_lines = [
            "# 法律问答系统评测报告",
            f"\n生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"\n测试集：{test_set_path}",
            "\n---\n",
            "\n## 1. 分类准确性",
        ]
        
        if "classification" in results:
            cls_result = results["classification"]
            report_lines.extend([
                f"\n- 准确率：{cls_result['accuracy']:.2%}",
                f"- 正确数：{cls_result['correct']}/{cls_result['total']}",
                "\n### 混淆矩阵（部分）："
            ])
            
            confusion = cls_result.get("confusion_matrix", {})
            for true_label in list(confusion.keys())[:5]:
                report_lines.append(f"\n{true_label}:")
                for pred_label, count in confusion[true_label].items():
                    report_lines.append(f"  -> {pred_label}: {count}")
        
        if "retrieval" in results:
            ret_result = results["retrieval"]
            report_lines.extend([
                "\n\n## 2. 检索效果",
                f"\n- 平均召回率：{ret_result['avg_recall']:.2%}",
                f"- 平均精确率：{ret_result['avg_precision']:.2%}",
                f"- MRR：{ret_result['mrr']:.4f}",
                f"- 评估用例数：{ret_result['evaluated_cases']}"
            ])
        
        if "answer_quality" in results:
            aq_result = results["answer_quality"]
            report_lines.extend([
                "\n\n## 3. 答案质量",
                f"\n- 包含关键词准确率：{aq_result['contain_accuracy']:.2%}",
                f"- 不包含错误内容准确率：{aq_result['not_contain_accuracy']:.2%}",
                f"- 拒答判断准确率：{aq_result['refuse_accuracy']:.2%}",
            ])
            
            if aq_result.get("detailed_errors"):
                report_lines.append("\n### 错误样例（前10个）：")
                for err in aq_result["detailed_errors"][:10]:
                    report_lines.append(f"\n- [{err['id']}] {err['question']}")
                    for e in err['errors']:
                        report_lines.append(f"  * {e}")
        
        report_lines.append("\n\n---\n报告结束")
        
        # 保存为Markdown
        report_text = "".join(report_lines)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        self.logger.info(f"评测报告已生成：{output_path}")
        
        return report_text


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="法律问答评测工具")
    parser.add_argument("--mode", type=str, 
                       choices=["create_template", "load", "report"],
                       required=True, help="运行模式")
    parser.add_argument("--test-set", type=str, help="测试集路径")
    parser.add_argument("--output", type=str, help="输出文件路径")
    parser.add_argument("--samples-per-type", type=int, default=10,
                       help="每种类型的样本数（create_template模式）")
    
    args = parser.parse_args()
    
    evaluator = LegalQAEvaluator()
    
    if args.mode == "create_template":
        output = args.output or "legal_qa_test_set_template.json"
        evaluator.create_test_set_template(output, args.samples_per_type)
        logger.info("请手工编辑测试集，填写question和expected_*字段")
    
    elif args.mode == "load":
        if not args.test_set:
            parser.error("load模式需要 --test-set")
        
        test_cases = evaluator.load_test_set(args.test_set)
        logger.info(f"成功加载 {len(test_cases)} 个测试用例")
        
        # 显示统计信息
        type_counts = {}
        for case in test_cases:
            q_type = case["question_type"]
            type_counts[q_type] = type_counts.get(q_type, 0) + 1
        
        logger.info("测试用例类型分布：")
        for q_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            logger.info(f"  {q_type}: {count}")
    
    elif args.mode == "report":
        # 示例：生成空报告模板
        output = args.output or "evaluation_report.md"
        sample_results = {
            "classification": {
                "accuracy": 0.85,
                "correct": 85,
                "total": 100,
                "confusion_matrix": {}
            },
            "retrieval": {
                "avg_recall": 0.75,
                "avg_precision": 0.80,
                "mrr": 0.82,
                "evaluated_cases": 80
            },
            "answer_quality": {
                "contain_accuracy": 0.88,
                "not_contain_accuracy": 0.92,
                "refuse_accuracy": 0.90,
                "detailed_errors": []
            }
        }
        
        evaluator.generate_report(
            args.test_set or "test_set.json",
            sample_results,
            output
        )


if __name__ == "__main__":
    main()
