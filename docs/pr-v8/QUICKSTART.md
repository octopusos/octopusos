# PR-V8: 验收测试快速入门

## 5 分钟快速验收

### 前置条件

1. **安装依赖**:
```bash
# Python 依赖
pip install pytest requests

# Node.js 依赖（可选，用于前端测试）
npm install -D @playwright/test jest
npx playwright install chromium
```

2. **启动 WebUI**:
```bash
python -m agentos.webui.app
```

等待 WebUI 在 http://localhost:8000 启动成功。

---

## 方式 1: 一键运行所有测试（推荐）

```bash
cd /Users/pangge/PycharmProjects/AgentOS
./tests/acceptance/run_all_tests.sh
```

**输出**:
- 测试报告: `tests/acceptance/reports/FINAL_ACCEPTANCE_REPORT.md`
- Demo 输出: `tests/demos/outputs/`

**预期时间**: 5-10 分钟

---

## 方式 2: 分步运行

### Step 1: 运行集成测试（最重要）

```bash
pytest tests/acceptance/test_full_pipeline_acceptance.py -v
```

**验证项**:
- ✅ Event API 存在
- ✅ 19 种事件类型埋点
- ✅ SSE 实时推送
- ✅ Work items 协调可见
- ✅ Evidence 可访问
- ✅ Gates fail/retry 可见
- ✅ Recovery 连续性
- ✅ 性能（100 并发）

**预期**: 10/10 tests PASS

---

### Step 2: 运行 Demo 脚本

#### Demo 1: 正常流程
```bash
python tests/demos/demo_1_normal_flow.py
```

**产出**: `tests/demos/outputs/demo_1/`
- `demo_1_timeline.json` - 事件时间线
- `evidence/` - Checkpoint 证据

#### Demo 2: Gate 失败
```bash
python tests/demos/demo_2_gate_fail_recovery.py
```

**产出**: `tests/demos/outputs/demo_2/`
- `demo_2_timeline.json` - Gate 事件

#### Demo 3: 恢复
```bash
python tests/demos/demo_3_recovery.py
```

**产出**: `tests/demos/outputs/demo_3/`
- `demo_3_recovery_events.json` - 恢复事件

---

### Step 3: 运行 E2E 测试（可选）

```bash
npx playwright test tests/e2e/test_end_to_end_runner_ui.spec.js --headed
```

**验证项**:
- ✅ 非技术用户理解性
- ✅ Pipeline 动态可视化
- ✅ Work items 协调
- ✅ Evidence drawer 可访问
- ✅ 连接状态显示
- ✅ 大量事件性能

**预期**: 7/8 tests PASS (1 skip)

---

## 方式 3: 手动验收

### 1. 打开 WebUI
```bash
open http://localhost:8000
```

### 2. 创建测试任务

点击 "New Task"，填写：
- Title: `Test Task`
- Description: `Test work items coordination`
- Work Items: 添加 3 个

### 3. 观察 UI

**Pipeline View**:
- [ ] 看到 4 个阶段（planning, executing, verifying, done）
- [ ] 阶段会高亮激活
- [ ] 3 个 work item 卡片出现
- [ ] Merge node 显示 "3/3"

**Timeline View**:
- [ ] 看到"当前在做什么"
- [ ] 看到"下一步是什么"
- [ ] 事件按时间排列

**Evidence Drawer**:
- [ ] 点击 checkpoint
- [ ] Drawer 弹出
- [ ] 看到证据列表

### 4. 测试恢复

- 刷新页面
- [ ] 事件仍然可见
- [ ] 叙事连续

---

## 验收清单

完成测试后，填写用户验收清单：

```bash
open docs/pr-v8/USER_ACCEPTANCE_CHECKLIST.md
```

---

## 查看报告

### 自动生成的报告

```bash
cat tests/acceptance/reports/FINAL_ACCEPTANCE_REPORT.md
```

### Demo 输出

```bash
ls tests/demos/outputs/
```

---

## 常见问题

### Q1: WebUI 无法启动

**检查端口占用**:
```bash
lsof -i :8000
kill -9 <PID>
```

### Q2: 测试失败

**查看日志**:
```bash
tail -f ~/.agentos/webui.log
```

### Q3: Playwright 测试跳过

需要先安装浏览器:
```bash
npx playwright install chromium
```

---

## 下一步

1. ✅ 运行自动化测试
2. ✅ 查看测试报告
3. ⚠️ 完成用户验收清单
4. ⚠️ 录制 Demo 视频（3 个 × 30 秒）
5. ⚠️ 截图补充

---

## 联系支持

如有问题，请查看：
- 完整文档: `docs/pr-v8/FINAL_ACCEPTANCE_REPORT.md`
- 用户清单: `docs/pr-v8/USER_ACCEPTANCE_CHECKLIST.md`

---

**文档版本**: 1.0
**最后更新**: 2026-01-30
