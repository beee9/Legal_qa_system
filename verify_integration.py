"""
快速验证意图分类器集成
"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("验证意图分类器集成")
print("=" * 70)

# 1. 测试分类器独立加载
print("\n[1/3] 测试分类器独立加载...")
try:
    from rag_qa.core.legal_query_classifier import LegalQueryClassifier
    model_path = Path("rag_qa/core/legal_intent_classifier/final_model")
    classifier = LegalQueryClassifier(model_path=model_path)
    print("✓ 分类器加载成功")

    # 快速测试
    test_query = "民法典第509条是什么"
    result = classifier.predict_category(test_query)
    print(f"✓ 测试查询: '{test_query}' -> {result}")

except Exception as e:
    print(f"✗ 分类器加载失败: {e}")
    sys.exit(1)

# 2. 检查 new_main.py 是否包含分类器代码
print("\n[2/3] 检查 new_main.py 集成...")
try:
    with open("new_main.py", "r", encoding="utf-8") as f:
        content = f.read()

    has_import = "LegalQueryClassifier" in content
    has_init = "self.query_classifier" in content
    has_logic = "intent ==" in content or "意图分类" in content

    if has_import and has_init and has_logic:
        print("✓ new_main.py 已集成分类器代码")
    else:
        print(f"✗ new_main.py 集成不完整:")
        print(f"  - 导入分类器: {'✓' if has_import else '✗'}")
        print(f"  - 初始化分类器: {'✓' if has_init else '✗'}")
        print(f"  - 分类逻辑: {'✓' if has_logic else '✗'}")

except Exception as e:
    print(f"✗ 检查失败: {e}")

# 3. 检查备份文件
print("\n[3/3] 检查备份...")
if Path("new_main_backup.py").exists():
    print("✓ 原文件已备份: new_main_backup.py")
else:
    print("✗ 未找到备份文件")

print("\n" + "=" * 70)
print("验证完成！")
print("=" * 70)
print("\n下一步操作：")
print("1. 确保 MySQL 和 Redis 服务已启动")
print("2. 运行: python app.py")
print("3. 访问: http://localhost:5001")
print("4. 观察日志中的意图分类结果")
