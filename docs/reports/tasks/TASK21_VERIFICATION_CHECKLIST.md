# Task #21: 前端交互完善 - 验收测试清单

## 测试前准备
- [ ] 启动 AgentOS WebUI
- [ ] 打开浏览器开发者工具（F12）
- [ ] 导航到 Providers 页面
- [ ] 确保至少有一个 Provider 已配置（Ollama 推荐）

---

## 1. 按钮状态管理测试

### 1.1 Start Instance 按钮
- [ ] 点击 Start 按钮
- [ ] 验证按钮显示 `<spinner> Starting...`
- [ ] 验证按钮被禁用（opacity: 0.6，不可点击）
- [ ] 等待启动完成
- [ ] 验证按钮恢复为 `Start` 图标和文本
- [ ] 验证按钮重新启用（可点击）
- [ ] 验证 1 秒后状态自动刷新

### 1.2 Stop Instance 按钮
- [ ] 点击 Stop 按钮
- [ ] 验证显示确认对话框："Are you sure you want to stop..."
- [ ] 点击 Cancel，验证操作取消
- [ ] 再次点击 Stop，点击 OK
- [ ] 验证按钮显示 `<spinner> Stopping...`
- [ ] 验证按钮被禁用
- [ ] 等待停止完成
- [ ] 验证按钮恢复为 `Stop` 图标和文本
- [ ] 验证 Toast 通知显示成功消息
- [ ] 验证 1 秒后状态自动刷新

### 1.3 Restart Instance 按钮
- [ ] 点击 Restart 按钮
- [ ] 验证显示确认对话框："Are you sure you want to restart..."
- [ ] 点击 Cancel，验证操作取消
- [ ] 再次点击 Restart，点击 OK
- [ ] 验证按钮显示 `<spinner> Restarting...`
- [ ] 验证按钮被禁用
- [ ] 验证 Toast 显示旧 PID 和新 PID
- [ ] 等待重启完成
- [ ] 验证按钮恢复为 `Restart` 图标和文本
- [ ] 验证 1 秒后状态自动刷新

---

## 2. 防抖机制测试

### 2.1 快速连续点击
- [ ] 快速连续点击 Start 按钮 5 次
- [ ] 验证按钮在第一次点击后立即被禁用
- [ ] 验证只有一个请求被发送（检查 Network 面板）
- [ ] 验证后续点击被忽略

### 2.2 操作进行中尝试其他操作
- [ ] 启动一个实例
- [ ] 在启动完成前尝试点击 Stop 按钮
- [ ] 验证按钮被禁用且无法点击
- [ ] 等待启动完成
- [ ] 验证现在可以点击 Stop 按钮

---

## 3. 自动刷新状态测试

### 3.1 操作后自动刷新
- [ ] 执行 Start 操作
- [ ] 观察 1 秒延迟后
- [ ] 验证状态从 STOPPED 变为 RUNNING
- [ ] 验证 Process 列显示 PID
- [ ] 执行 Stop 操作
- [ ] 观察 1 秒延迟后
- [ ] 验证状态从 RUNNING 变为 STOPPED

### 3.2 配置保存后刷新
- [ ] 保存可执行文件路径
- [ ] 验证 1 秒后状态刷新
- [ ] 验证 Resolved 路径更新

---

## 4. 配置验证与保存分离测试

### 4.1 Validate 按钮显示
- [ ] 导航到 Executable Configuration 部分
- [ ] 点击 Browse 按钮选择一个文件
- [ ] 验证 Validate 按钮出现（display: inline-flex）
- [ ] 验证 Save 按钮也出现

### 4.2 Validate 功能
- [ ] 在路径输入框中输入有效的可执行文件路径（如 `/usr/local/bin/ollama`）
- [ ] 点击 Validate 按钮
- [ ] 验证按钮显示 `<spinner> Validating...`
- [ ] 验证按钮被禁用
- [ ] 验证验证消息显示 `⏳ Validating...`（蓝色背景）
- [ ] 等待验证完成
- [ ] 验证验证消息显示 `✓ Valid executable`（绿色背景）
- [ ] 验证 Toast 显示成功消息
- [ ] 验证 Version 信息更新

### 4.3 Validate 失败场景
- [ ] 输入无效路径（如 `/invalid/path/to/ollama`）
- [ ] 点击 Validate 按钮
- [ ] 验证验证消息显示 `✗ Invalid executable` 或错误详情（红色背景）
- [ ] 验证 Toast 显示错误消息

### 4.4 Save 前验证
- [ ] 输入有效路径但不点击 Validate
- [ ] 直接点击 Save 按钮
- [ ] 验证自动触发验证
- [ ] 如果验证通过，保存成功
- [ ] 如果验证失败，显示错误并阻止保存

### 4.5 Save 失败阻止
- [ ] 输入无效路径
- [ ] 点击 Save 按钮
- [ ] 验证显示 Toast: "Please fix validation errors before saving"
- [ ] 验证路径未被保存
- [ ] 验证 Resolved 路径未改变

---

## 5. 操作确认对话框测试

### 5.1 Stop 确认
- [ ] 启动一个实例
- [ ] 点击 Stop 按钮
- [ ] 验证显示确认对话框
- [ ] 验证对话框文本：
  ```
  Are you sure you want to stop ollama instance?

  This will terminate the running process.
  ```
- [ ] 点击 Cancel，验证无操作
- [ ] 再次点击 Stop，点击 OK，验证停止执行

### 5.2 Restart 确认
- [ ] 启动一个实例
- [ ] 点击 Restart 按钮
- [ ] 验证显示确认对话框
- [ ] 验证对话框文本：
  ```
  Are you sure you want to restart ollama instance?

  This will stop and restart the running process.
  ```
- [ ] 点击 Cancel，验证无操作
- [ ] 再次点击 Restart，点击 OK，验证重启执行

---

## 6. 批量操作测试

### 6.1 按钮显示逻辑
- [ ] 初始状态无运行实例
- [ ] 验证 Stop All 和 Restart All 按钮不显示（display: none）
- [ ] 启动一个实例
- [ ] 验证两个按钮出现（display: inline-flex）
- [ ] 停止所有实例
- [ ] 验证两个按钮隐藏

### 6.2 Stop All 功能
- [ ] 启动 2-3 个实例（Ollama 和 llama.cpp）
- [ ] 验证 Stop All 按钮显示
- [ ] 点击 Stop All 按钮
- [ ] 验证显示确认对话框
- [ ] 验证对话框显示实例列表：
  ```
  Are you sure you want to stop 3 running instance(s)?

  • ollama:default
  • ollama:secondary
  • llamacpp:local
  ```
- [ ] 点击 Cancel，验证无操作
- [ ] 再次点击 Stop All，点击 OK
- [ ] 验证按钮显示 `<spinner> Stopping...`
- [ ] 验证按钮被禁用
- [ ] 等待操作完成
- [ ] 验证 Toast 显示："Stopped 3 instance(s)"
- [ ] 验证所有实例状态变为 STOPPED
- [ ] 验证 Stop All 按钮隐藏

### 6.3 Restart All 功能
- [ ] 启动 2-3 个实例
- [ ] 验证 Restart All 按钮显示
- [ ] 点击 Restart All 按钮
- [ ] 验证显示确认对话框和实例列表
- [ ] 点击 OK
- [ ] 验证按钮显示 `<spinner> Restarting...`
- [ ] 验证按钮被禁用
- [ ] 等待操作完成
- [ ] 验证 Toast 显示："Restarted 3 instance(s)"
- [ ] 验证所有实例保持 RUNNING 状态

### 6.4 批量操作部分失败
- [ ] 手动修改一个实例的 PID 为无效值（通过浏览器控制台）
- [ ] 执行 Stop All 或 Restart All
- [ ] 验证 Toast 显示："Stopped 2 instance(s), 1 failed"
- [ ] 验证成功的实例状态已更新

### 6.5 批量操作无实例
- [ ] 停止所有实例
- [ ] 观察 Stop All 和 Restart All 按钮应该隐藏
- [ ] 如果按钮仍显示（不应该），点击按钮
- [ ] 验证显示 Toast: "No running instances to stop/restart"

---

## 7. CSS 样式测试

### 7.1 Spinner 样式
- [ ] 触发任何带 loading 状态的操作
- [ ] 验证 spinner 正确显示
- [ ] 验证 spinner 旋转动画流畅
- [ ] 验证 spinner 颜色与按钮背景对比明显
- [ ] 在亮色按钮（如 Secondary）上验证深色 spinner
- [ ] 在暗色按钮（如 Primary、Warning）上验证浅色 spinner

### 7.2 禁用按钮样式
- [ ] 触发任何操作导致按钮禁用
- [ ] 验证按钮 opacity 降为 0.6
- [ ] 验证光标变为 not-allowed
- [ ] 验证鼠标悬停无效果
- [ ] 验证无法点击

### 7.3 验证状态样式
- [ ] 验证成功状态（绿色背景）
- [ ] 验证失败状态（红色背景）
- [ ] 验证验证中状态（蓝色背景）
- [ ] 验证信息状态（浅蓝色背景）
- [ ] 验证每种状态的文本颜色可读性
- [ ] 验证圆角和边框正确显示

### 7.4 按钮悬停效果
- [ ] 鼠标悬停在未禁用的按钮上
- [ ] 验证按钮轻微上移（translateY: -1px）
- [ ] 验证显示阴影（box-shadow）
- [ ] 点击按钮
- [ ] 验证按钮回到原位（translateY: 0）
- [ ] 验证阴影消失

### 7.5 Warning 按钮样式
- [ ] 定位 Stop All 按钮
- [ ] 验证黄色背景（#ffc107）
- [ ] 验证深色文本（#212529）
- [ ] 鼠标悬停
- [ ] 验证背景变深（#e0a800）
- [ ] 点击后验证禁用状态

### 7.6 重启行样式
- [ ] 执行 Restart 操作
- [ ] 验证表格行添加 `restarting` class
- [ ] 验证行背景变为浅黄色（#fff3cd）
- [ ] 验证行 opacity 降为 0.7
- [ ] 重启完成后验证样式恢复

### 7.7 动画效果
- [ ] 触发验证操作
- [ ] 验证验证消息淡入动画（validation-fade-in）
- [ ] 验证动画流畅，无卡顿
- [ ] 验证按钮状态转换平滑（0.2s transition）

---

## 8. 错误处理测试

### 8.1 网络错误
- [ ] 断开网络连接
- [ ] 尝试 Start 操作
- [ ] 验证显示错误 Toast
- [ ] 验证按钮状态恢复
- [ ] 重新连接网络

### 8.2 API 错误
- [ ] 触发一个会失败的操作（如启动未配置的 provider）
- [ ] 验证显示错误 Toast 或错误对话框
- [ ] 验证按钮状态恢复
- [ ] 验证没有无限 loading

### 8.3 超时处理
- [ ] 模拟慢速网络（Chrome DevTools -> Network -> Throttling）
- [ ] 触发操作
- [ ] 验证 spinner 持续显示直到完成或超时
- [ ] 验证超时后显示错误信息
- [ ] 验证按钮状态恢复

---

## 9. 浏览器兼容性测试

### 9.1 Chrome
- [ ] 所有功能正常
- [ ] CSS 样式正确
- [ ] 动画流畅

### 9.2 Firefox
- [ ] 所有功能正常
- [ ] CSS 样式正确
- [ ] 动画流畅

### 9.3 Safari（如果在 macOS 上）
- [ ] 所有功能正常
- [ ] CSS 样式正确
- [ ] 动画流畅

---

## 10. 性能测试

### 10.1 大量实例场景
- [ ] 创建 5+ 个实例
- [ ] 测试批量操作性能
- [ ] 验证 UI 无明显卡顿
- [ ] 验证状态刷新及时

### 10.2 快速操作切换
- [ ] 快速执行 Start → Stop → Restart 序列
- [ ] 验证每个操作正确完成
- [ ] 验证没有竞态条件
- [ ] 验证状态一致性

### 10.3 自动刷新性能
- [ ] 启用自动刷新（5秒间隔）
- [ ] 观察 5 分钟
- [ ] 验证 UI 响应正常
- [ ] 验证网络请求合理
- [ ] 验证内存使用稳定

---

## 11. 边界情况测试

### 11.1 空状态
- [ ] 无任何实例配置
- [ ] 验证 UI 显示 "No instances configured"
- [ ] 验证批量操作按钮隐藏

### 11.2 单实例场景
- [ ] 只有一个实例
- [ ] 测试所有操作
- [ ] 验证批量操作按钮行为正确

### 11.3 路径边界情况
- [ ] 输入空路径
- [ ] 验证 Validate 和 Save 按钮隐藏
- [ ] 输入只有空格的路径
- [ ] 验证被正确 trim
- [ ] 输入超长路径
- [ ] 验证 UI 不破坏

### 11.4 特殊字符路径
- [ ] 输入包含空格的路径
- [ ] 输入包含特殊字符的路径（~、$、等）
- [ ] 验证验证和保存正确处理

---

## 12. 回归测试

### 12.1 现有功能不受影响
- [ ] Add Instance 功能正常
- [ ] Edit Instance 功能正常
- [ ] Delete Instance 功能正常
- [ ] Models Directory 配置正常
- [ ] Detect Executable 功能正常
- [ ] Browse Executable 功能正常

### 12.2 自动刷新功能
- [ ] Toggle 开关正常工作
- [ ] 禁用自动刷新后验证不再刷新
- [ ] 启用自动刷新后验证每 5 秒刷新

### 12.3 错误处理
- [ ] 现有错误对话框正常显示
- [ ] 错误建议和详情正常显示
- [ ] Toast 通知正常工作

---

## 测试通过标准

- [ ] 所有测试项无失败
- [ ] 无控制台错误或警告
- [ ] UI 响应流畅，无卡顿
- [ ] 所有动画和过渡平滑
- [ ] 用户体验直观，无困惑
- [ ] 错误处理完善，有清晰提示

---

## 测试报告

### 测试日期: ________________

### 测试人员: ________________

### 通过项: ______ / 总计: ______

### 失败项详情:
1.
2.
3.

### 备注:


---

## 已知限制
- 批量操作为串行执行，大量实例时可能较慢
- 确认对话框使用原生 `confirm()`，样式无法自定义
- 验证失败时的错误消息依赖后端返回的格式

## 改进建议
- [ ] 考虑使用自定义模态对话框替代原生 confirm()
- [ ] 批量操作可考虑并行执行（需评估后端支持）
- [ ] 添加操作进度指示（x/n completed）
- [ ] 添加操作历史记录
