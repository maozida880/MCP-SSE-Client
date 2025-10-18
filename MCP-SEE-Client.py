import asyncio
import os
import json
from typing import Optional, Dict, Any, List

import aiohttp
from aiohttp_sse_client.client import EventSource
from dotenv import load_dotenv
from openai import OpenAI

# 加载环境变量
load_dotenv()


class Train12306MCPClient:
    """12306-MCP 标准客户端 (基于MCP JSON-RPC 2.0协议)"""
    
    def __init__(self, mcp_server_url: str = 'http://localhost:12306'):
        self.mcp_server_url = mcp_server_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.sse_task: Optional[asyncio.Task] = None
        self.tools_cache: List[Dict[str, Any]] = []
        self.request_id = 0
        
        # 初始化OpenAI客户端
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        self.base_url = os.getenv('BASE_URL', 'https://api.deepseek.com')
        self.model = os.getenv('MODEL', 'deepseek-chat')
        
        if not self.api_key:
            raise ValueError("请设置环境变量 DEEPSEEK_API_KEY")
        
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
    
    def _next_request_id(self) -> int:
        """生成下一个请求ID"""
        self.request_id += 1
        return self.request_id
    
    async def connect(self):
        """建立与MCP服务器的连接"""
        self.session = aiohttp.ClientSession()
        print(f"🔗 正在连接到 12306-MCP 服务器: {self.mcp_server_url}")
        
        try:
            # 启动SSE监听任务
            self.sse_task = asyncio.create_task(self._listen_sse())
            
            # 初始化MCP连接
            await self._initialize()
            
            # 获取可用工具列表
            await self._fetch_tools()
            
            print("✅ 连接成功,开始监听SSE事件")
            print(f"📦 已加载 {len(self.tools_cache)} 个工具\n")
            
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            await self.cleanup()
            raise
    
    async def _listen_sse(self):
        """监听SSE事件流"""
        sse_url = f"{self.mcp_server_url}/sse"
        
        try:
            async with EventSource(sse_url, session=self.session) as event_source:
                async for event in event_source:
                    if event.data and event.data.strip():
                        # 可以在这里处理服务器推送的事件
                        pass
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"⚠️ SSE连接异常: {e}")
    
    def _parse_sse_response(self, body: str) -> Optional[Dict[str, Any]]:
        """解析SSE格式的响应"""
        try:
            # 处理 "event: message\ndata: {...}" 格式
            if body.startswith('event:'):
                lines = body.strip().split('\n')
                for line in lines:
                    if line.startswith('data:'):
                        json_str = line[len('data:'):].strip()
                        return json.loads(json_str)
            # 处理 "data: {...}" 格式
            elif body.startswith('data:'):
                json_str = body[len('data:'):].strip()
                return json.loads(json_str)
            # 直接是JSON
            else:
                return json.loads(body)
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON解析失败: {e}")
            return None
    
    async def _make_mcp_request(self, method: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """发送标准MCP JSON-RPC 2.0请求"""
        if not self.session:
            raise RuntimeError("客户端未连接")
        
        mcp_url = f"{self.mcp_server_url}/mcp"
        
        # 标准MCP JSON-RPC 2.0格式
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": method,
            "params": params or {}
        }
        
        # 关键:必须同时接受两种格式
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/event-stream',
        }
        
        try:
            async with self.session.post(mcp_url, json=payload, headers=headers) as response:
                response.raise_for_status()
                body = await response.text()
                
                # 解析SSE格式响应
                data = self._parse_sse_response(body)
                
                if data:
                    # 检查错误
                    if 'error' in data:
                        error = data['error']
                        print(f"❌ MCP错误: {error.get('message', 'Unknown error')}")
                        return None
                    
                    # 返回结果
                    return data.get('result')
                
                return None
                    
        except aiohttp.ClientResponseError as e:
            print(f"❌ HTTP错误 {e.status}: {e.message}")
            return None
        except aiohttp.ClientError as e:
            print(f"❌ 请求错误: {e}")
            return None
    
    async def _initialize(self):
        """初始化MCP连接"""
        result = await self._make_mcp_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "12306-mcp-client",
                    "version": "1.0.0"
                }
            }
        )
        
        if result:
            server_info = result.get('serverInfo', {})
            print(f"✅ MCP初始化成功")
            print(f"   服务器: {server_info.get('name', 'unknown')}")
            print(f"   版本: {server_info.get('version', 'unknown')}")
            print(f"   协议: {result.get('protocolVersion', 'unknown')}")
    
    async def _fetch_tools(self):
        """获取可用工具列表"""
        result = await self._make_mcp_request("tools/list")
        
        if result and 'tools' in result:
            tools = result['tools']
            print(f"\n📋 可用工具:")
            for tool in tools:
                tool_name = tool.get('name', 'unknown')
                tool_desc = tool.get('description', '')[:60]
                print(f"   • {tool_name}: {tool_desc}...")
            
            # 转换为OpenAI函数调用格式
            self.tools_cache = []
            for tool in tools:
                input_schema = tool.get("inputSchema", {})
                self.tools_cache.append({
                    "type": "function",
                    "function": {
                        "name": tool.get("name", "unknown_tool"),
                        "description": tool.get("description", ""),
                        "parameters": input_schema
                    }
                })
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """调用MCP工具"""
        print(f"\n🔧 调用工具: {tool_name}")
        print(f"📝 参数: {json.dumps(arguments, ensure_ascii=False, indent=2)}")
        
        result = await self._make_mcp_request(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments
            }
        )
        
        if result:
            print(f"✅ 工具执行成功")
            return result
        
        return {"error": "工具调用失败"}

    def _build_system_prompt(self) -> str:
        """构建系统提示，帮助模型更好地理解和使用工具"""
        if not self.tools_cache:
            return "You are a helpful assistant."

        tool_descriptions = []
        for tool in self.tools_cache:
            func = tool.get('function', {})
            tool_name = func.get('name', 'unknown')
            tool_desc = func.get('description', '')
            tool_descriptions.append(f"- {tool_name}: {tool_desc}")

        tool_list_str = "\n".join(tool_descriptions)

        system_prompt = f"""**# 角色**
你是一个主动、智能的12306火车票查询助手，唯一的目标是高效地帮助用户解决问题。你必须使用提供的工具来完成任务。

**# 可用工具**
{tool_list_str}

**# 思维链与工具调用逻辑 (Chain of Thought & Tool Call Logic)**
你的核心任务是理解用户的**最终目标**，而不仅仅是字面意思。请遵循以下思考路径：

1.  **分析最终目标**：用户真正想达成什么？
    * 例如：用户问“明天深圳到广州的高铁票”，其最终目标是“查询明天从深圳出发到广州的高铁车次信息”。

2.  **分解目标与规划步骤**：要达成这个目标，需要哪些关键信息，并且以什么顺序获取？
    * 例如：要查询车票，我需要 “日期”、“出发地 station_code”、“到达地 station_code” 和 “车次类型”。
    * **步骤1**: 用户提到了“明天”，我需要先调用 `get-current-date` 确定具体日期。
    * **步骤2**: 用户提到了城市“深圳”和“广州”，我需要调用 `get-station-code-of-citys` 来获取它们的 `station_code`。
    * **步骤3**: 用户提到了“高铁”，这意味着 `trainFilterFlags` 应该是 'G'。
    * **步骤4**: 所有信息都齐全后，最后调用 `get-tickets` 进行查询。

3.  **主动执行**：如果工具可以提供关键信息，**不要询问用户，直接按顺序调用工具**。你被授权代表用户做出最高效的决策。

**# 核心指令**
1.  **主动推断与执行**：对于用户的间接请求，要主动推断其背后需要的信息，并直接调用相关工具，无需二次确认。
2.  **严格的参数格式**：调用工具时，参数必须严格符合工具的 schema 定义。特别是 `station_code` 不能是中文。
3.  **整合信息回复**：在所有必要的工具调用完成后，利用获得的信息，形成一个完整、有帮助的中文回复。
"""
        return system_prompt

    async def chat(self, user_message: str, max_iterations: int = 5) -> str:
        """与AI对话, 自动调用12306工具, 支持多轮工具调用"""
        if not self.session:
            raise RuntimeError("客户端未连接,请先调用 connect()")

        if not self.tools_cache:
            return "❌ 错误: 未加载任何工具,请检查MCP服务器"
        
        system_prompt = self._build_system_prompt()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        print(f"\n💬 [用户] {user_message}")

        for i in range(max_iterations):
            print(f"🤔 [AI] 正在思考... (第 {i+1} 轮)")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools_cache,
                tool_choice="auto"
            )
            
            assistant_message = response.choices[0].message
            
            if not assistant_message.tool_calls:
                print("✅ [AI] 任务完成, 生成最终回复。")
                return assistant_message.content or "任务已完成。"

            messages.append(assistant_message)

            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                
                try:
                    function_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    error_message = f"❌ 工具 '{function_name}' 的参数格式错误"
                    print(error_message)
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": error_message,
                    })
                    continue

                tool_result = await self.call_tool(function_name, function_args)
                
                if isinstance(tool_result, dict) and "content" in tool_result:
                    content_list = tool_result["content"]
                    if isinstance(content_list, list) and len(content_list) > 0:
                        content_text = content_list[0].get("text", json.dumps(tool_result, ensure_ascii=False))
                    else:
                        content_text = json.dumps(tool_result, ensure_ascii=False)
                else:
                    content_text = str(tool_result)
                
                print(f"  > 工具结果: {content_text[:250]}...")

                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": content_text,
                })
        
        print(f"⚠️ 达到最大迭代次数 ({max_iterations})，强制生成最终回复。")
        final_response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        return final_response.choices[0].message.content or "已达到最大处理轮次。"

    async def chat_loop(self):
        """交互式对话循环"""
        print("\n" + "="*70)
        print("🚄 12306-MCP 智能火车票查询助手")
        print("="*70)
        print("💡 输入 'quit' 或 'exit' 退出")
        print("💡 输入 'tools' 查看可用工具")
        print("💡 输入 'clear' 清屏")
        print("="*70 + "\n")
        
        while True:
            try:
                user_input = await asyncio.to_thread(
                    input, 
                    "\n❓ 请输入问题: "
                )
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 再见!")
                    break
                
                if user_input.lower() == 'tools':
                    print("\n📋 可用工具:")
                    for i, tool in enumerate(self.tools_cache, 1):
                        func = tool['function']
                        print(f"{i}. {func['name']}")
                        print(f"   {func['description'][:80]}...")
                    continue
                
                if user_input.lower() == 'clear':
                    os.system('cls' if os.name == 'nt' else 'clear')
                    continue
                
                if not user_input.strip():
                    continue
                
                # 处理用户查询
                response = await self.chat(user_input)
                print(f"\n🤖 [AI回复]\n{response}")
                
            except (KeyboardInterrupt, EOFError):
                print("\n\n👋 检测到退出信号")
                break
            except Exception as e:
                print(f"\n❌ 错误: {e}")
    
    async def cleanup(self):
        """清理资源"""
        if self.sse_task and not self.sse_task.done():
            self.sse_task.cancel()
            try:
                await self.sse_task
            except asyncio.CancelledError:
                pass
        
        if self.session and not self.session.closed:
            await self.session.close()
            print("✅ 连接已关闭")


async def main():
    """主函数"""
    url = 'http://localhost:12306'
    #url = 'https://mcp.api-inference.modelscope.net/e15d742f57a045/sse'
    mcp_server_url = os.getenv('MCP_SERVER_URL', url)
    
    client = Train12306MCPClient(mcp_server_url)
    
    try:
        await client.connect()
        
        if not client.tools_cache:
            print("⚠️ 警告: 未能获取工具列表")
            return
        
        await client.chat_loop()
        
    except Exception as e:
        print(f"❌ 程序错误: {e}")
    finally:
        await client.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n程序被中断")