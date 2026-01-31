# WebUI 重启脚本使用指南

## 📋 脚本说明

提供了两个重启脚本，用于不同场景：

### 1. `restart_webui.sh` - 完整重启脚本（推荐）

**特点**:
- ✅ 详细的步骤提示和进度显示
- ✅ 完整的错误检查和日志输出
- ✅ 健康检查验证
- ✅ 彩色输出，易于阅读
- ✅ 适合调试和故障排查

**使用场景**:
- 首次使用或不确定服务器状态时
- 需要查看详细启动过程时
- 遇到启动问题需要诊断时
- 需要确认每个步骤是否成功时

### 2. `quick_restart.sh` - 快速重启脚本

**特点**:
- ⚡ 极简输出，快速执行
- ⚡ 适合日常频繁重启
- ⚡ 只显示最终结果

**使用场景**:
- 日常开发，频繁重启服务器
- 更新代码后快速应用更改
- 不需要查看详细过程时

---

## 🚀 使用方法

### 方式 1: 完整重启（推荐用于首次使用）

```bash
cd /Users/pangge/PycharmProjects/AgentOS
./restart_webui.sh
```

**输出示例**:
```
==========================================
🔄 Restarting AgentOS WebUI
==========================================

📛 Step 1: Stopping existing WebUI processes...
   Found PIDs: 70688
   🛑 Killing process 70688...
   ⏳ Waiting for processes to terminate...
   ✓ Stopped all existing processes

🔍 Step 2: Checking if port 8080 is free...
   ✓ Port 8080 is free

🚀 Step 3: Starting WebUI server...
   📝 Server PID: 71234

⏳ Step 4: Waiting for server to start...
   ✓ Server is responding

🏥 Step 5: Verifying server health...
   ✓ Health check passed

==========================================
✅ WebUI restart completed successfully!
==========================================

📊 Server Info:
   • PID: 71234
   • URL: http://127.0.0.1:8080
   • Log: /tmp/agentos_webui.log

💡 Useful commands:
   • View logs:  tail -f /tmp/agentos_webui.log
   • Stop server: kill 71234
   • Check status: curl http://127.0.0.1:8080/api/health

🌐 Open in browser: http://127.0.0.1:8080
```

---

### 方式 2: 快速重启（日常使用）

```bash
cd /Users/pangge/PycharmProjects/AgentOS
./quick_restart.sh
```

**输出示例**:
```
✅ WebUI restarted successfully
🌐 http://127.0.0.1:8080
```

---

## 📝 脚本做了什么

### 完整重启脚本步骤

1. **停止现有进程**
   - 查找所有 `uvicorn agentos.webui` 进程
   - 优雅地终止进程（SIGTERM）
   - 如有必要，强制终止（SIGKILL）

2. **检查端口**
   - 确认端口 8080 已释放
   - 如果被占用，强制释放

3. **启动服务器**
   - 使用虚拟环境的 Python
   - 后台运行 uvicorn
   - 日志输出到 `/tmp/agentos_webui.log`

4. **等待启动**
   - 最多等待 15 秒
   - 每秒检查健康端点
   - 失败时显示日志

5. **验证健康**
   - 调用 `/api/health` 端点
   - 确认服务器正常响应

---

## 🔍 故障排查

### 问题 1: 脚本没有执行权限

**错误信息**:
```
-bash: ./restart_webui.sh: Permission denied
```

**解决方案**:
```bash
chmod +x restart_webui.sh
chmod +x quick_restart.sh
```

---

### 问题 2: 虚拟环境不存在

**错误信息**:
```
✗ Virtual environment not found at .venv
```

**解决方案**:
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

---

### 问题 3: 服务器启动失败

**症状**:
```
✗ Server failed to start within 15 seconds
```

**排查步骤**:

1. **查看完整日志**:
   ```bash
   tail -50 /tmp/agentos_webui.log
   ```

2. **常见错误**:

   **a) 模块导入错误**:
   ```
   ModuleNotFoundError: No module named 'xxx'
   ```
   解决: `pip install xxx` 或重新安装依赖

   **b) 端口被占用**:
   ```
   OSError: [Errno 48] Address already in use
   ```
   解决:
   ```bash
   lsof -ti:8080 | xargs kill -9
   ```

   **c) 代码语法错误**:
   ```
   SyntaxError: invalid syntax
   ```
   解决: 检查最近修改的代码文件

3. **手动启动调试**:
   ```bash
   .venv/bin/python -m uvicorn agentos.webui.app:app \
       --host 127.0.0.1 --port 8080
   ```
   这会在前台运行，显示所有日志。

---

### 问题 4: 端口被其他进程占用

**排查**:
```bash
# 查看占用端口 8080 的进程
lsof -i:8080

# 输出示例:
# COMMAND   PID   USER
# Python  12345  pangge
```

**解决**:
```bash
# 方式 1: 使用脚本自动处理（推荐）
./restart_webui.sh

# 方式 2: 手动终止进程
kill -9 12345
```

---

## 💡 高级用法

### 1. 查看实时日志

```bash
tail -f /tmp/agentos_webui.log
```

按 `Ctrl+C` 退出。

### 2. 仅停止服务器

```bash
pkill -f "uvicorn.*agentos.webui"
```

### 3. 检查服务器状态

```bash
# 检查进程是否运行
ps aux | grep "uvicorn.*agentos.webui" | grep -v grep

# 检查端口是否监听
lsof -i:8080

# 检查健康端点
curl http://127.0.0.1:8080/api/health
```

### 4. 使用不同端口启动

如果需要在不同端口启动（如 8081）:

```bash
# 停止现有服务器
pkill -f "uvicorn.*agentos.webui"

# 启动到新端口
nohup .venv/bin/python -m uvicorn agentos.webui.app:app \
    --host 127.0.0.1 --port 8081 --log-level warning \
    > /tmp/agentos_webui.log 2>&1 &

# 访问
open http://127.0.0.1:8081
```

---

## 🔄 与 Git 配合使用

典型的开发工作流：

```bash
# 1. 拉取最新代码
git pull

# 2. 重启服务器应用更改
./restart_webui.sh

# 3. 打开浏览器测试
open http://127.0.0.1:8080
```

---

## 📊 性能调优

### 调整日志级别

**开发环境**（详细日志）:
```bash
nohup .venv/bin/python -m uvicorn agentos.webui.app:app \
    --host 127.0.0.1 --port 8080 --log-level debug \
    > /tmp/agentos_webui.log 2>&1 &
```

**生产环境**（最少日志）:
```bash
nohup .venv/bin/python -m uvicorn agentos.webui.app:app \
    --host 127.0.0.1 --port 8080 --log-level error \
    > /tmp/agentos_webui.log 2>&1 &
```

### 增加 Workers（提高并发）

```bash
nohup .venv/bin/python -m uvicorn agentos.webui.app:app \
    --host 127.0.0.1 --port 8080 --workers 4 \
    > /tmp/agentos_webui.log 2>&1 &
```

---

## ✅ 快速参考

| 操作 | 命令 |
|------|------|
| **完整重启** | `./restart_webui.sh` |
| **快速重启** | `./quick_restart.sh` |
| **查看日志** | `tail -f /tmp/agentos_webui.log` |
| **停止服务器** | `pkill -f "uvicorn.*agentos.webui"` |
| **检查状态** | `curl http://127.0.0.1:8080/api/health` |
| **查看进程** | `ps aux \| grep uvicorn` |
| **查看端口** | `lsof -i:8080` |

---

**创建时间**: 2026-01-28
**适用版本**: AgentOS v0.3.2+
