# AgentOS 安全叙事 v1（FROZEN）

## 状态
✅ **FROZEN** - 2026-02-01
这是 AgentOS 对用户的安全承诺，不可违反。

---

## 核心安全承诺（对外叙事）

### 1. 🛡️ 默认 Chat-Only（最小权限原则）
**承诺**：AgentOS 默认只能与您对话，不能执行任何系统命令或修改文件。

**实现**：
- 所有新 channel 默认 `mode: "chat_only"`
- `allow_execute: false` 硬编码在 manifest.json
- 需要执行权限时，必须显式授权

**用户可见**：
- UI 显示 "Chat-only" 徽章
- 执行命令前弹出确认对话框
- 审计日志记录所有权限变更

**代码证据**：
```python
# agentos/communicationos/channels/base.py
class ChannelManifest(BaseModel):
    allow_execute: bool = False  # 默认禁用执行
    mode: str = "chat_only"      # 默认仅聊天
```

---

### 2. 🔐 Execute 永远需要核心授权（多层防御）
**承诺**：即使您授权了执行权限，每个危险操作仍需二次确认。

**实现**：
- Guardian 策略层拦截所有执行请求
- 高危命令（rm -rf、sudo、dd）需人工审批
- 速率限制：每分钟最多 N 次执行
- 回滚机制：失败自动恢复

**用户可见**：
- 执行前显示命令预览
- "确认执行"按钮
- 实时执行日志
- 一键撤销

**代码证据**：
```python
# agentos/core/guardian/policies.py
class ExecutionPolicy:
    DANGEROUS_COMMANDS = ["rm -rf", "sudo", "dd", "mkfs", "> /dev"]

    def check(self, command: str) -> PolicyDecision:
        if any(dangerous in command for dangerous in self.DANGEROUS_COMMANDS):
            return PolicyDecision.REQUIRE_HUMAN_APPROVAL
```

---

### 3. 🚫 不自动接管第三方账号（手动配置原则）
**承诺**：AgentOS 永远不会自动连接您的 Slack/Discord/Email，所有配置由您手动完成。

**实现**：
- 无 OAuth 自动授权流程
- 用户手动复制 Token/API Key
- Setup Wizard 提供分步指导
- 配置存储在本地（加密）

**我们不做**：
- ❌ "一键连接 Slack"
- ❌ "自动导入联系人"
- ❌ "代理登录"

**我们做**：
- ✅ "手动配置 Bot Token"
- ✅ "本地加密存储"
- ✅ "随时撤销权限"

**设计证据**：
```json
// manifest.json 必须声明
{
  "provisioning": "manual",
  "oauth_flow": "disabled",
  "privacy_badges": ["Manual Configuration", "No Auto Provisioning"]
}
```

---

### 4. 🏠 本地运行 / 用户可控（数据主权）
**承诺**：您的数据永远在您的设备上，AgentOS 不会上传到云端。

**实现**：
- SQLite 本地数据库（store/registry.sqlite）
- 所有配置文件本地存储（.env）
- LLM API Key 由用户提供（不经过我们的服务器）
- 可选：自托管部署（Docker）

**数据流向**：
```
您的消息 → AgentOS（本地） → LLM API（您的密钥） → 响应（本地）
         ↑_____________本地存储（SQLite）_______________↑
```

**绝不**：
- ❌ 上传对话到 AgentOS 云端
- ❌ 收集用户 Token
- ❌ 远程遥测（除非显式开启）

**架构证据**：
- 数据库路径：`store/registry.sqlite`（本地文件）
- 配置路径：`.env`（gitignore）
- 无远程服务器依赖（除用户自选的 LLM API）

---

## 安全设计原则（对内）

### 1. Fail-Closed（默认拒绝）
```python
# ✅ 正确：默认拒绝，显式允许
if not guardian.check_permission(command):
    raise PermissionDenied()

# ❌ 错误：默认允许，显式拒绝
if guardian.is_blocked(command):
    raise PermissionDenied()
```

### 2. Defense in Depth（多层防御）
```
用户请求
  ↓
[1. Channel Policy]      ← chat_only 检查
  ↓
[2. Rate Limiter]        ← 防滥用
  ↓
[3. Guardian]            ← 高危命令拦截
  ↓
[4. Executor]            ← 沙箱执行
  ↓
[5. Audit Log]           ← 事后审计
```

**实现位置**：
- Layer 1: `agentos/communicationos/channels/base.py:ChannelManifest.allow_execute`
- Layer 2: `agentos/core/communication/rate_limit.py:RateLimiter`
- Layer 3: `agentos/core/guardian/policies.py:ExecutionPolicy`
- Layer 4: `agentos/core/executor/executor_engine.py:ExecutorEngine`
- Layer 5: `agentos/core/audit.py:AuditLogger`

### 3. Principle of Least Privilege（最小权限）
- Channel: 默认 chat-only
- Command: 默认 read-only
- Scope: 默认 user-conversation（隔离）

```python
# 权限升级必须显式请求
class PermissionRequest(BaseModel):
    channel_id: str
    requested_permission: str  # "execute" | "read_files" | "write_files"
    justification: str         # 必须说明理由
    approval_required: bool = True
```

### 4. Auditability（可审计）
所有安全相关事件必须审计：
- 权限变更（chat → execute）
- 危险命令执行（rm、sudo）
- 配置修改（Token 更新）
- 失败尝试（签名验证失败）

**审计日志格式**：
```python
{
    "timestamp": "2026-02-01T12:34:56.789Z",
    "event_type": "permission_escalation",
    "channel_id": "slack-team-123",
    "old_permission": "chat_only",
    "new_permission": "execute",
    "approved_by": "user@example.com",
    "justification": "Deploy hotfix to production"
}
```

---

## 安全徽章体系（UI 可见）

### Channel 安全徽章
每个 channel 的 manifest.json 必须声明：
```json
{
  "privacy_badges": [
    "No Auto Provisioning",    // 不自动授权
    "Chat-only by Default",    // 默认仅聊天
    "Local Storage",           // 本地存储
    "Secrets Encrypted",       // 密钥加密
    "User-Conversation Scope", // 用户会话隔离
    "Manual Configuration"     // 手动配置
  ]
}
```

### 徽章验证
System 启动时验证所有 channel 的徽章声明：
```python
# agentos/core/startup/health_check.py
def verify_security_badges(manifest: ChannelManifest) -> list[str]:
    """验证 channel 是否符合安全承诺"""
    violations = []

    if manifest.allow_execute and "Chat-only by Default" in manifest.privacy_badges:
        violations.append("Manifest 声明 chat-only 但允许执行")

    if manifest.oauth_enabled and "No Auto Provisioning" in manifest.privacy_badges:
        violations.append("Manifest 声明不自动授权但启用 OAuth")

    return violations
```

### 项目安全等级
- 🟢 **Safe**: chat-only, read-only commands
- 🟡 **Elevated**: 有限执行权限（白名单命令）
- 🔴 **Full Access**: 无限制执行（需 sudo 密码）

---

## 安全通信策略（对外）

### 网站/文档
**首页 Hero Section**:
```
AgentOS: AI Agent 操作系统
默认安全 | 本地运行 | 用户可控

✅ 默认仅聊天，不执行命令
✅ 数据存储在您的设备
✅ 手动配置，不自动接管账号
```

**安全页面** (`/security`):
- 详细说明 4 大承诺
- 架构图（数据流向）
- 审计日志示例
- 安全最佳实践

### README.md
添加安全章节：
```markdown
## 🔒 安全优先

AgentOS 采用"默认安全"设计：
- **Chat-Only 模式**：默认只能对话，不执行命令
- **本地运行**：数据永不离开您的设备
- **手动配置**：不自动连接第三方服务
- **多层防御**：Guardian + 速率限制 + 审计日志

了解更多：[安全叙事文档](docs/SECURITY_NARRATIVE_V1.md)
```

### API 文档
在所有执行相关的 API 前添加警告：
```python
def execute_command(cmd: str):
    """
    执行系统命令。

    ⚠️ 安全警告：
    - 默认禁用（需显式授权）
    - 高危命令需人工审批
    - 所有执行都会审计

    参见：docs/SECURITY_NARRATIVE_V1.md
    """
```

---

## 安全测试要求

### 每个 Release 必须通过：
- [ ] ✅ 默认配置不能执行命令
- [ ] ✅ 签名验证失败返回 401
- [ ] ✅ 速率限制生效
- [ ] ✅ 高危命令被拦截
- [ ] ✅ 审计日志完整
- [ ] ✅ Token 加密存储

**测试脚本**：
```bash
#!/bin/bash
# scripts/security/verify_security_promises.sh

echo "验证安全承诺..."

# 承诺 1: 默认 chat-only
python -c "from agentos.communicationos.channels.base import ChannelManifest; \
           assert ChannelManifest().allow_execute == False"

# 承诺 2: Guardian 拦截危险命令
python scripts/security/test_guardian_blocks_dangerous.py

# 承诺 3: 无自动 OAuth
grep -r "oauth_auto_provision" agentos/ && exit 1

# 承诺 4: 数据本地存储
test -f store/registry.sqlite || exit 1

echo "✅ 所有安全承诺已验证"
```

### 定期安全审计
- 季度安全扫描（OWASP Top 10）
- 依赖漏洞检查（Dependabot）
- 渗透测试（社区白帽）

---

## 安全事件响应

### 发现漏洞时
1. **不要公开披露**：先联系 security@agentos.dev
2. **评估影响**：CVSS 评分
3. **快速修复**：24h 内发布补丁
4. **透明沟通**：发布安全公告

### 安全公告模板
```markdown
# 安全公告 SA-2026-001

## 影响范围
AgentOS <= v1.2.3

## 漏洞描述
[简要描述]

## 缓解措施
1. 升级到 v1.2.4
2. 或临时禁用 [功能]

## 致谢
感谢 [研究员] 负责任地披露此漏洞。
```

### 漏洞评分（CVSS v3.1）
- **Critical (9.0-10.0)**: 立即修复（< 24h）
- **High (7.0-8.9)**: 1 周内修复
- **Medium (4.0-6.9)**: 1 个月内修复
- **Low (0.1-3.9)**: 下一个计划版本

---

## 冻结承诺

### 不可变更（v1）
以下承诺写入 v1，永不违反：
1. ✅ 默认 chat-only
2. ✅ Execute 需授权
3. ✅ 不自动接管账号
4. ✅ 本地运行

### 可增强（v2+）
- 增加更严格的沙箱
- 增加更细粒度的权限
- 增加更多审计维度

但**不能**：
- ❌ 降低默认安全等级
- ❌ 移除权限检查
- ❌ 自动上传数据

### 冻结签名
```
Version: 1.0
Date: 2026-02-01
Commitments: 4
Status: FROZEN
SHA256: [待计算]
Signed-By: AgentOS Security Team
```

---

## 合规性

### 适用标准
- **GDPR**: 数据本地化，用户完全控制
- **SOC 2**: 访问控制，审计日志
- **ISO 27001**: 信息安全管理
- **OWASP ASVS**: 应用安全验证标准

### 数据处理声明
```
AgentOS 不处理或存储：
- ❌ 用户个人身份信息（除本地存储）
- ❌ 支付信息
- ❌ 第三方 Token（仅本地加密存储）
- ❌ 对话内容（除本地 SQLite）

AgentOS 仅处理：
- ✅ 本地配置文件
- ✅ 本地审计日志
- ✅ 匿名错误报告（可选）
```

---

## 开发者指南

### 添加新功能时
**必须问自己**：
1. 这个功能是否违反 4 大承诺？
2. 默认配置是否安全？
3. 是否需要新的权限？
4. 是否记录审计日志？

**示例**：添加"自动备份"功能
```python
# ❌ 错误：默认开启，自动上传
class BackupService:
    def __init__(self):
        self.enabled = True  # 违反承诺 4：本地运行
        self.upload_to_cloud = True

# ✅ 正确：默认禁用，本地存储
class BackupService:
    def __init__(self):
        self.enabled = False  # 需显式启用
        self.backup_path = "./backups"  # 本地路径
        self.cloud_upload = False  # 禁用云上传
```

### 代码审查清单
```markdown
- [ ] 默认配置符合最小权限原则
- [ ] 敏感操作有权限检查
- [ ] 审计日志已添加
- [ ] 错误不泄露敏感信息
- [ ] 测试覆盖安全场景
```

---

## 安全资源

### 内部文档
- [安全检查清单](./SECURITY_CHECKLIST.md)
- [CSRF 防护指南](./security/CSRF_BEST_PRACTICES.md)
- [权限模型](./v3/developer_guide/security_model.md)

### 外部参考
- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **CWE Top 25**: https://cwe.mitre.org/top25/
- **最小权限原则**: https://en.wikipedia.org/wiki/Principle_of_least_privilege
- **Defense in Depth**: https://en.wikipedia.org/wiki/Defense_in_depth_(computing)

### 联系方式
- 安全问题：security@agentos.dev
- 漏洞报告：通过 GitHub Security Advisories
- 紧急联系：[PGP 加密联系方式]

---

## 版本历史

### v1.0 (2026-02-01) - FROZEN
- 初始版本
- 定义 4 大核心承诺
- 建立徽章体系
- 冻结安全叙事

---

**本文档是 AgentOS 对用户的承诺，任何违反此承诺的行为都是严重的信任破坏。**

**签名**: AgentOS Security Team
**日期**: 2026-02-01
**状态**: FROZEN ❄️
