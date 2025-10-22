# 12306-MCP 智能查询客户端

## 🎉 当前版本：V2.0

**V2.0 是一次重大架构升级**，从"工具"升级为"智能助理平台"。

### ✨ 核心特性

- 🔌 **增强的连接管理**：自动重连、指数退避、心跳保持
- ⚙️ **JSON配置文件**：结构化配置管理
- 🧠 **会话级记忆**：告别失忆，支持连续对话
- 🛡️ **智能异常处理**：自动重试，任务成功率提升80%
- 👤 **用户持久化记忆**：个性化服务
- 📚 **跨会话历史**：AI更懂你

### 📚 完整文档

详细使用指南请查看：[README-V2.md](README-V2.md)

### 🚀 快速开始

\\\ash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境
cp .env.example .env
# 编辑 .env，填写 DEEPSEEK_API_KEY

# 3. 启动MCP服务器
npx -y 12306-mcp --port 12306

# 4. 运行客户端
python MCP-SEE-Client-V2.py
\\\

### 📖 文档导航

- [**完整用户手册**](README-V2.md) - 详细的使用指南
- [**迁移指南**](MIGRATION_GUIDE.md) - 从V1.0升级到V2.0
- [**技术架构**](ARCHITECTURE.md) - 深入了解技术实现
- [**项目总结**](PROJECT_SUMMARY.md) - 升级概览

### 🛣️ 版本历史

- **V2.0** (2025-10-22) - 重大架构升级 [查看详情](PROJECT_SUMMARY.md)
- V1.0 (2025-10-18) - 初始版本

### 📄 许可证

MIT License

---

**Happy Traveling! 🚄**
