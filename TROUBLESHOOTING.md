# 网络连接故障排除指南

## 🐛 问题：SSL 连接错误

如果你看到以下错误：
```
OSError: [Errno 0] Error
httpcore.ConnectError: [Errno 0] Error
openai.APIConnectionError: Connection error.
```

这是 **SSL/TLS 握手失败**，通常在公司网络或有防火墙的环境中出现。

---

## 🔧 解决方案（按推荐顺序）

### ✅ 方案1：使用本地 LLM（最推荐）

**优点**：
- ✅ 无需联网
- ✅ 无需担心 API 费用
- ✅ 数据隐私更好
- ✅ 响应速度快

**步骤**：

1. **安装 Ollama**
   - 访问：https://ollama.com/download
   - 下载 Windows 版本并安装
   - 安装后 Ollama 会自动运行

2. **下载模型**
   ```powershell
   # 推荐：中文支持好
   ollama pull qwen2:7b
   
   # 或者其他选择
   ollama pull llama3:8b
   ollama pull mistral
   ```

3. **修改配置**
   
   编辑 `config.json`：
   ```json
   {
     "llm": {
       "provider": "ollama",
       "model": "qwen2:7b",
       "base_url": "http://localhost:11434/v1"
     }
   }
   ```
   
   编辑 `.env`：
   ```env
   DEEPSEEK_API_KEY=ollama
   ```

4. **运行**
   ```powershell
   python MCP-SSE-Client.py
   ```

---

### ✅ 方案2：配置公司代理

如果你在公司网络，需要配置代理。

#### 2.1 查找代理地址

**方法1：从浏览器获取**
1. 打开 IE/Edge → 设置 → 网络和Internet → 代理
2. 查看"手动代理设置"中的地址和端口
3. 通常格式：`http://proxy.company.com:8080`

**方法2：从命令行查看**
```powershell
netsh winhttp show proxy
```

**方法3：询问 IT 部门**

#### 2.2 配置代理

编辑 `.env` 文件，添加：
```env
HTTP_PROXY=http://proxy.company.com:8080
HTTPS_PROXY=http://proxy.company.com:8080
```

如果代理需要认证：
```env
HTTP_PROXY=http://username:password@proxy.company.com:8080
HTTPS_PROXY=http://username:password@proxy.company.com:8080
```

#### 2.3 测试

```powershell
python MCP-SSE-Client.py
```

---

### ✅ 方案3：临时禁用 SSL 验证（仅测试用）

⚠️ **警告**：这会降低安全性，仅用于诊断问题。

编辑 `.env`，添加：
```env
VERIFY_SSL=false
```

运行测试：
```powershell
python MCP-SSE-Client.py
```

如果这样能工作，说明是 SSL 证书问题。然后：
1. 升级 SSL 库（见方案4）
2. 或使用本地模型（方案1）

---

### ✅ 方案4：升级 SSL 和 HTTP 库

Python 3.7 的 SSL 库较老，升级相关依赖：

```powershell
pip install --upgrade certifi urllib3 httpcore httpx openai

# 重新运行
python MCP-SSE-Client.py
```

---

### ✅ 方案5：测试网络连接

#### 5.1 测试能否访问 API

```powershell
# 测试1：curl 测试
curl -v https://api.deepseek.com

# 测试2：Python 测试
python -c "import urllib.request; print(urllib.request.urlopen('https://api.deepseek.com').read())"

# 测试3：直接测试 DeepSeek API
curl https://api.deepseek.com/v1/models -H "Authorization: Bearer your_api_key"
```

如果这些测试失败，确认是网络问题。

#### 5.2 检查防火墙

公司防火墙可能阻止了：
- HTTPS 出站连接
- 特定域名（api.deepseek.com）
- 非标准端口的连接

解决方法：
1. 联系 IT 部门申请白名单
2. 使用本地模型（方案1）

---

## 📋 完整诊断流程

```powershell
# 步骤1：检查代理设置
echo $env:HTTP_PROXY
echo $env:HTTPS_PROXY

# 步骤2：测试网络
curl https://api.deepseek.com

# 步骤3：尝试禁用SSL验证（测试）
$env:VERIFY_SSL="false"
python MCP-SSE-Client.py

# 步骤4：如果上面都不行，使用本地模型
ollama pull qwen2:7b
# 修改 config.json 和 .env（见方案1）
python MCP-SSE-Client.py
```

---

## 🎯 推荐配置（公司网络）

对于大多数公司网络环境，推荐使用**本地模型**：

### 优势
- ✅ 不受网络限制
- ✅ 无需申请 API 密钥
- ✅ 数据不出本地
- ✅ 无使用成本

### 配置

**config.json**：
```json
{
  "mcp_server": {
    "url": "http://123.60.169.171:5000"
  },
  "llm": {
    "provider": "ollama",
    "model": "qwen2:7b",
    "base_url": "http://localhost:11434/v1",
    "max_iterations": 5
  },
  "memory": {
    "session_enabled": true,
    "persistent_enabled": true
  }
}
```

**.env**：
```env
DEEPSEEK_API_KEY=ollama
```

**安装模型**：
```powershell
ollama pull qwen2:7b
```

**运行**：
```powershell
python MCP-SSE-Client.py
```

---

## 📞 仍然无法解决？

1. **检查 Python 版本**：
   ```powershell
   python --version
   ```
   推荐 Python 3.8+ （你当前是 3.7）

2. **查看完整错误日志**：
   设置详细日志级别，在 `config.json` 中：
   ```json
   {
     "logging": {
       "level": "DEBUG"
     }
   }
   ```

3. **联系支持**：
   - 提供完整的错误日志
   - 说明你的网络环境（公司/家庭）
   - 是否有代理或防火墙

---

## ✅ 快速决策树

```
你的网络环境是？
├─ 公司网络
│  ├─ 有代理 → 方案2（配置代理）
│  ├─ 无代理但有防火墙 → 方案1（本地模型）⭐
│  └─ SSL错误 → 方案1（本地模型）⭐
│
└─ 家庭网络
   ├─ SSL错误 → 方案4（升级库）
   └─ 仍然失败 → 方案1（本地模型）⭐

⭐ = 最推荐方案
```

---

**最简单的解决方案：使用 Ollama 本地模型！** 🎯
