"""
AI-Native 改造自动化执行助手
根据 AI_NATIVE_ROADMAP.md 自动检查环境、执行任务、更新进度
"""
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
ROADMAP_FILE = PROJECT_ROOT / "AI_NATIVE_ROADMAP.md"


class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'


def print_success(msg):
    print(f"{Colors.GREEN}[OK] {msg}{Colors.END}")


def print_warning(msg):
    print(f"{Colors.YELLOW}[WARNING] {msg}{Colors.END}")


def print_error(msg):
    print(f"{Colors.RED}[ERROR] {msg}{Colors.END}")


def print_info(msg):
    print(f"{Colors.BLUE}[INFO] {msg}{Colors.END}")


def print_header(title):
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}{Colors.END}\n")


class RoadmapExecutor:
    """路线图执行器"""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.tasks_completed = []
        self.tasks_failed = []
    
    def run(self):
        """运行完整流程"""
        print_header("AI-Native 改造执行助手")
        
        # 阶段一：环境检查
        self.check_environment()
        
        # 阶段二：测试工具集
        self.test_tools()
        
        # 阶段三：运行演示
        self.run_demo()
        
        # 生成报告
        self.generate_report()
    
    def check_environment(self):
        """1.1 环境准备检查"""
        print_header("[1/4] 环境准备检查")
        
        # 检查 Python 版本
        print_info("检查 Python 版本...")
        py_version = sys.version_info
        if py_version.major == 3 and py_version.minor >= 8:
            print_success(f"Python 版本: {py_version.major}.{py_version.minor}.{py_version.micro} ✓")
        else:
            print_error(f"Python 版本过低: {py_version.major}.{py_version.minor}.{py_version.micro}")
            print_warning("需要 Python 3.8+")
            return False
        
        # 检查必需依赖
        print_info("\n检查必需依赖...")
        required_packages = {
            'langchain-core': '0.1.0',
            'pymilvus': '2.3.0',
        }
        
        for package, min_version in required_packages.items():
            try:
                result = subprocess.run(
                    ['pip', 'show', package],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print_success(f"{package} 已安装")
                else:
                    print_warning(f"{package} 未安装")
                    print_info(f"  安装命令: pip install {package}>={min_version}")
            except Exception as e:
                print_error(f"检查 {package} 失败: {e}")
        
        # 检查 LangGraph
        print_info("\n检查 LangGraph...")
        try:
            import langgraph
            version = getattr(langgraph, '__version__', '已安装')
            print_success(f"LangGraph 已安装 (version: {version})")
        except ImportError:
            print_warning("LangGraph 未安装")
            print_info("  安装命令: pip install langgraph==0.0.50")
            
            response = input("\n是否现在安装 LangGraph? [y/N]: ")
            if response.lower() == 'y':
                self.install_langgraph()
        
        # 检查项目文件
        print_info("\n检查项目文件...")
        required_files = [
            'agentic/legal_agent_system.py',
            'agentic/legal_tools.py',
            'agentic/demo.py',
            'agentic/README.md'
        ]
        
        for file_path in required_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                print_success(f"{file_path} 存在")
            else:
                print_error(f"{file_path} 不存在")
        
        self.tasks_completed.append("环境检查")
        return True
    
    def install_langgraph(self):
        """安装 LangGraph"""
        print_info("正在安装 LangGraph...")
        try:
            subprocess.run(
                ['pip', 'install', 'langgraph==0.0.50', 'langchain-core==0.1.40'],
                check=True
            )
            print_success("LangGraph 安装成功")
            return True
        except subprocess.CalledProcessError as e:
            print_error(f"安装失败: {e}")
            return False
    
    def test_tools(self):
        """1.2 测试工具集"""
        print_header("[2/4] 测试法律工具集")
        
        tools_file = self.project_root / 'agentic' / 'legal_tools.py'
        
        if not tools_file.exists():
            print_error("legal_tools.py 不存在")
            self.tasks_failed.append("测试工具集")
            return False
        
        print_info("运行工具集测试...")
        
        try:
            result = subprocess.run(
                ['python', str(tools_file)],
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8'
            )
            
            if result.returncode == 0:
                print_success("工具集测试通过")
                print("\n输出示例 (前15行):")
                lines = result.stdout.split('\n')
                for line in lines[:15]:
                    if line.strip():
                        print(f"  {line}")
                if len(lines) > 15:
                    print("  ...")
                self.tasks_completed.append("工具集测试")
            else:
                print_error(f"工具集测试失败")
                print(result.stderr[:500])
                self.tasks_failed.append("工具集测试")
        except subprocess.TimeoutExpired:
            print_error("工具集测试超时")
            self.tasks_failed.append("工具集测试")
        except Exception as e:
            print_error(f"工具集测试异常: {e}")
            self.tasks_failed.append("工具集测试")
    
    def run_demo(self):
        """1.3 运行演示脚本"""
        print_header("[3/4] 运行 AI-Native 演示")
        
        demo_file = self.project_root / 'agentic' / 'demo.py'
        
        if not demo_file.exists():
            print_error("demo.py 不存在")
            self.tasks_failed.append("演示脚本")
            return False
        
        print_info("演示脚本包含3个场景:")
        print("  1. 劳动争议咨询 (主动追问 + 工具调用)")
        print("  2. 法条查询 (时效性检查)")
        print("  3. 文书生成 (催告函)")
        
        print_info("\n正在运行演示...")
        
        try:
            result = subprocess.run(
                ['python', str(demo_file)],
                capture_output=True,
                text=True,
                timeout=60,
                encoding='utf-8'
            )
            
            if result.returncode == 0:
                print_success("演示脚本运行成功")
                print("\n演示输出 (前20行):")
                lines = result.stdout.split('\n')
                for line in lines[:20]:
                    if line.strip():
                        print(f"  {line}")
                if len(lines) > 20:
                    print("  ... (更多内容见完整输出)")
                self.tasks_completed.append("演示脚本")
            else:
                print_error("演示脚本运行失败")
                print(result.stderr[:500])
                self.tasks_failed.append("演示脚本")
        except subprocess.TimeoutExpired:
            print_error("演示脚本超时")
            self.tasks_failed.append("演示脚本")
        except Exception as e:
            print_error(f"演示脚本异常: {e}")
            self.tasks_failed.append("演示脚本")
    
    def generate_report(self):
        """生成执行报告"""
        print_header("[4/4] 执行报告")
        
        print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        print("✅ 已完成任务:")
        if self.tasks_completed:
            for task in self.tasks_completed:
                print(f"  - {task}")
        else:
            print("  (无)")
        
        print("\n❌ 失败任务:")
        if self.tasks_failed:
            for task in self.tasks_failed:
                print(f"  - {task}")
        else:
            print("  (无)")
        
        print("\n" + "="*60)
        print("下一步操作:")
        print("="*60)
        
        if not self.tasks_failed:
            print("\n🎉 环境准备完成！可以开始集成到系统。")
            print("\n推荐操作顺序:")
            print("  1. 阅读 agentic/README.md 了解集成方案")
            print("  2. 修改 app.py 增加 /api/agent/query 接口")
            print("  3. 修改 static/index.html 增加 Agent 模式开关")
            print("  4. 本地测试验证")
            print("  5. 查看 AI_NATIVE_ROADMAP.md 继续后续步骤")
        else:
            print("\n⚠️ 部分任务失败，请先解决以下问题:")
            for task in self.tasks_failed:
                print(f"  - {task}")
            print("\n解决方法:")
            print("  1. 查看上方的错误信息")
            print("  2. 参考 agentic/README.md 排查")
            print("  3. 确保所有依赖已安装")
        
        print("\n📖 参考文档:")
        print("  - AI_NATIVE_ROADMAP.md (完整改造路线图)")
        print("  - agentic/README.md (Agent 系统使用文档)")
        print("  - docs/DATA_OPTIMIZATION_GUIDE.md (数据优化指南)")
        
        # 更新路线图进度
        self.update_roadmap_progress()
    
    def update_roadmap_progress(self):
        """更新路线图中的进度"""
        if not ROADMAP_FILE.exists():
            return
        
        try:
            with open(ROADMAP_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 更新今日日志
            today = datetime.now().strftime('%Y-%m-%d')
            log_section = f"### {today}\n"
            
            for task in self.tasks_completed:
                log_section += f"- [x] {task}\n"
            
            # 简单追加（实际项目中可以更智能地更新）
            if f"### {today}" not in content:
                content = content.replace(
                    "## 📝 每日工作日志",
                    f"## 📝 每日工作日志\n\n{log_section}"
                )
                
                with open(ROADMAP_FILE, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print_info(f"\n已更新路线图进度: {ROADMAP_FILE}")
        except Exception as e:
            print_warning(f"更新路线图失败: {e}")


def main():
    """主函数"""
    import sys
    import io
    # 设置标准输出编码为 UTF-8
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    executor = RoadmapExecutor()
    
    try:
        executor.run()
    except KeyboardInterrupt:
        print("\n\n用户中断执行")
    except Exception as e:
        print_error(f"\n执行异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
