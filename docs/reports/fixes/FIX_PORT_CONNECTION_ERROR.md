# 修复端口连接错误

## 问题描述
浏览器显示多个 `ERR_CONNECTION_REFUSED` 错误，API 请求失败：
```
GET http://127.0.0.1:8080/api/history?limit=100 net::ERR_CONNECTION_REFUSED
GET http://127.0.0.1:8080/api/health net::ERR_CONNECTION_REFUSED
GET http://127.0.0.1:8080/api/providers/status net::ERR_CONNECTION_REFUSED
```

## 根本原因
**WebUI 服务没有在运行**，或者浏览器打开的URL端口与服务运行的端口不匹配。

## 解决方案

### 步骤 1: 检查 AgentOS 服务是否运行

打开终端，运行：
```bash
# 检查 8080 端口是否有服务
lsof -i :8080

# 或者检查进程
ps aux | grep "agentos\|uvicorn"
```

**预期输出**（如果服务正在运行）：
```
Python    12345 user   10u  IPv4 0x...  TCP localhost:8080 (LISTEN)
```

**如果没有输出**：服务没有运行，需要启动。

### 步骤 2: 启动 AgentOS WebUI 服务

根据你的启动方式选择：

#### 方法 A: 使用 CLI 命令（推荐）
```bash
# 在项目根目录
agentos webui

# 或者指定端口
agentos webui --port 8080
```

#### 方法 B: 使用 Python 模块
```bash
# 在项目根目录
python -m agentos.webui.daemon

# 或者
python -m agentos.webui.app
```

#### 方法 C: 直接运行 daemon
```bash
cd /Users/pangge/PycharmProjects/AgentOS
python -m agentos.webui.daemon
```

### 步骤 3: 验证服务已启动

```bash
# 检查健康端点
curl http://127.0.0.1:8080/api/health
```

**预期输出**：
```json
{
  "status": "healthy",
  "version": "0.3.x",
  ...
}
```

### 步骤 4: 打开浏览器

服务启动后，在浏览器中访问：
```
http://127.0.0.1:8080
```

或者服务日志中显示的 URL。

### 步骤 5: 硬刷新浏览器

如果页面已经打开，清除缓存并刷新：
- **Mac**: `Cmd + Shift + R`
- **Windows/Linux**: `Ctrl + Shift + R`

## 常见问题

### Q1: 端口 8080 被占用
**错误**: `Address already in use: 8080`

**解决**:
```bash
# 查找占用端口的进程
lsof -i :8080

# 杀掉进程（替换 PID）
kill -9 <PID>

# 或者使用不同端口启动
agentos webui --port 8000
```

### Q2: 服务启动后立即退出
**可能原因**: Python 环境或依赖问题

**解决**:
```bash
# 检查 Python 版本
python --version  # 应该是 Python 3.8+

# 重新安装依赖
pip install -e .

# 或者在虚拟环境中
source venv/bin/activate  # Mac/Linux
pip install -e .
```

### Q3: 找不到 agentos 命令
**原因**: AgentOS 未安装或不在 PATH 中

**解决**:
```bash
# 在项目根目录安装
pip install -e .

# 或者直接用 Python 运行
python -m agentos.webui.daemon
```

### Q4: 服务在不同端口运行
**症状**: 服务在 8000 端口，但浏览器打开的是 8080

**解决**:
1. 检查服务实际运行的端口（查看启动日志）
2. 在浏览器中访问正确的端口
3. 关闭错误端口的标签页

## 诊断脚本

创建并运行这个脚本来诊断问题：

```bash
#!/bin/bash
# diagnosis.sh

echo "=== AgentOS WebUI 诊断 ==="
echo ""

echo "1. 检查 8080 端口..."
lsof -i :8080 || echo "   ✗ 端口 8080 没有服务"
echo ""

echo "2. 检查 AgentOS 进程..."
ps aux | grep -E "agentos|uvicorn" | grep -v grep || echo "   ✗ 没有找到 AgentOS 进程"
echo ""

echo "3. 检查 Python 环境..."
python --version
echo ""

echo "4. 测试健康端点..."
curl -s http://127.0.0.1:8080/api/health 2>&1 | head -5 || echo "   ✗ 无法连接到服务"
echo ""

echo "5. 检查 AgentOS 安装..."
pip show agentos 2>/dev/null || echo "   ✗ AgentOS 未安装"
echo ""

echo "=== 诊断完成 ==="
echo ""
echo "如果服务没有运行，执行："
echo "  python -m agentos.webui.daemon"
echo ""
echo "然后在浏览器中访问："
echo "  http://127.0.0.1:8080"
```

保存为 `diagnosis.sh`，然后运行：
```bash
chmod +x diagnosis.sh
./diagnosis.sh
```

## 快速修复命令

```bash
# 一键启动 AgentOS WebUI（在项目根目录）
cd /Users/pangge/PycharmProjects/AgentOS && python -m agentos.webui.daemon
```

启动后，浏览器访问：http://127.0.0.1:8080

## 正确的启动流程

1. **打开终端**
2. **进入项目目录**
   ```bash
   cd /Users/pangge/PycharmProjects/AgentOS
   ```

3. **激活虚拟环境**（如果使用）
   ```bash
   source venv/bin/activate  # Mac/Linux
   # 或
   venv\Scripts\activate  # Windows
   ```

4. **启动服务**
   ```bash
   python -m agentos.webui.daemon
   ```

5. **等待服务启动**
   看到类似输出：
   ```
   INFO:     Started server process [12345]
   INFO:     Waiting for application startup.
   INFO:     Application startup complete.
   INFO:     Uvicorn running on http://127.0.0.1:8080
   ```

6. **打开浏览器**
   访问：http://127.0.0.1:8080

## 检查清单

- [ ] AgentOS 服务正在运行
- [ ] 服务运行在 8080 端口（或其他已知端口）
- [ ] 浏览器访问的 URL 与服务端口匹配
- [ ] 没有防火墙阻止本地连接
- [ ] 浏览器缓存已清除
- [ ] 健康检查端点返回正常

## 需要帮助？

如果以上步骤都无法解决问题，请提供：
1. 服务启动命令和完整输出
2. `lsof -i :8080` 的输出
3. `ps aux | grep agentos` 的输出
4. 浏览器控制台的完整错误日志
