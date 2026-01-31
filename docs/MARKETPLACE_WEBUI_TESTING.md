# Marketplace WebUI 浏览器测试指南

## 测试环境准备

### 1. 启动 AgentOS WebUI

```bash
# 确保在 AgentOS 项目根目录
cd /Users/pangge/PycharmProjects/AgentOS

# 启动 WebUI
agentos webui
```

WebUI 应该在 `http://localhost:5000` 启动。

### 2. 确保后端 API 正常运行

验证以下 API 端点可访问：
- `GET /api/mcp/marketplace/packages` - Package 列表
- `GET /api/mcp/marketplace/packages/{id}` - Package 详情
- `GET /api/mcp/marketplace/governance-preview/{id}` - 治理预览
- `POST /api/mcp/marketplace/attach` - Attach MCP

## 测试场景

### 场景 1: 访问 Marketplace 列表页

#### 步骤
1. 打开浏览器访问 `http://localhost:5000`
2. 在左侧导航栏找到 **Settings** 部分
3. 点击 **MCP Marketplace**

#### 预期结果
- ✅ 页面标题显示 "MCP Marketplace"
- ✅ 显示搜索框和过滤器
- ✅ 加载 package 卡片列表
- ✅ 每个卡片显示:
  - Package 名称和作者
  - 简短描述
  - Tools 数量
  - Trust Tier 徽章
  - 连接状态（Connected / Not Connected）
  - "View Details" 按钮

#### 截图参考
```
+--------------------------------------------------+
| MCP Marketplace                      [Refresh]   |
| Discover and attach Model Context Protocol servers|
+--------------------------------------------------+
| [Search: ___________] [Filter: All ▼]            |
+--------------------------------------------------+
| +----------------+  +----------------+  +-------+ |
| | Echo Math      |  | GitHub         |  | ...   | |
| | AgentOS Team   |  | Smithery.ai    |  |       | |
| | 2 tools        |  | 15 tools       |  |       | |
| | [T1] Local MCP |  | [T3] Cloud MCP |  |       | |
| | ✅ Connected   |  | ⚪ Not Connected|  |       | |
| | [View Details] |  | [View Details] |  |       | |
| +----------------+  +----------------+  +-------+ |
+--------------------------------------------------+
```

### 场景 2: 测试搜索功能

#### 步骤
1. 在 Marketplace 列表页
2. 在搜索框输入 "echo"
3. 观察列表变化

#### 预期结果
- ✅ 列表实时过滤，只显示名称/作者/描述包含 "echo" 的 packages
- ✅ 清空搜索框后恢复完整列表

### 场景 3: 测试过滤器

#### 步骤
1. 点击过滤器下拉菜单
2. 选择 "Connected"
3. 观察列表变化
4. 选择 "Not Connected"
5. 选择 "All"

#### 预期结果
- ✅ 选择 "Connected" 时只显示已连接的 packages
- ✅ 选择 "Not Connected" 时只显示未连接的 packages
- ✅ 选择 "All" 时显示所有 packages

### 场景 4: 查看 Package 详情

#### 步骤
1. 在列表页点击任意 package 的 "View Details" 按钮

#### 预期结果
- ✅ 跳转到详情页
- ✅ 显示 "← Back to Marketplace" 链接
- ✅ 显示 package 完整信息:
  - 名称和版本
  - 作者、License、Repository
  - Tags
  - 完整描述
- ✅ 显示 "Tools (N)" 区域（默认可能收起）
- ✅ 显示 "Governance Preview" 区域（默认可能收起）
- ✅ 显示连接状态和操作按钮

### 场景 5: 查看 Tools 列表

#### 步骤
1. 在详情页点击 "Tools (N)" 标题

#### 预期结果
- ✅ 工具列表展开
- ✅ 每个工具显示:
  - 工具名称
  - 描述
  - Input Schema
  - Side Effects（如果有）
- ✅ 再次点击可收起

### 场景 6: 查看 Governance Preview

#### 步骤
1. 在详情页点击 "Governance Preview" 标题

#### 预期结果
- ✅ 治理信息展开，显示:
  - Trust Tier（带颜色徽章）
  - Risk Level（带颜色徽章）
  - Default Quota（calls/min, concurrent）
  - Requires Admin Token
  - Gate Warnings（如果有，橙色警告样式）
- ✅ 再次点击可收起

#### 截图参考
```
+-----------------------------------------------------------+
| Governance Preview                                 [展开▼] |
+-----------------------------------------------------------+
| Trust Tier: [T1 - Local MCP] (蓝色徽章)                   |
| Risk Level: [MEDIUM] (黄色徽章)                          |
| Default Quota: 500 calls/min, 5 concurrent                |
| Requires Admin Token: No                                  |
| Gate Warnings:                                            |
| ⚠️ No side effects declared - may need policy config      |
+-----------------------------------------------------------+
```

### 场景 7: Attach 流程（未连接的 Package）

#### 步骤
1. 在详情页（未连接状态）
2. 点击 "Attach to AgentOS" 按钮

#### 预期结果
- ✅ 弹出确认对话框
- ✅ 对话框显示:
  - Package 名称和作者
  - "This will:" 列表（Add MCP, Apply Trust Tier, Apply quota）
  - ⚠️ 黄色警告框: "MCP will be DISABLED after attach"
  - 💡 蓝色提示框: "You will need to:" 后续步骤
  - Advanced: Override Trust Tier 下拉菜单（可选）
  - "Cancel" 和 "Attach" 按钮

#### 截图参考
```
+-------------------------------------------+
| Attach MCP to AgentOS                 [×] |
+-------------------------------------------+
| Echo Math Server                          |
| by AgentOS Team                           |
|                                           |
| This will:                                |
| • Add MCP to your AgentOS capabilities    |
| • Apply Trust Tier: T1                    |
| • Apply default quota profile             |
|                                           |
| ⚠️ MCP will be DISABLED after attach      |
|                                           |
| 💡 You will need to:                      |
| 1. Review in Capabilities → MCP           |
| 2. Enable using CLI: agentos mcp enable...|
| 3. Configure admin token if needed        |
|                                           |
| Advanced: Override Trust Tier             |
| [Use Default (T1) ▼]                      |
|                                           |
| [Cancel]  [Attach]                        |
+-------------------------------------------+
```

### 场景 8: Attach 成功（模拟）

#### 步骤
1. 在确认对话框点击 "Attach" 按钮

#### 预期结果
- ✅ 对话框关闭
- ✅ 显示通知: "MCP attached successfully!"
- ✅ 页面刷新显示成功状态:
  - ✅ 绿色成功消息框
  - Package 信息（名称、Server ID、状态、Trust Tier）
  - ⚠️ 黄色警告框: "MCP is NOT enabled yet"
  - 后续步骤列表:
    1. "Review in Capabilities → MCP" + [Go to Capabilities] 按钮
    2. "Enable using CLI" + 命令代码块
    3. "Test the connection" + 命令代码块
  - "Back to Marketplace" 按钮

#### 截图参考
```
+-------------------------------------------+
| ✅ MCP Attached Successfully               |
+-------------------------------------------+
| Package: Echo Math Server                 |
| Server ID: echo-math                      |
| Status: Attached (Disabled)               |
| Trust Tier: T1                            |
|                                           |
| ⚠️ Important: MCP is NOT enabled yet      |
|                                           |
| Next Steps:                               |
| 1. Review in Capabilities → MCP           |
|    [Go to Capabilities]                   |
|                                           |
| 2. Enable using CLI:                      |
|    $ agentos mcp enable echo-math         |
|                                           |
| 3. Test the connection                    |
|    $ agentos mcp test echo-math           |
|                                           |
| [Back to Marketplace]                     |
+-------------------------------------------+
```

### 场景 9: 已连接的 Package

#### 步骤
1. 查看已连接状态的 package 详情

#### 预期结果
- ✅ 显示绿色成功消息: "MCP Already Connected"
- ✅ 显示管理指导:
  - "View in Capabilities → MCP Servers"
  - "Configure settings and admin tokens"
  - "Monitor usage and governance"
  - [Go to Capabilities] 按钮
- ✅ 没有 "Attach" 按钮

### 场景 10: 返回 Marketplace

#### 步骤
1. 在详情页点击 "← Back to Marketplace"
2. 或在成功页面点击 "Back to Marketplace"

#### 预期结果
- ✅ 返回 Marketplace 列表页
- ✅ 列表状态保持（搜索词、过滤器）

### 场景 11: 导航状态

#### 步骤
1. 访问 Marketplace
2. 查看左侧导航栏

#### 预期结果
- ✅ "MCP Marketplace" 导航项高亮显示
- ✅ 刷新页面后导航状态保持

### 场景 12: 响应式设计

#### 步骤
1. 调整浏览器窗口大小
2. 在不同设备模式下查看（Chrome DevTools）

#### 预期结果
- ✅ 在较小屏幕上，卡片网格变为单列
- ✅ 搜索和过滤器垂直排列
- ✅ 所有内容可见且可操作

## 错误处理测试

### 场景 13: API 错误

#### 步骤
1. 停止后端 API
2. 访问 Marketplace

#### 预期结果
- ✅ 显示错误状态
- ✅ 错误消息清晰
- ✅ 提供 "Retry" 按钮

### 场景 14: Package 不存在

#### 步骤
1. 手动修改 URL 访问不存在的 package
2. 或在 sessionStorage 中设置无效的 package ID

#### 预期结果
- ✅ 显示错误页面
- ✅ 提供 "Back to Marketplace" 按钮

## 样式和交互测试

### 场景 15: 卡片悬停效果

#### 步骤
1. 在列表页悬停在 package 卡片上

#### 预期结果
- ✅ 卡片有阴影效果
- ✅ 卡片略微上浮（translateY）

### 场景 16: Trust Tier 徽章颜色

#### 步骤
1. 查看不同 Trust Tier 的 packages

#### 预期结果
- ✅ T0: 绿色（Local Extension）
- ✅ T1: 蓝色（Local MCP）
- ✅ T2: 黄色（Remote MCP）
- ✅ T3: 红色（Cloud MCP）

### 场景 17: 连接状态指示器

#### 步骤
1. 查看已连接和未连接的 packages

#### 预期结果
- ✅ Connected: 绿色背景 + ✓ 图标
- ✅ Not Connected: 灰色背景 + ○ 图标

## 浏览器兼容性测试

测试以下浏览器:
- [ ] Chrome (最新版本)
- [ ] Firefox (最新版本)
- [ ] Safari (最新版本)
- [ ] Edge (最新版本)

## 性能测试

### 场景 18: 大量 Packages

#### 步骤
1. 加载包含 50+ packages 的列表
2. 测试搜索和过滤性能

#### 预期结果
- ✅ 列表加载流畅
- ✅ 搜索实时响应
- ✅ 过滤切换无延迟

## 测试报告模板

```markdown
# Marketplace WebUI 浏览器测试报告

测试日期: YYYY-MM-DD
测试人: [姓名]
浏览器: Chrome/Firefox/Safari/Edge [版本]

## 测试结果总览
- 总测试场景: 18
- 通过: X
- 失败: Y
- 跳过: Z

## 详细测试结果

### 场景 1: 访问 Marketplace 列表页
- 状态: ✅ 通过 / ❌ 失败
- 备注: [如有异常，请描述]

### 场景 2: 测试搜索功能
- 状态: ✅ 通过 / ❌ 失败
- 备注: [如有异常，请描述]

...（依次列出所有场景）

## 发现的问题

### 问题 1: [问题标题]
- 严重程度: 严重/中等/轻微
- 复现步骤:
  1. ...
  2. ...
- 预期结果: ...
- 实际结果: ...
- 截图: [如有]

## 建议改进

1. ...
2. ...

## 总体评价

[对 Marketplace WebUI 的整体评价]
```

## 快速验证脚本

如果需要快速验证 API 是否正常工作，可以使用以下 curl 命令:

```bash
# 测试 packages 列表 API
curl http://localhost:5000/api/mcp/marketplace/packages

# 测试 package 详情 API（假设有 ID 为 echo-math 的 package）
curl http://localhost:5000/api/mcp/marketplace/packages/echo-math

# 测试治理预览 API
curl http://localhost:5000/api/mcp/marketplace/governance-preview/echo-math

# 测试 attach API（POST 请求）
curl -X POST http://localhost:5000/api/mcp/marketplace/attach \
  -H "Content-Type: application/json" \
  -d '{"package_id": "echo-math"}'
```

## 注意事项

1. **确保后端 API 已实现**: 前端依赖后端 API，确保 `mcp_marketplace.py` 已部署并运行
2. **检查 CORS 设置**: 如果遇到跨域问题，检查 Flask CORS 配置
3. **浏览器缓存**: 测试时如果样式或脚本未更新，尝试硬刷新（Ctrl+Shift+R / Cmd+Shift+R）
4. **控制台日志**: 打开浏览器开发者工具查看控制台输出，有助于调试问题

## 自动化测试建议

未来可以使用以下工具进行自动化测试:
- Selenium WebDriver（功能测试）
- Cypress（端到端测试）
- Jest + React Testing Library（组件测试）
- Lighthouse（性能和可访问性测试）

---

**测试完成后，请填写测试报告并提交！** 🧪
