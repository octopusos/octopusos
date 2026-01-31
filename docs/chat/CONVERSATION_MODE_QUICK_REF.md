# Conversation Mode 快速参考卡片

## 5 种对话模式速查

| 模式 | 一句话描述 | 适用场景 |
|------|----------|---------|
| **chat** | 友好的日常助手 | 学习、咨询、探索 |
| **discussion** | 深度分析讨论 | 架构、决策、权衡 |
| **plan** | 战略规划模式 | 项目规划、里程碑 |
| **development** | 代码实现模式 | 编写代码、技术实现 |
| **task** | 简洁执行模式 | 快速修复、自动化 |

---

## 2 种执行阶段速查

| 阶段 | 权限级别 | 允许操作 | 禁止操作 |
|------|---------|---------|---------|
| **planning** | 只读、安全 | 读文件、搜索、分析 | 写文件、执行 bash、安装扩展 |
| **execution** | 完整权限 | 所有操作 | 无(需谨慎使用) |

---

## 常用命令速查

### 模式切换(自由切换)

```bash
/mode chat         # 切换到 chat 模式
/mode discussion   # 切换到 discussion 模式
/mode plan         # 切换到 plan 模式
/mode development  # 切换到 development 模式
/mode task         # 切换到 task 模式
```

### 阶段切换(需要批准)

```bash
/execute    # 切换到 execution 阶段(赋予完整权限)
/plan       # 切换回 planning 阶段(回到只读模式)
```

### 状态查询

```bash
/status     # 查看当前模式和阶段
/help mode  # 查看模式帮助
```

---

## API 端点速查

### 模式管理

```http
# 获取当前模式
GET /api/chat/mode

# 设置模式
POST /api/chat/mode
{
  "mode": "development"
}

# 获取模式列表
GET /api/chat/modes
```

### 阶段管理

```http
# 获取当前阶段
GET /api/chat/phase

# 切换阶段(需要批准)
POST /api/chat/phase
{
  "phase": "execution",
  "approved": true
}
```

---

## 最佳实践组合

| 使用场景 | 推荐模式 | 推荐阶段 | 命令 |
|---------|---------|---------|------|
| 学习新技术 | chat | planning | `/mode chat` |
| 架构讨论 | discussion | planning | `/mode discussion` |
| 制定计划 | plan | planning | `/mode plan` |
| 阅读代码 | development | planning | `/mode development` |
| 编写代码 | development | execution | `/mode development` + `/execute` |
| 快速修复 | task | execution | `/mode task` + `/execute` |
| 探索 API | chat | planning | `/mode chat` |
| 代码重构 | development | execution | `/mode development` + `/execute` |

---

## 权限对照表

| 操作 | planning 阶段 | execution 阶段 |
|------|--------------|---------------|
| 读取文件 | ✅ 允许 | ✅ 允许 |
| 列出目录 | ✅ 允许 | ✅ 允许 |
| Web 搜索 | ✅ 允许 | ✅ 允许 |
| Web 抓取 | ✅ 允许 | ✅ 允许 |
| 分析代码 | ✅ 允许 | ✅ 允许 |
| 写入文件 | ❌ 禁止 | ✅ 允许 |
| 删除文件 | ❌ 禁止 | ✅ 允许 |
| 执行 Bash | ❌ 禁止 | ✅ 允许 |
| 安装扩展 | ❌ 禁止 | ✅ 允许 |
| 执行扩展 | ❌ 禁止 | ✅ 允许 |

---

## 模式特征速查

### chat 模式
- **语气**: 友好、对话式
- **详细度**: 详细解释
- **输出**: 段落 + 代码示例 + 问题
- **交互**: 主动提问、引导对话

### discussion 模式
- **语气**: 分析性、多角度
- **详细度**: 深度分析
- **输出**: 结构化列表 + pros/cons
- **交互**: 苏格拉底式提问

### plan 模式
- **语气**: 战略性、高层次
- **详细度**: 概览性
- **输出**: 里程碑 + 步骤 + 风险
- **交互**: 结构化规划

### development 模式
- **语气**: 技术性、代码为中心
- **详细度**: 技术实现细节
- **输出**: 代码片段 + 技术说明
- **交互**: 实现建议

### task 模式
- **语气**: 简洁、结果导向
- **详细度**: 最少解释
- **输出**: 状态 + 结果
- **交互**: 直接执行、简报

---

## 故障排查

### 问题 1: 无法创建文件

**症状**:
```
用户: 创建 cache.py
系统: ❌ 错误: 无法在 planning 阶段创建文件
```

**原因**: 当前处于 planning 阶段(只读)

**解决**:
```bash
/execute    # 切换到 execution 阶段
# 再次尝试创建文件
```

---

### 问题 2: 无法执行 bash 命令

**症状**:
```
用户: 运行 pytest
系统: ❌ 错误: bash 命令在 planning 阶段不可用
```

**原因**: planning 阶段禁止执行外部命令

**解决**:
```bash
/execute    # 切换到 execution 阶段
# 再次尝试执行命令
```

---

### 问题 3: 对话风格不符合预期

**症状**:
```
用户: 我想要代码风格的交互
系统: 提供了大段文字解释(chat 模式)
```

**原因**: 当前处于 chat 模式

**解决**:
```bash
/mode development    # 切换到 development 模式
# 重新发起对话
```

---

### 问题 4: 模式切换后仍无法执行操作

**症状**:
```
用户: /mode development
用户: 创建文件
系统: ❌ 错误: 无法在 planning 阶段创建文件
```

**原因**: 模式切换不影响权限,需要切换阶段

**解决**:
```bash
/mode development    # 切换模式(UX)
/execute             # 切换阶段(权限)
# 现在可以创建文件
```

---

### 问题 5: 不确定当前状态

**症状**:
```
用户: 我现在在什么模式?能做什么?
```

**解决**:
```bash
/status    # 查看当前模式和阶段

# 输出示例:
# 当前模式: development
# 当前阶段: planning
# 可用操作: read_file, list_directory, web_search, web_fetch
# 禁止操作: write_file, bash, install_extension
```

---

## 安全提醒速查

| 提醒 | 说明 |
|------|------|
| ⚠️ 模式 ≠ 权限 | 切换到 development 模式不等于获得写入权限 |
| ⚠️ 确认阶段 | 执行危险操作前,确认处于 execution 阶段 |
| ⚠️ 审查操作 | 即使在 execution 阶段,也要审查系统建议的操作 |
| ⚠️ 谨慎使用 /execute | `/execute` 命令会赋予系统完整权限,请谨慎使用 |

---

## 快速决策树

```
需要修改文件/执行命令?
├─ 是 → 必须在 execution 阶段
│        ↓
│        /execute
│        ↓
│        选择模式: development(编码)或 task(快速执行)
│
└─ 否 → 保持 planning 阶段
         ↓
         选择模式:
         ├─ 学习 → chat
         ├─ 讨论 → discussion
         ├─ 规划 → plan
         └─ 阅读代码 → development
```

---

## 状态指示器说明

### WebUI 顶部显示

```
┌─────────────────────────────────────┐
│ 对话模式: development | 执行阶段: execution │
└─────────────────────────────────────┘
```

### CLI 提示符

```
AgentOS [development|execution] >
```

### 颜色指示(WebUI)

- **planning 阶段**: 🟢 绿色(安全)
- **execution 阶段**: 🟡 黄色(需谨慎)

---

## 常见误区速查

| 误区 | 事实 |
|------|------|
| development 模式就能写代码 | ❌ 还需要 execution 阶段 |
| planning 阶段不能用 development 模式 | ❌ 所有模式在所有阶段都可用 |
| 切换模式需要批准 | ❌ 模式切换自由,阶段切换需批准 |
| execution 阶段会改变对话风格 | ❌ 阶段只控制权限,不影响风格 |
| task 模式会跳过安全检查 | ❌ 所有模式都受阶段门控保护 |

---

## 进阶技巧

### 技巧 1: 模式链

先讨论,再规划,最后实施:

```bash
# 第 1 步: 讨论方案
/mode discussion
# 深度分析各种方案...

# 第 2 步: 制定计划
/mode plan
# 制定实施计划...

# 第 3 步: 实施
/mode development
/execute
# 开始编码...
```

---

### 技巧 2: 阶段保护

在 planning 阶段完成所有分析,确认无误后再切换:

```bash
# 在 planning 阶段充分探索
/mode discussion
# 讨论、分析、验证...

# 确认方案后切换
/execute
# 执行实施
```

---

### 技巧 3: 模式建议响应

系统建议切换阶段时的最佳响应:

```
系统: 💡 development 模式建议在 execution 阶段使用
      输入 /execute 切换?

情况 1 - 只是阅读代码:
用户: 不需要,我现在只是阅读

情况 2 - 准备编写代码:
用户: /execute
```

---

## 学习路径

### 新手(第 1 周)

1. 熟悉 `chat` 模式(默认模式)
2. 理解 `planning` vs `execution` 阶段
3. 尝试 `/execute` 切换(测试项目)

### 中级(第 2-3 周)

4. 探索 `discussion` 和 `plan` 模式
5. 理解模式和阶段的独立性
6. 根据任务选择合适的模式

### 高级(第 4+ 周)

7. 熟练使用所有 5 种模式
8. 建立个人工作流(模式链)
9. 理解安全边界和权限模型

---

## 相关文档

- [完整用户指南](./CONVERSATION_MODE_GUIDE.md) - 详细说明和示例
- [Mode vs Phase 对比](./MODE_VS_PHASE.md) - 概念区别详解
- [ADR-CHAT-MODE-001](../adr/ADR-CHAT-MODE-001-Conversation-Mode-Architecture.md) - 架构设计

---

## 获取帮助

```bash
/help          # 通用帮助
/help mode     # 模式帮助
/help phase    # 阶段帮助
/status        # 当前状态
```

---

**快速参考,随时查阅!**
