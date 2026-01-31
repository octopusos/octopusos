# 重启服务器指南

## 问题

代码已修改但未生效，因为 uvicorn 进程仍在运行旧代码。

## 检查当前进程

```bash
ps aux | grep "[p]ython.*webui\|[u]vicorn.*agentos"
```

当前输出：
```
pangge  57466  ... uvicorn agentos.webui.app:app --host 127.0.0.1 --port 9090
```

PID: **57466**

---

## ⚡ 快速解决（推荐）

**使用完整重启脚本**：

```bash
cd /Users/pangge/PycharmProjects/AgentOS
./restart_server_complete.sh
```

这个脚本会自动完成所有步骤：停止旧进程、释放端口、验证代码、启动新服务器。

详细说明请查看：[HOW_TO_RESTART.md](HOW_TO_RESTART.md)

---

## 重启步骤（手动）

### 方法 1: 使用 kill 命令（推荐）

```bash
# 找到进程 PID
ps aux | grep "[u]vicorn.*agentos"

# 优雅停止
kill 57466

# 等待 2 秒
sleep 2

# 检查是否已停止
ps aux | grep "[u]vicorn.*agentos"

# 如果还在运行，强制停止
kill -9 57466
```

### 方法 2: 使用 pkill

```bash
# 停止所有 uvicorn 进程
pkill -f "uvicorn agentos"

# 或强制停止
pkill -9 -f "uvicorn agentos"
```

### 方法 3: 从终端停止

如果在终端运行的服务器：
```bash
# 按 Ctrl+C
```

## 启动服务器

```bash
# 进入项目目录
cd /Users/pangge/PycharmProjects/AgentOS

# 启动服务器
python -m agentos webui start

# 或使用 uvicorn 直接启动
uvicorn agentos.webui.app:app --host 127.0.0.1 --port 9090 --reload
```

**注意**: 添加 `--reload` 参数可以自动重载代码（开发模式）

## 验证服务器已启动

```bash
# 测试 API
curl http://127.0.0.1:9090/api/health

# 或
curl http://127.0.0.1:9090/api/extensions
```

## 验证代码已生效

重启后运行测试：

```bash
python3 debug_install_step_by_step.py
```

应该看到：
- ✅ Install Record 被创建
- ✅ 不再返回 404
- ✅ 能查询到安装进度

## 快速重启命令（一键执行）

```bash
# 停止旧进程并启动新进程
pkill -f "uvicorn agentos" && sleep 2 && python -m agentos webui start &

# 或者只重启（保留日志）
pkill -f "uvicorn agentos" && sleep 2 && uvicorn agentos.webui.app:app --host 127.0.0.1 --port 9090 --reload &
```

## 检查修改是否已加载

启动后检查代码版本：

```bash
# 检查方法是否存在
grep -n "create_install_record_without_fk" agentos/webui/api/extensions.py

# 应该看到两处调用（第 451 和 665 行）
```

## 常见问题

### Q: kill 后进程还在？
A: 使用 `kill -9` 强制停止

### Q: 端口被占用？
A:
```bash
# 查找占用端口的进程
lsof -i :9090

# 停止该进程
kill -9 <PID>
```

### Q: 代码修改后还是不生效？
A:
1. 确认文件已保存
2. 确认进程已重启
3. 检查是否有多个 Python 环境
4. 使用 `--reload` 参数启动

## 测试修复

重启后立即测试：

```bash
# 1. 测试详细调试
python3 debug_install_step_by_step.py

# 2. 测试 404 修复
python3 test_404_fix.py
```

应该看到：
- ✅ Install Record 立即被创建
- ✅ 验证失败时返回 FAILED（不是 404）
- ✅ 前端能看到清晰的错误信息
