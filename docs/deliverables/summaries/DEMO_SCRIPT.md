# AgentOS v1.0 Demo 视频脚本

**时长**: 15 分钟  
**目标观众**: 技术决策者、开发者、DevOps 工程师  
**风格**: 技术演示 + 实际操作

---

## 视频结构

| 时间 | 段落 | 内容 | 视觉 |
|------|------|------|------|
| 0:00-1:00 | 开场 | 问题引入 | 标题 + 失控案例 |
| 1:00-3:00 | AgentOS 介绍 | 核心理念 | 架构图 |
| 3:00-6:00 | Demo 1: Interactive | 探索性任务 | 终端实录 |
| 6:00-9:00 | Demo 2: Semi-Auto | 自动化部署 | 终端实录 |
| 9:00-12:00 | Demo 3: Full-Auto | CI/CD 集成 | 终端实录 |
| 12:00-14:00 | 审计追踪 | ReviewPack 展示 | 审计界面 |
| 14:00-15:00 | 总结 + CTA | 开源地址 | GitHub 页面 |

---

## 脚本正文

### 第1段：开场（0:00-1:00）

**画面**: 黑屏 → 代码滚动 → 错误提示 → 红色警告

**旁白**:
> "假设你让 AI Agent 优化你的代码库。
>
> 你期望它分析代码、生成方案、等待审批。
>
> 但它做的是：删除了一个'看起来没用'的配置文件，
>
> 然后，生产环境崩溃了。"

**画面**: 标题淡入

```
═══════════════════════════════════
     AgentOS v1.0
From Natural Language to Auditable Execution
═══════════════════════════════════
```

**旁白**:
> "这不是假设，这是现实。
>
> 今天，我要展示一个让 AI 执行变得可控、可审计、可回滚的系统。"

---

### 第2段：AgentOS 介绍（1:00-3:00）

**画面**: 切换到演讲者（或纯旁白 + 动画）

**旁白**:
> "大部分 AI Agent 的问题在于：它们'一边想一边做'。
>
> 就像一个程序员，一边写代码，一边直接 push 到生产环境。
>
> AgentOS 的核心理念很简单：**把规划和执行彻底分离**。"

**画面**: 显示执行流程图（图 1）

```
自然语言
 → Intent
 → Coordinator
 → Dry Executor (Planning)
 → BLOCKED? (Question/Answer)
 → Executor (Execution)
 → Audit (ReviewPack)
```

**旁白**:
> "Planning 阶段，AI 只生成计划，不执行任何操作。
>
> 如果信息不足，系统进入 BLOCKED 状态，生成 QuestionPack。
>
> 只有在通过审查后，才进入 Execution 阶段。
>
> 最后，所有操作都记录在 ReviewPack 中，包含回滚指南。"

---

### 第3段：Demo 1 - Interactive 模式（3:00-6:00）

**画面**: 切换到终端实录

**旁白**:
> "让我们看第一个 Demo：Interactive 模式。
>
> 假设我们要重构一个认证模块，但不确定具体实现方式。"

**终端操作**:

```bash
# 1. 创建任务
$ cat > queue/task-001.json <<EOF
{
  "task_id": "task-001",
  "project_id": "demo-app",
  "intent": "重构认证模块，改用 JWT",
  "execution_mode": "interactive"
}
EOF

# 2. 启动 Orchestrator
$ uv run agentos orchestrate

# 输出（模拟）:
[INFO] Task task-001 started
[INFO] Execution mode: interactive
[INFO] Parsing intent...
```

**画面**: 显示 Intent 解析结果（JSON）

```json
{
  "intent_id": "i001",
  "objective": "重构认证模块，改用 JWT",
  "constraints": [],
  "success_criteria": ["JWT 认证工作", "所有测试通过"]
}
```

**旁白**:
> "AgentOS 首先解析意图，生成结构化的 Intent。"

**终端继续**:

```bash
[INFO] Coordinator: Risk assessment...
[INFO] Risk level: MEDIUM (affects auth logic)
[INFO] Dry Executor: Generating plan...
[INFO] Dry Run completed. Estimated changes: 5 files.

[QUESTION] QuestionPack generated:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Question 1 (clarification):
  - 使用哪个 JWT 库？jsonwebtoken 还是 jose？
  - Evidence: package.json 中未找到相关依赖

Question 2 (decision_needed):
  - Token 过期时间设置为多久？
  - Evidence: 当前 session 过期时间为 30 分钟
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[INFO] System state: BLOCKED
[INFO] Waiting for AnswerPack...
```

**旁白**:
> "Dry Executor 发现信息不足，生成了 QuestionPack。
>
> 系统进入 BLOCKED 状态，不会瞎猜，而是等待人类回答。"

**画面**: 创建 AnswerPack

```bash
$ cat > queue/task-001.answer.json <<EOF
{
  "answers": [
    {
      "question_id": "q1",
      "answer": "使用 jsonwebtoken（更成熟）"
    },
    {
      "question_id": "q2",
      "answer": "Token 过期时间 1 小时"
    }
  ]
}
EOF

# 提交答案
$ uv run agentos orchestrate --resume task-001
```

**终端继续**:

```bash
[INFO] AnswerPack received
[INFO] Resuming from BLOCKED...
[INFO] Re-planning with answers...
[INFO] Dry Run completed. Plan updated.

[GATE] Review Gate:
  - 5 files to change
  - 3 new dependencies
  - Risk: MEDIUM
  
Approve? (y/n): y

[INFO] Gate passed. Starting execution...
[INFO] Acquiring locks: src/auth/*.ts
[INFO] Lock acquired. Executing plan...

[EXEC] Installing jsonwebtoken...
[EXEC] Modifying src/auth/jwt.ts...
[EXEC] Modifying src/auth/middleware.ts...
[EXEC] Running tests...

[SUCCESS] All tests passed.
[INFO] Generating ReviewPack...
[INFO] ReviewPack saved: outputs/task-001/review_pack.md
```

**旁白**:
> "收到答案后，系统解除 BLOCKED，重新规划并执行。
>
> 执行完成后，生成 ReviewPack，记录所有变更。"

**画面**: 显示 ReviewPack 摘要

```markdown
# ReviewPack: task-001

## 执行摘要
- 模式: interactive
- 风险: MEDIUM
- 问题数: 2
- 变更文件: 5

## Patches
1. p001: 安装 JWT 库
   - 意图: 添加 jsonwebtoken 依赖
   - 文件: package.json
   - Diff Hash: sha256:abc123

2. p002: 实现 JWT 生成/验证
   - 意图: 创建 JWT 工具函数
   - 文件: src/auth/jwt.ts
   - Diff Hash: sha256:def456

## 回滚指南
```bash
git revert abc123^..HEAD
npm install
```
```

**旁白**:
> "ReviewPack 包含完整的变更记录，以及自动生成的回滚指南。"

---

### 第4段：Demo 2 - Semi-Auto 模式（6:00-9:00）

**画面**: 终端实录

**旁白**:
> "第二个 Demo：Semi-Auto 模式。
>
> 假设我们要自动化部署到 staging 环境。"

**终端操作**:

```bash
# 创建任务
$ cat > queue/task-002.json <<EOF
{
  "task_id": "task-002",
  "project_id": "demo-app",
  "intent": "部署到 staging 环境，版本 v2.3.1",
  "execution_mode": "semi_auto",
  "execution_policy": {
    "question_budget": 3,
    "risk_profile": "safe"
  }
}
EOF

$ uv run agentos orchestrate
```

**终端输出**:

```bash
[INFO] Task task-002 started
[INFO] Execution mode: semi_auto
[INFO] Question budget: 3

[INFO] Dry Executor: Generating deployment plan...
[INFO] Dry Run completed.

[PLAN] Deployment Steps:
  1. Build Docker image (tag: v2.3.1)
  2. Push to registry
  3. Update Kubernetes deployment
  4. Verify health check

[INFO] No blockers detected. Proceeding...
[INFO] Acquiring locks...
[INFO] Executing plan...

[EXEC] Building image demo-app:v2.3.1...
[EXEC] Pushing to registry.example.com...
[EXEC] Updating deployment/demo-app-staging...

[WARN] Health check endpoint not responding...

[BLOCKED] Blocker detected:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Type: blocker
Evidence:
  - Health check failed (3/3 attempts)
  - HTTP 503 Service Unavailable
  - Container logs show: "Database connection failed"

Question:
  - 数据库连接失败，是否：
    a) 回滚部署
    b) 检查数据库配置
    c) 继续部署（忽略健康检查）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[INFO] System state: BLOCKED
[INFO] Question budget remaining: 2
```

**旁白**:
> "Semi-Auto 模式下，AI 只能在遇到 blocker 时提问。
>
> 这里发现健康检查失败，自动进入 BLOCKED 状态。"

**画面**: 提交答案

```bash
$ cat > queue/task-002.answer.json <<EOF
{
  "answers": [
    {
      "answer": "a) 回滚部署（数据库问题需要单独排查）"
    }
  ]
}
EOF

$ uv run agentos orchestrate --resume task-002
```

**终端输出**:

```bash
[INFO] AnswerPack received
[INFO] Rolling back deployment...

[EXEC] kubectl rollout undo deployment/demo-app-staging
[INFO] Rollback completed.

[INFO] Generating ReviewPack...
[SUCCESS] Task completed (with rollback)
```

**旁白**:
> "根据人类决策，系统执行回滚。
>
> ReviewPack 记录了完整的执行过程，包括失败原因和回滚操作。"

---

### 第5段：Demo 3 - Full-Auto 模式（9:00-12:00）

**画面**: 终端实录

**旁白**:
> "第三个 Demo：Full-Auto 模式。
>
> 这是 AgentOS 最严格的模式，适合完全确定的任务。"

**终端操作**:

```bash
# 创建任务
$ cat > queue/task-003.json <<EOF
{
  "task_id": "task-003",
  "project_id": "demo-app",
  "intent": "生成每日性能报告",
  "execution_mode": "full_auto",
  "execution_policy": {
    "question_budget": 0,
    "require_memory_pack": true
  }
}
EOF

$ uv run agentos orchestrate
```

**终端输出**:

```bash
[INFO] Task task-003 started
[INFO] Execution mode: full_auto
[INFO] Question budget: 0 (禁止提问)

[GATE] Pre-execution checks:
  ✅ MemoryPack exists
  ✅ FactPack exists
  ✅ No missing information
  ✅ Risk level: LOW

[INFO] Dry Executor: Generating plan...
[INFO] Dry Run completed.

[PLAN] Report Generation:
  1. Query metrics database (last 24h)
  2. Generate charts
  3. Create PDF report
  4. Send email to team@example.com

[INFO] All steps deterministic. Proceeding...
[INFO] Executing plan...

[EXEC] Querying metrics...
[EXEC] Generating charts...
[EXEC] Creating PDF...
[EXEC] Sending email...

[SUCCESS] Task completed.
[INFO] ReviewPack: outputs/task-003/review_pack.md
```

**旁白**:
> "Full-Auto 模式下，question_budget 为 0，禁止提问。
>
> 如果遇到任何不确定情况，任务会直接失败，而不是瞎猜。"

**画面**: 显示 Gate 检查

```bash
[GATE] 10 条护城河检查:
  ✅ 1. MemoryPack 存在
  ✅ 2. question_budget = 0
  ✅ 3. 所有命令来源可追溯
  ✅ 4. run_steps 包含 Plan/Apply/Verify
  ✅ 5. ReviewPack 已生成
  ✅ 6. 所有 patch 包含 intent + diff_hash
  ✅ 7. Commit hash 已绑定
  ✅ 8. 无文件锁冲突
  ✅ 9. Task lock 已获取
  ✅ 10. Scheduler 规则可复现
```

**旁白**:
> "AgentOS 的 10 条护城河，每一条都是机器强制执行的约束。
>
> 这不是建议，而是 Gate 检查。"

---

### 第6段：审计追踪（12:00-14:00）

**画面**: 打开 ReviewPack 文件

**旁白**:
> "让我们看看审计追踪的威力。"

**画面**: 显示 ReviewPack 完整内容

```markdown
# ReviewPack: task-002 (Deployment)

## 元数据
- Task ID: task-002
- Run ID: 456
- 执行模式: semi_auto
- 开始时间: 2026-01-25T10:00:00Z
- 结束时间: 2026-01-25T10:15:00Z
- 状态: ROLLED_BACK

## 执行计划摘要
- 意图: 部署到 staging 环境，版本 v2.3.1
- 风险等级: MEDIUM
- 预计变更: 1 个 Deployment
- 预计影响: staging 环境

## 执行步骤
### Step 1: Build Docker Image
- 命令: `docker build -t demo-app:v2.3.1 .`
- 状态: ✅ SUCCESS
- 耗时: 45s
- 产物: registry.example.com/demo-app:v2.3.1

### Step 2: Push to Registry
- 命令: `docker push registry.example.com/demo-app:v2.3.1`
- 状态: ✅ SUCCESS
- 耗时: 12s

### Step 3: Update Deployment
- 命令: `kubectl set image deployment/demo-app-staging app=demo-app:v2.3.1`
- 状态: ⚠️ FAILED (health check)
- 耗时: 120s
- 错误: Health check endpoint returned 503

### Step 4: Rollback
- 命令: `kubectl rollout undo deployment/demo-app-staging`
- 状态: ✅ SUCCESS
- 耗时: 30s

## Patches
### Patch 1: Update Container Image
- Patch ID: p001
- 意图: 更新容器镜像到 v2.3.1
- 文件: k8s/staging/deployment.yaml
- Diff:
  ```diff
  - image: demo-app:v2.3.0
  + image: demo-app:v2.3.1
  ```
- Diff Hash: sha256:abc123...

## 问题与回答
### Question 1 (blocker)
- 类型: blocker
- 问题: 数据库连接失败，是否回滚？
- 证据:
  - Health check failed (3/3)
  - Container logs: "Database connection failed"
- 回答: a) 回滚部署
- 回答时间: 2026-01-25T10:12:00Z

## Commits
- SHA: abc123def456...
- Message: "deploy: update demo-app to v2.3.1 (rolled back)"
- Timestamp: 2026-01-25T10:15:00Z

## 回滚指南
```bash
# 已自动执行回滚
kubectl rollout undo deployment/demo-app-staging

# 如需回滚 Git 提交:
git revert abc123def456
```

## 验证
- 健康检查: ❌ FAILED
- 单元测试: N/A
- 集成测试: N/A

## 建议
- 排查数据库连接问题后重新部署
- 考虑在部署前增加数据库连接预检查
```

**旁白**:
> "ReviewPack 记录了完整的执行过程：
>
> - 每个步骤的命令和状态
> - 问题与回答
> - 变更的意图和 diff hash
> - 自动生成的回滚指南
>
> 如果出问题，你能精确知道：
> - 谁做的决定？
> - 为什么这么做？
> - 如何撤销？"

---

### 第7段：总结 + CTA（14:00-15:00）

**画面**: 回到演讲者（或标题画面）

**旁白**:
> "AgentOS 不是让 AI 更聪明，
>
> 而是让 AI 执行第一次变得像真正的软件系统：
>
> - 有状态（BLOCKED）
> - 有边界（10 条护城河）
> - 有审计（ReviewPack）
> - 有责任（可回滚）
>
> AgentOS 是开源的，MIT License。"

**画面**: 显示 GitHub 页面

```
https://github.com/yourusername/agentos
```

**旁白**:
> "访问 GitHub，查看完整代码、文档和示例。
>
> 欢迎贡献、讨论和挑战。
>
> 从自然语言到可审计执行，
>
> 这是 AI 工程化的下一步。"

**画面**: 淡出到结束画面

```
═══════════════════════════════════
     AgentOS v1.0
From Natural Language to Auditable Execution

GitHub: github.com/yourusername/agentos
Docs: agentos.dev
Community: github.com/discussions
═══════════════════════════════════
```

---

## 技术准备清单

### 环境准备

- [ ] 安装 AgentOS（`uv sync`）
- [ ] 准备 demo 项目（demo-app）
- [ ] 配置 OpenAI API Key
- [ ] 准备 Kubernetes 测试环境（可选）

### 录制准备

- [ ] 终端录制工具（asciinema / Terminalizer）
- [ ] 屏幕录制软件（OBS Studio / ScreenFlow）
- [ ] 麦克风测试
- [ ] 背景音乐（可选）

### 素材准备

- [ ] 架构图（PNG / SVG）
- [ ] ReviewPack 示例文件
- [ ] GitHub 页面截图

---

## 后期制作建议

### 剪辑要点

1. **节奏控制**
   - 终端操作用 1.5x 加速
   - 关键输出放慢或暂停
   - 配旁白时避免沉默

2. **字幕**
   - 命令行输出用等宽字体
   - 关键术语高亮（如 BLOCKED、ReviewPack）
   - 中英文双字幕（可选）

3. **视觉增强**
   - 关键步骤用箭头/高亮
   - 状态转换用动画
   - 错误信息用红色框

### 音频处理

- 降噪
- 均衡化
- 背景音乐音量 -20dB

### 导出设置

- 分辨率: 1920x1080 (Full HD)
- 帧率: 30fps
- 格式: MP4 (H.264)
- 码率: 5-8 Mbps

---

## 配套资源

### YouTube 描述

```
AgentOS v1.0: 让 AI 执行变得可控、可审计、可回滚

⏱️ 时间戳:
0:00 - 问题引入
1:00 - AgentOS 介绍
3:00 - Demo 1: Interactive 模式
6:00 - Demo 2: Semi-Auto 模式
9:00 - Demo 3: Full-Auto 模式
12:00 - 审计追踪
14:00 - 总结

🔗 链接:
- GitHub: https://github.com/yourusername/agentos
- 白皮书: https://agentos.dev/whitepaper
- 文档: https://agentos.dev/docs

📚 相关阅读:
- 为什么多数 AI Agent 注定失控
- AgentOS vs. LangGraph/AutoGPT
- 三张思想级架构图

#AI #AgentOS #MachineLearning #DevOps #Automation
```

### B站描述

```
AgentOS v1.0: 从自然语言到可审计执行

这是一个让 AI"把活干完"，但不失控、不越权、可审计、可回滚的执行操作系统。

核心特性：
✅ 规划与执行彻底分离
✅ BLOCKED 是一等状态
✅ 10 条机器门禁
✅ 完整审计追踪
✅ 自动回滚指南

开源地址：https://github.com/yourusername/agentos

三连支持！有问题欢迎评论区讨论~
```

---

## 可选变体

### 短视频版本（5 分钟）

**结构**:
1. 问题引入（0:00-0:30）
2. 核心理念（0:30-1:30）
3. 一个 Demo（1:30-4:00）
4. 总结 + CTA（4:00-5:00）

**适合平台**: 抖音、快手、YouTube Shorts

### 长视频版本（30 分钟）

**额外内容**:
- 代码走读（5 分钟）
- 架构深度解析（5 分钟）
- Q&A 环节（5 分钟）

**适合平台**: YouTube、B站

---

**创建时间**: 2026-01-25  
**维护者**: AgentOS Team  
**最后更新**: 2026-01-25
