"""
法律智能体工具集
提供金额计算、文书生成、时效性检查等工具
"""
import re
from typing import Dict, Optional
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base import logger, LawDatabase


class LegalTools:
    """法律智能体工具集"""
    
    def __init__(self):
        self.logger = logger
        self.law_db = LawDatabase()
    
    # ========== 金额计算工具 ==========
    
    def calculate_double_salary(self, months: int, monthly_salary: float) -> Dict:
        """
        计算未签订劳动合同的双倍工资差额
        
        法律依据：《劳动合同法》第82条
        - 超过1个月不满1年未签合同：支付双倍工资
        - 最多计算11个月
        """
        if months <= 0 or months > 11:
            return {"error": "可主张月数应在1-11个月之间"}
        
        total = months * monthly_salary
        
        return {
            "months": months,
            "monthly_salary": monthly_salary,
            "total_amount": total,
            "legal_basis": "《中华人民共和国劳动合同法》第82条",
            "explanation": f"用人单位自用工之日起超过一个月不满一年未与劳动者订立书面劳动合同的，应当向劳动者每月支付二倍的工资。您可主张 {months} 个月的双倍工资差额，共计 {total:.2f} 元。"
        }
    
    def calculate_economic_compensation(self, work_years: float, monthly_salary: float, 
                                       reason: str = "违法解除") -> Dict:
        """
        计算经济补偿金
        
        法律依据：《劳动合同法》第47条、第87条
        - 正常解除：N（工作年限）
        - 违法解除：2N
        - 每满1年支付1个月工资
        - 6个月以上不满1年按1年算，不满6个月按0.5年算
        """
        # 计算 N
        if work_years < 0.5:
            n = 0.5
        else:
            n = int(work_years) + (0.5 if work_years % 1 >= 0.5 else 0)
        
        # 违法解除是 2N
        multiplier = 2 if reason == "违法解除" else 1
        
        total = n * multiplier * monthly_salary
        
        return {
            "work_years": work_years,
            "compensation_months": n * multiplier,
            "monthly_salary": monthly_salary,
            "total_amount": total,
            "legal_basis": "《中华人民共和国劳动合同法》第47条、第87条",
            "explanation": f"根据您的工作年限 {work_years} 年和月工资 {monthly_salary} 元，{reason}情形下可主张 {n * multiplier} 个月工资的经济补偿金，共计 {total:.2f} 元。"
        }
    
    def calculate_overtime_pay(self, hours: float, hourly_wage: float, 
                              day_type: str = "工作日") -> Dict:
        """
        计算加班费
        
        法律依据：《劳动法》第44条
        - 工作日加班：1.5倍
        - 休息日加班：2倍
        - 法定节假日加班：3倍
        """
        multipliers = {
            "工作日": 1.5,
            "休息日": 2.0,
            "法定节假日": 3.0
        }
        
        if day_type not in multipliers:
            return {"error": f"day_type 应为：{list(multipliers.keys())}"}
        
        multiplier = multipliers[day_type]
        total = hours * hourly_wage * multiplier
        
        return {
            "hours": hours,
            "hourly_wage": hourly_wage,
            "day_type": day_type,
            "multiplier": multiplier,
            "total_amount": total,
            "legal_basis": "《中华人民共和国劳动法》第44条",
            "explanation": f"{day_type}加班 {hours} 小时，时薪 {hourly_wage} 元，按 {multiplier} 倍计算，共计加班费 {total:.2f} 元。"
        }
    
    def calculate_severance_pay(self, work_years: float, monthly_salary: float) -> Dict:
        """
        计算解除劳动合同的经济补偿金（N）
        与 calculate_economic_compensation 类似，但只计算 N，不考虑违法解除的 2N
        """
        if work_years < 0.5:
            n = 0.5
        else:
            n = int(work_years) + (0.5 if work_years % 1 >= 0.5 else 0)
        
        total = n * monthly_salary
        
        return {
            "work_years": work_years,
            "compensation_months": n,
            "monthly_salary": monthly_salary,
            "total_amount": total,
            "legal_basis": "《中华人民共和国劳动合同法》第47条",
            "explanation": f"工作 {work_years} 年，月工资 {monthly_salary} 元，经济补偿金为 {n} 个月工资，共计 {total:.2f} 元。"
        }
    
    # ========== 时效性检查工具 ==========
    
    def check_law_validity(self, law_short_name: str, article_no: str, 
                          check_date: Optional[datetime] = None) -> Dict:
        """
        检查法律条文是否在指定日期有效
        """
        if check_date is None:
            check_date = datetime.now()
        
        article = self.law_db.query_article(law_short_name, article_no, check_date)
        
        if article is None:
            return {
                "valid": False,
                "reason": f"未找到《{law_short_name}》第{article_no}条",
                "suggestion": "请核实法律名称和条文号是否正确"
            }
        
        is_valid = article.is_effective(check_date)
        
        if not is_valid:
            return {
                "valid": False,
                "law_name": article.law_name,
                "article_no": article.article_no,
                "status": article.status.value,
                "expiry_date": article.expiry_date.isoformat() if article.expiry_date else None,
                "reason": f"该法条已于 {article.expiry_date} 失效" if article.expiry_date else "该法条已失效",
                "suggestion": "请引用现行有效的法律条文"
            }
        
        return {
            "valid": True,
            "law_name": article.law_name,
            "article_no": article.article_no,
            "status": article.status.value,
            "effective_date": article.effective_date.isoformat() if article.effective_date else None,
            "content": article.article_content
        }
    
    def detect_obsolete_laws(self, text: str) -> Dict:
        """
        检测文本中是否引用了已废止的法律
        常见例子：《合同法》已被《民法典》合同编替代
        """
        obsolete_laws = {
            "合同法": {
                "replaced_by": "《中华人民共和国民法典》第三编 合同",
                "expiry_date": "2021-01-01"
            },
            "物权法": {
                "replaced_by": "《中华人民共和国民法典》第二编 物权",
                "expiry_date": "2021-01-01"
            },
            "婚姻法": {
                "replaced_by": "《中华人民共和国民法典》第五编 婚姻家庭",
                "expiry_date": "2021-01-01"
            },
            "继承法": {
                "replaced_by": "《中华人民共和国民法典》第六编 继承",
                "expiry_date": "2021-01-01"
            },
            "侵权责任法": {
                "replaced_by": "《中华人民共和国民法典》第七编 侵权责任",
                "expiry_date": "2021-01-01"
            }
        }
        
        detected = []
        for obsolete, info in obsolete_laws.items():
            if obsolete in text or f"《{obsolete}》" in text:
                detected.append({
                    "obsolete_law": obsolete,
                    "replaced_by": info["replaced_by"],
                    "expiry_date": info["expiry_date"],
                    "warning": f"《{obsolete}》已于 {info['expiry_date']} 废止，应引用 {info['replaced_by']}"
                })
        
        return {
            "has_obsolete": len(detected) > 0,
            "detected_laws": detected
        }
    
    # ========== 文书生成工具 ==========
    
    def generate_arbitration_application(self, facts: Dict) -> str:
        """
        生成劳动仲裁申请书
        
        facts 应包含：
        - applicant_name: 申请人姓名
        - company_name: 公司名称
        - claim_type: 请求类型（如"双倍工资"、"经济补偿金"）
        - claim_amount: 请求金额
        - facts_description: 事实描述
        """
        template = f"""
劳动仲裁申请书

申请人：{facts.get('applicant_name', '___________')}
被申请人：{facts.get('company_name', '___________')}

仲裁请求：
1. 裁决被申请人支付申请人{facts.get('claim_type', '_______')} {facts.get('claim_amount', '_______')} 元；
2. 本案仲裁费用由被申请人承担。

事实与理由：
{facts.get('facts_description', '（请详细描述劳动关系建立时间、工作内容、工资支付情况、争议发生经过等事实）')}

综上所述，被申请人的行为严重侵害了申请人的合法权益，特依据《中华人民共和国劳动争议调解仲裁法》向贵委提起仲裁，请求依法裁决。

此致
____________劳动人事争议仲裁委员会

申请人：{facts.get('applicant_name', '___________')}
日期：{datetime.now().strftime('%Y年%m月%d日')}

附：证据清单
"""
        return template.strip()
    
    def generate_evidence_list(self, evidence_items: list) -> str:
        """
        生成证据清单
        
        evidence_items: [
            {"name": "劳动合同", "copies": 1, "pages": 3},
            {"name": "工资银行流水", "copies": 1, "pages": 12}
        ]
        """
        if not evidence_items:
            evidence_items = [
                {"name": "劳动合同", "copies": "__", "pages": "__"},
                {"name": "工资条/银行流水", "copies": "__", "pages": "__"},
                {"name": "考勤记录", "copies": "__", "pages": "__"},
                {"name": "解除劳动关系通知书", "copies": "__", "pages": "__"}
            ]
        
        lines = ["证据清单\n"]
        for i, item in enumerate(evidence_items, 1):
            lines.append(f"{i}. {item['name']}  {item['copies']}份  共{item['pages']}页")
        
        return "\n".join(lines)
    
    def generate_demand_letter(self, facts: Dict) -> str:
        """
        生成律师函/催告函
        """
        template = f"""
催告函

{facts.get('recipient_name', '___________')}：

兹有{facts.get('sender_name', '___________')}与贵方存在{facts.get('dispute_type', '_______')}纠纷，现将有关事项函告如下：

一、基本事实
{facts.get('facts_description', '（请描述争议事实）')}

二、法律分析
根据《{facts.get('legal_basis', '_______')}》相关规定，{facts.get('legal_analysis', '（请描述法律依据和分析）')}

三、催告要求
现正式催告贵方于收到本函之日起{facts.get('deadline_days', '7')}日内：
{facts.get('demands', '1. （请列明具体要求）')}

逾期未履行，我方将依法通过诉讼等法律途径维护合法权益，由此产生的诉讼费、律师费等一切费用均由贵方承担。

特此函告！

{facts.get('sender_name', '___________')}
{datetime.now().strftime('%Y年%m月%d日')}
"""
        return template.strip()
    
    # ========== 风险评估工具 ==========
    
    def assess_litigation_risk(self, case_type: str, evidence_strength: str) -> Dict:
        """
        诉讼风险评估
        
        case_type: 案件类型（劳动争议、合同纠纷等）
        evidence_strength: 证据强度（强、中、弱）
        """
        risk_matrix = {
            "劳动争议": {
                "强": {"win_rate": 0.85, "risk_level": "低", "suggestion": "证据充分，建议仲裁"},
                "中": {"win_rate": 0.60, "risk_level": "中", "suggestion": "建议补充证据后再仲裁"},
                "弱": {"win_rate": 0.30, "risk_level": "高", "suggestion": "证据不足，建议先协商或补充证据"}
            },
            "合同纠纷": {
                "强": {"win_rate": 0.80, "risk_level": "低", "suggestion": "证据充分，可起诉"},
                "中": {"win_rate": 0.55, "risk_level": "中", "suggestion": "建议补充证据或先调解"},
                "弱": {"win_rate": 0.25, "risk_level": "高", "suggestion": "证据不足，胜诉可能性较低"}
            }
        }
        
        if case_type not in risk_matrix or evidence_strength not in risk_matrix[case_type]:
            return {"error": "无效的案件类型或证据强度"}
        
        result = risk_matrix[case_type][evidence_strength]
        
        return {
            "case_type": case_type,
            "evidence_strength": evidence_strength,
            "estimated_win_rate": result["win_rate"],
            "risk_level": result["risk_level"],
            "suggestion": result["suggestion"]
        }
    
    def calculate_statute_of_limitations(self, dispute_type: str, 
                                        dispute_date: datetime) -> Dict:
        """
        计算诉讼时效
        
        dispute_type: 争议类型
        - 劳动争议：1年（从知道或应当知道权利被侵害之日起）
        - 一般民事纠纷：3年
        - 特殊情况：具体分析
        """
        limitations = {
            "劳动争议": 365,  # 1年
            "一般民事": 1095,  # 3年
            "人身损害": 1095,  # 3年
            "环境污染": 1095,  # 3年
        }
        
        days = limitations.get(dispute_type, 1095)
        deadline = dispute_date + timedelta(days=days)
        remaining = (deadline - datetime.now()).days
        
        return {
            "dispute_type": dispute_type,
            "dispute_date": dispute_date.strftime("%Y-%m-%d"),
            "limitation_days": days,
            "deadline": deadline.strftime("%Y-%m-%d"),
            "remaining_days": remaining,
            "is_expired": remaining < 0,
            "warning": "诉讼时效已过！" if remaining < 0 else 
                      f"还剩 {remaining} 天，请尽快起诉！" if remaining < 30 else 
                      f"还剩 {remaining} 天"
        }


if __name__ == "__main__":
    tools = LegalTools()
    
    # 测试金额计算
    print("=" * 60)
    print("测试1：双倍工资计算")
    print("=" * 60)
    result = tools.calculate_double_salary(months=11, monthly_salary=8000)
    print(result["explanation"])
    
    print("\n" + "=" * 60)
    print("测试2：经济补偿金计算")
    print("=" * 60)
    result = tools.calculate_economic_compensation(work_years=3.5, monthly_salary=10000, reason="违法解除")
    print(result["explanation"])
    
    print("\n" + "=" * 60)
    print("测试3：已废止法律检测")
    print("=" * 60)
    text = "根据《合同法》第94条和《物权法》第23条..."
    result = tools.detect_obsolete_laws(text)
    if result["has_obsolete"]:
        for law in result["detected_laws"]:
            print(law["warning"])
    
    print("\n" + "=" * 60)
    print("测试4：劳动仲裁申请书生成")
    print("=" * 60)
    facts = {
        "applicant_name": "张三",
        "company_name": "某科技公司",
        "claim_type": "双倍工资差额",
        "claim_amount": "88,000",
        "facts_description": "申请人于2023年1月1日入职被申请人处，从事软件开发工作，月工资8000元。双方一直未签订书面劳动合同。2024年12月31日，被申请人口头通知申请人解除劳动关系。"
    }
    doc = tools.generate_arbitration_application(facts)
    print(doc)
    
    print("\n" + "=" * 60)
    print("测试5：诉讼时效计算")
    print("=" * 60)
    result = tools.calculate_statute_of_limitations(
        dispute_type="劳动争议",
        dispute_date=datetime(2024, 1, 1)
    )
    print(f"{result['dispute_type']} 时效：{result['limitation_days']} 天")
    print(f"争议发生日期：{result['dispute_date']}")
    print(f"诉讼时效截止：{result['deadline']}")
    print(f"状态：{result['warning']}")
