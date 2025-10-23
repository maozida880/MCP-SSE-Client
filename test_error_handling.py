"""
测试脚本：验证 MCP-SSE-Client 的错误处理和 fallback 机制
"""
import asyncio
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_queries():
    """测试一系列查询"""
    
    # 导入客户端（需要在正确的位置）
    try:
        from MCP_SSE_Client_V2_fixed import Train12306MCPClient
        print("✅ 成功导入修复后的客户端\n")
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("请确保文件名正确: MCP-SEE-Client-V2-fixed.py → MCP_SSE_Client_V2_fixed.py")
        return
    
    # 测试用例
    test_cases = [
        "明天从深圳到杭州的火车",
        "今天北京到上海的高铁",
        "后天从广州到北京的票",
    ]
    
    print("="*70)
    print("🧪 开始测试 MCP-SSE-Client 错误处理")
    print("="*70)
    
    client = Train12306MCPClient()
    
    try:
        await client.connect()
        
        if not client.tools_cache:
            print("❌ 未能加载工具列表")
            return
        
        print(f"\n✅ 连接成功，已加载 {len(client.tools_cache)} 个工具")
        print(f"📍 城市代码映射: {len(client.station_mapper.get_available_cities())} 个城市\n")
        
        for i, query in enumerate(test_cases, 1):
            print(f"\n{'='*70}")
            print(f"测试 {i}/{len(test_cases)}: {query}")
            print('='*70)
            
            try:
                response = await client.chat(query, max_iterations=6)
                
                # 检查响应
                if "无法查询" in response or "抱歉" in response:
                    print(f"\n❌ 测试失败 - AI 仍然无法查询")
                    print(f"响应: {response[:200]}...")
                elif "车次" in response or "G" in response or "D" in response:
                    print(f"\n✅ 测试成功 - 找到火车票信息")
                    print(f"响应预览: {response[:200]}...")
                else:
                    print(f"\n⚠️  测试结果不确定")
                    print(f"响应: {response[:200]}...")
                    
            except Exception as e:
                print(f"\n❌ 查询出错: {e}")
        
        print(f"\n{'='*70}")
        print("🏁 测试完成")
        print('='*70)
        
    except Exception as e:
        print(f"❌ 连接或测试失败: {e}")
    finally:
        await client.cleanup()


def test_station_mapper():
    """测试城市代码映射器"""
    print("\n" + "="*70)
    print("🧪 测试城市代码映射器")
    print("="*70)
    
    try:
        from MCP_SSE_Client_V2_fixed import StationCodeMapper
        
        mapper = StationCodeMapper()
        
        test_cities = ["深圳", "杭州", "北京", "上海", "广州", "成都"]
        
        print(f"\n✅ 映射器初始化成功")
        print(f"📍 支持的城市数量: {len(mapper.get_available_cities())}")
        print(f"\n测试城市代码获取:")
        
        for city in test_cities:
            code = mapper.get_code(city)
            if code:
                print(f"  ✅ {city:6s} → {code}")
            else:
                print(f"  ❌ {city:6s} → 未找到")
        
        print(f"\n测试别名:")
        aliases = ["京", "沪", "穗", "深"]
        for alias in aliases:
            city = mapper.aliases.get(alias, alias)
            code = mapper.get_code(alias)
            print(f"  {alias} → {city} → {code}")
            
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════════════╗
║        MCP-SSE-Client V2 错误处理测试套件                         ║
╚════════════════════════════════════════════════════════════════════╝
    """)
    
    # 首先测试映射器
    test_station_mapper()
    
    # 然后测试完整查询
    print("\n")
    choice = input("是否运行完整查询测试？(需要 MCP Server 运行) [y/N]: ").lower()
    
    if choice == 'y':
        asyncio.run(test_queries())
    else:
        print("\n跳过完整查询测试")
    
    print("\n✅ 所有测试完成")
