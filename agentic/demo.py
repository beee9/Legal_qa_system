"""
AI-Native 智能体系统快速测试
演示多步推理、工具调用、主动追问的完整流程
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentic.legal_tools import LegalTools
from base import logger

# 简化版：不依赖 LangGraph，展示核心思路
class SimpleAgentDemo:
    """简化版智能体演示（不需要安装 LangGraph）"""
    
    def __init__(self):
        self.tools = LegalTools()
        self.logger = logger
    
    def demo_scenario_1(self):
        """场景1：劳动争议 - 展示主动追问和工具调用"""
        print("\n" + "="*70)
        print("[场景1] 劳动争议咨询")
        print("="*70)
        
        query = "老板拖欠我两个月工资，我该怎么办？"
        print(f"\n[用户] {query}")
        
        # Step 1: 识别缺失信息
        print("\n[AI分析] 识别到以下关键信息缺失，需要追问...")
        missing_info = [
            "是否签订书面劳动合同？",
            "拖欠金额是多少？拖欠多长时间？",
            "公司注册地或工作地在哪个省市？",
            "是否有工资条、转账记录、打卡记录等证据？"
        ]
        
        for i, info in enumerate(missing_info, 1):
            print(f"   {i}. {info}")
        
        # 模拟用户补充信息
        print("\n[用户补充]")
        user_input = """
        - 没有签订书面劳动合同
        - 月薪 8000 元，拖欠 2 个月
        - 工作了 11 个月，公司在北京
        - 有银行转账记录和钉钉打卡记录
        """
        print(user_input)
        
        # Step 2: 调用工具计算
        print("\n[AI工具调用]")
        
        print("\n   [工具1] 计算双倍工资差额...")
        result1 = self.tools.calculate_double_salary(months=11, monthly_salary=8000)
        print(f"   >> {result1['explanation']}")
        
        print("\n   [工具2] 计算拖欠工资...")
        owed_salary = 8000 * 2
        print(f"   >> 拖欠工资：{owed_salary} 元")
        
        print("\n   [工具3] 评估诉讼风险...")
        result3 = self.tools.assess_litigation_risk(
            case_type="劳动争议",
            evidence_strength="强"
        )
        print(f"   >> 胜诉概率：{result3['estimated_win_rate']*100:.0f}%")
        print(f"   >> 风险等级：{result3['risk_level']}")
        
        print("\n   [工具4] 检查诉讼时效...")
        from datetime import datetime, timedelta
        result4 = self.tools.calculate_statute_of_limitations(
            dispute_type="劳动争议",
            dispute_date=datetime.now() - timedelta(days=60)
        )
        print(f"   >> {result4['warning']}")
        
        # Step 3: 生成综合答案
        print("\n[AI生成最终方案]")
        print("-" * 70)
        
        answer = f"""
根据您的情况，我为您分析如下：

一、法律分析
1. 未签劳动合同：根据《劳动合同法》第82条，您可主张双倍工资差额
2. 拖欠工资：根据《劳动合同法》第30条，您可要求支付拖欠工资

二、金额计算（已自动计算）
- 拖欠工资：{owed_salary:,} 元
- 双倍工资差额：{result1['total_amount']:,.0f} 元
- 合计可主张：{owed_salary + result1['total_amount']:,} 元

三、维权步骤
1. 先与公司协商解决（保留协商记录）
2. 如协商不成，向北京市劳动仲裁委员会申请劳动仲裁
3. 仲裁地址：（需查询具体区县仲裁委）
4. 准备证据材料：银行转账记录、钉钉打卡记录、工作邮件/微信聊天记录

四、胜诉概率评估
- 证据强度：强（有银行流水和打卡记录）
- 预计胜诉率：{result3['estimated_win_rate']*100:.0f}%
- 风险等级：{result3['risk_level']}
- 建议：{result3['suggestion']}

五、时效提醒
- 劳动仲裁时效：1年（从知道权利被侵害之日起）
- 您的时效剩余：{result4['remaining_days']} 天
- {result4['warning']}

六、我已为您生成《劳动仲裁申请书》模板（见附件）

【免责声明】以上内容仅供参考，不构成法律意见。具体金额以仲裁委认定为准。
        """
        print(answer)
        
        # Step 4: 生成文书
        print("\n[附件] 劳动仲裁申请书")
        print("-" * 70)
        
        facts = {
            "applicant_name": "张三（请替换为真实姓名）",
            "company_name": "某科技公司（北京）",
            "claim_type": "双倍工资差额及拖欠工资",
            "claim_amount": f"{owed_salary + result1['total_amount']:,}",
            "facts_description": f"""
申请人于 2024年1月1日 入职被申请人处，从事软件开发工作，月工资 8,000 元。
双方一直未签订书面劳动合同。
2024年12月1日起，被申请人拖欠申请人工资至今，共计拖欠 2 个月工资 {owed_salary:,} 元。
2024年12月31日，被申请人口头通知申请人解除劳动关系。

根据《劳动合同法》第82条，被申请人应支付申请人双倍工资差额 {result1['total_amount']:,.0f} 元（11个月）。
根据《劳动合同法》第30条，被申请人应支付拖欠工资 {owed_salary:,} 元。
            """.strip()
        }
        
        doc = self.tools.generate_arbitration_application(facts)
        print(doc[:800] + "\n...\n（完整版见文书生成工具）")
    
    def demo_scenario_2(self):
        """场景2：法条精确查询 - 展示时效性检查"""
        print("\n" + "="*70)
        print("🎯 场景2：法条查询 + 时效性自动检查")
        print("="*70)
        
        query = "合同法第94条是什么？"
        print(f"\n👤 用户问题：{query}")
        
        print("\n🔍 AI 检索中...")
        print("   → 识别到用户查询《合同法》第94条")
        
        print("\n🔧 [工具] 时效性检查...")
        result = self.tools.detect_obsolete_laws("《合同法》第94条")
        
        if result['has_obsolete']:
            print(f"   ⚠️  检测到已废止法律！")
            for law in result['detected_laws']:
                print(f"   ⚠️  {law['warning']}")
        
        print("\n📋 AI 回答：")
        print("-" * 70)
        answer = """
【重要提示】《中华人民共和国合同法》已于 2021年1月1日 废止。

您查询的《合同法》第94条关于"合同解除"的规定，现已被《民法典》第563条替代。

《民法典》第563条规定：
有下列情形之一的，当事人可以解除合同：
（一）因不可抗力致使不能实现合同目的；
（二）在履行期限届满前，当事人一方明确表示或者以自己的行为表明不履行主要债务；
（三）当事人一方迟延履行主要债务，经催告后在合理期限内仍未履行；
（四）当事人一方迟延履行债务或者有其他违约行为致使不能实现合同目的；
（五）法律规定的其他情形。

【法律依据】《中华人民共和国民法典》第563条（现行有效）
【提示】请在实务中引用《民法典》相关条文，而非已废止的《合同法》。
        """
        print(answer)
    
    def demo_scenario_3(self):
        """场景3：文书生成 + 证据清单"""
        print("\n" + "="*70)
        print("🎯 场景3：一键生成法律文书")
        print("="*70)
        
        query = "帮我生成一份催告函，对方欠我5万块钱货款3个月了"
        print(f"\n👤 用户问题：{query}")
        
        print("\n🤖 AI 分析：")
        print("   → 识别为文书生成需求")
        print("   → 类型：催告函")
        print("   → 争议：拖欠货款")
        
        print("\n🔧 [工具] 生成催告函...")
        
        facts = {
            "recipient_name": "某公司（请替换为实际名称）",
            "sender_name": "您的姓名/公司名称",
            "dispute_type": "买卖合同",
            "facts_description": """
双方于2024年9月1日签订《买卖合同》，约定我方向贵方供应货物，总价款50,000元。
货物已于2024年9月15日交付完毕，贵方签收确认。
合同约定付款期限为货到后30日内付清，即2024年10月15日前。
截至今日，贵方仍未支付任何款项，已逾期3个月。
            """.strip(),
            "legal_basis": "中华人民共和国民法典",
            "legal_analysis": "根据《民法典》第509条，当事人应当按照约定全面履行自己的义务。贵方未按约定支付货款，已构成违约。",
            "deadline_days": "7",
            "demands": """
1. 立即支付拖欠货款 50,000 元；
2. 支付逾期利息（按全国银行间同业拆借中心公布的贷款市场报价利率计算）；
3. 承担因催收产生的一切费用（包括但不限于律师费、差旅费等）。
            """.strip()
        }
        
        doc = self.tools.generate_demand_letter(facts)
        
        print("\n📄 生成的催告函：")
        print("-" * 70)
        print(doc)
        
        print("\n\n📋 [工具] 生成证据清单...")
        evidence = [
            {"name": "买卖合同", "copies": 1, "pages": 5},
            {"name": "货物交付签收单", "copies": 1, "pages": 1},
            {"name": "微信/邮件催款记录", "copies": 1, "pages": 3},
            {"name": "公司营业执照复印件", "copies": 1, "pages": 1}
        ]
        
        evidence_list = self.tools.generate_evidence_list(evidence)
        print(evidence_list)


def main():
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("\n" + "="*70)
    print("   AI-Native 法律智能体系统演示")
    print("   Legal QA System - Agentic Workflow Demo")
    print("="*70)
    
    demo = SimpleAgentDemo()
    
    # 运行三个演示场景
    demo.demo_scenario_1()
    
    input("\n按回车键继续下一个场景...")
    demo.demo_scenario_2()
    
    input("\n按回车键继续下一个场景...")
    demo.demo_scenario_3()
    
    print("\n" + "="*70)
    print("✅ 演示完成！")
    print("="*70)
    
    print("\n📊 AI-Native 模式 vs 传统模式对比：")
    print("-" * 70)
    print("| 维度           | 传统模式      | AI-Native 模式    |")
    print("|---------------|-------------|------------------|")
    print("| 主动追问       | ❌          | ✅ 自动识别缺失信息 |")
    print("| 金额计算       | ❌          | ✅ 自动计算       |")
    print("| 文书生成       | ❌          | ✅ 一键生成       |")
    print("| 时效性检查     | ❌          | ✅ 自动检测废止法律|")
    print("| 风险评估       | ❌          | ✅ 量化评估       |")
    print("| 多步推理       | ❌          | ✅ 逐步分析       |")
    print("-" * 70)
    
    print("\n💡 下一步：")
    print("   1. 安装 LangGraph：pip install langgraph langchain-core")
    print("   2. 运行完整版：python agentic/legal_agent_system.py")
    print("   3. 集成到 Web 系统：参考 agentic/README.md")
    print("   4. 查看详细文档：agentic/README.md")
    
    print("\n🎉 开始体验 AI-Native 法律咨询吧！")


if __name__ == "__main__":
    main()
