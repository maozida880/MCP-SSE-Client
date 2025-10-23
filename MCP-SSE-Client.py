import asyncio
import os
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pathlib import Path
import sys

import aiohttp
from aiohttp_sse_client.client import EventSource
from dotenv import load_dotenv
from openai import OpenAI

# 加载环境变量
load_dotenv()


# ===== Python 3.7/3.8 兼容性函数 =====
async def async_input(prompt: str) -> str:
    """
    异步输入函数，兼容Python 3.7+
    在Python 3.9+中使用asyncio.to_thread，在旧版本中使用run_in_executor
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, input, prompt)


class StationCodeMapper:
    """车站代码映射器：提供城市到车站代码的 fallback 映射"""
    
    # 常见城市代码映射表
    CITY_CODES = {
        "北京": "BJP", "上海": "SHH", "广州": "GZQ", "深圳": "SZQ",
        "杭州": "HZH", "南京": "NJH", "成都": "CDW", "武汉": "WHN",
        "西安": "XAY", "郑州": "ZZF", "重庆": "CQW", "天津": "TJP",
        "长沙": "CSQ", "沈阳": "SYT", "哈尔滨": "HBB", "大连": "DLT",
        "青岛": "QDK", "济南": "JNK", "福州": "FZS", "厦门": "XMS",
        "昆明": "KMM", "贵阳": "GIW", "兰州": "LZJ", "太原": "TYV",
        "石家庄": "SJP", "合肥": "HFH", "南昌": "NCG", "长春": "CCT",
        "乌鲁木齐": "URQ", "拉萨": "LSA", "呼和浩特": "HHC", "银川": "YIJ",
        "西宁": "XNO", "海口": "VUQ", "三亚": "SEQ", "苏州": "SZH",
        "无锡": "WXH", "常州": "CZH", "南通": "NTH", "宁波": "NVH",
        "温州": "RZH", "金华": "JHH", "珠海": "ZHQ", "汕头": "STQ",
        "佛山": "FSQ", "东莞": "DMQ", "中山": "ZSQ"
    }
    
    # 城市别名
    CITY_ALIASES = {
        "京": "北京", "沪": "上海", "穗": "广州", "深": "深圳",
        "蓉": "成都", "汉": "武汉", "杭": "杭州", "宁": "南京",
        "渝": "重庆", "津": "天津"
    }
    
    def __init__(self, custom_mapping_file: Optional[str] = None):
        self.mapping = self.CITY_CODES.copy()
        self.aliases = self.CITY_ALIASES.copy()
        
        # 加载自定义映射（如果存在）
        if custom_mapping_file and Path(custom_mapping_file).exists():
            try:
                with open(custom_mapping_file, 'r', encoding='utf-8') as f:
                    custom_data = json.load(f)
                    if 'station_codes' in custom_data:
                        self.mapping.update(custom_data['station_codes'])
                    if 'city_aliases' in custom_data:
                        self.aliases.update(custom_data['city_aliases'])
                logging.info(f"✅ 已加载自定义城市代码映射: {custom_mapping_file}")
            except Exception as e:
                logging.warning(f"⚠️ 加载自定义映射失败: {e}")
    
    def get_code(self, city_name: str) -> Optional[str]:
        """获取城市代码"""
        # 处理别名
        city = self.aliases.get(city_name, city_name)
        # 返回代码
        return self.mapping.get(city)
    
    def get_available_cities(self) -> List[str]:
        """获取所有支持的城市列表"""
        return list(self.mapping.keys())
    
    def search_city(self, keyword: str) -> List[str]:
        """搜索包含关键字的城市"""
        return [city for city in self.mapping.keys() if keyword in city]


class ConfigManager:
    """配置管理器：支持JSON配置文件和环境变量"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not Path(self.config_path).exists():
            logging.warning(f"配置文件 {self.config_path} 不存在，使用默认配置")
            return self._get_default_config()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"加载配置文件失败: {e}，使用默认配置")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            "mcp_server": {
                "url": "http://localhost:12306",
                "connection": {
                    "retry_attempts": 3,
                    "retry_delay": 1.0,
                    "max_retry_delay": 30.0,
                    "timeout_seconds": 30,
                    "sse_reconnect_enabled": True,
                    "heartbeat_interval": 60
                }
            },
            "llm": {
                "provider": "deepseek",
                "model": "deepseek-chat",
                "max_iterations": 5
            },
            "memory": {
                "session_enabled": True,
                "max_context_messages": 20
            },
            "logging": {
                "level": "INFO"
            }
        }
    
    def get(self, path: str, default: Any = None) -> Any:
        """获取配置项，支持点分路径，如 'mcp_server.url'"""
        keys = path.split('.')
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value


class UserProfileManager:
    """用户配置管理器：管理用户偏好和记忆"""
    
    def __init__(self, profile_path: str = "user_profile.json"):
        self.profile_path = profile_path
        self.profile = self._load_profile()
    
    def _load_profile(self) -> Dict[str, Any]:
        """加载用户配置"""
        if not Path(self.profile_path).exists():
            return self._create_default_profile()
        
        try:
            with open(self.profile_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"加载用户配置失败: {e}")
            return self._create_default_profile()
    
    def _create_default_profile(self) -> Dict[str, Any]:
        """创建默认用户配置"""
        profile = {
            "user_id": "default_user",
            "created_at": datetime.now().isoformat(),
            "preferences": {},
            "aliases": {},
            "travel_history": {"frequent_routes": []},
            "metadata": {"total_queries": 0}
        }
        self.save()
        return profile
    
    def save(self):
        """保存用户配置"""
        try:
            with open(self.profile_path, 'w', encoding='utf-8') as f:
                json.dump(self.profile, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"保存用户配置失败: {e}")
    
    def get_user_context(self) -> str:
        """获取用户上下文信息，用于增强系统提示"""
        prefs = self.profile.get('preferences', {})
        aliases = self.profile.get('aliases', {})
        
        context_parts = []
        
        if prefs.get('default_departure_city'):
            context_parts.append(f"- 常用出发地: {prefs['default_departure_city']}")
        
        if prefs.get('default_arrival_city'):
            context_parts.append(f"- 常用目的地: {prefs['default_arrival_city']}")
        
        if prefs.get('preferred_seat_type'):
            context_parts.append(f"- 偏好席别: {prefs['preferred_seat_type']}")
        
        if aliases:
            alias_strs = [f"'{k}' = '{v}'" for k, v in aliases.items() if v]
            if alias_strs:
                context_parts.append(f"- 地点别名: {', '.join(alias_strs)}")
        
        if context_parts:
            return "\n# 用户偏好\n" + "\n".join(context_parts) + "\n"
        return ""
    
    def update_query_stats(self):
        """更新查询统计"""
        if 'metadata' not in self.profile:
            self.profile['metadata'] = {}
        self.profile['metadata']['total_queries'] = self.profile['metadata'].get('total_queries', 0) + 1
        self.profile['metadata']['last_active'] = datetime.now().isoformat()


class ConversationMemory:
    """会话记忆管理器：管理对话历史"""
    
    def __init__(self, history_path: str = "conversation_history.json", max_messages: int = 20):
        self.history_path = history_path
        self.max_messages = max_messages
        self.current_session: List[Dict[str, Any]] = []
        self.history = self._load_history()
    
    def _load_history(self) -> List[Dict[str, Any]]:
        """加载历史对话"""
        if not Path(self.history_path).exists():
            return []
        
        try:
            with open(self.history_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"加载对话历史失败: {e}")
            return []
    
    def save_history(self):
        """保存对话历史"""
        try:
            # 只保存最近的会话
            recent_history = self.history[-50:] if len(self.history) > 50 else self.history
            with open(self.history_path, 'w', encoding='utf-8') as f:
                json.dump(recent_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"保存对话历史失败: {e}")
    
    def add_message(self, role: str, content: str):
        """添加消息到当前会话"""
        message = {"role": role, "content": content, "timestamp": datetime.now().isoformat()}
        self.current_session.append(message)
    
    def get_current_session(self, include_system: bool = True) -> List[Dict[str, str]]:
        """获取当前会话（用于LLM调用）"""
        # 截断过长的会话，保留最新的消息
        messages = self.current_session[-self.max_messages:] if len(self.current_session) > self.max_messages else self.current_session
        
        # 转换为LLM格式（移除timestamp）
        return [{"role": msg["role"], "content": msg["content"]} for msg in messages]
    
    def clear_session(self):
        """清除当前会话"""
        if self.current_session:
            # 保存到历史记录
            self.history.append({
                "session_id": datetime.now().isoformat(),
                "messages": self.current_session.copy()
            })
            self.save_history()
        self.current_session = []
    
    def get_recent_context(self, count: int = 3) -> str:
        """获取最近的对话上下文摘要"""
        if not self.history or count <= 0:
            return ""
        
        recent_sessions = self.history[-count:]
        context_parts = []
        
        for session in recent_sessions:
            messages = session.get('messages', [])
            # 只提取用户问题和助手回复的摘要
            for msg in messages:
                if msg['role'] == 'user':
                    content = msg['content'][:100]  # 截断
                    context_parts.append(f"用户曾问: {content}")
        
        if context_parts:
            return "\n# 最近对话记录\n" + "\n".join(context_parts[-5:]) + "\n"
        return ""


class Train12306MCPClient:
    """12306-MCP 增强版客户端 (V2.0) - Python 3.7+ 兼容版本"""
    
    def __init__(self, config_path: str = 'config.json'):
        # 加载配置
        self.config = ConfigManager(config_path)
        self.mcp_server_url = self.config.get('mcp_server.url', 'http://localhost:12306')
        
        # 设置日志
        self._setup_logging()
        
        # 连接相关
        self.session: Optional[aiohttp.ClientSession] = None
        self.sse_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.tools_cache: List[Dict[str, Any]] = []
        self.request_id = 0
        self.is_connected = False
        
        # 记忆系统
        if self.config.get('memory.session_enabled', True):
            max_context = self.config.get('memory.max_context_messages', 20)
            history_path = self.config.get('memory.history_path', 'conversation_history.json')
            self.memory = ConversationMemory(history_path, max_context)
        else:
            self.memory = None
        
        # 用户配置
        if self.config.get('memory.persistent_enabled', True):
            profile_path = self.config.get('memory.user_profile_path', 'user_profile.json')
            self.profile = UserProfileManager(profile_path)
        else:
            self.profile = None
        
        # 城市代码映射器
        city_codes_file = self.config.get('city_codes_file', 'city_codes.json')
        self.station_mapper = StationCodeMapper(city_codes_file)
        logging.info(f"📍 已加载 {len(self.station_mapper.get_available_cities())} 个城市代码映射")
        
        # 初始化OpenAI客户端
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        self.base_url = self.config.get('llm.base_url') or os.getenv('BASE_URL', 'https://api.deepseek.com')
        self.model = self.config.get('llm.model') or os.getenv('MODEL', 'deepseek-chat')
        
        if not self.api_key:
            raise ValueError("请设置环境变量 DEEPSEEK_API_KEY")
        
        # 配置 HTTP 客户端（支持代理和 SSL 设置）
        import httpx
        
        # 读取代理配置
        http_proxy = os.getenv('HTTP_PROXY') or os.getenv('http_proxy')
        https_proxy = os.getenv('HTTPS_PROXY') or os.getenv('https_proxy')
        
        # 是否禁用 SSL 验证（默认开启验证）
        verify_ssl = os.getenv('VERIFY_SSL', 'true').lower() != 'false'
        
        # 配置 httpx 客户端
        http_client_config = {
            'verify': verify_ssl,
            'timeout': 60.0,
        }
        
        # 如果有代理设置
        if http_proxy or https_proxy:
            http_client_config['proxies'] = {}
            if http_proxy:
                http_client_config['proxies']['http://'] = http_proxy
            if https_proxy:
                http_client_config['proxies']['https://'] = https_proxy
            logging.info(f"🌐 使用代理: HTTP={http_proxy}, HTTPS={https_proxy}")
        
        if not verify_ssl:
            logging.warning("⚠️ SSL 验证已禁用（不推荐用于生产环境）")
        
        http_client = httpx.Client(**http_client_config)
        
        self.client = OpenAI(
            api_key=self.api_key, 
            base_url=self.base_url,
            http_client=http_client
        )
        
        logging.info(f"🚀 MCP客户端初始化完成 (V2.0) - Python {sys.version_info.major}.{sys.version_info.minor}")
    
    def _setup_logging(self):
        """设置日志系统"""
        log_level = self.config.get('logging.level', 'INFO')
        log_format = self.config.get('logging.format', '%(asctime)s - %(levelname)s - %(message)s')
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format,
            handlers=[logging.StreamHandler()]
        )
    
    def _next_request_id(self) -> int:
        """生成下一个请求ID"""
        self.request_id += 1
        return self.request_id
    
    async def connect(self):
        """建立与MCP服务器的连接（增强版：支持自动重连）"""
        retry_attempts = self.config.get('mcp_server.connection.retry_attempts', 3)
        retry_delay = self.config.get('mcp_server.connection.retry_delay', 1.0)
        
        for attempt in range(retry_attempts):
            try:
                self.session = aiohttp.ClientSession()
                logging.info(f"🔗 正在连接到 12306-MCP 服务器: {self.mcp_server_url}")
                
                # 启动SSE监听任务
                if self.config.get('mcp_server.connection.sse_reconnect_enabled', True):
                    self.sse_task = asyncio.create_task(self._listen_sse_with_reconnect())
                
                # 启动心跳任务
                heartbeat_interval = self.config.get('mcp_server.connection.heartbeat_interval', 60)
                if heartbeat_interval > 0:
                    self.heartbeat_task = asyncio.create_task(self._heartbeat_loop(heartbeat_interval))
                
                # 初始化MCP连接
                await self._initialize()
                
                # 获取可用工具列表
                await self._fetch_tools()
                
                self.is_connected = True
                logging.info(f"✅ 连接成功,已加载 {len(self.tools_cache)} 个工具")
                
                # 加载最近的对话历史（如果启用）
                if self.memory and self.config.get('memory.load_recent_history', True):
                    recent_count = self.config.get('memory.recent_history_count', 3)
                    recent_context = self.memory.get_recent_context(recent_count)
                    if recent_context:
                        logging.info("📚 已加载最近对话记录")
                
                return
                
            except Exception as e:
                logging.error(f"❌ 连接失败 (尝试 {attempt + 1}/{retry_attempts}): {e}")
                if attempt < retry_attempts - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    logging.info(f"⏳ {wait_time:.1f}秒后重试...")
                    await asyncio.sleep(wait_time)
                else:
                    await self.cleanup()
                    raise
    
    async def _listen_sse_with_reconnect(self):
        """监听SSE事件流（增强版：支持自动重连）"""
        sse_url = f"{self.mcp_server_url}/sse"
        reconnect_interval = self.config.get('mcp_server.connection.sse_reconnect_interval', 5)
        
        while self.is_connected:
            try:
                logging.info("🔌 连接SSE事件流...")
                async with EventSource(sse_url, session=self.session) as event_source:
                    async for event in event_source:
                        if event.data and event.data.strip():
                            logging.debug(f"收到SSE事件: {event.data[:100]}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self.is_connected:
                    logging.warning(f"⚠️ SSE连接断开: {e}，{reconnect_interval}秒后重连...")
                    await asyncio.sleep(reconnect_interval)
                else:
                    break
    
    async def _heartbeat_loop(self, interval: int):
        """心跳循环：定期检查连接状态"""
        while self.is_connected:
            try:
                await asyncio.sleep(interval)
                # 发送一个轻量级的请求来保持连接
                await self._make_mcp_request("ping", {})
                logging.debug("💓 心跳检查成功")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.warning(f"⚠️ 心跳检查失败: {e}")
    
    def _parse_sse_response(self, body: str) -> Optional[Dict[str, Any]]:
        """解析SSE格式的响应"""
        try:
            if body.startswith('event:'):
                lines = body.strip().split('\n')
                for line in lines:
                    if line.startswith('data:'):
                        json_str = line[len('data:'):].strip()
                        return json.loads(json_str)
            elif body.startswith('data:'):
                json_str = body[len('data:'):].strip()
                return json.loads(json_str)
            else:
                return json.loads(body)
        except json.JSONDecodeError as e:
            logging.error(f"⚠️ JSON解析失败: {e}")
            return None
    
    async def _make_mcp_request(self, method: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """发送标准MCP JSON-RPC 2.0请求（增强版：支持重试）"""
        if not self.session:
            raise RuntimeError("客户端未连接")
        
        retry_attempts = self.config.get('mcp_server.connection.retry_attempts', 3)
        retry_delay = self.config.get('mcp_server.connection.retry_delay', 1.0)
        timeout = self.config.get('mcp_server.connection.timeout_seconds', 30)
        
        mcp_url = f"{self.mcp_server_url}/mcp"
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": method,
            "params": params or {}
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/event-stream',
        }
        
        last_error = None
        for attempt in range(retry_attempts):
            try:
                async with self.session.post(
                    mcp_url, 
                    json=payload, 
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    response.raise_for_status()
                    body = await response.text()
                    data = self._parse_sse_response(body)
                    
                    if data:
                        if 'error' in data:
                            error = data['error']
                            logging.error(f"❌ MCP错误: {error.get('message', 'Unknown error')}")
                            return None
                        return data.get('result')
                    return None
                    
            except (aiohttp.ClientResponseError, aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                logging.warning(f"⚠️ 请求失败 (尝试 {attempt + 1}/{retry_attempts}): {e}")
                
                if attempt < retry_attempts - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    await asyncio.sleep(wait_time)
                    continue
        
        logging.error(f"❌ 请求最终失败: {last_error}")
        return None
    
    async def _initialize(self):
        """初始化MCP连接"""
        result = await self._make_mcp_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "12306-mcp-client-v2",
                    "version": "2.0.0"
                }
            }
        )
        
        if result:
            server_info = result.get('serverInfo', {})
            logging.info(f"✅ MCP初始化成功")
            logging.info(f"   服务器: {server_info.get('name', 'unknown')}")
            logging.info(f"   版本: {server_info.get('version', 'unknown')}")
    
    async def _fetch_tools(self):
        """获取可用工具列表"""
        result = await self._make_mcp_request("tools/list")
        
        if result and 'tools' in result:
            tools = result['tools']
            logging.info(f"\n📋 可用工具:")
            for tool in tools:
                tool_name = tool.get('name', 'unknown')
                tool_desc = tool.get('description', '')[:60]
                logging.info(f"   • {tool_name}: {tool_desc}...")
            
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
        """调用MCP工具（增强版：智能重试）"""
        logging.info(f"\n🔧 调用工具: {tool_name}")
        logging.debug(f"📝 参数: {json.dumps(arguments, ensure_ascii=False, indent=2)}")
        
        result = await self._make_mcp_request(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments
            }
        )
        
        if result:
            logging.info(f"✅ 工具执行成功")
            return result
        
        return {"error": "工具调用失败，已自动重试"}

    def _build_system_prompt(self) -> str:
        """构建系统提示（增强版：集成用户偏好和历史）"""
        if not self.tools_cache:
            return "You are a helpful assistant."

        tool_descriptions = []
        for tool in self.tools_cache:
            func = tool.get('function', {})
            tool_name = func.get('name', 'unknown')
            tool_desc = func.get('description', '')
            tool_descriptions.append(f"- {tool_name}: {tool_desc}")

        tool_list_str = "\n".join(tool_descriptions)
        
        # 构建基础提示
        base_prompt = f"""# 角色
你是一个主动、智能、**有韧性**的12306火车票查询助手。你的唯一目标是高效地帮助用户找到火车票信息。

# 可用工具
{tool_list_str}

# 核心查询流程（必须严格遵循）
当用户查询火车票时，按以下顺序执行：

1. **获取日期**：调用 `get-current-date` 获取当前日期
2. **确定车站代码**：尝试以下方法（按优先级）：
   a. 使用 `get-station-code-of-citys` 获取城市代表站代码
   b. 如果失败，使用 `get-stations-code-in-city` 获取城市所有车站
   c. **如果仍然失败，使用常见城市代码表（见下方）**
3. **查询车票**：**无论前面是否成功获取车站信息，都必须调用 `get-tickets`**

# 常见城市代码表（Fallback）
当车站查询工具返回错误时，直接使用以下代码：
- 北京: BJP (北京站)
- 上海: SHH (上海站)
- 广州: GZQ (广州站)
- 深圳: SZQ (深圳站)
- 杭州: HZH (杭州站)
- 南京: NJH (南京站)
- 成都: CDW (成都站)
- 武汉: WHN (武汉站)
- 西安: XAY (西安站)
- 郑州: ZZF (郑州站)
- 重庆: CQW (重庆站)
- 天津: TJP (天津站)
- 长沙: CSQ (长沙站)
- 沈阳: SYT (沈阳站)
- 哈尔滨: HBB (哈尔滨站)

# 错误处理策略（关键！）
**重要**：当工具返回 "Error" 或 "not found" 时：
1. **不要放弃！** 这只是一个提示，不是终点
2. 立即尝试使用上面的城市代码表
3. 如果用户查询的城市在代码表中，**直接使用代码调用 `get-tickets`**
4. 只有在调用 `get-tickets` 后仍然失败时，才告诉用户无法查询

# 示例错误处理
❌ 错误做法：
```
工具返回 "Error: City not found"
→ 告诉用户"无法查询车站信息"
→ 结束
```

✅ 正确做法：
```
工具返回 "Error: City not found"
→ 查看城市代码表
→ 找到 深圳=SZQ, 杭州=HZH
→ 调用 get-tickets(fromStation="SZQ", toStation="HZH", ...)
→ 返回查询结果
```

# 核心指令
1. **永不轻言放弃**：遇到错误时，先尝试 fallback 方案
2. **必须查票**：只要用户想查票，就一定要调用 `get-tickets`
3. **主动推断**：不要询问用户，直接使用最佳策略
4. **严格格式**：调用工具时参数必须正确
"""
        
        # 添加用户偏好上下文
        if self.profile:
            user_context = self.profile.get_user_context()
            if user_context:
                base_prompt += f"\n{user_context}"
        
        # 添加最近对话历史
        if self.memory and self.config.get('memory.load_recent_history', True):
            recent_context = self.memory.get_recent_context(
                self.config.get('memory.recent_history_count', 3)
            )
            if recent_context:
                base_prompt += f"\n{recent_context}"
        
        return base_prompt

    async def chat(self, user_message: str, max_iterations: int = None) -> str:
        """与AI对话（增强版：会话记忆）"""
        if not self.session:
            raise RuntimeError("客户端未连接,请先调用 connect()")

        if not self.tools_cache:
            return "❌ 错误: 未加载任何工具,请检查MCP服务器"
        
        if max_iterations is None:
            max_iterations = self.config.get('llm.max_iterations', 5)
        
        # 记录用户消息
        if self.memory:
            self.memory.add_message("user", user_message)
        
        # 更新用户统计
        if self.profile:
            self.profile.update_query_stats()
        
        # 构建系统提示
        system_prompt = self._build_system_prompt()
        
        # 获取当前会话历史
        if self.memory:
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(self.memory.get_current_session(include_system=False))
        else:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        
        logging.info(f"\n💬 [用户] {user_message}")

        for i in range(max_iterations):
            logging.info(f"🤔 [AI] 正在思考... (第 {i+1} 轮)")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools_cache,
                tool_choice="auto"
            )
            
            assistant_message = response.choices[0].message
            
            if not assistant_message.tool_calls:
                final_response = assistant_message.content or "任务已完成。"
                logging.info("✅ [AI] 任务完成, 生成最终回复。")
                
                # 记录助手回复
                if self.memory:
                    self.memory.add_message("assistant", final_response)
                
                return final_response

            messages.append(assistant_message)

            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                
                try:
                    function_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    error_message = f"❌ 工具 '{function_name}' 的参数格式错误"
                    logging.error(error_message)
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
                
                logging.debug(f"  > 工具结果: {content_text[:250]}...")

                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": content_text,
                })
        
        logging.warning(f"⚠️ 达到最大迭代次数 ({max_iterations})，强制生成最终回复。")
        final_response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        final_text = final_response.choices[0].message.content or "已达到最大处理轮次。"
        
        # 记录助手回复
        if self.memory:
            self.memory.add_message("assistant", final_text)
        
        return final_text

    async def chat_loop(self):
        """交互式对话循环（增强版）- Python 3.7+ 兼容"""
        print("\n" + "="*70)
        print("🚄 12306-MCP 智能火车票查询助手 V2.0")
        print("="*70)
        print("💡 输入 'quit' 或 'exit' 退出")
        print("💡 输入 'tools' 查看可用工具")
        print("💡 输入 'clear' 清空当前会话")
        print("💡 输入 'profile' 查看用户配置")
        print("💡 输入 'history' 查看对话历史")
        print("="*70 + "\n")
        
        while True:
            try:
                # 使用兼容的异步输入函数
                user_input = await async_input("\n❓ 请输入问题: ")
                
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
                    if self.memory:
                        self.memory.clear_session()
                        print("✅ 当前会话已清空")
                    os.system('cls' if os.name == 'nt' else 'clear')
                    continue
                
                if user_input.lower() == 'profile':
                    if self.profile:
                        print("\n👤 用户配置:")
                        print(json.dumps(self.profile.profile, ensure_ascii=False, indent=2))
                    else:
                        print("⚠️ 用户配置未启用")
                    continue
                
                if user_input.lower() == 'history':
                    if self.memory:
                        print("\n📚 对话历史:")
                        print(f"当前会话消息数: {len(self.memory.current_session)}")
                        print(f"历史会话数: {len(self.memory.history)}")
                    else:
                        print("⚠️ 对话记忆未启用")
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
                logging.error(f"\n❌ 错误: {e}", exc_info=True)
    
    async def cleanup(self):
        """清理资源（增强版）"""
        self.is_connected = False
        
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        if self.sse_task and not self.sse_task.done():
            self.sse_task.cancel()
            try:
                await self.sse_task
            except asyncio.CancelledError:
                pass
        
        # 保存记忆
        if self.memory:
            self.memory.save_history()
        
        # 保存用户配置
        if self.profile:
            self.profile.save()
        
        if self.session and not self.session.closed:
            await self.session.close()
            logging.info("✅ 连接已关闭")


async def main():
    """主函数"""
    config_path = os.getenv('CONFIG_PATH', 'config.json')
    
    client = Train12306MCPClient(config_path)
    
    try:
        await client.connect()
        
        if not client.tools_cache:
            logging.warning("⚠️ 警告: 未能获取工具列表")
            return
        
        await client.chat_loop()
        
    except Exception as e:
        logging.error(f"❌ 程序错误: {e}", exc_info=True)
    finally:
        await client.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n程序被中断")
