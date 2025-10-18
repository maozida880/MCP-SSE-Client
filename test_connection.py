import asyncio
import aiohttp
import json
import uuid


async def test_tool_call(session: aiohttp.ClientSession, mcp_url: str, headers: dict):
    """测试工具调用功能"""
    print("\n  测试调用 get-current-date 工具...")
    
    # 使用标准MCP JSON-RPC格式
    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "get-current-date",
            "arguments": {}
        }
    }
    
    try:
        async with session.post(mcp_url, json=payload, headers=headers) as response:
            status = response.status
            body = await response.text()
            
            print(f"    状态码: {status}")
            
            if status == 200:
                print(f"    ✓ 工具调用成功!")
                
                # 解析SSE格式响应
                try:
                    if body.startswith('event:'):
                        lines = body.strip().split('\n')
                        for line in lines:
                            if line.startswith('data:'):
                                json_str = line[len('data:'):].strip()
                                data = json.loads(json_str)
                                break
                    elif body.startswith('data:'):
                        json_str = body[len('data:'):].strip()
                        data = json.loads(json_str)
                    else:
                        data = json.loads(body)
                    
                    print(f"    响应结构: {list(data.keys())}")
                    
                    if 'result' in data:
                        result = data['result']
                        print(f"    ✓ 结果: {json.dumps(result, ensure_ascii=False)[:200]}...")
                    elif 'error' in data:
                        print(f"    ✗ 错误: {data['error']}")
                        
                except json.JSONDecodeError as e:
                    print(f"    ⚠️ JSON解析失败: {e}")
            else:
                print(f"    ✗ 工具调用失败: {status}")
                print(f"    响应: {body[:200]}")
                
    except Exception as e:
        print(f"    ✗ 工具调用异常: {e}")


async def test_connection(server_url: str = "http://localhost:12306"):
    """测试与MCP服务器的连接"""
    
    print("="*60)
    print("12306-MCP 连接测试工具")
    print("="*60)
    
    async with aiohttp.ClientSession() as session:
        
        # 测试1: 检查服务器是否可访问
        print("\n[测试1] 检查服务器可访问性...")
        try:
            async with session.get(server_url) as response:
                print(f"✓ 服务器响应: HTTP {response.status}")
                print(f"  Content-Type: {response.headers.get('Content-Type')}")
        except Exception as e:
            print(f"✗ 服务器不可访问: {e}")
            return
        
        # 测试2: 测试SSE端点
        print("\n[测试2] 测试SSE端点...")
        sse_url = f"{server_url}/sse"
        try:
            async with session.get(sse_url) as response:
                print(f"✓ SSE端点响应: HTTP {response.status}")
                print(f"  Content-Type: {response.headers.get('Content-Type')}")
                # 读取第一个事件
                chunk = await response.content.read(100)
                print(f"  首个响应: {chunk[:50]}...")
        except Exception as e:
            print(f"⚠️ SSE端点测试失败: {e}")
        
        # 测试3: 测试MCP端点 (JSON格式)
        print("\n[测试3] 测试MCP端点 (JSON格式)...")
        mcp_url = f"{server_url}/mcp"
        
        # 保存成功的配置
        successful_config = None
        
        # 尝试不同的请求格式
        test_payloads = [
            {
                "name": "标准MCP JSON-RPC (tools/list)",
                "payload": {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                    "params": {}
                },
                "headers": {
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                }
            },
            {
                "name": "标准MCP JSON-RPC (initialize)",
                "payload": {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "test-client",
                            "version": "1.0.0"
                        }
                    }
                },
                "headers": {
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                }
            },
            {
                "name": "mcp-http-server格式 (空payload)",
                "payload": {},
                "headers": {
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                }
            },
            {
                "name": "GET风格查询",
                "payload": None,
                "headers": {
                    "Accept": "application/json, text/event-stream"
                },
                "method": "GET"
            }
        ]
        
        for test in test_payloads:
            print(f"\n  尝试: {test['name']}")
            try:
                # 支持GET和POST方法
                method = test.get('method', 'POST')
                
                if method == 'GET':
                    async with session.get(
                        mcp_url,
                        headers=test['headers']
                    ) as response:
                        status = response.status
                        content_type = response.headers.get('Content-Type')
                        body = await response.text()
                elif test['payload'] is None:
                    # 空body的POST
                    async with session.post(
                        mcp_url,
                        headers=test['headers']
                    ) as response:
                        status = response.status
                        content_type = response.headers.get('Content-Type')
                        body = await response.text()
                else:
                    # 正常POST
                    async with session.post(
                        mcp_url, 
                        json=test['payload'],
                        headers=test['headers']
                    ) as response:
                        status = response.status
                        content_type = response.headers.get('Content-Type')
                        body = await response.text()
                    
                    print(f"    状态码: {status}")
                    print(f"    Content-Type: {content_type}")
                    
                    if status == 200:
                        print(f"    ✓ 成功!")
                        print(f"    响应预览: {body[:200]}...")
                        
                        # 保存成功的配置
                        successful_config = test
                        
                        # 尝试解析响应
                        try:
                            if body.startswith('data:'):
                                json_str = body[len('data:'):].strip()
                                data = json.loads(json_str)
                            else:
                                data = json.loads(body)
                            
                            print(f"    响应结构: {list(data.keys())}")
                            
                            # 检查是否包含工具列表
                            if 'tools' in data:
                                tools = data['tools']
                                print(f"    ✓ 找到 {len(tools)} 个工具:")
                                for tool in tools[:5]:
                                    print(f"      - {tool.get('name')}: {tool.get('description', '')[:40]}...")
                                
                                # 记录成功配置用于后续测试
                                if not successful_config:
                                    successful_config = test
                                
                            elif 'result' in data and 'tools' in data['result']:
                                tools = data['result']['tools']
                                print(f"    ✓ 找到 {len(tools)} 个工具:")
                                for tool in tools[:5]:
                                    print(f"      - {tool.get('name')}: {tool.get('description', '')[:40]}...")
                                
                                # 记录成功配置用于后续测试
                                if not successful_config:
                                    successful_config = test
                                    
                        except json.JSONDecodeError as e:
                            print(f"    ⚠️ 响应不是有效JSON: {e}")
                    else:
                        print(f"    ✗ 失败: {status}")
                        if body:
                            try:
                                error_data = json.loads(body)
                                print(f"    错误: {error_data.get('error', {}).get('message', 'Unknown')}")
                                if 'data' in error_data.get('error', {}):
                                    print(f"    详情: {error_data['error']['data'][:500]}...")
                            except:
                                print(f"    响应: {body[:200]}")
                        
            except Exception as e:
                print(f"    ✗ 请求失败: {e}")
        
        # 如果找到成功的配置,进行工具调用测试
        if successful_config:
            print(f"\n[测试5] 测试工具调用 (使用成功的配置)...")
            await test_tool_call(session, mcp_url, successful_config['headers'])
        
        # 测试4: 直接HTTP GET测试
        print("\n[测试4] 测试HTTP GET请求...")
        try:
            async with session.get(mcp_url) as response:
                print(f"  GET响应: HTTP {response.status}")
                body = await response.text()
                print(f"  响应内容: {body[:200]}...")
        except Exception as e:
            print(f"  GET请求失败: {e}")
        
        print("\n" + "="*60)
        print("测试完成")
        print("="*60)


if __name__ == "__main__":
    import sys
    
    server_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:12306"
    print(f"\n测试服务器: {server_url}\n")
    
    try:
        asyncio.run(test_connection(server_url))
    except KeyboardInterrupt:
        print("\n测试被中断")