# AgentOS 安全快速参考卡

> 开发者必读 - 贴在显示器上的安全提醒

---

## 🚨 四大承诺（不可违反）

### 1. 🛡️ 默认 Chat-Only
```python
# ✅ 正确
SecurityDefaults(allow_execute=False)

# ❌ 错误
SecurityDefaults(allow_execute=True)
```

### 2. 🔐 Execute 需授权
```python
# ✅ 正确：检查权限
if not guardian.check_permission(cmd):
    raise PermissionDenied()

# ❌ 错误：直接执行
subprocess.run(cmd, shell=True)
```

### 3. 🚫 不自动授权
```python
# ✅ 正确：手动配置
token = input("Paste your token: ")

# ❌ 错误：自动 OAuth
oauth.auto_authorize()
```

### 4. 🏠 本地存储
```python
# ✅ 正确：本地 SQLite
db_path = "store/registry.sqlite"

# ❌ 错误：远程数据库
db_url = "postgresql://remote.com/db"
```

---

## ⚡ 开发时自查（5 秒检查）

添加新功能前问自己：

1. **默认安全吗？**
   - [ ] 默认配置是最安全的吗？

2. **需要权限吗？**
   - [ ] 是否添加了权限检查？

3. **有审计日志吗？**
   - [ ] 是否记录了操作日志？

4. **会泄露信息吗？**
   - [ ] 错误消息是否泄露敏感信息？

5. **测试覆盖吗？**
   - [ ] 是否有安全测试用例？

---

## 🔒 安全设计模式

### Fail-Closed（默认拒绝）
```python
# ✅ 正确
if user.has_permission():
    execute()
else:
    deny()

# ❌ 错误
if user.is_blocked():
    deny()
else:
    execute()
```

### Defense in Depth（多层防御）
```python
# ✅ 正确：多层检查
@rate_limit(20)
@require_permission
@audit_log
def execute_command(cmd):
    if is_dangerous(cmd):
        require_approval()
    return subprocess.run(cmd)
```

### Least Privilege（最小权限）
```python
# ✅ 正确：显式升级
user = User(permissions=["read"])
user.request_permission("write", reason="Need to update config")

# ❌ 错误：默认高权限
user = User(permissions=["admin"])
```

---

## 🚫 常见安全错误

### 1. 直接拼接 SQL
```python
# ❌ 错误：SQL 注入
query = f"SELECT * FROM users WHERE id = {user_id}"

# ✅ 正确：参数化查询
query = "SELECT * FROM users WHERE id = ?"
cursor.execute(query, (user_id,))
```

### 2. 使用 shell=True
```python
# ❌ 错误：命令注入
subprocess.run(f"echo {user_input}", shell=True)

# ✅ 正确：列表形式
subprocess.run(["echo", user_input])
```

### 3. 明文存储密码
```python
# ❌ 错误：明文
config["password"] = "secret123"

# ✅ 正确：加密
from cryptography.fernet import Fernet
encrypted = cipher.encrypt(password.encode())
```

### 4. 泄露敏感信息
```python
# ❌ 错误：泄露路径
raise ValueError(f"File not found: /home/user/.env")

# ✅ 正确：模糊错误
raise ValueError("Configuration file not found")
```

### 5. 无审计日志
```python
# ❌ 错误：无日志
execute_command(cmd)

# ✅ 正确：记录日志
audit_log.record("command_executed", {
    "command": cmd,
    "user": user_id,
    "timestamp": now()
})
execute_command(cmd)
```

---

## 📋 PR 提交前检查（1 分钟）

```bash
# 1. 运行安全验证
bash scripts/security/verify_security_promises.sh

# 2. 检查敏感信息
git diff | grep -i "password\|token\|secret\|api_key"

# 3. 运行安全测试
pytest tests/security/ -v

# 4. 检查依赖漏洞
pip install safety && safety check
```

预期结果：
```
✅ All security promises verified
✅ No sensitive info in diff
✅ All security tests pass
✅ No critical vulnerabilities
```

---

## 🔍 代码审查检查点

审查他人 PR 时检查：

- [ ] 默认配置安全
- [ ] 敏感操作有权限检查
- [ ] 审计日志完整
- [ ] 错误不泄露信息
- [ ] 输入经过验证
- [ ] SQL 使用参数化
- [ ] 命令避免 shell=True
- [ ] Token 加密存储
- [ ] 测试覆盖安全场景

---

## 🚨 危险命令清单

永远需要人工批准：

```python
DANGEROUS_COMMANDS = [
    "rm -rf",       # 递归删除
    "sudo",         # 提权
    "dd if=",       # 磁盘写入
    "mkfs",         # 格式化
    "> /dev/",      # 设备写入
    "chmod 777",    # 权限放宽
    "chown root",   # 所有权变更
    "kill -9",      # 强制终止
    "reboot",       # 重启
    "shutdown",     # 关机
]
```

---

## 🎯 审计日志必记事件

```python
AUDIT_EVENTS = [
    "permission_escalation",  # 权限升级
    "dangerous_command",      # 危险命令
    "failed_auth",            # 认证失败
    "config_change",          # 配置变更
    "token_rotation",         # Token 轮换
    "data_export",            # 数据导出
    "admin_action",           # 管理员操作
]
```

---

## 📞 紧急联系

- **安全问题**: security@agentos.dev
- **漏洞报告**: GitHub Security Advisories
- **文档**: [SECURITY_NARRATIVE_V1.md](./SECURITY_NARRATIVE_V1.md)

---

## 🎓 延伸阅读

- [安全叙事（FROZEN）](./SECURITY_NARRATIVE_V1.md)
- [安全检查清单](./SECURITY_CHECKLIST.md)
- [CSRF 防护指南](./security/CSRF_BEST_PRACTICES.md)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)

---

**记住**: 安全不是可选项，是必选项。

**签名**: AgentOS Security Team
**日期**: 2026-02-01
