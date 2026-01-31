# Shell=True 修复摘要

## 修复完成时间
2026-01-29

## 问题描述
在代码审查中发现 `/Users/pangge/PycharmProjects/AgentOS/agentos/core/model/model_invoker.py` 文件中存在使用 `shell=True` 的安全漏洞，可能导致命令注入攻击。

## 修复内容

### 1. 修复文件列表

#### ✅ agentos/core/model/model_registry.py
**修改内容**:
- 在 `InvocationConfig` 数据类中添加了 `cli_command_list` 字段(列表形式，推荐)
- 将所有 CLI 配置从字符串形式迁移到列表形式：
  - `llamacpp`: `["llama-cpp-cli", "--model", "{model_id}", "--prompt", "{prompt}"]`
  - `Codex`: `["codex", "{prompt}"]`
  - `Claude-Code-CLI`: `["claude-code-cli", "{prompt}"]`
- 保留了旧的 `cli_command` 字段以保持向后兼容性

**代码变更**:
```python
@dataclass
class InvocationConfig:
    """调用配置"""
    method: str
    cli_command: Optional[str] = None  # 已废弃，不安全
    cli_command_list: Optional[List[str]] = None  # 新增，推荐使用
    api_endpoint: Optional[str] = None
    requires_auth: bool = True
    auth_env_vars: List[str] = field(default_factory=list)
```

#### ✅ agentos/core/model/model_invoker.py
**修改内容**:
1. **添加导入**: 导入 `shlex` 和 `logging` 模块
2. **重写 `invoke_cli` 方法**:
   - 优先使用 `cli_command_list` (安全的列表形式)
   - 向后兼容 `cli_command` (使用 shlex.quote 保护)
   - **完全移除 shell=True**，使用列表形式调用 subprocess
3. **添加辅助方法**:
   - `_build_safe_command_list()`: 安全地构建命令列表
   - `_build_legacy_command()`: 为旧配置提供向后兼容(使用 shlex 保护)

**关键安全改进**:
```python
# 之前 (不安全)
command = config.cli_command.format(model_id=model_id, prompt=prompt)
result = subprocess.run(command, shell=True, ...)  # ❌ 危险!

# 现在 (安全)
cmd = self._build_safe_command_list(config.cli_command_list, model_id=model_id, prompt=prompt)
result = subprocess.run(cmd, ...)  # ✅ 安全! 不使用 shell=True
```

### 2. 新增测试文件

#### ✅ tests/test_model_invoker_security.py
**测试覆盖**:
- ✅ 基础命令列表构建测试
- ✅ Shell 特殊字符处理测试 (`;`, `|`, `&&`, `||`, `$()`, `` ` ``, `>`, `<`, `*`, `$VAR`)
- ✅ 命令注入攻击防护测试 (12种不同的注入场景)
- ✅ 多占位符替换测试
- ✅ 旧式命令向后兼容性测试
- ✅ 超时和错误处理测试
- ✅ Unicode 字符处理测试
- ✅ 验证不使用 `shell=True`

**测试结果**: 24个测试全部通过 ✅

### 3. 生成审查报告

#### ✅ SHELL_TRUE_AUDIT_REPORT.md
详细的安全审查报告，包含：
- 统计数据和关键发现
- 详细的风险分析
- 攻击示例演示
- 修复方案对比
- 跨平台兼容性分析
- 实施计划建议
- 安全最佳实践参考

## 安全影响

### 修复前风险
- 🔴 **高危**: 命令注入漏洞
- 攻击者可以通过 `prompt` 参数注入任意 shell 命令
- 示例攻击: `"test'; rm -rf /; echo '"`

### 修复后状态
- 🟢 **安全**: 完全防止命令注入
- 所有用户输入被当作字面量处理
- 不使用 `shell=True`，避免 shell 解释

## 兼容性

### 向后兼容性
- ✅ 保留了旧的 `cli_command` 字段
- ✅ 自动检测并使用新的 `cli_command_list` (如果存在)
- ✅ 对旧配置发出弃用警告
- ✅ 使用 shlex.quote 保护旧配置(最小化风险)

### 跨平台兼容性
- ✅ 列表形式在 Windows/Unix/macOS 上都能正常工作
- ✅ 不依赖 shell 语法，避免平台差异
- ✅ 正确处理 Unicode 字符

## 测试验证

### 运行的测试
```bash
# 安全测试
uv run pytest tests/test_model_invoker_security.py -v
# 结果: 24 passed ✅

# 回归测试
uv run pytest tests/test_model_registry.py -v -k "not slow"
# 结果: 10 passed ✅
```

### 测试覆盖的攻击场景
1. ✅ 命令分隔符注入 (`;`)
2. ✅ 逻辑运算符注入 (`&&`, `||`)
3. ✅ 管道注入 (`|`)
4. ✅ 重定向注入 (`>`, `<`)
5. ✅ 命令替换注入 (`$()`, `` ` ``)
6. ✅ 环境变量注入 (`$VAR`)
7. ✅ 通配符注入 (`*`)
8. ✅ 换行符注入 (`\n`)
9. ✅ 后台任务注入 (`&`)

## 迁移指南

### 对于新配置
使用列表形式的 `cli_command_list`:
```python
InvocationConfig(
    method="cli",
    cli_command_list=["tool-name", "--option", "{placeholder}"],
    requires_auth=False
)
```

### 对于现有配置
1. **建议**: 迁移到 `cli_command_list`
2. **可选**: 保留 `cli_command` (会有警告，但使用 shlex 保护)

### 示例迁移
```python
# 旧配置 (仍然有效，但会发出警告)
config = InvocationConfig(
    method="cli",
    cli_command="echo {message}"  # ⚠️ 弃用
)

# 新配置 (推荐)
config = InvocationConfig(
    method="cli",
    cli_command_list=["echo", "{message}"]  # ✅ 推荐
)
```

## 最佳实践

### ✅ 正确做法
```python
# 1. 使用列表形式
subprocess.run(["command", user_input])

# 2. 如果必须使用字符串，用 shlex.quote
import shlex
subprocess.run(["command", shlex.quote(user_input)])
```

### ❌ 错误做法
```python
# 永远不要这样做
subprocess.run(f"command {user_input}", shell=True)
subprocess.run("command " + user_input, shell=True)
```

## 相关资源

- [CWE-78: OS Command Injection](https://cwe.mitre.org/data/definitions/78.html)
- [OWASP Command Injection](https://owasp.org/www-community/attacks/Command_Injection)
- [Python subprocess security](https://docs.python.org/3/library/subprocess.html#security-considerations)

## 后续建议

### 短期 (已完成)
- ✅ 修复 model_invoker.py 的命令注入漏洞
- ✅ 添加安全测试
- ✅ 生成审查报告

### 中期 (建议)
- ⏳ 在 CI/CD 中添加 bandit 安全扫描
- ⏳ 添加 pre-commit hook 检测 `shell=True`
- ⏳ 更新开发者文档，添加安全最佳实践

### 长期 (建议)
- ⏳ 定期进行安全审计 (每季度)
- ⏳ 添加运行时监控和告警
- ⏳ 考虑使用安全框架(如 bandit, semgrep)

## 结论

✅ **修复完成**: 已成功消除 model_invoker.py 中的命令注入风险
✅ **测试验证**: 所有安全测试通过，确保防护有效
✅ **向后兼容**: 不会破坏现有功能
✅ **文档完善**: 提供了详细的审查报告和迁移指南

项目现在对命令注入攻击有了完善的防护，安全态势从"中等"提升到"优秀"。

---

**修复人**: Claude Code Assistant
**审查日期**: 2026-01-29
**状态**: ✅ 完成
