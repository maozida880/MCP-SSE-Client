# 快速修复指南 - 解决火车票查询失败问题

## 🎯 问题
AI 总是回复"无法查询车站信息"，从不返回实际火车票。

## ⚡ 快速修复（3分钟）

### 方法1：下载修复版本（推荐）

```powershell
# 1. 进入项目目录
cd E:\work\workspace\agent_MCP

# 2. 备份原文件
Copy-Item "MCP-SEE-Client-V2.py" "MCP-SEE-Client-V2.py.backup"

# 3. 下载修复后的文件（从 Claude 输出）
# - MCP-SEE-Client-V2-fixed.py
# - city_codes.json
# - test_error_handling.py

# 4. 替换主程序
Move-Item "MCP-SEE-Client-V2-fixed.py" "MCP-SEE-Client-V2.py" -Force

# 5. 测试
python MCP-SEE-Client-V2.py
```

### 方法2：手动修改（如果方法1不行）

如果你想在现有文件上修改，只需要改**一个地方**：

打开 `MCP-SEE-Client-V2.py`，找到 `_build_system_prompt` 方法（约第500行），替换为以下内容：

```python
def _build_system_prompt(self) -> str:
    """构建系统提示（增强版）"""
    if not self.tools_cache:
        return "You are a helpful assistant."

    tool_descriptions = []
    for tool in self.tools_cache:
        func = tool.get('function', {})
        tool_name = func.get('name', 'unknown')
        tool_desc = func.get('description', '')
        tool_descriptions.append(f"- {tool_name}: {tool_desc}")

    tool_list_str = "\n".join(tool_descriptions)
    
    base_prompt = f"""# 角色
你是一个主动、智能、**有韧性**的12306火车票查询助手。

# 可用工具
{tool_list_str}

# 查询流程（必须严格遵循）
1. 获取日期: get-current-date
2. 确定车站代码（尝试任意工具）
3. **查询车票: get-tickets**（必须调用，即使车站查询失败）

# 常见城市代码（当工具返回错误时使用）
北京=BJP, 上海=SHH, 广州=GZQ, 深圳=SZQ, 杭州=HZH, 
南京=NJH, 成都=CDW, 武汉=WHN, 西安=XAY, 郑州=ZZF,
重庆=CQW, 天津=TJP, 长沙=CSQ, 沈阳=SYT, 哈尔滨=HBB

# 错误处理（最重要！）
当车站查询工具返回 "Error" 或 "not found":
1. 不要放弃！
2. 查看上面的城市代码表
3. 直接使用代码调用 get-tickets
4. 只有 get-tickets 也失败时才告诉用户无法查询

# 示例
❌ 错误: 车站查询失败 → 告诉用户无法查询
✅ 正确: 车站查询失败 → 用代码表 → 调用get-tickets → 返回结果
"""
    
    # ... 其余代码保持不变 ...
```

保存后重新运行即可。

---

## 🧪 验证修复

```powershell
# 运行程序
python MCP-SEE-Client-V2.py

# 测试查询
输入: 明天从深圳到杭州的火车
```

**修复前**：
```
🤖 [AI回复]
很抱歉，目前我无法查询到深圳和杭州的车站信息...
```

**修复后**：
```
🤖 [AI回复]
找到以下车次:
G1234 深圳北(SZQ) -> 杭州东(HZH) 08:30 -> 14:50
- 二等座: 有票 562元
...
```

---

## 📝 技术细节

### 问题原因
1. MCP Server 的 `get-stations-code-in-city` 对某些城市返回错误
2. AI 收到错误后直接放弃，从不调用 `get-tickets`
3. 缺少 fallback 机制

### 修复方案
1. 在系统提示中添加城市代码表
2. 教导 AI 在遇到错误时使用 fallback
3. 强调必须调用 `get-tickets`

### 为什么有效
- AI 现在知道即使工具返回错误也要继续尝试
- 有了备用的城市代码表
- 明确了"必须查票"的指令

---

## 📦 完整文件列表

修复需要的文件（从 Claude 输出下载）：

1. ✅ **MCP-SEE-Client-V2-fixed.py** - 主程序（必需）
2. ✅ **city_codes.json** - 城市代码配置（可选，代码中有内置）
3. ✅ **test_error_handling.py** - 测试脚本（可选）
4. ✅ **ERROR_HANDLING_FIX.md** - 详细说明（参考）
5. ✅ **TROUBLESHOOTING.md** - 故障排除（参考）

---

## 🚨 如果还是不行

### 检查1：确认 MCP Server 运行

```powershell
# 测试 MCP Server
curl http://123.60.169.171:5000/mcp
```

### 检查2：查看详细日志

修改 `config.json`：
```json
{
  "logging": {
    "level": "DEBUG"
  }
}
```

### 检查3：测试单独工具

```python
# 测试 get-tickets 是否能直接工作
# （见 test_mcp_2.py 示例）
```

### 检查4：确认 API 密钥

```powershell
cat .env
# 确保 DEEPSEEK_API_KEY 正确
```

---

## 📞 仍需帮助？

提供以下信息：
1. 完整的运行日志（包括工具调用）
2. MCP Server 的版本
3. Python 版本
4. config.json 内容

---

## ✅ 成功标志

修复成功后，你应该看到：
1. ✅ AI 会调用 `get-tickets` 工具
2. ✅ 返回实际的车次信息
3. ✅ 不再说"无法查询车站信息"
4. ✅ 查询成功率 > 90%

---

**核心改变**：教会 AI "遇到错误不要放弃，尝试 fallback 并继续查询"！ 🎯
