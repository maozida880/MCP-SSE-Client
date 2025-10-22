#!/usr/bin/env python3
"""
V2.0 功能测试脚本
测试所有新增的核心功能
"""

import asyncio
import json
import sys
from pathlib import Path


class V2FeatureTester:
    """V2.0 功能测试器"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
    
    def print_header(self, text: str):
        """打印测试标题"""
        print(f"\n{'='*60}")
        print(f"  {text}")
        print(f"{'='*60}\n")
    
    def print_test(self, name: str, passed: bool, message: str = ""):
        """打印测试结果"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
        if message:
            print(f"     {message}")
        
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    def print_warning(self, message: str):
        """打印警告"""
        print(f"⚠️  WARNING - {message}")
        self.warnings += 1
    
    def test_file_structure(self):
        """测试 1: 文件结构"""
        self.print_header("测试 1: 检查文件结构")
        
        files = {
            "MCP-SEE-Client-V2.py": "主客户端文件",
            "config.json": "配置文件",
            "user_profile.json": "用户配置文件",
            ".env.example": "环境变量示例",
            "requirements.txt": "依赖列表"
        }
        
        for filename, desc in files.items():
            exists = Path(filename).exists()
            self.print_test(
                f"{desc} ({filename})",
                exists,
                "文件已存在" if exists else "文件缺失"
            )
    
    def test_config_json(self):
        """测试 2: config.json 配置"""
        self.print_header("测试 2: 检查 config.json 配置")
        
        if not Path("config.json").exists():
            self.print_warning("config.json 不存在，将使用默认配置")
            return
        
        try:
            with open("config.json", 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 检查必要的配置项
            checks = [
                ("mcp_server" in config, "MCP 服务器配置"),
                ("llm" in config, "LLM 配置"),
                ("memory" in config, "内存配置"),
                ("logging" in config, "日志配置"),
            ]
            
            for check, name in checks:
                self.print_test(name, check)
            
            # 检查关键子配置
            if "mcp_server" in config:
                conn = config["mcp_server"].get("connection", {})
                self.print_test(
                    "自动重连配置",
                    "retry_attempts" in conn,
                    f"重试次数: {conn.get('retry_attempts', 'N/A')}"
                )
                self.print_test(
                    "SSE 重连配置",
                    "sse_reconnect_enabled" in conn,
                    f"启用: {conn.get('sse_reconnect_enabled', 'N/A')}"
                )
            
            if "memory" in config:
                mem = config["memory"]
                self.print_test(
                    "会话记忆配置",
                    "session_enabled" in mem,
                    f"启用: {mem.get('session_enabled', 'N/A')}"
                )
                self.print_test(
                    "持久化记忆配置",
                    "persistent_enabled" in mem,
                    f"启用: {mem.get('persistent_enabled', 'N/A')}"
                )
        
        except json.JSONDecodeError as e:
            self.print_test("JSON 格式", False, f"解析错误: {e}")
        except Exception as e:
            self.print_test("配置读取", False, f"读取错误: {e}")
    
    def test_user_profile(self):
        """测试 3: user_profile.json"""
        self.print_header("测试 3: 检查 user_profile.json")
        
        if not Path("user_profile.json").exists():
            self.print_warning("user_profile.json 不存在，首次运行时会自动创建")
            return
        
        try:
            with open("user_profile.json", 'r', encoding='utf-8') as f:
                profile = json.load(f)
            
            checks = [
                ("user_id" in profile, "用户 ID"),
                ("preferences" in profile, "用户偏好"),
                ("aliases" in profile, "地点别名"),
            ]
            
            for check, name in checks:
                self.print_test(name, check)
            
            # 检查是否已配置
            if "preferences" in profile:
                prefs = profile["preferences"]
                has_config = any(prefs.values())
                if has_config:
                    print(f"     已配置偏好: {list(prefs.keys())}")
                else:
                    self.print_warning("用户偏好未配置，建议添加常用出发地和目的地")
        
        except json.JSONDecodeError as e:
            self.print_test("JSON 格式", False, f"解析错误: {e}")
    
    def test_env_file(self):
        """测试 4: .env 文件"""
        self.print_header("测试 4: 检查 .env 文件")
        
        if not Path(".env").exists():
            self.print_test(".env 文件存在", False, "请创建 .env 文件并配置 API Key")
            return
        
        self.print_test(".env 文件存在", True)
        
        # 检查 API Key（不显示实际值）
        try:
            with open(".env", 'r') as f:
                content = f.read()
            
            has_key = "DEEPSEEK_API_KEY" in content
            self.print_test(
                "DEEPSEEK_API_KEY 已配置",
                has_key,
                "请确保 API Key 有效" if has_key else "缺少 API Key"
            )
        except Exception as e:
            self.print_test("读取 .env", False, str(e))
    
    def test_imports(self):
        """测试 5: Python 依赖"""
        self.print_header("测试 5: 检查 Python 依赖")
        
        dependencies = [
            ("aiohttp", "异步 HTTP 客户端"),
            ("aiohttp_sse_client", "SSE 客户端"),
            ("dotenv", "环境变量加载"),
            ("openai", "OpenAI SDK"),
        ]
        
        for module, desc in dependencies:
            try:
                __import__(module)
                self.print_test(f"{desc} ({module})", True)
            except ImportError:
                self.print_test(
                    f"{desc} ({module})",
                    False,
                    f"请运行: pip install {module}"
                )
    
    def test_syntax(self):
        """测试 6: Python 语法"""
        self.print_header("测试 6: 检查 Python 语法")
        
        if not Path("MCP-SEE-Client-V2.py").exists():
            self.print_test("主文件存在", False)
            return
        
        try:
            with open("MCP-SEE-Client-V2.py", 'r', encoding='utf-8') as f:
                code = f.read()
            
            compile(code, "MCP-SEE-Client-V2.py", "exec")
            self.print_test("Python 语法", True, "代码语法正确")
        except SyntaxError as e:
            self.print_test("Python 语法", False, f"语法错误: {e}")
    
    def print_summary(self):
        """打印测试摘要"""
        self.print_header("测试摘要")
        
        total = self.passed + self.failed
        success_rate = (self.passed / total * 100) if total > 0 else 0
        
        print(f"总测试数: {total}")
        print(f"✅ 通过: {self.passed}")
        print(f"❌ 失败: {self.failed}")
        print(f"⚠️  警告: {self.warnings}")
        print(f"成功率: {success_rate:.1f}%")
        
        if self.failed == 0:
            print("\n🎉 所有测试通过！可以开始使用 V2.0 了！")
        else:
            print(f"\n⚠️  有 {self.failed} 项测试失败，请先解决这些问题。")
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "="*60)
        print("  12306-MCP 客户端 V2.0 功能测试")
        print("="*60)
        
        self.test_file_structure()
        self.test_config_json()
        self.test_user_profile()
        self.test_env_file()
        self.test_imports()
        self.test_syntax()
        
        self.print_summary()
        
        return self.failed == 0


def main():
    """主函数"""
    tester = V2FeatureTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n💡 下一步:")
        print("   1. 确保 12306-MCP 服务器已启动")
        print("   2. 运行: python MCP-SEE-Client-V2.py")
        print("   3. 开始体验新功能！")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
