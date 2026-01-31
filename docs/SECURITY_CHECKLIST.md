# AgentOS 安全检查清单

> 在 PR 合并前和 Release 发布前，必须完成此清单。

## 使用说明

- **PR 审查**：审查者必须验证清单中相关项
- **Release 发布**：Release Manager 必须验证所有项
- **自动化**：可通过 CI/CD 自动执行部分检查

---

## A. 核心安全承诺验证

### A1. 默认 Chat-Only ✅

- [ ] 新增 Channel 的 manifest.json 中 `allow_execute: false`
- [ ] 新增 Channel 的默认 mode 是 `chat_only`
- [ ] UI 正确显示 "Chat-only" 徽章
- [ ] 尝试执行命令时弹出权限请求对话框

**测试命令**：
```bash
python scripts/security/test_default_chat_only.py
```

**预期输出**：
```
✅ 所有新 Channel 默认 chat-only
✅ UI 徽章显示正确
✅ 执行请求被拒绝
```

---

### A2. Execute 需授权 🔐

- [ ] 执行请求通过 Guardian 策略检查
- [ ] 危险命令（rm -rf、sudo、dd）被拦截
- [ ] 执行前显示命令预览和确认按钮
- [ ] 所有执行操作记录到审计日志

**测试命令**：
```bash
python scripts/security/test_execute_authorization.py
```

**预期输出**：
```
✅ Guardian 拦截危险命令
✅ 确认对话框弹出
✅ 审计日志已记录
```

**危险命令清单**：
```python
DANGEROUS_COMMANDS = [
    "rm -rf",
    "sudo",
    "dd if=",
    "mkfs",
    "> /dev/",
    "chmod 777",
    "chown root",
]
```

---

### A3. 不自动接管账号 🚫

- [ ] 无 OAuth 自动授权流程（grep -r "oauth_auto"）
- [ ] Setup Wizard 要求手动输入 Token
- [ ] 配置文件存储在本地（不上传云端）
- [ ] Token 加密存储（使用 Fernet/AES-256）

**测试命令**：
```bash
python scripts/security/test_no_auto_provision.py
```

**预期输出**：
```
✅ 无自动 OAuth 代码
✅ Token 加密存储
✅ 无云端上传
```

**代码审查重点**：
- 检查是否有 `requests.post(oauth_url, auto_approve=True)` 类似代码
- 检查是否有 `save_token_to_cloud()` 类似函数

---

### A4. 本地运行 🏠

- [ ] 数据库路径为本地文件（store/registry.sqlite）
- [ ] 无远程数据库连接（MySQL、PostgreSQL）
- [ ] LLM API Key 由用户提供
- [ ] 无遥测数据上传（除非用户显式开启）

**测试命令**：
```bash
python scripts/security/test_local_storage.py
```

**预期输出**：
```
✅ 数据库为本地 SQLite
✅ 无远程数据库配置
✅ 无默认遥测上传
```

**数据流向验证**：
```
用户消息 → AgentOS (本地) → LLM API (用户密钥) → 响应 (本地)
           ↓
      store/registry.sqlite (本地)
```

---

## B. 代码安全审查

### B1. 输入验证

- [ ] 所有用户输入都经过验证（Pydantic/Marshmallow）
- [ ] 文件路径经过规范化（防止路径穿越）
- [ ] 命令参数经过转义（防止命令注入）
- [ ] SQL 查询使用参数化（防止 SQL 注入）

**示例检查**：
```python
# ❌ 错误：直接拼接 SQL
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# ✅ 正确：参数化查询
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
```

**测试命令**：
```bash
python scripts/security/test_input_validation.py
```

---

### B2. 权限检查

- [ ] 所有执行操作都检查 `allow_execute`
- [ ] 文件操作检查路径权限
- [ ] API 端点检查认证 Token
- [ ] 跨项目操作检查隔离性

**关键代码位置**：
```python
# agentos/core/executor/executor_engine.py
if not channel.manifest.allow_execute:
    raise PermissionDenied("Channel does not have execute permission")

# agentos/core/guardian/policies.py
if command in DANGEROUS_COMMANDS:
    return PolicyDecision.REQUIRE_HUMAN_APPROVAL
```

**测试命令**：
```bash
python scripts/security/test_permission_checks.py
```

---

### B3. 审计日志

- [ ] 权限变更已记录
- [ ] 危险操作已记录
- [ ] 失败尝试已记录
- [ ] 日志包含完整上下文（who、what、when、where）

**审计事件类型**：
```python
AUDIT_EVENTS = [
    "permission_escalation",   # 权限升级
    "dangerous_command",       # 危险命令
    "failed_auth",             # 认证失败
    "config_change",           # 配置变更
    "token_rotation",          # Token 轮换
]
```

**测试命令**：
```bash
python scripts/security/test_audit_logging.py
```

---

### B4. 错误处理

- [ ] 错误消息不泄露敏感信息（堆栈、路径、Token）
- [ ] 生产环境禁用 DEBUG 模式
- [ ] 异常被正确捕获和记录
- [ ] 失败时 fail-closed（拒绝而非允许）

**错误消息审查**：
```python
# ❌ 错误：泄露路径
raise ValueError(f"File not found: /home/user/.env")

# ✅ 正确：模糊错误
raise ValueError("Configuration file not found")
```

**测试命令**：
```bash
python scripts/security/test_error_handling.py
```

---

### B5. 依赖安全

- [ ] 无已知高危漏洞（运行 `safety check`）
- [ ] 依赖版本固定（requirements.txt）
- [ ] 定期更新安全补丁
- [ ] 最小化依赖数量

**测试命令**：
```bash
pip install safety
safety check --json > safety-report.json
python scripts/security/analyze_safety_report.py
```

**预期输出**：
```
✅ 无 Critical/High 漏洞
⚠️  2 个 Medium 漏洞（已知可接受）
```

---

## C. Web 安全（WebUI）

### C1. CSRF 防护

- [ ] 所有 POST/PUT/DELETE 端点验证 CSRF Token
- [ ] 敏感 GET 端点也验证 CSRF（如 /api/execute）
- [ ] Origin/Referer 检查已启用
- [ ] SameSite Cookie 设置正确

**测试命令**：
```bash
python tests/security/test_csrf_comprehensive.py
```

**参考文档**：
- [CSRF 最佳实践](./security/CSRF_BEST_PRACTICES.md)
- [CSRF 回归防护](./security/CSRF_REGRESSION_PREVENTION.md)

---

### C2. 认证授权

- [ ] API Token 使用安全随机生成（secrets.token_urlsafe）
- [ ] Token 存储加密（不明文存储）
- [ ] 过期 Token 自动失效
- [ ] 速率限制已启用（防暴力破解）

**Token 生成示例**：
```python
import secrets
token = secrets.token_urlsafe(32)  # 256-bit
```

**测试命令**：
```bash
python scripts/security/test_auth.py
```

---

### C3. XSS 防护

- [ ] 用户输入经过 HTML 转义
- [ ] 使用 Content-Security-Policy 头
- [ ] 避免 innerHTML（使用 textContent）
- [ ] 模板引擎自动转义（Jinja2）

**CSP 配置**：
```python
# agentos/webui/app.py
@app.after_request
def set_csp(response):
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline';"
    )
    return response
```

**测试命令**：
```bash
python tests/security/test_xss_prevention.py
```

---

### C4. 敏感数据处理

- [ ] Token 不出现在 URL 中（使用 Header）
- [ ] 密码使用 bcrypt/argon2 哈希
- [ ] 敏感字段不记录日志
- [ ] HTTPS 强制（生产环境）

**敏感字段列表**：
```python
SENSITIVE_FIELDS = [
    "password",
    "token",
    "api_key",
    "secret",
    "private_key",
]
```

**日志过滤**：
```python
# ✅ 正确：过滤敏感字段
def sanitize_log(data: dict) -> dict:
    return {k: "***" if k in SENSITIVE_FIELDS else v for k, v in data.items()}
```

---

## D. 基础设施安全

### D1. 数据库安全

- [ ] SQLite 使用 WAL 模式（防数据损坏）
- [ ] 数据库文件权限正确（600）
- [ ] 备份加密存储
- [ ] 定期完整性检查（PRAGMA integrity_check）

**测试命令**：
```bash
python scripts/security/test_db_security.py
```

---

### D2. 文件系统安全

- [ ] 临时文件使用 tempfile 模块
- [ ] 敏感文件权限正确（600/700）
- [ ] 路径穿越防护（os.path.abspath）
- [ ] 定期清理临时文件

**路径验证示例**：
```python
import os

def safe_path(base: str, filename: str) -> str:
    path = os.path.abspath(os.path.join(base, filename))
    if not path.startswith(base):
        raise ValueError("Path traversal detected")
    return path
```

---

### D3. 进程隔离

- [ ] 执行命令使用最低权限
- [ ] 避免使用 shell=True
- [ ] 超时保护（防止无限执行）
- [ ] 资源限制（CPU、内存）

**安全执行示例**：
```python
import subprocess

# ❌ 错误：shell=True 有注入风险
subprocess.run(f"echo {user_input}", shell=True)

# ✅ 正确：列表形式，无 shell
subprocess.run(["echo", user_input], timeout=30)
```

---

## E. Release 前终极检查

### E1. 安全测试套件

- [ ] 所有安全测试通过（pytest tests/security/）
- [ ] OWASP Top 10 测试通过
- [ ] 渗透测试报告已审查
- [ ] 无未修复的 High/Critical 漏洞

**测试命令**：
```bash
pytest tests/security/ -v --tb=short
python scripts/security/verify_security_promises.sh
```

---

### E2. 文档更新

- [ ] SECURITY_NARRATIVE_V1.md 已更新
- [ ] CHANGELOG.md 包含安全相关变更
- [ ] README.md 安全章节已更新
- [ ] API 文档包含安全警告

---

### E3. 合规性检查

- [ ] GDPR 合规（数据本地化）
- [ ] 开源许可证正确（MIT/Apache）
- [ ] 第三方组件许可证兼容
- [ ] 安全公告模板准备就绪

---

### E4. 团队确认

- [ ] 安全负责人签字批准
- [ ] 代码审查者确认
- [ ] QA 测试完成
- [ ] Release Manager 最终批准

---

## F. 自动化检查（CI/CD）

### GitHub Actions 工作流

```yaml
# .github/workflows/security.yml
name: Security Checks

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: 验证默认 Chat-Only
        run: python scripts/security/test_default_chat_only.py

      - name: 检查依赖漏洞
        run: |
          pip install safety
          safety check

      - name: CSRF 测试
        run: pytest tests/security/test_csrf_comprehensive.py

      - name: 代码扫描
        run: bandit -r agentos/ -ll

      - name: 安全承诺验证
        run: bash scripts/security/verify_security_promises.sh
```

---

## G. 快速参考

### 常见安全问题速查

| 问题 | 检查命令 | 修复指南 |
|------|---------|---------|
| 默认配置不安全 | `grep -r "allow_execute.*True"` | 改为 `False` |
| 缺少权限检查 | `grep -r "execute(" \| grep -v "check_permission"` | 添加 Guardian 检查 |
| Token 明文存储 | `grep -r "save.*token" \| grep -v "encrypt"` | 使用 Fernet 加密 |
| SQL 注入风险 | `grep -r "cursor.execute.*f\""` | 改为参数化查询 |
| 命令注入风险 | `grep -r "subprocess.*shell=True"` | 改为列表形式 |

---

## H. 审查模板

### PR 安全审查评论模板

```markdown
## 安全审查

- [ ] ✅ 默认配置安全（chat-only）
- [ ] ✅ 权限检查完整
- [ ] ✅ 审计日志已添加
- [ ] ✅ 输入验证正确
- [ ] ✅ 无敏感信息泄露

**审查者**: @security-team
**日期**: 2026-02-01
**状态**: APPROVED / REQUIRES CHANGES
```

---

## I. 联系方式

- **安全问题**: security@agentos.dev
- **紧急联系**: [PGP 加密方式]
- **Slack 频道**: #security（内部）

---

**最后更新**: 2026-02-01
**文档版本**: 1.0
**适用范围**: AgentOS v1.x
