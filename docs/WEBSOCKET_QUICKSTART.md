# WebSocket 修复 - 快速验收指南

> 🚀 **5 分钟快速验收** - 确保 Safari/Windows 跨平台问题已修复

---

## 📦 已修复的问题

### ✅ P0 修复
1. **Safari bfcache 僵尸连接** - 后退恢复页面时自动重连
2. **Windows 静默失效** - 网络波动时自动重连，不需要手动刷新
3. **长连接心跳** - 30s ping/60s pong 超时检测
4. **连接唯一性** - 防止重复连接和消息重复

### ✅ P1 增强
5. **Windows localhost fallback** - IPv6 问题兜底
6. **Lifecycle 冷却机制** - 防止抖动重连
7. **非 JSON 消息兜底** - 不会吞掉纯文本消息
8. **诊断工具** - `wsDebug()`, `wsReconnect()`, `wsTest`

---

## 🏃 5 分钟快速验收

### 步骤 1: 启动 WebUI

```bash
cd /Users/pangge/PycharmProjects/AgentOS
# 启动你的 WebUI 服务
python -m agentos.webui.daemon
# 或者你的启动命令
```

### 步骤 2: 打开聊天页面

浏览器访问: http://localhost:8000 （或你的端口）

### 步骤 3: 打开浏览器控制台

- **Mac**: `Cmd + Option + J` (Chrome) 或 `Cmd + Option + C` (Safari)
- **Windows**: `Ctrl + Shift + J` (Chrome/Edge) 或 `F12`

### 步骤 4: 检查 WebSocket 状态

在控制台执行:
```javascript
wsDebug()
```

**预期输出**:
```
🔍 WebSocket Diagnostics
  URL: ws://localhost:8000/ws/chat/main
  Ready State: OPEN (1)
  Retry Count: 0 / 10
  ...
  Health Score: 100/100 🟢 优秀
```

### 步骤 5: 运行自动化测试（可选）

```javascript
// 加载测试脚本
fetch('/static/js/ws-acceptance-test.js')
    .then(r => r.text())
    .then(code => eval(code))
    .then(() => wsTest.runAll());

// 或者直接访问
// http://localhost:8000/static/js/ws-acceptance-test.js
// 复制内容到控制台执行
```

---

## 🧪 关键测试场景

### 测试 A: Safari bfcache 恢复 ⭐️ 最重要

**平台**: Mac Safari

**步骤**:
1. 打开聊天页面，发送一条消息确认工作正常
2. 点击导航栏的 "Overview" 或 "Projects"
3. 点击浏览器后退按钮（← 按钮）
4. **不刷新页面**，直接在聊天输入框发送 "test"
5. 观察是否能收到回复

**✅ 通过标准**:
- 不需要刷新页面
- 消息发送后能实时收到回复
- 控制台看到 `[Lifecycle] pageshow (bfcache restored) → force reconnect`

**❌ 如果失败**:
- 执行 `wsDebug()`，查看 `readyState` 和 `isAlive`
- 截图控制台日志，发送给开发团队

---

### 测试 B: Windows 网络恢复

**平台**: Windows Chrome/Edge

**步骤**:
1. 打开聊天页面，发送一条消息确认工作正常
2. 在控制台执行 `wsDebug()` 记录初始状态
3. 断开网络（关闭 WiFi 或拔网线）
4. 等待 5 秒，观察控制台日志
5. 恢复网络
6. 等待最多 30 秒
7. 执行 `wsDebug()` 检查是否恢复
8. 发送测试消息验证

**✅ 通过标准**:
- 断网时看到 `[WS] reconnect scheduled`
- 恢复网络后 30 秒内自动重连成功
- `wsDebug()` 显示 `Ready State: OPEN`
- 消息能正常发送

**❌ 如果失败**:
- 检查 `retryCount` 是否打满 10 次
- 查看 Windows 防火墙/杀毒软件日志

---

### 测试 C: 长连接心跳（可选）

**平台**: 所有

**步骤**:
1. 打开聊天页面，不操作
2. 等待 2 分钟
3. 观察控制台，应该看到 ping/pong 日志
4. 执行 `wsDebug()`，查看 `Idle Time`
5. 发送测试消息，确认仍能正常工作

**✅ 通过标准**:
- 每 30 秒看到 `[WS] sent ping` 和 `[WS] received pong`
- 空闲时间正常递增
- 不会出现每 60 秒重连一次的现象

---

## 🔍 诊断工具使用

### 基础诊断

```javascript
// 查看完整状态
wsDebug()

// 手动重连
wsReconnect()

// 查看内部状态
console.log(WS.getDiagnostics())
```

### 高级诊断

```javascript
// 强制触发重连
WS.forceReconnect('manual_test')

// 检查连接唯一性
wsTest.test1_ConnectionUniqueness()

// 检查心跳机制（需等待 35 秒）
await wsTest.test3_HeartbeatVerification()

// 检查冷却机制
await wsTest.test6_LifecycleCooldown()
```

### 生成完整报告

```javascript
// 运行所有测试并生成报告
await wsTest.runAll()

// 生成 Markdown 格式报告
wsTest.generateReport()
// 复制输出，可用于 GitHub Issue
```

---

## 🚨 常见问题排查

### 问题 1: 消息重复出现

**症状**: 发送一条消息，UI 上显示两条

**排查**:
```javascript
wsDebug()  // 查看连接状态
// DevTools → Network → WS 查看连接数
```

**可能原因**: 多个连接同时存在

**解决**: 刷新页面，如果仍然出现，报告给开发团队

---

### 问题 2: 每 60 秒重连一次

**症状**: 页面正常使用，但每分钟看到一次重连

**排查**:
```javascript
// 观察控制台日志
// 应该看到成对的 ping/pong，而不是频繁重连
```

**可能原因**: pong 消息格式不匹配

**解决**: 检查后端 WebSocket pong 响应格式

---

### 问题 3: Safari 后退后收不到消息

**症状**: 后退恢复页面后，状态显示 Connected，但发送消息没反应

**排查**:
```javascript
wsDebug()
// 查看 lastOpenAt 是否更新
// 查看 isAlive 是否为 true
```

**可能原因**: pageshow 事件未触发或 forceReconnect 失败

**解决**: 手动执行 `wsReconnect()` 临时解决

---

### 问题 4: Windows 恢复网络后连不上

**症状**: 断网后恢复，但一直显示 Disconnected

**排查**:
```javascript
wsDebug()
// 查看 Retry Count 是否打满 10/10
// 查看 Ready State 是否卡在 CONNECTING
```

**可能原因**: 防火墙阻止 WebSocket 连接

**解决**:
1. 检查 Windows 防火墙设置
2. 临时关闭杀毒软件测试
3. 手动执行 `wsReconnect()` 重试

---

## 📊 健康评分说明

执行 `wsDebug()` 后会显示健康评分：

- **90-100 分 (🟢 优秀)**: 连接完美，所有指标正常
- **70-89 分 (🟡 良好)**: 连接正常，有轻微问题
- **50-69 分 (🟠 一般)**: 连接不稳定，需要关注
- **0-49 分 (🔴 差)**: 连接有严重问题，需要重连

**评分标准**:
- `readyState === OPEN`: +40 分
- `isAlive === true`: +30 分
- `retryCount === 0`: +20 分
- `idleMs < 60s`: +10 分

---

## 📋 提交 Bug 报告

如果遇到问题，请提供以下信息：

### 必需信息
```javascript
// 1. WebSocket 诊断信息
wsDebug()
// 复制完整输出

// 2. 浏览器信息
navigator.userAgent
// 复制输出

// 3. 控制台日志
// 复制最后 20 行 [WS] 开头的日志
```

### 可选信息
```javascript
// 4. 完整测试报告
await wsTest.runAll()
wsTest.generateReport()
// 复制 Markdown 输出

// 5. Network 面板截图
// DevTools → Network → WS
// 截图连接列表
```

### GitHub Issue 模板

```markdown
## Bug 描述
[描述问题]

## 平台信息
- 操作系统: [Mac/Windows]
- 浏览器: [Safari/Chrome/Edge + 版本号]
- WebUI 版本: v0.3.2+ws-fixes

## 复现步骤
1. [步骤 1]
2. [步骤 2]
3. [步骤 3]

## wsDebug() 输出
\```
[粘贴 wsDebug() 完整输出]
\```

## 控制台日志
\```
[粘贴最后 20 行 [WS] 日志]
\```

## 截图
[如果有的话]
```

---

## ✅ 验收通过标准

所有关键测试通过后，可以认为修复成功：

- [x] `wsDebug()` 显示健康评分 ≥ 90 分
- [x] **Safari**: 后退恢复测试通过
- [x] **Windows**: 网络恢复测试通过
- [x] **所有平台**: 消息不重复，连接唯一
- [x] **所有平台**: 长时间运行稳定，无节律性重连

---

## 🔗 相关文档

- [完整验收清单](./WEBSOCKET_ACCEPTANCE_CHECKLIST.md) - 详细的守门员验收文档
- [验收测试脚本](../agentos/webui/static/js/ws-acceptance-test.js) - 自动化测试代码
- [问题根因分析](../SHELL_TRUE_FIX_SUMMARY.md) - 原始问题分析报告（如果存在）

---

**最后更新**: 2026-01-29
**版本**: v0.3.2+ws-fixes
**状态**: ✅ Ready for Testing
