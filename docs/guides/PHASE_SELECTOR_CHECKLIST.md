# Phase Selector 修复验证清单

## ✅ 自动化验证（已完成）

- [x] 移除原生 confirm() fallback
- [x] 添加 Dialog 组件未加载错误处理
- [x] 添加详细日志前缀 `[PhaseSelector]`
- [x] 文本中文化
- [x] Dialog.js 文件存在
- [x] Dialog 组件已在 index.html 中加载
- [x] Dialog CSS 样式已加载
- [x] 未发现其他使用原生 alert/confirm 的文件
- [x] 自动化测试通过

## 📋 手动验证（待测试）

### 测试环境准备

- [ ] 启动 AgentOS: `python3 -m agentos.webui.app`
- [ ] 浏览器访问: http://localhost:5000
- [ ] 打开开发者工具 Console (F12)

### 功能测试

#### 1. 正常 Phase 切换 (Planning -> Execution)

- [ ] 进入 Chat 页面
- [ ] 点击顶部 Phase 切换按钮（从 Planning 切换到 Execution）
- [ ] **验证**: 出现自定义 Dialog 弹窗（不是浏览器原生弹窗）
- [ ] **验证**: 弹窗标题是 "确认阶段变更"
- [ ] **验证**: 弹窗内容是 "切换到执行阶段？这将允许外部通信..."
- [ ] **验证**: 按钮文字是 "切换到执行" 和 "取消"
- [ ] 点击 "切换到执行"
- [ ] **验证**: Phase 成功切换到 Execution
- [ ] **验证**: 显示成功提示 "阶段已切换至: execution"
- [ ] **验证**: Console 输出详细日志（包含 `[PhaseSelector]` 前缀）

**预期 Console 日志**:
```
[PhaseSelector] 尝试切换阶段: planning -> execution, session: main
[PhaseSelector] 发送 API 请求: {...}
[PhaseSelector] API 响应状态: 200 OK
[PhaseSelector] 阶段更新成功: {...}
```

#### 2. 取消 Phase 切换

- [ ] 点击 Phase 切换按钮（从 Execution 切换到 Planning）
- [ ] 在确认对话框中点击 "取消"
- [ ] **验证**: Phase 保持不变（仍为 Execution）
- [ ] **验证**: Console 输出 `[PhaseSelector] 用户取消了阶段切换`
- [ ] **验证**: 无错误提示

#### 3. Execution -> Planning 切换（无需确认）

- [ ] 点击 Phase 切换按钮（从 Execution 切换到 Planning）
- [ ] **验证**: 不显示确认对话框（仅 Planning -> Execution 需要确认）
- [ ] **验证**: Phase 直接切换到 Planning
- [ ] **验证**: 显示成功提示 "阶段已切换至: planning"

#### 4. 错误场景：Plan Mode 限制

- [ ] 将 Conversation Mode 切换到 "Plan"
- [ ] 尝试将 Phase 切换到 Execution
- [ ] **验证**: Phase 选择器应该被禁用（灰色）
- [ ] **验证**: 显示提示 "Fixed to Planning in Plan mode"
- [ ] **验证**: 无法点击切换按钮

#### 5. Session 切换时 Phase 状态保持

- [ ] 创建一个新 Session
- [ ] 在 Session 1 中将 Phase 设置为 Execution
- [ ] 切换到 Session 2
- [ ] **验证**: Session 2 的 Phase 是 Planning（默认）
- [ ] 切换回 Session 1
- [ ] **验证**: Session 1 的 Phase 仍是 Execution

### UI/UX 验证

#### Dialog 弹窗样式

- [ ] 弹窗背景有半透明遮罩
- [ ] 弹窗居中显示
- [ ] 弹窗有圆角和阴影
- [ ] 弹窗有淡入动画效果
- [ ] 点击遮罩可关闭弹窗
- [ ] 按 Escape 键可关闭弹窗
- [ ] 按 Enter 键确认操作
- [ ] 按钮样式统一（蓝色主按钮 + 灰色次级按钮）

#### Toast 提示样式

- [ ] 成功提示显示为绿色
- [ ] 错误提示显示为红色
- [ ] 提示自动消失
- [ ] 提示位置合理（不遮挡主要内容）

### 性能验证

- [ ] Phase 切换响应迅速（< 500ms）
- [ ] Dialog 弹窗动画流畅
- [ ] 无 Console 错误或警告
- [ ] 无内存泄漏（多次切换后）

### 兼容性验证

浏览器测试:
- [ ] Chrome/Edge (推荐)
- [ ] Firefox
- [ ] Safari

设备测试:
- [ ] 桌面浏览器
- [ ] 平板设备（可选）

### 回归测试

确保其他功能未受影响:
- [ ] Mode 切换功能正常
- [ ] Chat 消息发送正常
- [ ] Session 创建/删除正常
- [ ] 其他 Dialog 使用场景正常（如果有）

## 🐛 已知问题和限制

### 设计限制

1. **Plan Mode 限制**: 当 Conversation Mode 为 "plan" 时，Phase 被锁定为 "planning"，这是设计行为
2. **确认对话框**: 仅在从 Planning 切换到 Execution 时显示确认对话框

### 潜在风险

1. **Dialog 组件依赖**: 如果 Dialog.js 加载失败，将无法显示确认对话框
   - 缓解措施: 显示错误提示，不会静默失败
   - 监控: 通过 Sentry 监控 Dialog 加载失败

2. **Session ID 缺失**: 如果 Session 未正确初始化，Phase 切换会失败
   - 缓解措施: 显示友好错误消息
   - 预防: 确保 Chat 视图正确初始化

## 📊 测试结果记录

### 测试执行人: _______________
### 测试日期: _______________
### AgentOS 版本: v0.3.1

| 测试项 | 通过 | 失败 | 备注 |
|-------|------|------|------|
| 自动化验证 | ☑ | ☐ | |
| 正常 Phase 切换 | ☐ | ☐ | |
| 取消 Phase 切换 | ☐ | ☐ | |
| Execution -> Planning | ☐ | ☐ | |
| Plan Mode 限制 | ☐ | ☐ | |
| Session 切换保持 | ☐ | ☐ | |
| Dialog 弹窗样式 | ☐ | ☐ | |
| Toast 提示样式 | ☐ | ☐ | |
| 性能验证 | ☐ | ☐ | |
| 浏览器兼容性 | ☐ | ☐ | |
| 回归测试 | ☐ | ☐ | |

### 测试总结

**通过项**: ___ / 11

**失败项**: ___

**问题描述**:


**是否批准发布**: ☐ 是  ☐ 否

**签字**: _______________

## 🚀 部署建议

### 部署前

1. [ ] 备份当前版本
2. [ ] 在测试环境验证所有功能
3. [ ] 清除浏览器缓存
4. [ ] 准备回滚计划

### 部署后

1. [ ] 监控错误率（Sentry）
2. [ ] 检查用户反馈
3. [ ] 验证 Phase 切换成功率
4. [ ] 观察 1-2 天无重大问题

### 回滚计划

如果发现严重问题:
```bash
git revert <commit-hash>
# 或恢复备份的文件
```

## 📞 支持联系

如遇问题，请查看:
1. `PHASE_SELECTOR_FIX_REPORT.md` - 完整修复报告
2. `PHASE_SELECTOR_FIX_SUMMARY.md` - 快速参考
3. Console 日志（过滤 `[PhaseSelector]`）
