# PR-E 验证指南

**WebUI 状态**: ✅ **已运行** (PID: 23772)
**访问地址**: http://127.0.0.1:9090
**当前时间**: 2026-01-30 15:43

---

## 🎯 快速验证步骤

### 1. 刷新浏览器
打开 http://127.0.0.1:9090，按 `Cmd+R` 或 `F5` 刷新页面

### 2. 测试 Extension 命令

#### 测试 A: /test hello
```
在聊天框输入: /test hello
```

**期望结果**:
```
Hello from Test Extension! 🎉
Args: []
```

**验证点**:
- ✅ 无错误信息
- ✅ 显示上述文本
- ✅ 响应时间 < 3 秒

---

#### 测试 B: /test status
```
在聊天框输入: /test status
```

**期望结果**:
```
System Status
=============
Python: 3.13.x
Platform: darwin
Architecture: arm64
Time: 2026-01-30 15:43:xx
```

**验证点**:
- ✅ 显示系统信息
- ✅ 无错误信息

---

#### 测试 C: 内置命令不受影响
```
/help
```

**期望结果**: 显示命令列表，包括所有内置命令

```
/model
```

**期望结果**: 显示模型信息

**验证点**:
- ✅ 内置命令正常工作
- ✅ 无破坏性变更

---

### 3. API 测试 (可选)

打开新终端，执行：

```bash
# 测试 1: 启动执行
curl -X POST http://localhost:9090/api/extensions/execute \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test-session","command":"/test hello","dry_run":false}'
```

**期望输出**:
```json
{
  "run_id": "run_xxxxxxxxxx",
  "status": "PENDING"
}
```

**验证点**:
- ✅ 返回 200 状态码
- ✅ 包含 run_id
- ✅ status 为 PENDING

---

```bash
# 测试 2: 查询状态（使用上面返回的 run_id）
curl http://localhost:9090/api/runs/run_xxxxxxxxxx
```

**期望输出**:
```json
{
  "run_id": "run_xxxxxxxxxx",
  "extension_id": "tools.test",
  "action": "hello",
  "status": "SUCCEEDED",
  "progress_pct": 100,
  "stdout": "Hello from Test Extension! 🎉\nArgs: []",
  "started_at": "2026-01-30T15:43:xx",
  "ended_at": "2026-01-30T15:43:xx"
}
```

**验证点**:
- ✅ status 为 SUCCEEDED
- ✅ progress_pct 为 100
- ✅ stdout 包含正确的输出

---

## 🔍 故障排除

### 问题 1: 显示 "Unknown command: /test"

**原因**: Extension 可能未正确安装

**解决方案**:
```bash
# 检查扩展列表
curl http://localhost:9090/api/extensions | jq
```

应该看到 `tools.test` 扩展，状态为 `INSTALLED` 且 `enabled: true`

如果没有，运行：
```bash
cd /Users/pangge/PycharmProjects/AgentOS
.venv/bin/python << 'EOF'
from agentos.core.extensions.registry import ExtensionRegistry
registry = ExtensionRegistry()
extensions = registry.list_extensions()
for ext in extensions:
    print(f"{ext.id}: enabled={ext.enabled}, status={ext.status}")
EOF
```

---

### 问题 2: 显示 "message_idcontentrolemetadatacontext"

**原因**: WebUI 未重启，仍在运行旧代码

**解决方案**:
```bash
# 强制重启
pkill -9 -f "uvicorn agentos.webui.app"
sleep 2
.venv/bin/uvicorn agentos.webui.app:app --host 127.0.0.1 --port 9090 &
```

---

### 问题 3: 返回 405 Method Not Allowed

**原因**: 路由修复未生效（不应该发生，因为已重启）

**验证**:
```bash
# 检查 app.py 路由顺序
grep -A 2 "extensions_execute.router" agentos/webui/app.py
```

应该看到 `extensions_execute.router` 在 `extensions.router` **之前** 注册

---

### 问题 4: Handler 执行失败

**原因**: handlers.py 可能不存在或有语法错误

**检查**:
```bash
# 验证 handlers.py
cat ~/.agentos/extensions/tools.test/handlers.py

# 或者
cat store/extensions/tools.test/handlers.py
```

应该包含 `hello_fn` 和 `status_fn`，以及 `HANDLERS` 字典

---

## 📊 性能基准

### 预期性能指标

| 操作 | 预期时间 | 可接受范围 |
|-----|---------|----------|
| /test hello | 100-200ms | < 500ms |
| /test status | 150-300ms | < 1s |
| API 调用 | 50-100ms | < 200ms |
| 端到端 | 1-2s | < 3s |

### 性能测试脚本

```bash
cd /Users/pangge/PycharmProjects/AgentOS

# 运行性能测试
.venv/bin/python << 'EOF'
import requests
import time

url = "http://localhost:9090/api/extensions/execute"
times = []

for i in range(10):
    start = time.time()

    resp = requests.post(url, json={
        "session_id": f"perf-{i}",
        "command": "/test hello"
    })

    if resp.status_code == 200:
        run_id = resp.json()["run_id"]

        # Poll until complete
        status_url = f"http://localhost:9090/api/runs/{run_id}"
        while True:
            status_resp = requests.get(status_url)
            if status_resp.json()["status"] in ["SUCCEEDED", "FAILED"]:
                break
            time.sleep(0.05)

        elapsed = time.time() - start
        times.append(elapsed)
        print(f"Run {i+1}: {elapsed:.3f}s")

if times:
    print(f"\n平均: {sum(times)/len(times):.3f}s")
    print(f"最快: {min(times):.3f}s")
    print(f"最慢: {max(times):.3f}s")
EOF
```

**预期输出**:
```
Run 1: 0.152s
Run 2: 0.143s
...
Run 10: 0.158s

平均: 0.150s
最快: 0.143s
最慢: 0.158s
```

---

## ✅ 验收清单

完成以下检查项：

### 基础功能
- [ ] /test hello 正常工作
- [ ] /test status 正常工作
- [ ] /help 正常工作
- [ ] /model 正常工作
- [ ] 无 "message_idcontentrolemetadatacontext" 错误

### API 功能
- [ ] POST /api/extensions/execute 返回 200
- [ ] GET /api/runs/{run_id} 返回正确状态
- [ ] status 从 PENDING → RUNNING → SUCCEEDED
- [ ] stdout 包含正确输出

### 性能
- [ ] 响应时间 < 2 秒
- [ ] 无明显延迟
- [ ] 10 次连续执行稳定

### 审计
- [ ] 审计日志包含执行记录
- [ ] 字段完整（ext_id, action, decision）

---

## 📚 参考文档

### 完整文档
- **完成总结**: `PR_E_COMPLETION_SUMMARY.md`
- **验收报告**: `PR_E_FINAL_ACCEPTANCE_REPORT.md`
- **快速参考**: `TASK_8_QUICK_REFERENCE.md`

### 架构文档
- **ADR**: `docs/architecture/ADR_CAPABILITY_RUNNER.md`
- **开发指南**: `docs/extensions/CAPABILITY_RUNNER_GUIDE.md`
- **架构详解**: `docs/extensions/RUNNER_ARCHITECTURE.md`

### 实施报告
- PR-E1 到 PR-E6 各个任务的详细实施报告

---

## 🎉 验证完成后

如果所有测试通过，恭喜！PR-E: Capability Runner 已成功部署。

### 下一步
1. ✅ 合并 PR-E 到主分支
2. 📝 更新 CHANGELOG.md
3. 🏷️ 打版本标签 (v0.7.0)
4. 🚀 部署到生产环境
5. 📊 监控执行日志和性能指标

---

## 💬 反馈和支持

如果遇到任何问题：
1. 查看故障排除章节
2. 检查日志文件 `/tmp/webui_pr_e_final.log`
3. 运行诊断脚本 `test_acceptance_webui.py`
4. 查看审计日志验证执行记录

---

**祝测试顺利！** 🎊

*最后更新: 2026-01-30 15:43*
