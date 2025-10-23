# 12306-MCP 智能查询客户端 V2.0

## 🎉 V2.0 重大升级

基于产品规划和技术评审，V2.0 完成了 **P0 级核心架构增强**，将客户端从"工具"升级为"智能助理平台"。

### ✨ 核心升级特性

#### 🔌 1. 增强的连接管理
- **自动重连机制**：网络断开时自动重连（SSE 和 HTTP 请求）
- **指数退避算法**：智能重试，避免服务器压力
- **心跳保持**：定期检查连接状态，保持长连接稳定
- **超时控制**：可配置的请求超时时间

#### ⚙️ 2. JSON 配置文件支持
- **结构化配置**：使用 `config.json` 管理所有配置项
- **分层配置**：服务器、LLM、内存、日志等模块化配置
- **环境变量**：敏感信息（API Key）仍使用 `.env` 管理
- **默认配置**：配置文件缺失时自动使用合理默认值

#### 🧠 3. 会话级上下文记忆
- **连续对话**：记住当前会话的所有上下文，支持追问和补充
- **智能截断**：自动管理上下文长度，避免超出 Token 限制
- **会话管理**：支持 `clear` 命令清空当前会话
- **历史保存**：会话结束时自动保存到历史记录

#### 🛡️ 4. 智能异常处理与重试
- **网络故障重试**：自动重试瞬时网络错误
- **错误分类处理**：区分瞬时故障和永久错误
- **优雅降级**：工具调用失败时给出友好提示
- **详细日志**：完整的错误追踪和调试信息

#### 👤 5. 用户持久化记忆（Bonus）
- **用户配置文件**：保存常用出发地、目的地、偏好等
- **地点别名**：支持"家"、"公司"等自定义别名
- **查询统计**：记录使用频率和最后活跃时间
- **个性化提示**：系统提示自动注入用户偏好

#### 📚 6. 跨会话历史记忆（Bonus）
- **历史记录加载**：可选加载最近几次对话的摘要
- **长期记忆**：AI 可以参考用户的历史行为模式
- **智能上下文**：自动提取历史对话的关键信息

---

## 📋 项目信息
- **Python**：版本 3.7+
- **版本**：V2.0
- **协议**：基于 MCP JSON-RPC 2.0
- **许可证**：MIT

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install aiohttp aiohttp-sse-client python-dotenv openai
```

### 2. 配置环境变量

创建 `.env` 文件（仅存放敏感信息）：

```env
# 大语言模型 API Key
DEEPSEEK_API_KEY="your_deepseek_api_key_here"
```

### 3. 配置 config.json

复制并编辑 `config.json`：

```json
{
  "mcp_server": {
    "url": "http://localhost:12306"
  },
  "llm": {
    "provider": "deepseek",
    "model": "deepseek-chat",
    "base_url": "https://api.deepseek.com"
  },
  "memory": {
    "session_enabled": true,
    "persistent_enabled": true,
    "load_recent_history": true
  }
}
```

### 4. 启动 12306-MCP 服务器

```bash
npx -y 12306-mcp --port 12306
```

### 5. 运行客户端

```bash
python MCP-SEE-Client.py
```

---

## 💡 使用指南

### 基本命令

客户端启动后，支持以下交互命令：

| 命令 | 说明 |
|------|------|
| `quit` / `exit` / `q` | 退出程序 |
| `tools` | 查看所有可用工具 |
| `clear` | 清空当前会话（开始新对话） |
| `profile` | 查看用户配置信息 |
| `history` | 查看对话历史统计 |

### 示例对话

#### 示例 1：会话记忆 - 连续追问

```
❓ 请输入问题: 明天深圳到广州的高铁票

🤖 [AI回复]
明天（2025-10-23）从深圳到广州的高铁车次如下：
1. G1234 - 08:00出发，09:15到达...
...

❓ 请输入问题: 最早的那趟有二等座吗？

🤖 [AI回复]
G1234次列车二等座还有票，票价为￥75...
```

**说明**：AI 记住了上一轮查询的结果，无需重复查询。

---

#### 示例 2：用户偏好 - 自动填充

编辑 `user_profile.json`：

```json
{
  "preferences": {
    "default_departure_city": "深圳",
    "default_arrival_city": "北京"
  },
  "aliases": {
    "home": "深圳北",
    "公司": "北京南"
  }
}
```

对话：

```
❓ 请输入问题: 明天回家的票

🤖 [AI回复]
（AI 自动识别"家"是"深圳北"，并查询从当前位置到深圳北的车票）
```

---

#### 示例 3：中转查询

```
❓ 请输入问题: 后天从拉萨到深圳，可以在西安中转吗？

🤖 [AI回复]
为您找到以下中转方案...
```

---

## ⚙️ 配置说明

### config.json 完整示例

```json
{
  "mcp_server": {
    "url": "http://localhost:12306",
    "connection": {
      "retry_attempts": 3,           // 重试次数
      "retry_delay": 1.0,            // 初始重试延迟（秒）
      "max_retry_delay": 30.0,       // 最大重试延迟（秒）
      "timeout_seconds": 30,         // 请求超时时间
      "sse_reconnect_enabled": true, // 启用SSE自动重连
      "sse_reconnect_interval": 5,   // SSE重连间隔（秒）
      "heartbeat_interval": 60       // 心跳间隔（秒，0表示禁用）
    }
  },
  "llm": {
    "provider": "deepseek",          // LLM提供商
    "model": "deepseek-chat",        // 模型名称
    "base_url": "https://api.deepseek.com",
    "max_iterations": 5,             // 最大工具调用轮数
    "system_prompt_path": "system_prompt.txt"  // 可选：自定义系统提示
  },
  "memory": {
    "session_enabled": true,         // 启用会话记忆
    "persistent_enabled": true,      // 启用持久化记忆
    "user_profile_path": "user_profile.json",
    "history_path": "conversation_history.json",
    "max_context_messages": 20,      // 最大上下文消息数
    "load_recent_history": true,     // 加载最近历史
    "recent_history_count": 3        // 加载最近N次会话
  },
  "logging": {
    "level": "INFO",                 // 日志级别：DEBUG, INFO, WARNING, ERROR
    "format": "%(asctime)s - %(levelname)s - %(message)s",
    "file": "mcp_client.log",        // 日志文件（可选）
    "console_enabled": true          // 控制台输出
  },
  "features": {
    "confirmation_mode": false,      // 确认-执行模式（P1功能）
    "confirmation_threshold": 3      // 超过N步调用时需确认
  }
}
```

### user_profile.json 配置

```json
{
  "user_id": "default_user",
  "preferences": {
    "default_departure_city": "深圳",      // 默认出发城市
    "default_arrival_city": "北京",        // 默认到达城市
    "preferred_seat_type": "二等座",       // 偏好席别
    "preferred_train_types": ["G", "D"]    // 偏好车次类型
  },
  "aliases": {
    "home": "深圳北",                      // 地点别名
    "office": "北京南",
    "常去": ["上海虹桥", "广州南"]
  }
}
```

---

## 🔄 更换 LLM 提供商

### OpenAI GPT-4

```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-4-turbo",
    "base_url": "https://api.openai.com/v1"
  }
}
```

`.env` 文件：
```env
DEEPSEEK_API_KEY="sk-your_openai_api_key"
```

### 本地模型 (Ollama)

```json
{
  "llm": {
    "provider": "ollama",
    "model": "qwen2:7b",
    "base_url": "http://localhost:11434/v1"
  }
}
```

`.env` 文件：
```env
DEEPSEEK_API_KEY="ollama"
```

---

## 🐛 故障排除

### 连接失败

**现象**：`❌ 连接失败: Cannot connect to host...`

**解决方案**：
1. 确认 `12306-mcp` 服务器已启动
2. 检查 `config.json` 中的 `mcp_server.url` 配置
3. 查看服务器日志，确认端口正确

### 工具调用失败

**现象**：`⚠️ 工具调用失败，已自动重试`

**解决方案**：
- V2.0 已内置自动重试，多数瞬时故障会自动恢复
- 如持续失败，检查网络连接和服务器状态
- 增加 `config.json` 中的 `retry_attempts` 和 `timeout_seconds`

### API Key 错误

**现象**：`Invalid API key`

**解决方案**：
1. 检查 `.env` 文件中的 `DEEPSEEK_API_KEY`
2. 确认 API Key 格式正确且有效
3. 检查 `config.json` 中的 `base_url` 是否正确

### 内存不足

**现象**：对话历史过长导致 Token 超限

**解决方案**：
1. 使用 `clear` 命令清空当前会话
2. 减小 `config.json` 中的 `max_context_messages`
3. 禁用历史加载：`"load_recent_history": false`

---

## 🛣️ 升级路线图

### ✅ V2.0（已完成）- P0 核心架构
- [x] 增强的连接管理
- [x] JSON 配置文件
- [x] 会话级上下文记忆
- [x] 智能异常处理
- [x] 用户持久化记忆（Bonus）
- [x] 跨会话历史记忆（Bonus）

### 🔜 V2.1（计划中）- P1 智能化
- [ ] 确认-执行模式
- [ ] 主动学习与澄清
- [ ] 历史对话摘要生成
- [ ] 多用户支持（SQLite）

### 🔮 V3.0（未来）- P2 服务化
- [ ] FastAPI 服务化封装
- [ ] RESTful API 接口
- [ ] WebUI 图形界面
- [ ] Docker 容器化部署

---

## 📊 架构对比

### V1.0 vs V2.0

| 特性 | V1.0 | V2.0 |
|------|------|------|
| 配置管理 | .env 文件 | .env + config.json |
| 连接稳定性 | 基础连接 | 自动重连 + 心跳 |
| 对话记忆 | 无记忆 | 会话级 + 历史记忆 |
| 异常处理 | 直接失败 | 智能重试 + 优雅降级 |
| 个性化 | 不支持 | 用户 Profile + 别名 |
| 可维护性 | 一般 | 结构化配置 + 日志 |

---

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

## 📝 更新日志

### V2.0.0 (2025-10-22)

**重大升级**：
- ✨ 新增 JSON 配置文件支持
- ✨ 实现会话级上下文记忆
- ✨ 增强连接管理（自动重连、心跳）
- ✨ 智能异常处理与重试
- ✨ 用户持久化记忆系统
- ✨ 跨会话历史记忆
- 🐛 修复 SSE 连接不稳定问题
- 📝 完善日志系统

### V1.0.0 (2025-10-18)

**初始版本**：
- ✨ 基础 MCP 客户端功能
- ✨ 工具调用支持
- ✨ 命令行交互界面

---

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。

---

## 🙏 致谢

- [12306-mcp](https://github.com/Joooook/12306-mcp) - MCP 服务端
- [Anthropic MCP](https://modelcontextprotocol.io/) - MCP 协议规范
- [DeepSeek](https://www.deepseek.com/) - LLM 提供商

---

## 📧 联系方式

如有问题或建议，请：
- 提交 Issue
- 发送邮件
- 加入讨论组

**Happy Traveling! 🚄**
