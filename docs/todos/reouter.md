要把 Provider/Instances 接到 Task Router，最终要实现的效果不是“能选个模型聊天”，而是 Task 从创建到完成，全程可路由、可解释、可审计、可回放。你现在 Provider 层已经齐了（fingerprint、instances、process、output），Task Router 接上去后，应该马上带来这些“肉眼可见”的效果：

⸻

1) 用户能感知到的效果（UI/体验）

A. 新建任务时：自动选对“执行引擎”

你输入一句：

“把 landing page 做出来，React + MUI，生成可运行代码并写 README”

系统会：
	•	把 task 解析成 能力需求（coding、long_ctx、frontend、file-gen、tests）
	•	Router 根据 实例能力画像 自动选择：
	•	llamacpp:qwen3-coder-30b（更强 coding/上下文）
	•	或 ollama:default（轻任务）
	•	或 openai/anthropic（如果本地不可用）

并在 Task 详情里显示：
	•	✅ Selected engine: llamacpp:qwen3-coder-30b
	•	✅ Why: capabilities match: coding+frontend, ctx>=4096, latency best among READY
	•	✅ Alternatives: llamacpp:glm47flash-q8 (lower score)

B. 任务执行中：可以“切换实例/降级/升级”

如果执行中发现：
	•	选的实例变 ERROR / 端口冲突 / OOM
Router 自动 failover：
	•	llamacpp:qwen3-coder-30b → llamacpp:glm47flash-q8 → openai（若配置存在）

UI 会显示：
	•	🔁 Rerouted due to: CONN_REFUSED / MODEL_OOM / TIMEOUT
	•	🧾 Audit: 路由决策记录（什么时候切、为什么切）

C. 任务完成后：可回放、可复现

你能看到：
	•	用了哪个 provider instance
	•	用的模型（metadata）
	•	关键参数（ctx、threads、ngl、extra args）
	•	产生了哪些 artifact
	•	失败/重试次数

这会直接为你后面 “Supervisor/Guardian 验收流” 铺路。

⸻

2) 系统层面必须实现的效果（你要的“Task OS”）

1) Capability 驱动的路由（不是写死 provider）

Router 输入：
	•	TaskSpec（需求）
	•	Candidate Instances（来自 ProviderRegistry + WebUI 配置 + Runtime 状态）

Router 输出：
	•	RoutePlan（选哪个实例、用什么模式、fallback 链）

关键词：评分 + 解释 + 可审计

2) “可解释”是一等公民

每次选路由必须产出一段结构化解释：

{
  "task_id": "...",
  "selected": "llamacpp:qwen3-coder-30b",
  "scores": {
    "llamacpp:qwen3-coder-30b": 0.92,
    "llamacpp:glm47flash-q8": 0.71,
    "ollama:default": 0.40
  },
  "reasons": [
    "READY",
    "capability_match=coding,frontend",
    "ctx>=8192",
    "latency=good"
  ],
  "fallback_chain": ["llamacpp:glm47flash-q8", "openai"]
}

这份解释要写进：
	•	task events（可视化）
	•	logs（可 grep）
	•	audit chain（未来 governance 必需）

3) Router 必须是“动态路由”，而不是一次性选择

在任务生命周期中，Router 至少要处理 3 种 reroute：
	•	实例变不可用（CONN_REFUSED / PORT_CONFLICT）
	•	超时/性能不达标（TIMEOUT / SLOW）
	•	能力不足（输出质量低、上下文不足、tool call 失败）

⸻

3) 你应该先落地的 MVP 路由能力（最小闭环）

为了最快见效，我建议先做 4 个 “Router MVP” 能力：

MVP-1：实例画像（Instance Profile）

从你现有的 providers.json + runtime probe 提取：
	•	provider_type（llamacpp/ollama/lmstudio/cloud）
	•	model_name（metadata）
	•	context_limit（ctx，如果 unknown 先不强推）
	•	tags（手工配置：coding/fast/cheap/vision等）
	•	availability（READY/ERROR + latency）

先允许用户在 WebUI 里给 instance 打标签（coding、fast、big_ctx）

MVP-2：能力需求提取（Task → Requirements）

简单做法：先用规则/heuristic，不依赖大模型：
	•	包含 “写代码/实现/修复/PR” → coding
	•	包含 “长文/总结/多文件” → long_ctx
	•	包含 “React/MUI/Vue” → frontend
	•	包含 “SQL/DB” → data
	•	包含 “测试/pytest/jest” → testing

MVP-3：评分与选择（Scoring）

一个明确公式：
	•	必须 READY
	•	capability match 越多分越高
	•	latency 越低越高
	•	ctx 足够加分
	•	provider preference（本地优先、云 fallback）

MVP-4：fallback chain（失败自动切）

只要执行时遇到：
	•	CONN_REFUSED / TIMEOUT / PROCESS_EXITED
就按 fallback_chain 自动切换，并写 event。

⸻

4) 做完 Router 后，你马上能演示的 3 个 Demo

Demo 1：同一句话，不同环境自动选不同实例
	•	本地 llamacpp READY → 选 llamacpp
	•	本地都挂了 → 自动切 openai/anthropic（若配置）
	•	UI 显示决策原因

Demo 2：强制制造故障 → 自动 reroute

你手动 Stop llamacpp:qwen3-coder-30b
	•	Router 发现任务执行中断 → 自动切到 glm47flash-q8
	•	Output + Event 记录完整

Demo 3：不同任务选不同模型
	•	“写 PRD/白皮书” → long_ctx/fast 文本模型
	•	“修 bug + 生成代码” → coding 模型
	•	“写 SQL 迁移脚本” → data/coding

⸻

5) 你一句话总结“Router 接上后实现什么效果”

Task 变成“可路由的工作单元”：系统会自动选择最合适的模型实例执行，失败能自动切换，并且每一次选择都有解释与审计记录。

⸻

落地方案
行，两个入口都接，而且要做到同一套 Router 内核，只是挂载点不同：
	•	Chat 入口：在“把一句话变成 TaskSpec”之后立刻路由，生成 RoutePlan（可展示/可编辑/可审计）。
	•	Task Runner 入口：在真正执行前再次路由（或验证/刷新），支持 failover / reroute。

下面是直接可落地的方案（按你们现在 AgentOS 的风格：可观测、可解释、可审计、最小侵入）。

⸻

目标效果（你们上线后肉眼可见）
	1.	Chat 输入一句话 → 创建 Task → 立即显示“选中哪个 provider instance + 为什么 + fallback 链”
	2.	点击 Run → Runner 执行时 再次验证实例仍 READY，不 READY 就按 fallback 自动切换
	3.	运行过程中实例挂了/超时 → 自动 reroute，并写 event + logs + audit
	4.	任务结束后可回放：当时选了谁、评分、原因、切换记录

⸻

总体架构

Router 作为一个独立“决策组件”
	•	输入：TaskSpec + RouterContext（所有可用实例 + 状态）
	•	输出：RoutePlan（选择、备选链、解释、约束）

数据流（两入口共用）

Chat：Message → Intent/TaskSpec → Router.route(task_spec) → RoutePlan → 保存 → UI 展示
Runner：task_id → 读 TaskSpec/RoutePlan → Router.verify_or_reroute() → 执行

⸻

需要新增/改造的核心对象（最小集合）

1) InstanceProfile（实例画像）

从你已经有的：
	•	providers.json（metadata）
	•	probe 结果（READY/ERROR、latency、fingerprint、process_running）

聚合成统一结构：

{
  "instance_id": "llamacpp:qwen3-coder-30b",
  "provider_type": "llamacpp",
  "base_url": "http://127.0.0.1:11435",
  "state": "READY",
  "latency_ms": 38,
  "fingerprint": "llamacpp",
  "tags": ["coding", "big_ctx", "local"],
  "ctx": 8192,
  "cost": "local",
  "model": "Qwen3-Coder-30B..."
}

tags/ctx/cost 先允许手工配置（WebUI），自动探测以后再加。

2) TaskRequirements（任务能力需求）

先别上 LLM 解析，MVP 用规则即可（稳定且可控）：

{
  "needs": ["coding", "frontend"],
  "prefer": ["local"],
  "min_ctx": 4096,
  "latency_class": "normal"
}

3) RoutePlan（路由计划）

必须可解释、可审计：

{
  "selected": "llamacpp:qwen3-coder-30b",
  "fallback": ["llamacpp:glm47flash-q8", "openai"],
  "scores": {
    "llamacpp:qwen3-coder-30b": 0.92,
    "llamacpp:glm47flash-q8": 0.73,
    "openai": 0.66
  },
  "reasons": [
    "READY",
    "tags_match=coding,frontend",
    "ctx>=4096",
    "local_preferred"
  ],
  "router_version": "v1",
  "timestamp": "..."
}


⸻

路由策略（MVP 评分公式）

硬门槛：
	•	instance.state == READY（否则直接淘汰）
	•	fingerprint 与 provider_type 预期匹配（你们已经做了）

加分项：
	•	tags 命中每个 need：+0.2
	•	ctx 满足 min_ctx：+0.1（未知 ctx 只给 +0.02）
	•	latency 更低：+0.0~0.1（归一化）
	•	prefer local：本地实例 +0.05，云实例 -0.02（可调）

输出：
	•	top1 selected
	•	topN fallback（默认 2 个）
	•	reasons（必须包含：为何选它、为何淘汰其它）

⸻

两个入口怎么接（关键点）

A) Chat 入口：创建 task 时即路由（“提前决策”）

Hook 点

Chat → Task creation pipeline（你们现有的“chat→task”边界那里）

行为
	1.	生成 TaskSpec（title/goal/constraints）
	2.	Router 获取最新 InstanceProfiles（调用你已做好的 /api/providers/instances 或内部 ProviderRegistry 状态）
	3.	RoutePlan = router.route(TaskSpec)
	4.	保存到 taskdb（或 task 记录里）：
	•	task.route_plan_json
	•	task.requirements_json
	•	task.route_selected_instance
	5.	写 Event：
	•	TASK_ROUTED（包含 selected、fallback、reasons、scores）

UI

Chat 创建 Task 的确认卡里展示：
	•	Selected instance
	•	Why（reasons 简要）
	•	Change…（可手动改 selected，改动写 TASK_ROUTE_OVERRIDDEN）

手动改是“产品级必需”：当 router 不懂你意图时，你能一键改。

⸻

B) Runner 入口：执行前验证/刷新路由（“临场决策”）

Runner 里真正开始执行前做：

verify_or_reroute
	•	读取 task.route_plan
	•	检查 selected instance 当前状态：
	•	READY → 继续
	•	否 → 按 fallback 顺序找第一个 READY
	•	都不 READY → 如果 cloud 可用，落到 cloud；否则任务标记为 BLOCKED/ERROR

写 Event：
	•	TASK_ROUTE_VERIFIED（仍使用同一实例）
	•	TASK_REROUTED（从 A 切到 B，附 reason_code：CONN_REFUSED/TIMEOUT/EXITED）

运行中 failover

当执行阶段出现以下错误之一：
	•	CONN_REFUSED
	•	TIMEOUT（可定义连续 N 次/或单次超阈值）
	•	PROCESS_EXITED
	•	FINGERPRINT_MISMATCH（极少，但要兜底）

触发：
	•	TASK_REROUTED + 继续执行（从失败 step 重新开始，或从最近 checkpoint 继续）

⸻

数据库/模型改造（最小侵入）

在 task 表里加 3~4 列即可（JSON 足够，不必先做新表）：
	•	route_plan_json (TEXT)
	•	requirements_json (TEXT)
	•	selected_instance_id (TEXT)
	•	router_version (TEXT)

事件表（你们已有 event/log 体系）新增 event_type：
	•	TASK_ROUTED
	•	TASK_ROUTE_OVERRIDDEN
	•	TASK_ROUTE_VERIFIED
	•	TASK_REROUTED

⸻

WebUI / Providers 页需要补的一点点（为了 Router）

你已经有 ProvidersView 了，只加两处小扩展：
	1.	Instance Row 增加 Tags 编辑（逗号输入即可）
	2.	instance metadata 增加 ctx（可选）与 role（coding/general/fast）

这些写回 providers.json，Router 就能用了。

⸻

交付拆 PR（直接能干）

PR-1 Router Core（纯后端，不动 UI）
	•	agentos/router/ 新模块：
	•	requirements_extractor.py（规则版）
	•	instance_profiles.py（从现有 providers 状态聚合）
	•	scorer.py
	•	router.py（route / verify_or_reroute）
	•	新 event types + 写入
	•	task model 增加 route_plan/requirements 字段

✅ 完成后：你可以在 CLI/日志看到 task 被路由到哪个实例。

PR-2 Chat→Task 路由接入（入口 1）
	•	Chat 创建 task 时调用 Router.route
	•	保存 route_plan
	•	在 chat/任务详情里展示 selected + reasons（哪怕先是 text）

✅ 完成后：Chat 入口创建任务就能看到“选了谁”。

PR-3 Runner 执行前路由验证 + failover（入口 2）
	•	Runner start 前 verify_or_reroute
	•	执行中错误触发 reroute
	•	事件/日志可观测

✅ 完成后：模拟 stop 某个 llama-server，任务会自动切换实例继续跑。

PR-4 WebUI 路由可视化增强 ✅ COMPLETE
	•	ProvidersView：tags/ctx/role 编辑（完成）
	•	Task view：显示 route timeline（TASK_ROUTED/TASK_REROUTED/TASK_ROUTE_VERIFIED/TASK_ROUTE_OVERRIDDEN）（完成）
	•	RouteDecisionCard 组件：路由决策卡片（完成）
	•	完整 CSS 样式：~500 行路由可视化样式（完成）
	•	文档：PR-4-Router-Visualization.md（完成）

⸻

MVP 的验收用例（你们“守门员硬验证”风格）
	1.	三个 llamacpp READY，ollama/lmstudio CONN_REFUSED
Chat 创建“写代码任务” → selected 必须是 qwen3-coder-30b（或你 tags 分最高那个）
	2.	Runner 执行前，把 selected 实例 stop 掉
→ verify_or_reroute 必须切到 fallback，并写 TASK_REROUTED
	3.	执行中模拟 TIMEOUT（人为让 endpoint 不响应）
→ reroute 发生，event+log 可见
	4.	Cloud 未配置时，本地全挂
→ 任务必须进入 BLOCKED/ERROR，reason 清晰（NO_AVAILABLE_INSTANCE）

⸻

如果你现在就要开干：先落 PR-1 + PR-3（Router Core + Runner 接入）。
原因：这两步一完成，你马上就能演示“自动切换实例继续跑”，这是最硬核的价值点；Chat 入口只是“更早展示同一份决策”，属于锦上添花。
