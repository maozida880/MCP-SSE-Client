# 12306-MCP 客户端 V2.0 技术架构文档

## 📐 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     用户交互层                                │
│  ┌────────────┐  ┌────────────┐  ┌──────────────┐          │
│  │ Chat Loop  │  │  Commands  │  │   CLI UI     │          │
│  └────────────┘  └────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   核心客户端层 (V2.0)                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Train12306MCPClient                          │   │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────┐  │   │
│  │  │Config Mgr  │  │Profile Mgr │  │ Memory Mgr   │  │   │
│  │  └────────────┘  └────────────┘  └──────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ LLM Service  │   │ MCP Server   │   │ Local Files  │
│ (DeepSeek)   │   │ (12306-mcp)  │   │ (JSON/Log)   │
└──────────────┘   └──────────────┘   └──────────────┘
```

---

## 🏗️ 核心模块设计

### 1. ConfigManager（配置管理器）

**职责**：统一管理所有配置项，支持 JSON 配置文件和默认配置。

**核心方法**：
- `_load_config()`: 加载配置文件
- `get(path, default)`: 通过点分路径获取配置项

**设计亮点**：
- 支持嵌套配置（如 `mcp_server.connection.retry_attempts`）
- 配置缺失时使用合理默认值
- 环境变量优先级高于配置文件

**示例**：
```python
config = ConfigManager("config.json")
retry_attempts = config.get('mcp_server.connection.retry_attempts', 3)
```

---

### 2. UserProfileManager（用户配置管理器）

**职责**：管理用户偏好、地点别名和历史统计。

**核心方法**：
- `get_user_context()`: 生成用户上下文字符串，注入到系统提示
- `update_query_stats()`: 更新查询统计
- `save()`: 持久化用户配置

**数据模型**：
```json
{
  "user_id": "string",
  "preferences": {
    "default_departure_city": "string",
    "preferred_seat_type": "string"
  },
  "aliases": {
    "home": "深圳北",
    "office": "北京南"
  },
  "metadata": {
    "total_queries": 0,
    "last_active": "ISO8601"
  }
}
```

**设计亮点**：
- 用户偏好自动注入到 LLM 系统提示
- 支持地点别名，提升用户体验
- 统计信息用于未来的个性化推荐

---

### 3. ConversationMemory（会话记忆管理器）

**职责**：管理当前会话和历史对话记录。

**核心方法**：
- `add_message(role, content)`: 添加消息到当前会话
- `get_current_session()`: 获取当前会话（用于 LLM）
- `clear_session()`: 清空会话并保存到历史
- `get_recent_context()`: 获取最近对话的摘要

**数据模型**：
```python
current_session = [
    {"role": "user", "content": "...", "timestamp": "ISO8601"},
    {"role": "assistant", "content": "...", "timestamp": "ISO8601"},
]

history = [
    {
        "session_id": "ISO8601",
        "messages": [...]
    }
]
```

**设计亮点**：
- 智能截断：保留最新的 N 条消息，避免上下文超限
- 历史加载：可选加载最近几次会话的摘要
- 时间戳记录：便于未来分析对话模式

---

### 4. Train12306MCPClient（主客户端）

**职责**：协调所有模块，管理与 MCP 服务器和 LLM 的交互。

#### 4.1 增强的连接管理

##### 自动重连机制

**实现**：指数退避算法

```python
async def _make_mcp_request(self, method, params):
    for attempt in range(retry_attempts):
        try:
            # 发送请求
            ...
        except NetworkError:
            wait_time = retry_delay * (2 ** attempt)
            await asyncio.sleep(wait_time)
```

**退避策略**：
- 第1次重试：等待 1 秒
- 第2次重试：等待 2 秒
- 第3次重试：等待 4 秒
- ...（最大不超过 `max_retry_delay`）

##### SSE 自动重连

**实现**：
```python
async def _listen_sse_with_reconnect(self):
    while self.is_connected:
        try:
            # 连接 SSE
            ...
        except Exception:
            await asyncio.sleep(reconnect_interval)
```

**特点**：
- 连接断开后自动重连
- 可配置重连间隔
- 支持优雅关闭（`is_connected` 标志）

##### 心跳保持

**实现**：
```python
async def _heartbeat_loop(self, interval):
    while self.is_connected:
        await asyncio.sleep(interval)
        await self._make_mcp_request("ping", {})
```

**作用**：
- 定期检查连接状态
- 防止长连接超时
- 及早发现网络问题

#### 4.2 智能异常处理

**错误分类**：

| 错误类型 | 处理策略 | 示例 |
|---------|----------|------|
| 瞬时故障 | 自动重试 | 网络超时、服务器 503 |
| 永久错误 | 返回错误信息给 LLM | 参数错误 400、认证失败 401 |
| 系统错误 | 记录日志并退出 | 配置错误、依赖缺失 |

**重试决策树**：
```
错误发生
    │
    ├─ 网络错误？
    │   └─ 是 → 重试（最多 N 次）
    │
    ├─ HTTP 5xx？
    │   └─ 是 → 重试（最多 N 次）
    │
    └─ 其他错误？
        └─ 返回错误信息
```

#### 4.3 会话记忆集成

**系统提示构建**：
```python
def _build_system_prompt(self):
    base_prompt = "..."  # 基础提示
    
    # 注入用户偏好
    if self.profile:
        base_prompt += self.profile.get_user_context()
    
    # 注入历史摘要
    if self.memory:
        base_prompt += self.memory.get_recent_context()
    
    return base_prompt
```

**对话流程**：
```
用户输入 → 记录到 memory → 构建 messages → 调用 LLM
                                              ↓
助手回复 ← 记录到 memory ← 解析响应 ← 接收响应
```

---

## 🔄 关键流程

### 1. 启动流程

```
main()
  │
  ├─ 加载配置 (ConfigManager)
  ├─ 初始化日志
  ├─ 加载用户配置 (UserProfileManager)
  ├─ 初始化记忆 (ConversationMemory)
  │
  ├─ connect()
  │   ├─ 创建 HTTP Session
  │   ├─ 启动 SSE 监听任务
  │   ├─ 启动心跳任务
  │   ├─ 初始化 MCP 连接
  │   └─ 获取工具列表
  │
  └─ chat_loop()
      └─ 进入交互循环
```

### 2. 对话流程（带记忆）

```
用户输入: "明天深圳到广州的高铁票"
  │
  ├─ memory.add_message("user", ...)
  ├─ 构建 system_prompt (含用户偏好和历史)
  ├─ messages = [system, *history, user_message]
  │
  ├─ LLM 思考
  │   ├─ 决定调用 get-current-date
  │   ├─ 决定调用 get-station-code-of-citys
  │   └─ 决定调用 get-tickets
  │
  ├─ 执行工具调用（自动重试）
  │
  ├─ LLM 生成回复
  └─ memory.add_message("assistant", ...)

用户继续输入: "最早的那趟有二等座吗？"
  │
  ├─ memory.add_message("user", ...)
  ├─ messages 包含上一轮的完整对话
  │
  └─ LLM 直接根据上下文回答（无需重新查询）
```

### 3. 错误恢复流程

```
工具调用失败
  │
  ├─ 是网络错误？
  │   ├─ 是 → 等待 1 秒，重试
  │   ├─ 仍失败 → 等待 2 秒，重试
  │   └─ 仍失败 → 等待 4 秒，重试
  │
  ├─ 是服务器错误 (5xx)？
  │   └─ 同上，自动重试
  │
  └─ 是参数错误 (4xx)？
      └─ 返回错误信息给 LLM，让其修正
```

---

## 🧩 数据流

### 配置加载

```
启动
  ↓
尝试读取 config.json
  ├─ 成功 → 使用配置
  └─ 失败 → 使用默认配置
  ↓
读取 .env 文件
  ├─ API Key → 环境变量
  └─ 其他配置 → 可被 config.json 覆盖
  ↓
最终配置 = 环境变量 > config.json > 默认值
```

### 用户上下文传递

```
UserProfileManager
  ↓
get_user_context()
  ↓
"# 用户偏好\n- 常用出发地: 深圳\n..."
  ↓
_build_system_prompt()
  ↓
System Prompt → LLM
  ↓
LLM 自动利用用户偏好
```

### 会话记忆传递

```
messages = [
  {"role": "system", "content": "..."},
  {"role": "user", "content": "明天..."},
  {"role": "assistant", "content": "..."},
  {"role": "user", "content": "最早的那趟..."}  ← 当前输入
]
  ↓
LLM 看到完整上下文
  ↓
理解"最早的那趟"指的是上一轮的查询结果
```

---

## 🎯 性能优化

### 1. 内存管理

**问题**：对话历史无限增长会导致 Token 超限。

**解决方案**：
- 智能截断：保留最新的 N 条消息
- 历史保存：旧消息保存到文件
- 按需加载：只在必要时加载历史摘要

**实现**：
```python
def get_current_session(self):
    # 只返回最新的 max_context_messages 条
    messages = self.current_session[-self.max_context_messages:]
    return messages
```

### 2. 网络优化

**问题**：频繁的网络请求导致延迟。

**优化**：
- 工具列表缓存：只在启动时获取一次
- 批量操作：未来可考虑批量工具调用
- 长连接：使用 HTTP/1.1 Keep-Alive

### 3. 并发控制

**当前**：单线程异步 I/O（`asyncio`）

**优势**：
- 高效处理 I/O 密集型任务
- 低内存占用
- 简单的错误处理

**未来**：
- 支持多用户：使用进程池或多实例
- 工具并行调用：某些独立工具可并行执行

---

## 🔐 安全设计

### 1. 凭证管理

**原则**：敏感信息不存储在配置文件中。

**实现**：
- API Key 只存储在 `.env` 文件
- `.env` 文件加入 `.gitignore`
- 日志中不输出 API Key

### 2. 错误信息

**原则**：不向用户暴露系统内部细节。

**实现**：
- 捕获所有异常
- 向用户显示友好的错误信息
- 详细错误记录到日志文件

### 3. 输入验证

**工具调用参数**：
- LLM 生成参数 → JSON 校验
- 格式错误 → 返回错误信息给 LLM
- LLM 自我修正

---

## 📊 可观测性

### 1. 日志系统

**分级**：
- `DEBUG`：详细的调试信息（工具参数、响应）
- `INFO`：正常操作流程
- `WARNING`：警告（重试、配置缺失）
- `ERROR`：错误（连接失败、工具调用失败）

**输出**：
- 控制台：实时查看
- 文件：持久化存储

### 2. 性能监控

**未来增强**：
- 工具调用耗时统计
- 成功率监控
- Token 使用量统计

---

## 🧪 测试策略

### 单元测试（未来）

```python
# test_config_manager.py
def test_config_loading():
    config = ConfigManager("test_config.json")
    assert config.get("mcp_server.url") == "http://test:12306"

# test_memory.py
def test_session_memory():
    memory = ConversationMemory(max_messages=5)
    memory.add_message("user", "test")
    assert len(memory.current_session) == 1
```

### 集成测试

使用 `test_v2_features.py`：
- 文件结构检查
- 配置验证
- 依赖检查
- 语法检查

### 端到端测试

手动测试关键场景：
1. 基础查询
2. 连续对话
3. 断线重连
4. 工具调用失败

---

## 🚀 部署建议

### 本地部署

```bash
# 1. 克隆项目
git clone ...

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境
cp .env.example .env
# 编辑 .env 填写 API Key

# 4. 启动服务器
npx -y 12306-mcp --port 12306

# 5. 运行客户端
python MCP-SEE-Client-V2.py
```

### 生产部署（未来）

```bash
# 使用 systemd 服务
sudo systemctl start mcp-client

# 使用 Docker
docker-compose up -d

# 使用 supervisor
supervisorctl start mcp-client
```

---

## 📖 API 文档（内部）

### ConfigManager

```python
class ConfigManager:
    def __init__(self, config_path: str)
    def get(self, path: str, default: Any = None) -> Any
```

### UserProfileManager

```python
class UserProfileManager:
    def __init__(self, profile_path: str)
    def get_user_context(self) -> str
    def update_query_stats(self)
    def save(self)
```

### ConversationMemory

```python
class ConversationMemory:
    def __init__(self, history_path: str, max_messages: int)
    def add_message(self, role: str, content: str)
    def get_current_session(self) -> List[Dict]
    def clear_session(self)
    def get_recent_context(self, count: int) -> str
```

### Train12306MCPClient

```python
class Train12306MCPClient:
    def __init__(self, config_path: str)
    async def connect(self)
    async def chat(self, user_message: str) -> str
    async def call_tool(self, name: str, args: Dict) -> Any
    async def cleanup(self)
```

---

## 🔮 扩展性设计

### 插件系统（V3.0）

未来可支持自定义工具：

```python
class CustomTool:
    def __init__(self):
        self.name = "my-tool"
        self.description = "..."
    
    async def execute(self, args: Dict) -> Any:
        # 自定义逻辑
        pass

# 注册工具
client.register_tool(CustomTool())
```

### 多 LLM 支持

通过适配器模式支持多种 LLM：

```python
class LLMAdapter:
    async def chat(self, messages, tools): ...

class DeepSeekAdapter(LLMAdapter): ...
class OpenAIAdapter(LLMAdapter): ...
class OllamaAdapter(LLMAdapter): ...
```

---

## 📚 参考资料

- [MCP 协议规范](https://modelcontextprotocol.io/)
- [12306-mcp 服务端](https://github.com/Joooook/12306-mcp)
- [aiohttp 文档](https://docs.aiohttp.org/)
- [OpenAI API 文档](https://platform.openai.com/docs/)

---

**文档版本**: V2.0.0  
**更新日期**: 2025-10-22  
**维护者**: 算法工程团队
