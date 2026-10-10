"""
法律原文数据库管理
提供法律条文的存储、查询、版本管理功能
"""
import pymysql
from typing import List, Optional, Dict
from datetime import datetime
from .law_article import LawArticle, LawLevel, LawStatus
from .config import Config
from .logger import logger


class LawDatabase:
    """法律原文数据库管理类"""
    
    def __init__(self, mysql_client=None):
        """初始化法律数据库"""
        self.config = Config()
        self.mysql_client = mysql_client
        self.logger = logger
        self._init_tables()
    
    def _init_tables(self):
        """初始化法律原文表"""
        try:
            if not self.mysql_client:
                from mysql_qa import MySQLClient
                self.mysql_client = MySQLClient()
            
            # 创建法律原文表
            self.mysql_client.cursor.execute("""
                CREATE TABLE IF NOT EXISTS law_articles (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    law_id VARCHAR(100) NOT NULL COMMENT '法律唯一ID',
                    law_name VARCHAR(200) NOT NULL COMMENT '法律全称',
                    law_short_name VARCHAR(100) NOT NULL COMMENT '法律简称',
                    law_level VARCHAR(50) NOT NULL COMMENT '法律层级',
                    article_no VARCHAR(50) NOT NULL COMMENT '条文号',
                    article_title VARCHAR(500) COMMENT '条文标题',
                    article_content TEXT NOT NULL COMMENT '条文正文',
                    chapter VARCHAR(200) COMMENT '章节',
                    section VARCHAR(200) COMMENT '节',
                    subsection VARCHAR(200) COMMENT '款项',
                    effective_date DATE COMMENT '生效日期',
                    expiry_date DATE COMMENT '失效日期',
                    version VARCHAR(20) DEFAULT 'v1' COMMENT '版本号',
                    status VARCHAR(20) DEFAULT '现行有效' COMMENT '状态',
                    region VARCHAR(100) DEFAULT '全国' COMMENT '适用地域',
                    source_url VARCHAR(500) COMMENT '来源URL',
                    crawl_time DATETIME COMMENT '抓取时间',
                    last_verified DATETIME COMMENT '最近核验时间',
                    parent_article VARCHAR(50) COMMENT '父条文',
                    related_articles TEXT COMMENT '相关条文（JSON数组）',
                    referenced_laws TEXT COMMENT '引用法律（JSON数组）',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_law_id (law_id),
                    INDEX idx_law_short_name (law_short_name),
                    INDEX idx_article_no (article_no),
                    INDEX idx_status (status),
                    INDEX idx_effective_date (effective_date),
                    INDEX idx_region (region),
                    UNIQUE KEY uk_law_article (law_id, article_no, version)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='法律原文表'
            """)
            
            self.mysql_client.connection.commit()
            self.logger.info("法律原文表初始化成功")
        except pymysql.MySQLError as e:
            self.logger.error(f"初始化法律原文表失败: {e}")
            raise
    
    def insert_article(self, article: LawArticle) -> bool:
        """插入法律条文"""
        try:
            import json
            
            sql = """
                INSERT INTO law_articles (
                    law_id, law_name, law_short_name, law_level,
                    article_no, article_title, article_content,
                    chapter, section, subsection,
                    effective_date, expiry_date, version, status, region,
                    source_url, crawl_time, last_verified,
                    parent_article, related_articles, referenced_laws
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """
            
            values = (
                article.law_id,
                article.law_name,
                article.law_short_name,
                article.law_level.value,
                article.article_no,
                article.article_title,
                article.article_content,
                article.chapter,
                article.section,
                article.subsection,
                article.effective_date,
                article.expiry_date,
                article.version,
                article.status.value,
                article.region,
                article.source_url,
                article.crawl_time,
                article.last_verified,
                article.parent_article,
                json.dumps(article.related_articles, ensure_ascii=False),
                json.dumps(article.referenced_laws, ensure_ascii=False),
            )
            
            self.mysql_client.cursor.execute(sql, values)
            self.mysql_client.connection.commit()
            return True
        except pymysql.MySQLError as e:
            self.logger.error(f"插入法律条文失败: {e}")
            self.mysql_client.connection.rollback()
            return False
    
    def batch_insert_articles(self, articles: List[LawArticle]) -> int:
        """批量插入法律条文"""
        success_count = 0
        for article in articles:
            if self.insert_article(article):
                success_count += 1
        self.logger.info(f"批量插入完成：成功 {success_count}/{len(articles)} 条")
        return success_count
    
    def query_article(self, law_short_name: str, article_no: str, 
                     check_date: Optional[datetime] = None) -> Optional[LawArticle]:
        """查询指定法律的指定条文（返回有效版本）"""
        try:
            # 规范化条文号（去掉"第"和"条"）
            normalized_no = article_no.replace("第", "").replace("条", "").strip()
            
            sql = """
                SELECT * FROM law_articles
                WHERE law_short_name = %s 
                AND (article_no = %s OR article_no = %s OR article_no = %s)
                AND status = '现行有效'
            """
            
            params = [law_short_name, article_no, normalized_no, f"第{normalized_no}条"]
            
            # 如果指定了日期，添加时效性过滤
            if check_date:
                sql += """ AND (effective_date IS NULL OR effective_date <= %s)
                          AND (expiry_date IS NULL OR expiry_date > %s)
                """
                params.extend([check_date, check_date])
            
            sql += " ORDER BY version DESC LIMIT 1"
            
            self.mysql_client.cursor.execute(sql, params)
            row = self.mysql_client.cursor.fetchone()
            
            if row:
                return self._row_to_article(row)
            return None
        except pymysql.MySQLError as e:
            self.logger.error(f"查询法律条文失败: {e}")
            return None
    
    def query_articles_by_law(self, law_short_name: str, 
                             status: Optional[str] = "现行有效") -> List[LawArticle]:
        """查询指定法律的所有条文"""
        try:
            sql = "SELECT * FROM law_articles WHERE law_short_name = %s"
            params = [law_short_name]
            
            if status:
                sql += " AND status = %s"
                params.append(status)
            
            sql += " ORDER BY CAST(REGEXP_REPLACE(article_no, '[^0-9]', '') AS UNSIGNED)"
            
            self.mysql_client.cursor.execute(sql, params)
            rows = self.mysql_client.cursor.fetchall()
            
            return [self._row_to_article(row) for row in rows]
        except pymysql.MySQLError as e:
            self.logger.error(f"查询法律条文列表失败: {e}")
            return []
    
    def search_articles(self, keyword: str, law_short_name: Optional[str] = None,
                       region: Optional[str] = None, limit: int = 10) -> List[LawArticle]:
        """全文检索法律条文"""
        try:
            sql = """
                SELECT * FROM law_articles
                WHERE status = '现行有效'
                AND (article_content LIKE %s OR article_title LIKE %s)
            """
            params = [f"%{keyword}%", f"%{keyword}%"]
            
            if law_short_name:
                sql += " AND law_short_name = %s"
                params.append(law_short_name)
            
            if region:
                sql += " AND (region = %s OR region = '全国')"
                params.append(region)
            
            sql += " LIMIT %s"
            params.append(limit)
            
            self.mysql_client.cursor.execute(sql, params)
            rows = self.mysql_client.cursor.fetchall()
            
            return [self._row_to_article(row) for row in rows]
        except pymysql.MySQLError as e:
            self.logger.error(f"检索法律条文失败: {e}")
            return []
    
    def _row_to_article(self, row) -> LawArticle:
        """将数据库行转换为LawArticle对象"""
        import json
        
        # 获取列名
        columns = [desc[0] for desc in self.mysql_client.cursor.description]
        row_dict = dict(zip(columns, row))
        
        return LawArticle(
            law_id=row_dict['law_id'],
            law_name=row_dict['law_name'],
            law_short_name=row_dict['law_short_name'],
            law_level=LawLevel(row_dict['law_level']),
            article_no=row_dict['article_no'],
            article_title=row_dict.get('article_title'),
            article_content=row_dict['article_content'],
            chapter=row_dict.get('chapter'),
            section=row_dict.get('section'),
            subsection=row_dict.get('subsection'),
            effective_date=row_dict.get('effective_date'),
            expiry_date=row_dict.get('expiry_date'),
            version=row_dict.get('version', 'v1'),
            status=LawStatus(row_dict.get('status', '现行有效')),
            region=row_dict.get('region', '全国'),
            source_url=row_dict.get('source_url'),
            crawl_time=row_dict.get('crawl_time'),
            last_verified=row_dict.get('last_verified'),
            parent_article=row_dict.get('parent_article'),
            related_articles=json.loads(row_dict.get('related_articles', '[]')),
            referenced_laws=json.loads(row_dict.get('referenced_laws', '[]')),
        )
    
    def get_law_statistics(self) -> Dict:
        """获取法律数据库统计信息"""
        try:
            stats = {}
            
            # 总条文数
            self.mysql_client.cursor.execute(
                "SELECT COUNT(*) FROM law_articles WHERE status = '现行有效'"
            )
            stats['total_articles'] = self.mysql_client.cursor.fetchone()[0]
            
            # 按法律分组统计
            self.mysql_client.cursor.execute("""
                SELECT law_short_name, COUNT(*) as count
                FROM law_articles
                WHERE status = '现行有效'
                GROUP BY law_short_name
                ORDER BY count DESC
            """)
            stats['by_law'] = {row[0]: row[1] for row in self.mysql_client.cursor.fetchall()}
            
            # 按层级统计
            self.mysql_client.cursor.execute("""
                SELECT law_level, COUNT(*) as count
                FROM law_articles
                WHERE status = '现行有效'
                GROUP BY law_level
            """)
            stats['by_level'] = {row[0]: row[1] for row in self.mysql_client.cursor.fetchall()}
            
            return stats
        except pymysql.MySQLError as e:
            self.logger.error(f"获取统计信息失败: {e}")
            return {}
