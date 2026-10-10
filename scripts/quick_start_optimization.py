"""
数据优化快速启动脚本
一键执行数据质量检查和优化流程
"""
import os
import sys

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from base import logger, Config
from data_tools.data_quality_optimizer import DataQualityOptimizer
import pandas as pd


def check_environment():
    """检查环境依赖"""
    logger.info("=" * 60)
    logger.info("步骤1: 检查环境")
    logger.info("=" * 60)
    
    issues = []
    
    # 检查MySQL连接
    try:
        from mysql_qa import MySQLClient
        mysql_client = MySQLClient()
        logger.info("✅ MySQL连接正常")
        mysql_client.connection.close()
    except Exception as e:
        logger.error(f"❌ MySQL连接失败: {e}")
        issues.append("MySQL连接失败")
    
    # 检查Milvus连接
    try:
        from pymilvus import MilvusClient
        conf = Config()
        client = MilvusClient(uri=f"http://{conf.MILVUS_HOST}:{conf.MILVUS_PORT}")
        logger.info("✅ Milvus连接正常")
    except Exception as e:
        logger.error(f"❌ Milvus连接失败: {e}")
        issues.append("Milvus连接失败")
    
    # 检查数据文件
    data_path = os.path.join(project_root, "mysql_qa", "data", "legal_qa_full.csv")
    if os.path.exists(data_path):
        logger.info(f"✅ 找到数据文件: {data_path}")
    else:
        logger.error(f"❌ 数据文件不存在: {data_path}")
        issues.append("数据文件不存在")
    
    if issues:
        logger.error(f"\n发现 {len(issues)} 个问题，请先解决：")
        for issue in issues:
            logger.error(f"  - {issue}")
        return False
    
    logger.info("\n✅ 环境检查通过！\n")
    return True


def init_law_database():
    """初始化法律数据库"""
    logger.info("=" * 60)
    logger.info("步骤2: 初始化法律原文数据库")
    logger.info("=" * 60)
    
    try:
        from base import LawDatabase
        db = LawDatabase()
        logger.info("✅ 法律原文表已创建")
        
        # 显示统计信息
        stats = db.get_law_statistics()
        if stats.get('total_articles', 0) > 0:
            logger.info(f"  当前已有 {stats['total_articles']} 条法律条文")
            logger.info("  按法律分布：")
            for law, count in list(stats.get('by_law', {}).items())[:5]:
                logger.info(f"    - {law}: {count}条")
        else:
            logger.info("  数据库为空，请使用law_importer.py导入法律条文")
        
        return True
    except Exception as e:
        logger.error(f"❌ 初始化失败: {e}")
        return False


def analyze_qa_data():
    """分析问答数据质量"""
    logger.info("\n" + "=" * 60)
    logger.info("步骤3: 分析问答数据质量")
    logger.info("=" * 60)
    
    data_path = os.path.join(project_root, "mysql_qa", "data", "legal_qa_full.csv")
    
    try:
        df = pd.read_csv(data_path)
        logger.info(f"✅ 读取数据: {len(df)} 条记录")
        
        # 基础统计
        logger.info("\n基础统计：")
        logger.info(f"  - 总记录数: {len(df)}")
        logger.info(f"  - 字段数: {len(df.columns)}")
        logger.info(f"  - 字段名: {', '.join(df.columns.tolist())}")
        
        # 领域分布
        if 'subject' in df.columns:
            logger.info("\n领域分布（Top 10）：")
            subject_counts = df['subject'].value_counts().head(10)
            for subject, count in subject_counts.items():
                logger.info(f"  - {subject}: {count}条 ({count/len(df)*100:.1f}%)")
        
        # 数据质量问题
        logger.info("\n数据质量检查：")
        
        # 空值检查
        if 'question' in df.columns:
            empty_q = df['question'].isna().sum()
            if empty_q > 0:
                logger.warning(f"  ⚠️  {empty_q} 条记录的问题为空")
        
        if 'answer' in df.columns:
            empty_a = df['answer'].isna().sum()
            if empty_a > 0:
                logger.warning(f"  ⚠️  {empty_a} 条记录的答案为空")
        
        # 长度统计
        if 'question' in df.columns:
            avg_q_len = df['question'].str.len().mean()
            logger.info(f"  - 平均问题长度: {avg_q_len:.1f} 字符")
        
        if 'answer' in df.columns:
            avg_a_len = df['answer'].str.len().mean()
            logger.info(f"  - 平均答案长度: {avg_a_len:.1f} 字符")
        
        return True
    except Exception as e:
        logger.error(f"❌ 分析失败: {e}")
        return False


def optimize_qa_data():
    """优化问答数据"""
    logger.info("\n" + "=" * 60)
    logger.info("步骤4: 优化问答数据")
    logger.info("=" * 60)
    
    input_path = os.path.join(project_root, "mysql_qa", "data", "legal_qa_full.csv")
    output_path = os.path.join(project_root, "mysql_qa", "data", "legal_qa_full_enhanced.csv")
    
    try:
        logger.info("开始数据优化...")
        df = pd.read_csv(input_path)
        
        optimizer = DataQualityOptimizer()
        
        # 去重
        logger.info("\n[1/3] 执行去重...")
        df_clean, dedup_report = optimizer.detect_duplicates(df)
        logger.info(f"  去重结果: 原始{dedup_report['original_count']}条 -> "
                   f"保留{dedup_report['final_count']}条 "
                   f"(去除{dedup_report['removed_count']}条)")
        
        # 验证法律引用
        logger.info("\n[2/3] 验证法律引用...")
        issues = optimizer.validate_law_references(df_clean)
        if issues:
            logger.warning(f"  发现 {len(issues)} 处可能的引用问题（详见日志）")
            # 只显示前3个
            for issue in issues[:3]:
                logger.warning(f"    - {issue['issue_type']}: {issue['details']}")
        else:
            logger.info("  ✅ 未发现明显的引用问题")
        
        # 增强元数据
        logger.info("\n[3/3] 增强元数据...")
        df_enhanced = optimizer.enhance_qa_metadata(df_clean)
        
        # 生成质量报告
        report = optimizer.generate_quality_report(df_enhanced)
        logger.info("\n质量报告：")
        logger.info(f"  - 总记录数: {report['total_records']}")
        logger.info(f"  - 包含条文引用: {report['has_article_refs']} 条")
        logger.info(f"  - 包含法律依据: {report['has_legal_basis']} 条")
        logger.info(f"  - 平均置信度: {report['avg_confidence']:.2f}")
        
        # 保存结果
        df_enhanced.to_csv(output_path, index=False, encoding='utf-8-sig')
        logger.info(f"\n✅ 优化完成，已保存到: {output_path}")
        
        return True
    except Exception as e:
        logger.error(f"❌ 优化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_test_set():
    """创建测试集模板"""
    logger.info("\n" + "=" * 60)
    logger.info("步骤5: 创建测试集模板")
    logger.info("=" * 60)
    
    test_set_dir = os.path.join(project_root, "test_set")
    os.makedirs(test_set_dir, exist_ok=True)
    
    template_path = os.path.join(test_set_dir, "legal_qa_test_template.json")
    
    try:
        from data_tools.evaluator import LegalQAEvaluator
        evaluator = LegalQAEvaluator()
        
        evaluator.create_test_set_template(template_path, samples_per_type=5)
        
        logger.info(f"✅ 测试集模板已创建: {template_path}")
        logger.info("\n下一步：")
        logger.info("  1. 编辑测试集模板，填写question和expected_*字段")
        logger.info("  2. 重命名为legal_qa_test.json")
        logger.info("  3. 运行评测脚本进行系统评估")
        
        return True
    except Exception as e:
        logger.error(f"❌ 创建失败: {e}")
        return False


def generate_summary():
    """生成总结报告"""
    logger.info("\n" + "=" * 60)
    logger.info("数据优化完成总结")
    logger.info("=" * 60)
    
    logger.info("\n✅ 已完成的工作：")
    logger.info("  1. ✅ 环境检查")
    logger.info("  2. ✅ 法律数据库初始化")
    logger.info("  3. ✅ 问答数据质量分析")
    logger.info("  4. ✅ 问答数据优化（去重、验证、增强）")
    logger.info("  5. ✅ 测试集模板创建")
    
    logger.info("\n📋 后续建议：")
    logger.info("  1. 查看优化后的数据: mysql_qa/data/legal_qa_full_enhanced.csv")
    logger.info("  2. 导入法律原文数据（使用data_tools/law_importer.py）")
    logger.info("  3. 创建增强版向量集合（使用rag_qa/scripts/init_enhanced_collection.py）")
    logger.info("  4. 编写测试集（编辑test_set/legal_qa_test_template.json）")
    logger.info("  5. 运行评测验证效果")
    
    logger.info("\n📖 详细文档：")
    logger.info("  docs/DATA_OPTIMIZATION_GUIDE.md")
    
    logger.info("\n" + "=" * 60)


def main():
    """主流程"""
    logger.info("\n\n")
    logger.info("╔" + "=" * 58 + "╗")
    logger.info("║" + " " * 10 + "Legal QA System - 数据优化工具" + " " * 16 + "║")
    logger.info("╚" + "=" * 58 + "╝")
    logger.info("\n")
    
    # 步骤1：环境检查
    if not check_environment():
        logger.error("\n❌ 环境检查失败，请先解决环境问题")
        return
    
    # 步骤2：初始化数据库
    if not init_law_database():
        logger.error("\n❌ 数据库初始化失败")
        return
    
    # 步骤3：分析数据
    if not analyze_qa_data():
        logger.error("\n❌ 数据分析失败")
        return
    
    # 步骤4：优化数据
    response = input("\n是否执行数据优化（去重、验证、增强）？这会创建新文件。[Y/n]: ")
    if response.lower() in ['y', 'yes', '']:
        if not optimize_qa_data():
            logger.error("\n❌ 数据优化失败")
            return
    else:
        logger.info("跳过数据优化")
    
    # 步骤5：创建测试集
    response = input("\n是否创建测试集模板？[Y/n]: ")
    if response.lower() in ['y', 'yes', '']:
        create_test_set()
    else:
        logger.info("跳过测试集创建")
    
    # 生成总结
    generate_summary()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\n用户中断执行")
    except Exception as e:
        logger.error(f"\n\n执行出错: {e}")
        import traceback
        traceback.print_exc()
