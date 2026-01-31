# ADR-EXT-001: Declarative Extensions Only

## Status
Accepted (2026-01-30)

## Context
AgentOS 需要一个扩展系统来支持新功能的添加，但必须保证核心系统的稳定性和安全性。Extension 系统已经实现，但需要明确固化其不可变契约：**Extension 只能做声明式的 capability 扩展，不能执行任意代码，不能干扰 AgentOS 运行规则。**

## Decision

### 1. Extension 不可执行任意代码

**禁止：**
- Extension 不得包含可执行的 Python/JavaScript/Shell 脚本（除非在 plan.yaml 中声明）
- manifest.json 的 `entrypoint` 字段必须为 `null`
- Extension 不得被 import 或 exec
- Extension 不得注册 hook、middleware 或 patch AgentOS 内部逻辑

**允许：**
- 声明式的 manifest.json（元信息）
- 声明式的 install/plan.yaml（安装步骤）
- 声明式的 commands/commands.yaml（命令映射）
- 静态的 docs/USAGE.md（使用文档）
- 静态的 icon.png（图标）

### 2. 所有动作由 Core 受控执行

**受控执行器（ExtensionInstallEngine / CapabilityRunner）必须：**
- 限制工作目录：`.agentos/extensions/<extension_id>/work/`
- 限制 PATH：系统基础命令 + `.agentos/bin/` + `.agentos/tools/`
- 限制 ENV：白名单环境变量（HOME, USER, PATH, TMPDIR, TEMP, LANG, LC_ALL）
- 限制可写目录：`.agentos/extensions/<extension_id>/`、`.agentos/tools/`
- 超时控制：默认 300 秒（5 分钟）
- 审计日志：每个步骤写入 system_logs 和 task_audits

**白名单 Step Types（仅这 8 种）：**
1. `detect.platform` - 检测操作系统和架构
2. `download.http` - HTTP 下载（由 Core Downloader 执行，SHA256 校验）
3. `extract.zip` - ZIP 文件解压（由 Core 执行）
4. `exec.shell` - Shell 命令执行（受控环境）
5. `exec.powershell` - PowerShell 执行（受控环境）
6. `verify.command_exists` - 命令存在性验证
7. `verify.http` - HTTP 健康检查
8. `write.config` - 配置写入（仅限扩展 namespace）

### 3. 权限门控

**Admin Token（未来如果系统支持）：**
- 安装扩展
- 卸载扩展
- 修改扩展配置（敏感字段）

**Permissions 声明：**
- Extension 必须在 manifest.json 中声明 `permissions_required`
- Plan step 必须声明 `requires_permissions`
- 执行时强校验：step 所需权限必须在 manifest 中存在
- 默认权限是 deny（没声明 = 不允许）

**支持的权限：**
- `network` - 网络访问
- `exec` - 执行命令
- `filesystem.read` - 文件读取
- `filesystem.write` - 文件写入

### 4. Zip 安全

**Validator 必须检查：**
- Zip 只有一个顶层目录
- 必须包含：manifest.json, install/plan.yaml, commands/commands.yaml, docs/USAGE.md
- 文件大小限制：50MB
- SHA256 哈希计算和校验（URL 安装时强制）
- 禁止根目录可执行文件（.py, .js, .sh, .exe, .bat）

**Installer 必须防护：**
- 路径穿越：拒绝 `../`、绝对路径、symlink
- 只解压到：`.agentos/extensions/<extension_id>/`
- 解压后再次验证文件结构

### 5. Marketplace 只是索引

**Marketplace 不改变安装执行机制：**
- Marketplace 只提供 index.json（扩展列表）
- 安装仍然走 Core 的受控执行器
- 不允许从 Marketplace 直接执行代码
- Marketplace index 必须 HTTPS + 可选域名白名单

## Consequences

**优点：**
- 安全：Extension 无法执行任意代码或破坏系统
- 可审计：所有动作都有日志记录
- 可维护：Extension 结构简单，易于理解和调试
- 可扩展：白名单机制易于添加新的 step types

**缺点：**
- 灵活性受限：Extension 不能做复杂的自定义逻辑
- 开发者需要学习 plan.yaml 的声明式语法

## Deployment Modes

### Local-Only Mode (v1.0+)
**Production-Ready**: ✅

- Single user, localhost only
- No admin token required (user trusts themselves)
- Install/uninstall/enable/disable operations allowed
- Trust model: Self-trust

**Security rationale**:
Admin token is unnecessary in single-user mode because:
1. User is installing extensions for themselves
2. User has full control over the machine anyway
3. Core contracts (no code execution, sandboxing, audit) still enforced
4. Additional auth layer adds friction without security benefit in this mode

### Remote-Exposed Mode (v1.1+)
**Production-Ready**: v1.1+ only

- Multi-user or network-accessible
- Admin token REQUIRED for:
  - Extension install/uninstall
  - Extension enable/disable
  - Sensitive config writes
- Audit log monitoring REQUIRED
- Trust model: Admin approval

**Security rationale**:
Admin token is critical in multi-user mode because:
1. Malicious users could install dangerous extensions
2. Extensions have exec/network/filesystem permissions
3. One user's extension affects all users on the system
4. Audit logs alone are insufficient (need prevention, not just detection)

### v1.0 on Remote (Not Recommended)
If deploying v1.0 remotely before v1.1:
- Use reverse proxy + basic auth
- Firewall rules to restrict extension API
- Monitor audit logs actively
- See: docs/deployment/LOCAL_VS_REMOTE.md

## Enforcement

**在代码中强制执行（见 ADR-EXT-001-ENFORCEMENT.md）：**
1. Validator 拒绝 entrypoint != null
2. Validator 拒绝白名单外的文件类型
3. Engine 拒绝白名单外的 step types
4. Engine 在执行前检查 permissions
5. Installer 防护路径穿越

## References
- Extension 核心基础设施实现：`agentos/core/extensions/`
- Install Engine 和进度事件：`agentos/core/extensions/engine.py`
- Semantic Freeze 守门员复核（2026-01-30）
- 相关测试：`tests/unit/core/extensions/`

## Review Schedule
- Next Review Date: 2026-02-15
- Reviewer: Security Team
