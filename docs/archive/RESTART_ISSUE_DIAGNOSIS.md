# 重启问题诊断报告

## 🔍 问题诊断

### 当前状态

1. **运行中的进程**：
   ```
   PID: 57466
   启动时间: 5:48PM
   命令: uvicorn agentos.webui.app:app --host 127.0.0.1 --port 9090
   ```

2. **PID 文件内容**：
   ```
   文件: ~/.agentos/webui.pid
   内容: 97238
   状态: 进程 97238 已不存在
   ```

### 🚨 问题根因

**PID 文件与实际运行进程不匹配！**

- PID 文件记录的 `97238` 是旧进程（已停止）
- 当前运行的 `57466` 是手动启动的，**未记录在 PID 文件中**

### ❌ 为什么 `uv run agentos webui restart` 不工作

`restart` 命令的执行流程：

```python
def restart(self) -> bool:
    self.stop()        # 1. 尝试停止 PID 文件中的进程
    time.sleep(1)
    return self.start() # 2. 启动新进程
```

```python
def stop(self) -> bool:
    pid = int(self.pid_file.read_text())  # 读取到 97238
    if not is_process_running(pid):        # 97238 不存在
        return True                         # 直接返回（认为已停止）
    # ...
```

**结果**：
1. `stop()` 读取 PID 文件，得到 `97238`
2. 检查发现 `97238` 不存在，认为服务器已停止
3. `start()` 尝试启动新服务器
4. **但是 `57466` 仍在运行！**
5. 新服务器可能与 `57466` 冲突（端口占用）

### 🎯 解决方案

#### 方案 1：使用完整重启脚本（推荐）

```bash
cd /Users/pangge/PycharmProjects/AgentOS
./restart_server_complete.sh
```

这个脚本会：
- ✅ 找到**所有** uvicorn 进程（不依赖 PID 文件）
- ✅ 停止所有进程
- ✅ 释放端口 9090
- ✅ 清理 PID 文件
- ✅ 启动新服务器
- ✅ 验证服务器正常运行

#### 方案 2：手动修复

```bash
# 1. 停止当前进程
kill 57466
sleep 2

# 2. 验证已停止
ps -p 57466 || echo "进程已停止"

# 3. 清理 PID 文件
rm -f ~/.agentos/webui.pid

# 4. 启动新服务器
uv run agentos webui start
```

#### 方案 3：强制停止所有进程

```bash
# 停止所有 uvicorn 进程
pkill -f "uvicorn agentos"

# 清理 PID 文件
rm -f ~/.agentos/webui.pid

# 启动新服务器
uv run agentos webui start
```

## 🔧 改进建议

### 1. 增强 `restart` 命令

修改 `daemon.py` 的 `stop()` 方法，不仅检查 PID 文件，还查找所有匹配的进程：

```python
def stop(self) -> bool:
    # 1. 先尝试从 PID 文件停止
    is_running, pid = self.is_running()
    if is_running:
        terminate_process(pid, timeout=5.0)
        self.pid_file.unlink(missing_ok=True)
        return True

    # 2. 查找所有匹配的 uvicorn 进程
    import subprocess
    try:
        result = subprocess.run(
            ["pgrep", "-f", f"uvicorn.*agentos.*{self.port}"],
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                logger.warning(f"Found orphan process {pid}, stopping...")
                terminate_process(int(pid), timeout=5.0)
            self.pid_file.unlink(missing_ok=True)
            return True
    except Exception as e:
        logger.debug(f"Failed to find orphan processes: {e}")

    return True
```

### 2. 添加 `restart --force` 选项

```python
@webui_group.command(name="restart")
@click.option("--force", is_flag=True, help="Force stop all uvicorn processes")
def restart_cmd(force: bool):
    if force:
        # 强制停止所有进程
        subprocess.run(["pkill", "-f", "uvicorn agentos"], check=False)
        time.sleep(1)

    daemon.restart()
```

## 📊 验证步骤

重启后，验证以下内容：

### 1. 进程状态

```bash
# 应该只有一个 uvicorn 进程
ps aux | grep "[u]vicorn.*agentos"
```

### 2. PID 文件

```bash
# PID 文件应该存在且内容与运行进程匹配
cat ~/.agentos/webui.pid
```

### 3. API 可访问

```bash
# 应该返回 {"status": "ok"}
curl http://127.0.0.1:9090/api/health
```

### 4. 代码已更新

```bash
# 测试 404 修复
python3 test_404_fix.py

# 应该看到：
# ✓ 测试 1 (错误 ZIP): ✓ 通过
# ✓ 测试 2 (正常 ZIP): ✓ 通过
```

## 🎯 立即行动

**推荐执行顺序**：

1. **停止旧进程并清理**：
   ```bash
   kill 57466 && rm -f ~/.agentos/webui.pid
   ```

2. **启动新服务器**：
   ```bash
   uv run agentos webui start
   ```

3. **验证修复**：
   ```bash
   python3 test_404_fix.py
   ```

或者使用一键脚本：
```bash
./restart_server_complete.sh
```

## 📝 总结

- ❌ **问题**：PID 文件过时，`restart` 命令无法找到真正运行的进程
- ✅ **解决**：使用完整重启脚本，或手动停止进程 + 清理 PID 文件
- 🔧 **改进**：增强 `restart` 命令，支持查找孤立进程

执行重启后，404 修复应该立即生效！
