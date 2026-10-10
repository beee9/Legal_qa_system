"""
法律原文结构化数据模型
提供法律条文的完整元数据支持，包括版本、时效性、地域等
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from enum import Enum


class LawLevel(Enum):
    """法律层级"""
    CONSTITUTION = "宪法"
    LAW = "法律"
    ADMINISTRATIVE_REGULATION = "行政法规"
    DEPARTMENT_REGULATION = "部门规章"
    JUDICIAL_INTERPRETATION = "司法解释"
    LOCAL_REGULATION = "地方性法规"
    GUIDING_CASE = "指导性案例"


class LawStatus(Enum):
    """法律状态"""
    EFFECTIVE = "现行有效"
    EXPIRED = "已废止"
    AMENDED = "已修订"
    DRAFT = "草案"


@dataclass
class LawArticle:
    """法律条文数据模型"""
    # 基础信息
    law_id: str  # 法律唯一ID，如 "minfa_2020_v1"
    law_name: str  # 法律名称，如 "中华人民共和国民法典"
    law_short_name: str  # 法律简称，如 "民法典"
    law_level: LawLevel  # 法律层级
    
    # 条文信息
    article_no: str  # 条文号，如 "509" 或 "第五百零九条"
    article_title: Optional[str] = None  # 条文标题
    article_content: str = ""  # 条文正文
    
    # 结构化层级
    chapter: Optional[str] = None  # 编/章，如 "第三编 合同"
    section: Optional[str] = None  # 节，如 "第一章 一般规定"
    subsection: Optional[str] = None  # 款/项/目
    
    # 时效性
    effective_date: Optional[datetime] = None  # 生效日期
    expiry_date: Optional[datetime] = None  # 失效日期
    version: str = "v1"  # 版本号
    status: LawStatus = LawStatus.EFFECTIVE  # 现行状态
    
    # 地域
    region: str = "全国"  # 适用地域，如 "全国" "北京市" "广东省"
    
    # 来源追溯
    source_url: Optional[str] = None  # 权威来源URL
    crawl_time: Optional[datetime] = None  # 抓取时间
    last_verified: Optional[datetime] = None  # 最近核验时间
    
    # 关联关系
    parent_article: Optional[str] = None  # 父条文（用于款项）
    related_articles: List[str] = None  # 相关条文
    referenced_laws: List[str] = None  # 引用的其他法律
    
    def __post_init__(self):
        """初始化默认值"""
        if self.related_articles is None:
            self.related_articles = []
        if self.referenced_laws is None:
            self.referenced_laws = []
    
    def is_effective(self, check_date: Optional[datetime] = None) -> bool:
        """判断条文在指定日期是否有效"""
        if check_date is None:
            check_date = datetime.now()
        
        # 检查状态
        if self.status == LawStatus.EXPIRED:
            return False
        
        # 检查生效日期
        if self.effective_date and check_date < self.effective_date:
            return False
        
        # 检查失效日期
        if self.expiry_date and check_date >= self.expiry_date:
            return False
        
        return True
    
    def get_full_article_no(self) -> str:
        """获取完整条文号，如 "第509条" "第五百零九条" """
        if not self.article_no:
            return ""
        # 如果已经包含"第"和"条"，直接返回
        if self.article_no.startswith("第") and self.article_no.endswith("条"):
            return self.article_no
        # 否则补充
        return f"第{self.article_no}条"
    
    def to_dict(self) -> dict:
        """转换为字典格式，用于存储到向量数据库"""
        return {
            "law_id": self.law_id,
            "law_name": self.law_name,
            "law_short_name": self.law_short_name,
            "law_level": self.law_level.value,
            "article_no": self.article_no,
            "article_title": self.article_title,
            "article_content": self.article_content,
            "chapter": self.chapter,
            "section": self.section,
            "subsection": self.subsection,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "version": self.version,
            "status": self.status.value,
            "region": self.region,
            "source_url": self.source_url,
            "crawl_time": self.crawl_time.isoformat() if self.crawl_time else None,
            "last_verified": self.last_verified.isoformat() if self.last_verified else None,
            "parent_article": self.parent_article,
            "related_articles": self.related_articles,
            "referenced_laws": self.referenced_laws,
        }
    
    def get_display_text(self, include_metadata: bool = True) -> str:
        """获取用于显示的文本"""
        lines = []
        
        # 法律名称和条文号
        header = f"《{self.law_short_name}》{self.get_full_article_no()}"
        if self.article_title:
            header += f" {self.article_title}"
        lines.append(header)
        
        # 条文内容
        lines.append(self.article_content)
        
        # 元数据（可选）
        if include_metadata:
            metadata = []
            if self.chapter:
                metadata.append(f"所属：{self.chapter}")
            if self.section:
                metadata.append(f" - {self.section}")
            if self.effective_date:
                metadata.append(f"生效日期：{self.effective_date.strftime('%Y年%m月%d日')}")
            if self.status != LawStatus.EFFECTIVE:
                metadata.append(f"状态：{self.status.value}")
            if self.region != "全国":
                metadata.append(f"适用地域：{self.region}")
            
            if metadata:
                lines.append("")
                lines.append("【" + "，".join(metadata) + "】")
        
        return "\n".join(lines)
    
    def get_search_text(self) -> str:
        """获取用于检索的完整文本（包含所有可检索字段）"""
        parts = [
            self.law_name,
            self.law_short_name,
            self.get_full_article_no(),
            self.article_title or "",
            self.chapter or "",
            self.section or "",
            self.article_content,
        ]
        return " ".join(filter(None, parts))
