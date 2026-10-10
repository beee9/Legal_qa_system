"""
增强的问答数据模型
提供完整的法律问答元数据支持
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict


@dataclass
class EnhancedQA:
    """增强的法律问答数据模型"""
    # 基础问答
    question: str  # 用户问题
    answer: str  # 通俗解释
    subject: str  # 法律领域分类
    
    # 法律依据
    legal_basis: Optional[str] = None  # 法律依据概述
    article_refs: List[Dict] = None  # 引用条文列表 [{"law": "民法典", "article": "509"}]
    
    # 适用条件和例外
    conditions: Optional[str] = None  # 适用条件
    exceptions: Optional[str] = None  # 例外情形
    
    # 实操指导
    procedure: Optional[str] = None  # 办理/维权步骤
    evidence_needed: Optional[str] = None  # 所需证据
    risk_notice: Optional[str] = None  # 风险提示
    
    # 时效性和地域
    effective_date: Optional[datetime] = None  # 适用起始时间
    region: str = "全国"  # 适用地域
    
    # 数据质量
    source_type: str = "human"  # 来源类型：human/model_generated/verified
    verified: bool = False  # 是否经过人工审核
    last_verified_at: Optional[datetime] = None  # 最近核验时间
    confidence_score: float = 1.0  # 置信度分数
    
    # 追溯
    original_question: Optional[str] = None  # 原始问题（清洗前）
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """初始化默认值"""
        if self.article_refs is None:
            self.article_refs = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "question": self.question,
            "answer": self.answer,
            "subject": self.subject,
            "legal_basis": self.legal_basis,
            "article_refs": self.article_refs,
            "conditions": self.conditions,
            "exceptions": self.exceptions,
            "procedure": self.procedure,
            "evidence_needed": self.evidence_needed,
            "risk_notice": self.risk_notice,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "region": self.region,
            "source_type": self.source_type,
            "verified": self.verified,
            "last_verified_at": self.last_verified_at.isoformat() if self.last_verified_at else None,
            "confidence_score": self.confidence_score,
            "original_question": self.original_question,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def get_full_answer(self) -> str:
        """获取完整答案（包含所有补充信息）"""
        parts = [self.answer]
        
        if self.legal_basis:
            parts.append(f"\n\n【法律依据】\n{self.legal_basis}")
        
        if self.article_refs:
            refs_text = "、".join([f"《{ref['law']}》第{ref['article']}条" 
                                   for ref in self.article_refs])
            parts.append(f"\n\n【相关条文】\n{refs_text}")
        
        if self.conditions:
            parts.append(f"\n\n【适用条件】\n{self.conditions}")
        
        if self.exceptions:
            parts.append(f"\n\n【例外情形】\n{self.exceptions}")
        
        if self.procedure:
            parts.append(f"\n\n【办理步骤】\n{self.procedure}")
        
        if self.evidence_needed:
            parts.append(f"\n\n【所需证据】\n{self.evidence_needed}")
        
        if self.risk_notice:
            parts.append(f"\n\n【风险提示】\n{self.risk_notice}")
        
        # 添加地域和时效说明
        metadata_parts = []
        if self.region != "全国":
            metadata_parts.append(f"适用地域：{self.region}")
        if self.effective_date:
            metadata_parts.append(f"适用时间：{self.effective_date.strftime('%Y年%m月%d日')}起")
        
        if metadata_parts:
            parts.append(f"\n\n【说明】\n{' | '.join(metadata_parts)}")
        
        return "".join(parts)
