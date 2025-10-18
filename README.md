# 12306-MCP 智能客户端

基于 **MCP JSON-RPC 2.0** 协议的12306火车票智能查询客户端。

## ✨ 特性

- ✅ **标准MCP协议** - 完全符合MCP JSON-RPC 2.0规范
- ✅ **SSE实时通信** - 支持服务器推送事件
- ✅ **智能对话** - LLM自动理解需求并调用工具
- ✅ **完整工具支持** - 支持所有# 12306-MCP SSE客户端

一个基于SSE(Server-Sent Events)模式的12306-MCP智能客户端,可以通过自然语言查询火车票信息。

## 功能特性

- ✅ **SSE实时通信**: 与12306-MCP服务器建立持久连接
- 🤖 **智能对话**: 使用大语言模型理解自然语言查询
- 🔧 **自动工具调用**: AI自动选择合适的12306接口
- 📊 **完整工具支持**: 支持所有12306-MCP提供的工具
  - 查询余票信息
  - 查询中转方案
  - 查询列车经停站
  - 查询车站信息
  - 获取当前日期

## 安装步骤

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置:

```bash
cp .env.example .env
```

编辑 `.env` 文件:

```env
# MCP服务器地址
MCP_SERVER_URL=http://localhost:12306

# API配置
DEEPSEEK_API_KEY=your_api_key_here
BASE_URL=https://api.deepseek.com
MODEL=deepseek-chat
```

### 3. 启动12306-MCP服务器

首先需要启动12306-MCP服务器(HTTP模式):

```bash
# 使用npm
npx -y 12306-mcp --port 12306

# 或使用Docker
docker run -p 12306:8080 -d 12306-mcp npx 12306-mcp --port 8080
```

### 4. 运行客户端

```bash
python mcp_sse_client.py
```

## 使用示例

启动客户端后,可以用自然语言提问:

```
💬 请输入问题: 明天从北京到上海的高铁票

🤖 [AI回复]
根据查询结果,明天(2025-10-19)从北京到上海的高铁票信息如下:

1. G1次 (07:00出发 -> 11:28到达,历时4小时28分)
   - 二等座: 有票 553元
   - 一等座: 有票 933元
   - 商务座: 有票 1748元

2. G3次 (08:00出发 -> 12:35到达,历时4小时35分)
   ...
```

更多示例:

```
# 查询中转方案
💬 从深圳到拉萨,经过西安中转

# 查询列车经停站
💬 G1033次列车明天经过哪些站?

# 筛选特定时间
💬 后天下午3点到6点从杭州到北京的动车票

# 查询车站信息
💬 北京有哪些火车站?
```

## 特殊命令

在对话中可以使用以下命令:

- `tools` - 查看所有可用工具
- `quit` 或 `exit` - 退出程序

## 工作原理

```
┌─────────┐         SSE          ┌──────────────┐
│  用户   │ ◄─────────────────── │ 12306-MCP    │
│         │                      │   服务器     │
└────┬────┘                      └──────┬───────┘
     │                                  │
     │  自然语言查询                      │
     ▼                                  │
┌─────────┐                            │
│   客户端 │ ─────── HTTP POST ─────────┘
│  (本程序) │         (工具调用)
└────┬────┘
     │
     │  Tool Calling
     ▼
┌─────────┐
│   LLM   │ (DeepSeek/GPT-4/本地模型)
│  (AI)   │
└─────────┘
```

1. 用户输入自然语言查询
2. 客户端将查询发送给LLM
3. LLM决定需要调用哪些12306工具
4. 客户端通过HTTP POST调用MCP服务器
5. MCP服务器返回结果
6. LLM基于结果生成用户友好的回复

## 架构特点

### SSE连接
- 使用SSE保持与MCP服务器的长连接
- 实时接收服务器推送的事件通知
- 异步处理事件流

### 工具调用流程
```python
# 1. 获取工具列表
tools = await client._fetch_tools()

# 2. LLM决定工具调用
response = llm.chat(tools=tools)

# 3. 执行工具调用
result = await client.call_tool(name, args)

# 4. 生成最终回复
final = llm.chat(messages + tool_results)
```

## 配置说明

### MCP服务器URL
```env
MCP_SERVER_URL=http://localhost:12306
```
确保与12306-MCP服务器的 `--port` 参数一致

### API密钥
支持多种LLM提供商:

**DeepSeek** (推荐,性价比高):
```env
DEEPSEEK_API_KEY=sk-xxx
BASE_URL=https://api.deepseek.com
MODEL=deepseek-chat
```

**OpenAI**:
```env
DEEPSEEK_API_KEY=sk-xxx
BASE_URL=https://api.openai.com/v1
MODEL=gpt-4-turbo-preview
```

**本地模型(Ollama)**:
```env
DEEPSEEK_API_KEY=ollama
BASE_URL=http://localhost:11434/v1
MODEL=qwen2:7b
```

## 故障排除

### 1. 连接失败
```
✗ 连接失败: Cannot connect to host localhost:12306
```
**解决**: 确保12306-MCP服务器已启动

### 2. 未获取到工具
```
警告: 未能获取工具列表
```
**解决**: 
- 检查MCP服务器URL是否正确
- 确认服务器运行在HTTP模式(`--port`参数)

### 3. API调用失败
```
对话过程中发生错误: Invalid API key
```
**解决**: 检查`.env`文件中的API密钥配置

## 开发说明

### 核心类结构

```python
class Train12306MCPClient:
    async def connect()           # 连接MCP服务器
    async def _listen_sse()       # 监听SSE事件
    async def _fetch_tools()      # 获取工具列表
    async def call_tool()         # 调用MCP工具
    async def chat()              # 智能对话
    async def chat_loop()         # 交互循环
    async def cleanup()           # 清理资源
```

### 扩展开发

如需扩展功能,可以:

1. **添加工具过滤**:
```python
# 只使用特定工具
filtered_tools = [t for t in tools if t['function']['name'] in ['get-tickets']]
```

2. **自定义提示词**:
```python
system_message = {
    "role": "system",
    "content": "你是12306火车票查询助手..."
}
messages = [system_message, user_message]
```

3. **添加对话历史**:
```python
self.conversation_history = []
```

## 许可证

MIT License

## 相关项目

- [12306-MCP](https://github.com/Joooook/12306-mcp) - MCP服务器
- [MCP Specification](https://modelcontextprotocol.io) - MCP协议规范