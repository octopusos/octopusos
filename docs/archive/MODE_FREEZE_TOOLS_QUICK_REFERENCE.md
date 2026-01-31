# Mode Freeze 工具快速参考

**版本**: 1.0.0
**创建日期**: 2026-01-30

---

## 快速导航

| 我想... | 使用工具 | 命令 |
|---------|---------|------|
| 检查我的变更是否违规 | verify_mode_freeze.sh | `./scripts/verify_mode_freeze.sh` |
| 安装自动检查 | install_mode_freeze_hooks.sh | `./scripts/install_mode_freeze_hooks.sh` |
| 记录例外批准 | record_mode_freeze_exception.py | `python3 scripts/record_mode_freeze_exception.py ...` |
| 查看检查清单 | MODE_FREEZE_CHECKLIST.md | `cat docs/governance/MODE_FREEZE_CHECKLIST.md` |
| 了解冻结规范 | MODE_FREEZE_SPECIFICATION.md | `cat docs/governance/MODE_FREEZE_SPECIFICATION.md` |

---

## 常用命令

### 1. 检查当前变更

```bash
# 基础检查
./scripts/verify_mode_freeze.sh

# 详细输出
./scripts/verify_mode_freeze.sh --verbose

# JSON 输出（CI/CD）
./scripts/verify_mode_freeze.sh --json
```

### 2. 安装 Git Hook

```bash
# 一键安装
./scripts/install_mode_freeze_hooks.sh

# 配置
git config hooks.modeFreezeVerify true   # 启用
git config hooks.modeFreezeVerify false  # 禁用
```

### 3. 记录例外批准

```bash
# Bug 修复
python3 scripts/record_mode_freeze_exception.py \
  --file agentos/core/mode/mode.py \
  --type bug_fix \
  --severity P1 \
  --approval "Your Name" \
  --reason "Fix critical bug #123"

# 安全补丁
python3 scripts/record_mode_freeze_exception.py \
  --file agentos/core/mode/mode_policy.py \
  --type security_patch \
  --severity P0 \
  --approval "Your Name" \
  --reason "Fix CVE-2026-1234"

# 干运行（预览）
python3 scripts/record_mode_freeze_exception.py \
  --file ... --type ... --severity ... --approval ... --reason ... \
  --dry-run
```

---

## 冻结文件列表

### 核心模块 (6 个)
- `agentos/core/mode/mode_policy.py`
- `agentos/core/mode/mode_alerts.py`
- `agentos/core/mode/mode.py`
- `agentos/core/mode/mode_proposer.py`
- `agentos/core/mode/mode_selector.py`
- `agentos/core/mode/pipeline_runner.py`

### API 层 (1 个)
- `agentos/webui/api/mode_monitoring.py`

### 前端层 (1 个)
- `agentos/webui/static/js/views/ModeMonitorView.js`

### 配置文件 (5 个)
- `configs/mode/default_policy.json`
- `configs/mode/dev_policy.json`
- `configs/mode/strict_policy.json`
- `configs/mode/alert_config.json`
- `agentos/core/mode/mode_policy.schema.json`

### 文档 (2 个)
- `agentos/core/mode/README.md`
- `agentos/core/mode/README_POLICY.md`

---

## 允许的变更类型

| 类型 | 说明 | 需要批准？ |
|------|------|-----------|
| ✅ Bug 修复 (P0/P1) | 不改变 API | 否（但需标记） |
| ✅ 安全补丁 | CVE Critical/High | 否（但需标记） |
| ✅ 性能优化 | 不改变行为 | 否（但需标记） |
| ✅ 文档更新 | 修正错误 | 否 |
| ✅ 测试增强 | 不修改代码 | 否 |
| ❌ 新功能 | 任何新功能 | 需要例外批准 |
| ❌ API 变更 | 任何 API 变更 | 需要例外批准 |
| ❌ P2/P3 Bug | 非关键 bug | 推迟到冻结期后 |

---

## Commit Message 模板

### Bug 修复
```
fix(mode): <简短描述>

<详细说明>

Fixes: #<issue-number>
Severity: P0/P1
```

### 安全补丁
```
security(mode): <简短描述>

<详细说明>

CVE: CVE-YYYY-XXXXX
Severity: Critical/High
```

### 例外批准
```
<type>(mode): <简短描述> [mode-freeze-exception]

<详细说明>

Exception: EXC-<编号>
Approval: <审批人>
```

---

## 快速决策流程图

```
修改 Mode 文件？
  ├─ 否 → ✅ 正常提交
  └─ 是 → 文件在冻结列表？
           ├─ 否 → ✅ 正常提交
           └─ 是 → 什么类型？
                    ├─ 文档/测试 → ✅ 标记 commit
                    ├─ P0/P1 Bug → 记录例外 → 提交
                    ├─ 安全 Critical/High → 记录例外 → 提交
                    └─ 其他 → ❌ 申请例外或推迟
```

---

## 紧急情况处理

### P0 故障（生产环境宕机）

```bash
# 1. 立即修复（可先修复后审批）
vim agentos/core/mode/mode.py

# 2. 绕过 hook 紧急提交
git commit --no-verify -m "fix(mode): emergency fix for P0 outage"

# 3. 24 小时内补充文档
python3 scripts/record_mode_freeze_exception.py \
  --file agentos/core/mode/mode.py \
  --type bug_fix \
  --severity P0 \
  --approval "Your Name" \
  --reason "Emergency fix for production outage"

# 4. 事后分析（Postmortem）
# 编写事故报告
```

---

## 帮助和支持

### 获取帮助

```bash
# 查看工具帮助
./scripts/verify_mode_freeze.sh --help
python3 scripts/record_mode_freeze_exception.py --help

# 查看完整文档
cat docs/governance/MODE_FREEZE_CHECKLIST.md
cat docs/governance/MODE_FREEZE_SPECIFICATION.md
```

### 联系方式

- **技术负责人**: mode-system-owner@company.com
- **架构委员会**: architecture-committee@company.com
- **紧急热线**: mode-emergency@company.com

---

## 故障排除

### Hook 不运行？

```bash
# 检查和修复
ls -la .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
git config hooks.modeFreezeVerify true
```

### 验证失败但确认无问题？

```bash
# 临时绕过（不推荐）
git commit --no-verify

# 或联系技术负责人
```

### 记录例外失败？

```bash
# 检查文件权限
ls -la docs/governance/MODE_FREEZE_LOG.md

# 使用干运行测试
python3 scripts/record_mode_freeze_exception.py ... --dry-run
```

---

## 相关文档

- [MODE_FREEZE_SPECIFICATION.md](docs/governance/MODE_FREEZE_SPECIFICATION.md) - 完整规范
- [MODE_FREEZE_CHECKLIST.md](docs/governance/MODE_FREEZE_CHECKLIST.md) - 详细检查清单
- [MODE_BUG_FIX_PROCESS.md](docs/governance/MODE_BUG_FIX_PROCESS.md) - Bug 修复流程
- [TASK32_MODE_FREEZE_TOOLS_IMPLEMENTATION.md](TASK32_MODE_FREEZE_TOOLS_IMPLEMENTATION.md) - 工具实施报告

---

**最后更新**: 2026-01-30
**维护者**: Architecture Committee
