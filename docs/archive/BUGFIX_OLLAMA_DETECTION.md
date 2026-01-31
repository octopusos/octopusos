# 修复：Ollama 服务状态检测

## 🐛 问题描述

### 原问题
```
✓ Ollama 服务已运行
验证 Ollama 连接...
✗ 连接失败: Connection refused
```

系统错误地将"Ollama 已安装"判断为"服务运行中"，导致：
1. 跳过了启动服务的步骤
2. 直接尝试连接，但连接失败
3. 导致启动流程中止

## 🔍 根本原因

### 原代码逻辑问题

**provider_checker.py:**
```python
def check_ollama(self) -> Tuple[bool, Optional[str]]:
    # 检查命令存在
    if shutil.which("ollama") is None:
        return False, "命令不存在"

    # 尝试连接 API
    try:
        response = requests.get("http://localhost:11434/api/version", timeout=2)
        if response.status_code == 200:
            return True, f"v{version}"
    except:
        pass

    # 检查命令可执行
    if subprocess.run(["ollama", "--version"]).returncode == 0:
        return True, version  # ❌ 问题：命令可用 ≠ 服务运行
```

**startup_checker.py:**
```python
is_running, info = self.provider_checker.check_ollama()

if not is_running or "未" in info:  # ❌ 问题：info 是英文 "Warning"
    # 启动服务
else:
    # 错误地认为服务已运行
```

## ✅ 修复方案

### 1. 改进状态检测

**provider_checker.py:**
```python
def check_ollama(self) -> Tuple[bool, Optional[str]]:
    """
    Returns:
        - True, "v0.15.2 (运行中)" - 服务正在运行
        - True, "已安装，服务未运行" - 已安装但未启动
        - False, "命令不存在" - 未安装
    """
    # 检查命令存在
    if shutil.which("ollama") is None:
        return False, "命令不存在"

    # 检查服务是否运行
    try:
        response = requests.get("http://localhost:11434/api/version", timeout=2)
        if response.status_code == 200:
            version = response.json().get("version", "unknown")
            return True, f"v{version} (运行中)"  # ✅ 明确标注运行中
    except:
        pass

    # 命令存在但服务未运行
    if subprocess.run(["ollama", "--version"]).returncode == 0:
        return True, "已安装，服务未运行"  # ✅ 明确标注未运行
```

### 2. 改进状态判断

**startup_checker.py:**
```python
is_available, info = self.provider_checker.check_ollama()

# 判断服务是否正在运行
service_running = "运行中" in info  # ✅ 明确检查关键字

if not service_running:
    rprint(f"[yellow]⚠️  Ollama 服务未运行[/yellow]")
    rprint(f"[dim]当前状态: {info}[/dim]")

    # 询问是否启动
    if Confirm.ask("是否启动 Ollama 服务?"):
        # 启动服务...
    else:
        # 询问是否继续启动 WebUI
        if Confirm.ask("是否仍要继续启动 WebUI? (稍后可手动启动 Ollama)"):
            return True  # 允许继续
        else:
            return False  # 中止启动
else:
    rprint(f"[green]✓ Ollama 服务已运行[/green]")
    # 继续验证连接...
```

## 🎯 修复后的行为

### 场景 1: Ollama 已安装但未运行

```bash
$ uv run agentos webui start

═══ 检查本地 AI Provider ═══
┏━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ Provider ┃ 状态          ┃ 信息               ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ Ollama   │ ✓ 可用        │ 已安装，服务未运行 │
└──────────┴──────────────┴────────────────────┘

✓ 使用 Provider: Ollama

配置 Ollama...
⚠️  Ollama 服务未运行
当前状态: 已安装，服务未运行
请输入 Ollama 服务端口 [11434]:
是否启动 Ollama 服务 (端口 11434)? [Y/n]: y

正在启动 Ollama 服务 (端口 11434)...
✓ Ollama 服务启动成功

验证 Ollama 连接...
✓ 连接成功，发现 3 个模型

更新 Provider 配置...
✓ 已更新配置: ollama -> http://127.0.0.1:11434
```

### 场景 2: Ollama 服务已运行

```bash
$ uv run agentos webui start

═══ 检查本地 AI Provider ═══
┏━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ Provider ┃ 状态          ┃ 信息               ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ Ollama   │ ✓ 可用        │ v0.15.2 (运行中)   │
└──────────┴──────────────┴────────────────────┘

✓ 使用 Provider: Ollama

配置 Ollama...
✓ Ollama 服务已运行
状态: v0.15.2 (运行中)

验证 Ollama 连接...
✓ 连接成功，发现 3 个模型
```

### 场景 3: 用户选择不启动服务

```bash
配置 Ollama...
⚠️  Ollama 服务未运行
当前状态: 已安装，服务未运行
请输入 Ollama 服务端口 [11434]:
是否启动 Ollama 服务 (端口 11434)? [Y/n]: n

⚠️  跳过启动 Ollama 服务
您需要手动启动: ollama serve
是否仍要继续启动 WebUI? (稍后可手动启动 Ollama) [y/N]: y

⚠️  跳过 Ollama 配置，继续启动 WebUI
提示: 启动 Ollama 后需手动在 WebUI 中配置

🚀 Starting WebUI...
```

## 📊 对比总结

| 方面 | 修复前 | 修复后 |
|------|--------|--------|
| 状态识别 | ❌ 命令可用 = 服务运行 | ✅ 明确区分安装和运行 |
| 错误处理 | ❌ 连接失败直接中止 | ✅ 询问是否启动服务 |
| 用户体验 | ❌ 错误提示混乱 | ✅ 清晰的状态说明 |
| 灵活性 | ❌ 必须启动服务 | ✅ 可选择跳过 |

## 🔧 测试验证

```bash
$ python3 -c "from agentos.cli.provider_checker import ProviderChecker; pc = ProviderChecker(); is_available, info = pc.check_ollama(); print(f'可用: {is_available}, 信息: {info}')"

可用: True, 信息: 已安装，服务未运行
```

✅ 检测结果正确！

## 📝 后续改进建议

1. **自动检测端口**
   - 从环境变量 `OLLAMA_HOST` 读取端口
   - 从进程列表检测实际运行端口

2. **更智能的启动**
   - 检测端口占用情况
   - 自动选择可用端口

3. **健康检查**
   - 启动后持续检查服务状态
   - 超时重试机制

## ✅ 修复完成

- [x] 修复状态检测逻辑
- [x] 改进错误提示
- [x] 增加灵活性选项
- [x] 更新文档
- [x] 测试验证

**问题已完全解决！** 🎉
