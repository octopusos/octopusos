# UI 手动验证清单 - Task #8

## 测试环境
- **WebUI URL**: http://127.0.0.1:9090
- **测试日期**: 2026-01-30
- **测试人员**: [待填写]
- **浏览器**: [待填写]

---

## A. 导航和布局验证

### A1. 侧边栏 (Sidebar)
- [ ] AgentOS logo 和版本号显示正常
- [ ] 导航项图标显示正常 (SVG icons)
- [ ] 导航项悬停效果正常
- [ ] 活动导航项高亮正常
- [ ] 滚动条样式正常

**验证截图**: ___

---

## B. 主要视图验证

### B1. Chat 视图
- [ ] 聊天输入框显示正常
- [ ] 发送按钮图标正常
- [ ] 消息历史显示正常
- [ ] 连接状态指示器显示 (彩色圆点)
  - [ ] 绿色 = 已连接
  - [ ] 黄色 = 连接中
  - [ ] 红色 = 断开连接
  - [ ] 橙色 = 重连中

**验证截图**: ___

### B2. Events 视图
- [ ] **Header 按钮**
  - [ ] Refresh 按钮 - `refresh` 图标显示
  - [ ] Clear 按钮 - `delete` 图标显示
  - [ ] Live Stream 开关显示正常
- [ ] **过滤器**
  - [ ] 过滤器输入框和下拉框正常
  - [ ] Reset 按钮功能正常
- [ ] **数据表格**
  - [ ] 事件列表显示正常
  - [ ] 事件类型图标显示 (如果有)
  - [ ] 时间戳格式正确
  - [ ] 分页控件图标正常
- [ ] **详情抽屉**
  - [ ] 点击事件打开详情抽屉
  - [ ] 关闭按钮 (close) 显示正常
  - [ ] JSON 查看器展开/折叠图标正常

**交互测试**:
- [ ] 点击 Refresh 按钮刷新数据
- [ ] 点击 Clear 按钮清除事件
- [ ] 开启 Live Stream 实时更新
- [ ] 点击事件查看详情

**验证截图**: ___

### B3. Tasks 视图
- [ ] **Header 按钮**
  - [ ] Refresh 按钮 - `refresh` 图标
  - [ ] Batch Create 按钮 - `add` 图标
  - [ ] Create Task 按钮 - `add` 图标
- [ ] **过滤器**
  - [ ] Task ID 输入框
  - [ ] Status 下拉框
  - [ ] Project 下拉框
  - [ ] Session ID 输入框
  - [ ] Time Range 选择器
  - [ ] Reset 按钮
- [ ] **任务列表**
  - [ ] 任务状态图标/徽章正确显示
    - [ ] Pending (待定)
    - [ ] Running (运行中) - 蓝色
    - [ ] Completed (完成) - 绿色
    - [ ] Failed (失败) - 红色
    - [ ] Cancelled (取消) - 灰色
  - [ ] 任务 ID 可点击
  - [ ] 操作按钮图标正常
- [ ] **详情抽屉**
  - [ ] 任务详情完整显示
  - [ ] 多个标签页图标正常
  - [ ] Decision Trace 图标显示
  - [ ] Plan 视图图标显示
  - [ ] 关闭按钮正常

**交互测试**:
- [ ] 创建新任务
- [ ] 点击任务查看详情
- [ ] 切换详情标签页
- [ ] 过滤任务列表

**验证截图**: ___

### B4. Projects 视图
- [ ] **Header**
  - [ ] Refresh 按钮
  - [ ] Create Project 按钮
- [ ] **项目卡片**
  - [ ] 项目图标显示
  - [ ] 项目状态指示器 (彩色圆点)
  - [ ] 操作按钮图标
    - [ ] Settings 图标
    - [ ] Delete 图标
- [ ] **项目详情**
  - [ ] Knowledge Base 状态图标
  - [ ] Context 配置图标

**交互测试**:
- [ ] 创建新项目
- [ ] 编辑项目设置
- [ ] 查看项目详情

**验证截图**: ___

### B5. Providers 视图
- [ ] **Header 按钮**
  - [ ] Auto-refresh 开关
  - [ ] Stop All 按钮 - `stop_circle` 图标
  - [ ] Restart All 按钮 - `restart_alt` 图标
  - [ ] Refresh All 按钮 - `refresh` 图标
- [ ] **Executable Configuration**
  - [ ] Detect 按钮 - `search` 图标
  - [ ] Browse 按钮 - `folder_open` 图标
  - [ ] Validate 按钮 - `check_circle` 图标
  - [ ] Save 按钮 - `save` 图标
- [ ] **Diagnostics**
  - [ ] Show Diagnostics 按钮 - `assessment` 图标
  - [ ] Health Check 按钮 - `health_and_safety` 图标
  - [ ] Copy Diagnostics 按钮 - `content_copy` 图标
- [ ] **Instance Cards**
  - [ ] 实例状态指示器 (彩色圆点)
    - [ ] 绿色 = 运行中
    - [ ] 红色 = 停止
    - [ ] 黄色 = 启动中
  - [ ] Start 按钮图标
  - [ ] Stop 按钮图标
  - [ ] Restart 按钮图标

**交互测试**:
- [ ] Detect 检测可执行文件
- [ ] Start 启动实例
- [ ] Stop 停止实例
- [ ] Restart 重启实例
- [ ] 查看 Diagnostics

**验证截图**: ___

### B6. Sessions 视图
- [ ] **Header**
  - [ ] Refresh 按钮
  - [ ] Create Session 按钮
- [ ] **Session 列表**
  - [ ] Session 卡片图标
  - [ ] 状态指示器
  - [ ] 操作按钮
- [ ] **详情抽屉**
  - [ ] Session 消息显示
  - [ ] 关闭按钮

**验证截图**: ___

### B7. Extensions 视图
- [ ] **Header**
  - [ ] Refresh 按钮
  - [ ] Install Extension 按钮
  - [ ] Create Extension 按钮
- [ ] **Extension Cards**
  - [ ] Extension 图标显示
  - [ ] 状态徽章显示
  - [ ] 操作按钮图标
    - [ ] Enable/Disable
    - [ ] Settings
    - [ ] Uninstall
- [ ] **Extension Wizard (如果打开)**
  - [ ] 步骤指示器图标
  - [ ] 表单输入框图标
  - [ ] 保存按钮图标

**验证截图**: ___

### B8. Models 视图
- [ ] **Header**
  - [ ] Refresh 按钮
  - [ ] Download Model 按钮
- [ ] **Model Cards**
  - [ ] Model 图标
  - [ ] 状态指示器
  - [ ] 下载进度条 (如果下载中)
  - [ ] 操作按钮图标
- [ ] **Model Parameters**
  - [ ] 参数配置图标
  - [ ] Save 按钮

**验证截图**: ___

### B9. Config 视图
- [ ] **Settings Sections**
  - [ ] Section 图标显示
  - [ ] Edit 按钮图标
  - [ ] Save 按钮图标
  - [ ] Cancel 按钮图标
- [ ] **Configuration Form**
  - [ ] 输入框图标
  - [ ] 下拉框图标
  - [ ] 开关按钮

**验证截图**: ___

### B10. Logs 视图
- [ ] **Header**
  - [ ] Refresh 按钮
  - [ ] Clear 按钮
  - [ ] Download 按钮
  - [ ] Level Filter 图标
- [ ] **Log Entries**
  - [ ] Log level 图标
    - [ ] Info - 蓝色
    - [ ] Warning - 黄色
    - [ ] Error - 红色
    - [ ] Debug - 灰色
  - [ ] 时间戳显示
  - [ ] 展开/折叠图标

**验证截图**: ___

---

## C. 特殊组件验证

### C1. 连接状态指示器 (Connection Status)
- [ ] **状态圆点显示正确**
  - [ ] `status-connected` - 绿色圆点 (#10B981)
  - [ ] `status-connecting` - 黄色圆点 (#F59E0B)
  - [ ] `status-disconnected` - 红色圆点 (#EF4444)
  - [ ] `status-reconnecting` - 橙色圆点 (#F97316)
- [ ] **动画效果**
  - [ ] 连接中显示脉动动画
  - [ ] 重连中显示脉动动画

**测试方法**:
1. 刷新页面观察连接过程
2. 停止 WebSocket 服务器观察断开状态
3. 重启服务器观察重连状态

**验证截图**: ___

### C2. Toast 通知
- [ ] **通知图标**
  - [ ] Success - `check_circle` 图标
  - [ ] Error - `error` 图标
  - [ ] Warning - `warning` 图标
  - [ ] Info - `info` 图标
- [ ] **关闭按钮**
  - [ ] Close 图标 (`close`)

**测试方法**: 执行操作触发通知 (如保存设置、创建任务等)

**验证截图**: ___

### C3. Modal 对话框
- [ ] **Modal Header**
  - [ ] 标题图标
  - [ ] 关闭按钮 (`close`)
- [ ] **Modal Body**
  - [ ] 内容图标正常
- [ ] **Modal Footer**
  - [ ] 确认按钮图标
  - [ ] 取消按钮图标

**验证截图**: ___

### C4. Data Table
- [ ] **表头**
  - [ ] 排序图标 (`arrow_upward`, `arrow_downward`)
  - [ ] 过滤图标 (`filter_list`)
- [ ] **分页**
  - [ ] First Page 图标
  - [ ] Previous 图标
  - [ ] Next 图标
  - [ ] Last Page 图标
- [ ] **行操作**
  - [ ] 编辑图标 (`edit`)
  - [ ] 删除图标 (`delete`)
  - [ ] 查看图标 (`visibility`)

**验证截图**: ___

### C5. JSON Viewer
- [ ] **展开/折叠图标**
  - [ ] Expand 图标 (`expand_more`)
  - [ ] Collapse 图标 (`expand_less`)
- [ ] **复制按钮**
  - [ ] Copy 图标 (`content_copy`)

**验证截图**: ___

---

## D. 交互功能测试

### D1. 点击操作
- [ ] Refresh 按钮可点击并刷新数据
- [ ] Search 按钮可点击并执行搜索
- [ ] Delete 按钮可点击并删除项目
- [ ] Edit 按钮可点击并打开编辑界面
- [ ] Save 按钮可点击并保存数据
- [ ] Cancel 按钮可点击并取消操作

### D2. 悬停效果
- [ ] 按钮悬停显示 tooltip
- [ ] 图标悬停改变颜色
- [ ] 列表项悬停显示高亮

### D3. 禁用状态
- [ ] 禁用按钮显示正确 (灰色、不可点击)
- [ ] 禁用按钮图标显示正确

---

## E. 空状态和错误状态

### E1. 空状态 (Empty State)
- [ ] 空任务列表显示 "No tasks" 消息和图标
- [ ] 空事件列表显示 "No events" 消息和图标
- [ ] 空会话列表显示 "No sessions" 消息和图标

**验证截图**: ___

### E2. 错误状态 (Error State)
- [ ] API 错误显示错误图标和消息
- [ ] 网络错误显示断连图标和消息
- [ ] 加载失败显示重试按钮

**验证截图**: ___

### E3. 加载状态 (Loading State)
- [ ] 加载中显示 spinner 或 loading 图标
- [ ] 加载完成后图标正确显示

**验证截图**: ___

---

## F. 响应式布局测试

### F1. 桌面端 (Desktop)
- [ ] 全屏显示正常 (1920x1080)
- [ ] 中等屏幕显示正常 (1366x768)
- [ ] 小屏幕显示正常 (1280x720)

### F2. 平板端 (Tablet)
- [ ] iPad 横屏显示正常
- [ ] iPad 竖屏显示正常

### F3. 移动端 (Mobile)
- [ ] 手机横屏显示正常
- [ ] 手机竖屏显示正常

---

## G. 浏览器兼容性测试

### G1. Chrome/Chromium
- [ ] Material Icons 加载正常
- [ ] 彩色状态圆点显示正常
- [ ] 所有交互功能正常

### G2. Firefox
- [ ] Material Icons 加载正常
- [ ] 彩色状态圆点显示正常
- [ ] 所有交互功能正常

### G3. Safari
- [ ] Material Icons 加载正常
- [ ] 彩色状态圆点显示正常
- [ ] 所有交互功能正常

### G4. Edge
- [ ] Material Icons 加载正常
- [ ] 彩色状态圆点显示正常
- [ ] 所有交互功能正常

---

## H. 性能测试

### H1. 页面加载
- [ ] 首次加载时间 < 3 秒
- [ ] Material Icons 字体加载时间 < 1 秒
- [ ] 无明显闪烁或重绘

### H2. 图标渲染
- [ ] 图标渲染流畅，无延迟
- [ ] 大量图标同时显示无性能问题
- [ ] 图标缩放清晰，无模糊

### H3. 交互响应
- [ ] 按钮点击响应时间 < 100ms
- [ ] 图标切换动画流畅 (60fps)
- [ ] 滚动平滑，无卡顿

---

## I. 可访问性测试

### I1. 键盘导航
- [ ] Tab 键可遍历所有可交互元素
- [ ] Enter 键可激活按钮
- [ ] Esc 键可关闭 Modal/Drawer

### I2. 屏幕阅读器
- [ ] 图标有适当的 aria-label
- [ ] 按钮有适当的 aria-label
- [ ] 状态变化有适当的提示

### I3. 对比度
- [ ] 图标颜色对比度符合 WCAG AA 标准
- [ ] 状态颜色易于区分 (色盲友好)

---

## J. 已知问题和限制

### J1. 已知限制
- [ ] Material Icons 依赖 Google CDN (需要网络连接)
- [ ] 某些图标在不同字体大小下可能对齐问题

### J2. 待修复问题
(从测试中发现的问题记录在此)

1. ___
2. ___
3. ___

---

## K. 测试总结

### K1. 通过率统计
- **总测试项**: [待统计]
- **通过项**: [待统计]
- **失败项**: [待统计]
- **通过率**: [待计算]%

### K2. 严重程度分类
- **P0 (严重)**: [数量] 个
- **P1 (重要)**: [数量] 个
- **P2 (轻微)**: [数量] 个

### K3. 总体评估
- [ ] **优秀** (通过率 >= 95%)
- [ ] **良好** (通过率 >= 85%)
- [ ] **合格** (通过率 >= 75%)
- [ ] **需要改进** (通过率 < 75%)

### K4. 发布建议
- [ ] **可以发布** - 所有 P0 问题已修复，UI 功能完整
- [ ] **需要修复后发布** - 存在 P0 问题，需要修复
- [ ] **不建议发布** - 存在多个严重问题

---

## L. 附加验证

### L1. 代码审查
- [x] CSS 文件包含所有状态颜色定义
- [x] JavaScript 文件正确引用 Material Icons
- [x] HTML 文件正确加载 Material Icons CDN
- [x] 图标尺寸规范统一 (md-14, md-16, md-18, etc.)

### L2. 文档完整性
- [x] Material Icons 使用方式已文档化
- [x] 状态颜色规范已文档化
- [x] 图标命名规范已文档化

---

## M. 截图附件

### M1. 主要视图截图
1. Chat 视图: ___
2. Events 视图: ___
3. Tasks 视图: ___
4. Projects 视图: ___
5. Providers 视图: ___
6. Sessions 视图: ___
7. Extensions 视图: ___
8. Models 视图: ___
9. Config 视图: ___
10. Logs 视图: ___

### M2. 特殊状态截图
1. 连接状态 (各种颜色): ___
2. Toast 通知: ___
3. Modal 对话框: ___
4. 空状态: ___
5. 错误状态: ___
6. 加载状态: ___

### M3. 浏览器对比截图
1. Chrome: ___
2. Firefox: ___
3. Safari: ___
4. Edge: ___

---

## N. 测试人员签名

- **测试人员**: ___
- **测试日期**: ___
- **测试时长**: ___
- **签名**: ___

---

**报告生成时间**: 2026-01-30
**文档版本**: v1.0
