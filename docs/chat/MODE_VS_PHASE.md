# Conversation Mode vs Execution Phase: 概念对比

## 核心区别

AgentOS 的交互系统基于两个独立的概念:

```
┌──────────────────────┐      ┌──────────────────────┐
│  Conversation Mode   │      │  Execution Phase     │
│  (对话模式)           │      │  (执行阶段)           │
├──────────────────────┤      ├──────────────────────┤
│ 控制: 如何交互        │      │ 控制: 能做什么        │
│ 影响: UX/语气/格式    │      │ 影响: 安全权限        │
│ 切换: 自由切换        │      │ 切换: 需要批准        │
└──────────────────────┘      └──────────────────────┘
```

**关键原则**: 这两个概念是**独立正交的**,不会相互影响。

---

## 为什么需要两个独立的概念?

### 问题 1: 混淆导致的安全风险

如果只有一个概念,会出现以下问题:

**场景**: 用户想要"友好的对话风格"但处于"只读探索阶段"

**单一概念的困境**:
```
如果用"development"模式表示开发风格:
  → 用户期望: 代码风格的对话
  → 系统理解: 赋予文件写入权限
  → 结果: 安全风险!

如果用"planning"模式表示只读:
  → 用户期望: 只读探索
  → 系统理解: 规划风格的对话
  → 结果: UX 受限!
```

**双概念的解决方案**:
```
Mode: development (代码风格的交互)
Phase: planning (只读权限)
  → 用户获得: 代码风格的对话 + 安全的只读权限
  → 完美平衡!
```

---

### 问题 2: 扩展性受限

**单一概念**:
- 添加新的交互风格 → 必须修改安全层
- 添加新的权限级别 → 必须修改 UX 层
- 紧耦合,难以维护

**双概念**:
- 添加新的交互风格(如"formal"模式)→ 只修改 UX 层
- 添加新的权限级别(如"review"阶段)→ 只修改安全层
- 松耦合,易于扩展

---

## 对比表格

| 维度 | Conversation Mode | Execution Phase |
|------|------------------|----------------|
| **本质** | 用户体验偏好 | 安全权限边界 |
| **控制内容** | 交互方式、语气、格式 | 功能访问、操作权限 |
| **值域** | chat, discussion, plan, development, task | planning, execution |
| **切换频率** | 经常(根据任务需要) | 较少(明确的权限升级) |
| **切换方式** | `/mode <name>` - 即时生效 | `/execute` 或 `/plan` - 需要确认 |
| **是否需要批准** | 否(纯 UX 变化) | 是(安全边界变化) |
| **影响安全** | 否 | 是 |
| **影响 UX** | 是 | 否 |
| **可扩展** | 是(可以添加自定义模式) | 否(核心安全概念) |
| **用户可见性** | 高(明确的风格变化) | 中(权限提示) |
| **系统审计** | 记录但不强制 | 强制审计日志 |

---

## 具体示例对比

### 示例 1: 探索代码库

**需求**: 用代码风格阅读和理解代码,但不修改任何内容

**配置**:
```
Mode: development (代码风格交互)
Phase: planning (只读权限)
```

**效果**:
- 对话以代码片段和技术术语为主(development 模式特点)
- 可以读取文件、列出目录、分析代码
- 不能修改文件、执行 bash、安装扩展(planning 阶段限制)

**如果只有单一概念**: 无法同时满足"代码风格"和"只读权限"的需求。

---

### 示例 2: 友好讨论后实施

**需求**: 先友好地讨论方案,再执行实施

**阶段 1 - 讨论**:
```
Mode: chat (友好对话)
Phase: planning (安全探索)
```
- 友好的语气,详细的解释
- 可以搜索资料、分析代码
- 不能执行危险操作

**阶段 2 - 实施**:
```
Mode: task (简洁执行)
Phase: execution (完整权限)
用户执行: /mode task && /execute
```
- 简洁的进度报告
- 可以修改文件、执行命令
- 审计日志记录所有操作

**如果只有单一概念**: 切换风格必然改变权限,或切换权限必然改变风格。

---

### 示例 3: 规划不应执行代码

**需求**: 制定项目计划,只做高层次规划,不编写代码

**配置**:
```
Mode: plan (规划风格)
Phase: planning (只读权限)
```

**效果**:
- 输出以里程碑、步骤、风险评估为主
- 按惯例不生成代码(plan 模式特点)
- 即使用户要求,也无法执行(planning 阶段限制)

**双重保护**:
1. Mode(plan)提供惯例指导:"规划模式不生成代码"
2. Phase(planning)提供强制保护:"规划阶段无法执行代码"

---

## Mode 决定什么

### Mode 控制的方面

1. **对话语气**
   - chat: 友好、解释性
   - discussion: 分析性、多角度
   - plan: 战略性、高层次
   - development: 技术性、代码为中心
   - task: 简洁、结果导向

2. **输出格式**
   - chat: 段落 + 代码示例 + 问题
   - discussion: 结构化列表 + pros/cons
   - plan: 里程碑 + 步骤 + 风险
   - development: 代码片段 + 技术细节
   - task: 简短状态 + 结果

3. **详细程度**
   - chat: 详细解释
   - discussion: 深度分析
   - plan: 高层次概述
   - development: 技术实现细节
   - task: 最少解释

4. **交互方式**
   - chat: 主动提问,引导对话
   - discussion: 苏格拉底式提问
   - plan: 结构化规划
   - development: 实现建议
   - task: 直接执行,简报结果

### Mode 不控制的方面

- 文件读写权限 ❌
- Bash 执行权限 ❌
- 扩展安装权限 ❌
- 网络访问权限 ❌
- 任何安全边界 ❌

---

## Phase 决定什么

### Phase 控制的方面

1. **功能访问权限**

**planning 阶段**:
```
允许:
✅ read_file      - 读取文件
✅ list_directory - 列出目录
✅ web_search     - Web 搜索
✅ web_fetch      - Web 抓取
✅ analyze_code   - 代码分析

禁止:
❌ bash           - 执行命令
❌ write_file     - 写入文件
❌ delete_file    - 删除文件
❌ install_extension - 安装扩展
❌ execute_extension - 执行扩展
```

**execution 阶段**:
```
允许:
✅ 所有 planning 阶段的功能
✅ bash           - 执行命令
✅ write_file     - 写入文件
✅ delete_file    - 删除文件
✅ install_extension - 安装扩展
✅ execute_extension - 执行扩展
```

2. **安全边界**
   - planning: 只读,安全探索
   - execution: 读写,完整操作

3. **审计级别**
   - planning: 标准审计
   - execution: 强化审计(记录所有操作)

### Phase 不控制的方面

- 对话语气 ❌
- 输出格式 ❌
- 详细程度 ❌
- 交互方式 ❌
- 任何 UX 方面 ❌

---

## 常见误解和澄清

### 误解 1: "development 模式就能写代码"

**错误理解**:
```
用户: /mode development
用户: 创建 cache.py
用户期望: 文件被创建 ❌
```

**正确理解**:
```
用户: /mode development
系统: 已切换到 development 模式(代码风格交互)
     当前阶段: planning(只读)
     提示: 需要 execution 阶段才能创建文件

用户: /execute
系统: 已切换到 execution 阶段
     当前模式: development
     现在可以创建文件 ✅

用户: 创建 cache.py
系统: 已创建 cache.py
```

**澄清**: development 是风格,execution 是权限,两者独立。

---

### 误解 2: "planning 阶段就不能用 development 模式"

**错误理解**:
```
系统: planning 阶段不支持 development 模式 ❌
```

**正确理解**:
```
系统: planning 阶段支持所有 5 种模式 ✅
用户可以选择:
- chat + planning: 友好地探索代码
- development + planning: 用代码风格阅读代码
- task + planning: 快速分析代码
```

**澄清**: 所有模式在所有阶段都可用,阶段只控制权限,不限制风格。

---

### 误解 3: "切换模式需要批准"

**错误理解**:
```
用户: /mode task
系统: 切换到 task 模式需要管理员批准 ❌
```

**正确理解**:
```
用户: /mode task
系统: 已切换到 task 模式(无需批准)✅
```

**澄清**: 模式切换是 UX 变化,随时可以切换;阶段切换是权限变化,需要明确批准。

---

### 误解 4: "execution 阶段会改变对话风格"

**错误理解**:
```
用户: /execute
系统: 已切换到 execution 阶段
     对话风格变为"技术模式" ❌
```

**正确理解**:
```
用户: /execute
系统: 已切换到 execution 阶段
     对话模式保持: chat(无变化)✅
```

**澄清**: 阶段切换只改变权限,不影响对话风格。

---

## 实际使用建议

### 建议 1: 探索时保持 planning 阶段

**场景**: 学习新技术、阅读代码、分析架构

**推荐**:
```
Phase: planning (安全探索)
Mode: 根据需要选择
  - chat: 学习新知识
  - discussion: 讨论架构
  - development: 阅读代码
```

**原因**: planning 阶段足够满足探索需求,且更安全。

---

### 建议 2: 实施时明确切换到 execution

**场景**: 编写代码、修改配置、部署系统

**推荐**:
```
1. 先在 planning 阶段规划
   Mode: plan
   Phase: planning
   操作: 制定实施计划

2. 明确切换到 execution
   命令: /execute
   确认: 是,我要执行实施

3. 切换到实施模式
   Mode: development 或 task
   Phase: execution
   操作: 编写代码、执行部署
```

**原因**: 分阶段进行,降低风险,保持清晰的审计轨迹。

---

### 建议 3: 根据任务性质选择模式

| 任务性质 | 推荐模式 | 推荐阶段 |
|---------|---------|---------|
| 学习、咨询 | chat | planning |
| 架构讨论 | discussion | planning |
| 项目规划 | plan | planning |
| 代码阅读 | development | planning |
| 代码编写 | development | execution |
| 快速修复 | task | execution |
| 深度分析 | discussion | planning |
| 探索 API | chat | planning |

---

### 建议 4: 利用系统建议

系统会根据您的模式选择提供阶段建议:

```
用户: /mode development
系统: 已切换到 development 模式
     当前阶段: planning
     💡 建议: development 模式通常在 execution 阶段效果最佳
             输入 /execute 切换?(需要明确批准)

用户: 稍后,我现在只是阅读代码
系统: 好的,继续在 planning 阶段使用 development 模式
```

**要点**: 建议仅供参考,最终决策权在您。

---

## 架构优势

### 1. 关注点分离

```
UX Layer (Mode)
  ↓
Security Layer (Phase)
  ↓
Capability Layer
```

每层有明确的职责,互不干扰。

---

### 2. 独立扩展

**扩展新模式** (无需修改安全层):
```python
# 添加新的"formal"模式(正式文档风格)
MODES = {
    "chat": ChatFormatter(),
    "discussion": DiscussionFormatter(),
    "plan": PlanFormatter(),
    "development": DevelopmentFormatter(),
    "task": TaskFormatter(),
    "formal": FormalFormatter(),  # 新增,不影响 Phase
}
```

**扩展新阶段** (无需修改 UX 层):
```python
# 添加新的"review"阶段(可读可写但不可执行)
PHASE_PERMISSIONS = {
    "planning": {"read_file", "list_directory"},
    "execution": {"read_file", "write_file", "bash"},
    "review": {"read_file", "write_file"},  # 新增,不影响 Mode
}
```

---

### 3. 防御深度

多层防护:

1. **惯例层(Mode)**: plan 模式按惯例不生成代码
2. **强制层(Phase)**: planning 阶段强制禁止执行代码
3. **审计层**: 所有阶段切换记录到审计日志

即使 Mode 层被绕过,Phase 层依然有效。

---

## 技术实现要点

### 正确实现

```python
class ConversationEngine:
    def __init__(self):
        self.mode = "chat"      # UX 层
        self.phase = "planning"  # 安全层

    def set_mode(self, new_mode: str):
        """切换模式(纯 UX 变化)"""
        self.mode = new_mode
        # ✅ 正确: 不修改 phase
        # ✅ 正确: 不检查权限
        # ✅ 正确: 可以提供阶段建议

    def set_phase(self, new_phase: str, approved: bool):
        """切换阶段(需要批准)"""
        if not approved:
            raise SecurityError("Phase transition requires approval")
        self.phase = new_phase
        # ✅ 正确: 记录审计日志
        # ✅ 正确: 不修改 mode

    def execute_capability(self, capability: str):
        """执行能力(阶段门控)"""
        # ✅ 正确: 只检查 phase,不检查 mode
        if not self._is_allowed(capability, self.phase):
            raise PermissionError(f"{capability} not allowed in {self.phase}")
        # 执行能力...
```

---

### 错误实现(反模式)

```python
# ❌ 错误 1: Mode 控制权限
def execute_capability(self, capability: str):
    if self.mode == "development":
        # ❌ 错误: 基于 mode 赋予权限
        return self._execute(capability)

# ❌ 错误 2: Phase 控制 UX
def format_output(self, content: str):
    if self.phase == "execution":
        # ❌ 错误: 基于 phase 改变输出格式
        return self._technical_format(content)

# ❌ 错误 3: Mode 自动切换 Phase
def set_mode(self, new_mode: str):
    self.mode = new_mode
    if new_mode == "development":
        # ❌ 错误: mode 自动切换 phase
        self.phase = "execution"
```

---

## 总结

| 概念 | Mode | Phase |
|------|------|-------|
| **本质** | 风格偏好 | 安全边界 |
| **问题** | 如何交互? | 能做什么? |
| **答案** | 5 种风格 | 2 个权限级别 |
| **切换** | 自由切换 | 需要批准 |
| **独立** | 不影响权限 | 不影响风格 |
| **扩展** | 可以添加新模式 | 核心概念(不建议改) |

**Golden Rule**:
- 如果影响**怎么说**(how),是 Mode
- 如果影响**能做啥**(what),是 Phase

---

## 相关文档

- [Conversation Mode 用户指南](./CONVERSATION_MODE_GUIDE.md)
- [ADR-CHAT-MODE-001: 架构决策记录](../adr/ADR-CHAT-MODE-001-Conversation-Mode-Architecture.md)
- [快速参考卡片](./CONVERSATION_MODE_QUICK_REF.md)

---

**理解了 Mode 和 Phase 的区别,就能更安全、更高效地使用 AgentOS!**
