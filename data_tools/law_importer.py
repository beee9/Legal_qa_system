"""
法律原文导入工具
支持从多种格式导入法律条文到MySQL和Milvus
"""
import pandas as pd
import json
from datetime import datetime
from typing import List, Dict, Optional
import sys, os

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from base import LawArticle, LawLevel, LawStatus, LawDatabase, logger, Config
from rag_qa.core.vector_store import VectorStore
from langchain_core.documents import Document


class LawImporter:
    """法律原文导入器"""
    
    def __init__(self):
        self.logger = logger
        self.config = Config()
        self.law_db = LawDatabase()
        self.vector_store = None  # 延迟初始化
    
    def import_from_csv(self, csv_path: str, 
                       law_name: str,
                       law_short_name: str,
                       law_level: LawLevel,
                       version: str = "v1",
                       effective_date: Optional[datetime] = None) -> int:
        """
        从CSV导入法律条文
        CSV格式：article_no, article_title, article_content, chapter, section
        """
        self.logger.info(f"开始从CSV导入法律条文：{csv_path}")
        
        df = pd.read_csv(csv_path)
        required_cols = ["article_no", "article_content"]
        
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"CSV缺少必需列：{col}")
        
        articles = []
        law_id = f"{law_short_name}_{version}".replace(" ", "_")
        
        for idx, row in df.iterrows():
            article = LawArticle(
                law_id=law_id,
                law_name=law_name,
                law_short_name=law_short_name,
                law_level=law_level,
                article_no=str(row["article_no"]),
                article_title=row.get("article_title", ""),
                article_content=row["article_content"],
                chapter=row.get("chapter", ""),
                section=row.get("section", ""),
                version=version,
                status=LawStatus.EFFECTIVE,
                effective_date=effective_date,
                region=row.get("region", "全国"),
                source_url=row.get("source_url", ""),
            )
            articles.append(article)
        
        # 插入MySQL
        success_count = self.law_db.batch_insert_articles(articles)
        self.logger.info(f"MySQL入库完成：{success_count}/{len(articles)} 条")
        
        return success_count
    
    def import_from_json(self, json_path: str) -> int:
        """
        从JSON导入法律条文
        JSON格式：
        {
          "law_name": "中华人民共和国民法典",
          "law_short_name": "民法典",
          "law_level": "法律",
          "version": "v1",
          "effective_date": "2021-01-01",
          "articles": [
            {
              "article_no": "1",
              "article_content": "...",
              "chapter": "第一编 总则",
              ...
            }
          ]
        }
        """
        self.logger.info(f"开始从JSON导入法律条文：{json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        law_name = data["law_name"]
        law_short_name = data["law_short_name"]
        law_level = LawLevel(data["law_level"])
        version = data.get("version", "v1")
        law_id = f"{law_short_name}_{version}".replace(" ", "_")
        
        effective_date = None
        if "effective_date" in data:
            effective_date = datetime.strptime(data["effective_date"], "%Y-%m-%d")
        
        articles = []
        for item in data["articles"]:
            article = LawArticle(
                law_id=law_id,
                law_name=law_name,
                law_short_name=law_short_name,
                law_level=law_level,
                article_no=str(item["article_no"]),
                article_title=item.get("article_title", ""),
                article_content=item["article_content"],
                chapter=item.get("chapter", ""),
                section=item.get("section", ""),
                subsection=item.get("subsection", ""),
                version=version,
                status=LawStatus.EFFECTIVE,
                effective_date=effective_date,
                expiry_date=None,
                region=item.get("region", "全国"),
                source_url=item.get("source_url", ""),
                parent_article=item.get("parent_article", ""),
                related_articles=item.get("related_articles", []),
                referenced_laws=item.get("referenced_laws", []),
            )
            articles.append(article)
        
        # 插入MySQL
        success_count = self.law_db.batch_insert_articles(articles)
        self.logger.info(f"MySQL入库完成：{success_count}/{len(articles)} 条")
        
        return success_count
    
    def import_to_vector_store(self, law_short_name: str,
                               collection_name: Optional[str] = None) -> int:
        """
        将MySQL中的法律条文导入到向量数据库
        """
        self.logger.info(f"开始将 {law_short_name} 导入向量数据库")
        
        # 初始化向量存储
        if self.vector_store is None:
            self.vector_store = VectorStore(
                collection_name=collection_name or self.config.MILVUS_COLLECTION_NAME
            )
        
        # 从MySQL读取条文
        articles = self.law_db.query_articles_by_law(law_short_name)
        
        if not articles:
            self.logger.warning(f"未找到法律 {law_short_name} 的条文")
            return 0
        
        self.logger.info(f"找到 {len(articles)} 条法律条文")
        
        # 转换为Document
        documents = []
        for article in articles:
            # 使用get_search_text作为向量化文本，包含所有可检索字段
            search_text = article.get_search_text()
            
            # 构建元数据
            metadata = {
                "source": article.law_short_name,
                "law_name": article.law_name,
                "law_short_name": article.law_short_name,
                "article_no": article.article_no,
                "law_level": article.law_level.value,
                "version": article.version,
                "status": article.status.value,
                "effective_date": article.effective_date.isoformat() if article.effective_date else "",
                "expiry_date": article.expiry_date.isoformat() if article.expiry_date else "",
                "region": article.region,
                "chapter": article.chapter or "",
                "section": article.section or "",
                "source_url": article.source_url or "",
                "parent_content": article.get_display_text(include_metadata=False),
            }
            
            doc = Document(page_content=search_text, metadata=metadata)
            documents.append(doc)
        
        # 批量插入向量数据库
        batch_size = 100
        success_count = 0
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]
            try:
                self.vector_store.add_documents(batch)
                success_count += len(batch)
                self.logger.info(f"已导入 {success_count}/{len(documents)} 条到向量数据库")
            except Exception as e:
                self.logger.error(f"批次 {i//batch_size + 1} 导入失败：{e}")
        
        self.logger.info(f"向量数据库导入完成：{success_count}/{len(documents)} 条")
        return success_count
    
    def create_sample_json(self, output_path: str):
        """创建示例JSON模板"""
        sample = {
            "law_name": "中华人民共和国民法典",
            "law_short_name": "民法典",
            "law_level": "法律",
            "version": "v1",
            "effective_date": "2021-01-01",
            "articles": [
                {
                    "article_no": "509",
                    "article_title": "",
                    "article_content": "当事人应当按照约定全面履行自己的义务。当事人应当遵循诚信原则，根据合同的性质、目的和交易习惯履行通知、协助、保密等义务。当事人在履行合同过程中，应当避免浪费资源、污染环境和破坏生态。",
                    "chapter": "第三编 合同",
                    "section": "第一分编 通则",
                    "subsection": "",
                    "region": "全国",
                    "source_url": "http://www.npc.gov.cn/npc/c30834/202006/75ba6483b8344591abd07917e1d25cc8.shtml",
                    "parent_article": "",
                    "related_articles": ["510", "511"],
                    "referenced_laws": []
                }
            ]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(sample, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"已生成示例JSON模板：{output_path}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="法律原文导入工具")
    parser.add_argument("--mode", type=str, choices=["csv", "json", "to_vector", "sample"],
                       required=True, help="导入模式")
    parser.add_argument("--input", type=str, help="输入文件路径")
    parser.add_argument("--law-name", type=str, help="法律全称")
    parser.add_argument("--law-short-name", type=str, help="法律简称")
    parser.add_argument("--law-level", type=str, 
                       choices=["法律", "行政法规", "部门规章", "司法解释", "地方性法规"],
                       help="法律层级")
    parser.add_argument("--version", type=str, default="v1", help="版本号")
    parser.add_argument("--effective-date", type=str, help="生效日期 (YYYY-MM-DD)")
    parser.add_argument("--collection", type=str,
                       help="向量数据库集合名称，默认读取 config.ini")
    parser.add_argument("--output", type=str, help="输出文件路径（sample模式）")
    
    args = parser.parse_args()
    
    importer = LawImporter()
    
    if args.mode == "sample":
        output = args.output or "law_sample.json"
        importer.create_sample_json(output)
    
    elif args.mode == "csv":
        if not all([args.input, args.law_name, args.law_short_name, args.law_level]):
            parser.error("CSV模式需要 --input, --law-name, --law-short-name, --law-level")
        
        effective_date = None
        if args.effective_date:
            effective_date = datetime.strptime(args.effective_date, "%Y-%m-%d")
        
        law_level = LawLevel(args.law_level)
        
        count = importer.import_from_csv(
            args.input, args.law_name, args.law_short_name,
            law_level, args.version, effective_date
        )
        logger.info(f"CSV导入完成：{count} 条")
    
    elif args.mode == "json":
        if not args.input:
            parser.error("JSON模式需要 --input")
        
        count = importer.import_from_json(args.input)
        logger.info(f"JSON导入完成：{count} 条")
    
    elif args.mode == "to_vector":
        if not args.law_short_name:
            parser.error("向量导入模式需要 --law-short-name")
        
        count = importer.import_to_vector_store(args.law_short_name, args.collection)
        logger.info(f"向量导入完成：{count} 条")


if __name__ == "__main__":
    main()
