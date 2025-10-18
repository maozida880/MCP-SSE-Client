# 12306-MCP 智能查询客户端

\<p align="center"\>
\<strong\>一个基于 MCP (Model Context Protocol) 协议的 12306 火车票智能查询客户端，可以通过自然语言与大语言模型（LLM）对话，实现复杂的票务查询。\</strong\>
\</p\>

\<p align="center"\>
\<img src="[https://img.shields.io/badge/Python-3.7+-blue.svg?logo=python\&logoColor=white](https://www.google.com/search?q=https://img.shields.io/badge/Python-3.7%2B-blue.svg%3Flogo%3Dpython%26logoColor%3Dwhite)" alt="Python Version"\>
\<img src="[https://img.shields.io/badge/MCP%20Protocol-JSON--RPC%202.0-brightgreen](https://www.google.com/search?q=https://img.shields.io/badge/MCP%2520Protocol-JSON--RPC%25202.0-brightgreen)" alt="MCP Protocol"\>
\<img src="[https://img.shields.io/badge/LLM-Tool%20Calling-orange](https://www.google.com/search?q=https://img.shields.io/badge/LLM-Tool%2520Calling-orange)" alt="LLM Tool Calling"\>
\<img src="[https://img.shields.io/github/license/Joooook/12306-mcp?style=flat-square\&color=000000](https://www.google.com/search?q=https://img.shields.io/github/license/Joooook/12306-mcp%3Fstyle%3Dflat-square%26color%3D000000)" alt="License"\>
\</p\>

-----

## ✨ 核心特性

  - 🤖 **高级智能对话**：内置强大的系统提示（System Prompt），引导大语言模型进行**多轮工具调用（Multi-turn Tool Calling）**，自动规划并执行复杂查询任务。
  - 🔧 **全功能支持**：全面支持 `12306-mcp` 服务端提供的所有工具，包括：
      - `get-tickets`: 查询余票信息（支持按车次类型筛选）
      - `get-interline-tickets`: 查询中转换乘方案
      - `get-train-route-stations`: 查询列车经停站
      - `get-station-code-of-citys`: 查询城市或车站的编码
      - `get-current-date`: 获取当前日期以解析“明天”、“后天”等相对时间
  - 🔌 **标准协议**：客户端与服务端之间采用标准的 MCP JSON-RPC 2.0 协议通过 HTTP/SSE 进行通信。
  - ⚙️ **高度可配置**：支持通过环境变量轻松切换不同的大语言模型提供商（如 DeepSeek, OpenAI, Ollama 本地模型等）。
  - 🖥️ **用户友好**：提供清晰的命令行交互界面，并支持 `tools`, `clear`, `quit` 等便捷指令。

## 🚀 快速开始

### 1\. 安装依赖

请确保您的 Python 环境 \>= 3.7，然后安装所需的依赖库。

```bash
pip install -r requirements.txt
```

*(如果项目中没有 `requirements.txt` 文件，请根据 `mcp_see_client.py` 中的 `import` 手动安装 `aiohttp`, `aiohttp-sse-client`, `python-dotenv`, `openai`)*

### 2\. 配置环境变量

复制 `.env.example` 文件为 `.env`，并根据您的配置填写：

```bash
cp .env.example .env
```

编辑 `.env` 文件内容：

```env
# 12306-MCP 服务器运行的地址和端口
MCP_SERVER_URL=http://localhost:12306

# 大语言模型 API 配置 (以 DeepSeek 为例)
DEEPSEEK_API_KEY="your_deepseek_api_key_here"
BASE_URL="https://api.deepseek.com"
MODEL="deepseek-chat"
```

### 3\. 启动 12306-MCP 服务器

在运行客户端之前，必须先启动后端的 `12306-mcp` 服务。请参考 [12306-mcp 项目文档](https://github.com/Joooook/12306-mcp)进行安装和启动。推荐使用 npx 启动：

```bash
# --port 参数必须与 .env 文件中的 MCP_SERVER_URL 端口一致
npx -y 12306-mcp --port 12306
```

### 4\. 运行客户端

一切就绪后，运行 Python 客户端程序：

```bash
python mcp_see_client.py
```

## 💡 使用示例

客户端启动后，您可以像聊天一样用自然语言提出复杂问题。

#### 示例 1：多步查询 - 查询明天的高铁票

> **❓ 请输入问题: 明天深圳到广州的高铁票**

**AI 内部执行流程：**

1.  **思考**: 用户想查票，需要日期、出发地代码、目的地代码。
2.  **调用 `get-current-date`**: 获取今天是 `2025-10-18`，计算出明天是 `2025-10-19`。
3.  **调用 `get-station-code-of-citys`**: 分别查询 "深圳" 和 "广州" 的车站代码。
4.  **调用 `get-tickets`**: 使用以上信息，结合“高铁”(`G`)作为筛选条件，查询车票。
5.  **生成回复**: 整合查询结果，以清晰的格式呈现给用户。

-----

#### 示例 2：中转查询

> **❓ 请输入问题: 从深圳到拉萨，最好在西安中转**

-----

#### 示例 3：经停站查询

> **❓ 请输入问题: G1033 这趟车明天都会经过哪些站？**

## 🔧 工作原理

本客户端是一个智能的“调度中心”，它本身不处理业务逻辑，而是将用户的自然语言请求交由大语言模型（LLM）进行分析和规划，然后精确地调用后端的 `12306-MCP` 服务来执行具体任务。

```mermaid
graph TD
    A[用户] -- 自然语言 --> B{智能客户端 (mcp_see_client.py)};
    B -- "1. 思考需要什么工具" --> C[LLM (如 DeepSeek)];
    C -- "2. 决定调用工具A" --> B;
    B -- "3. HTTP POST (JSON-RPC)" --> D[12306-MCP 服务器];
    D -- "4. 返回工具A结果" --> B;
    B -- "5. 将结果喂给LLM，继续思考" --> C;
    C -- "6. 决定调用工具B" --> B;
    B -- "7. ...重复调用..." --> D;
    D -- "8. 返回最终所需信息" --> B;
    B -- "9. 将所有结果汇总给LLM" --> C;
    C -- "10. 生成最终答复" --> B;
    B -- "11. 格式化输出" --> A;
```

这种**多轮工具调用**的能力，使得客户端能够自主解决需要多个前置步骤才能完成的复杂问题，而无需用户进行繁琐的手动分步查询。

## 🛠️ 配置与开发

### 更换 LLM 提供商

本客户端兼容所有遵循 OpenAI API 格式的大模型。您只需修改 `.env` 文件即可无缝切换。

**OpenAI GPT-4:**

```env
DEEPSEEK_API_KEY="sk-your_openai_api_key"
BASE_URL="https://api.openai.com/v1"
MODEL="gpt-4-turbo"
```

**本地模型 (Ollama):**

```env
DEEPSEEK_API_KEY="ollama"
BASE_URL="http://localhost:11434/v1"
MODEL="qwen2:7b" # 或者你本地运行的其他模型
```

### 故障排除

1.  **连接失败 (`Cannot connect to host...`)**:

      * 请确认 `12306-mcp` 服务器已在本地成功启动。
      * 检查 `.env` 文件中的 `MCP_SERVER_URL` 地址和端口是否与服务器启动时的一致。

2.  **未能获取工具列表**:

      * 大概率是 `MCP_SERVER_URL` 配置错误，或服务器未能正常启动。

3.  **API 调用失败 (`Invalid API key`)**:

      * 请检查 `.env` 文件中的 `DEEPSEEK_API_KEY` 和 `BASE_URL` 是否正确无误。

## 许可证

本项目基于 [MIT License](https://www.google.com/search?q=LICENSE) 开源。