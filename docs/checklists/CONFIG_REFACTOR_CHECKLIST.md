# Config 页面统一改造 Checklist

**目标**：让 Config 页面从"技术信息面板"升级为 AgentOS Control Surface 的一部分

---

## 📊 改造前后对比

| 维度 | 改造前 | 改造后 |
|------|--------|--------|
| **信息组织** | Structured / Raw JSON 并列 Tab | Structured 默认视图 + Raw JSON Modal |
| **Settings 展示** | JsonViewer（开发者视角） | Property Grid（操作者视角） |
| **Env Variables** | 全量展示，无过滤 | Filter + 默认 20 条 + Show all |
| **Page Header** | 标题 + 按钮 | 标题 + Subtitle (read-only) + 按钮 |
| **视觉风格** | 独立样式 | 和 Runtime / Providers 一致 |

---

## ✅ P0 - 核心改造（必须完成）

### 1. 移除 Tab 系统

- [ ] 删除 `config-tabs` DOM 结构
  - **文件**：`ConfigView.js` L33-40
  - **行动**：完全移除 tab 导航

- [ ] 删除 `currentTab` 状态
  - **文件**：`ConfigView.js` L12
  - **行动**：移除 `this.currentTab = 'structured'`

- [ ] 删除 `switchTab()` 方法
  - **文件**：`ConfigView.js` L122-137
  - **行动**：完全移除该方法

- [ ] 删除 Tab 切换事件监听
  - **文件**：`ConfigView.js` L68-76
  - **行动**：移除 tab 点击事件绑定

### 2. Raw JSON 改为 Modal

- [ ] 在 PageHeader 添加「View Raw JSON」按钮
  - **位置**：`header-actions` 区域
  - **图标**：`<span class="material-icons">code</span>`
  - **样式**：`btn-secondary`

- [ ] 创建 Modal 结构
  - **参考**：ProvidersView 的 Modal 实现
  - **包含**：Modal overlay + Modal content + Close button

- [ ] `renderRawView()` 改为 `showRawJsonModal()`
  - **行为**：打开 Modal，在 Modal 中渲染 JsonViewer
  - **关闭**：点击 overlay 或 close 按钮

- [ ] 测试 Modal 交互
  - [ ] 打开 Modal
  - [ ] ESC 键关闭（如果支持）
  - [ ] 点击 overlay 关闭
  - [ ] Copy to Clipboard 按钮工作

### 3. 增强 PageHeader

- [ ] 添加 subtitle
  ```html
  <div class="view-header">
      <div>
          <h2>Configuration</h2>
          <p class="text-sm text-gray-600 mt-1">
              Runtime configuration snapshot (read-only)
          </p>
      </div>
      <div class="header-actions">...</div>
  </div>
  ```

- [ ] 调整按钮顺序和样式
  - [ ] Refresh（`btn-refresh`）
  - [ ] View Raw JSON（`btn-secondary`）
  - [ ] Download（`btn-secondary`）

### 4. Application Settings 改为 Property Grid

- [ ] 移除 `json-viewer-container-settings`
  - **文件**：`ConfigView.js` L177, L244-247

- [ ] 使用 `detail-grid` 结构（和 RuntimeView 一致）
  ```html
  <div class="detail-grid">
      <div class="detail-item">
          <span class="detail-label">Language</span>
          <span class="detail-value">en</span>
      </div>
  </div>
  ```

- [ ] 添加 `formatLabel()` 辅助方法
  - **功能**：将 `snake_case` 转为 `Title Case`
  - **示例**：`log_level` → `Log Level`

- [ ] 更新 read-only 提示
  - **文案**：🔒 Settings are read-only. Edit the config file to make changes.
  - **位置**：Section 底部

---

## ✅ P1 - 增强功能（强烈推荐）

### 5. Environment Variables 过滤与分页

- [ ] 添加 Filter 输入框
  - **位置**：Section header 右侧
  - **样式**：`input-sm w-64`
  - **Placeholder**：🔍 Filter variables...

- [ ] 实现 client-side filter
  - [ ] 监听 `input` 事件
  - [ ] 根据 `data-env-key` 过滤表格行
  - [ ] 更新 count badge（显示 "X of Y variables"）

- [ ] 默认显示前 20 条
  - **状态**：`this.envLimit = 20`
  - **逻辑**：`allEnvs.slice(0, this.envLimit)`

- [ ] 添加「Show all」按钮
  - **显示条件**：`totalCount > this.envLimit`
  - **点击行为**：`this.envLimit = totalCount` + 重新渲染

- [ ] 测试过滤功能
  - [ ] 输入搜索词，表格正确过滤
  - [ ] count badge 实时更新
  - [ ] 清空搜索词，恢复所有行
  - [ ] "Show all" 按钮展示全部变量

### 6. 视觉风格统一

- [ ] Section class 对齐
  - **保持**：`config-section` + `config-section-title`
  - **或改为**：`detail-section` + `detail-section-title`（完全对齐 RuntimeView）

- [ ] 检查间距和密度
  - [ ] Section 间距：24px
  - [ ] Card padding：16-20px
  - [ ] 行高：32-36px

- [ ] Icon 使用统一
  - [ ] Refresh: `refresh`
  - [ ] Download: `download`（原为 `save`）
  - [ ] View Raw: `code`
  - [ ] Copy: `content_copy`

---

## ✅ P2 - 细节优化（可选）

### 7. System Overview 增强

- [ ] 添加 "Last Loaded Time"
  - **值**：`new Date().toLocaleString()`

- [ ] 添加 "Runtime Mode"
  - **值**：`Local (Open)` 或动态读取

### 8. Environment Variables 分类提示

- [ ] 添加 category hint
  - **分类**：Runtime / Provider / System / User
  - **展示**：badge 或 tooltip

- [ ] 值的 mask/unmask
  - **目标**：敏感值默认 masked
  - **交互**：点击 eye icon 切换

### 9. Deep Link 预留

- [ ] 在 Env Variable 行添加 "Used by" hint
  - **示例**：`OLLAMA_HOST → Used by Ollama`
  - **当前**：仅 UI，不实现跳转逻辑

---

## 🧪 测试清单

### 功能测试

- [ ] 页面加载正常，显示所有 Section
- [ ] Refresh 按钮重新加载配置
- [ ] View Raw JSON 打开 Modal，显示完整 JSON
- [ ] Modal 中 Copy to Clipboard 工作
- [ ] Download 按钮下载 JSON 文件
- [ ] Environment Variables Filter 正常过滤
- [ ] "Show all" 按钮展示全部变量
- [ ] Quick Actions 跳转到 Providers / Selfcheck

### 视觉测试

- [ ] PageHeader 和 RuntimeView 风格一致
- [ ] Card 间距和密度统一
- [ ] Property Grid 清晰易读
- [ ] Environment Variables 表格整洁
- [ ] Modal 样式和其他页面一致

### 边界测试

- [ ] 无配置数据时显示友好提示
- [ ] API 错误时显示错误信息
- [ ] Environment Variables 为空时不显示该 Section
- [ ] Filter 无匹配结果时显示 "No results"

---

## 📂 文件清单

### 需要修改的文件

1. **`agentos/webui/static/js/views/ConfigView.js`**
   - 主要改造文件
   - 约 300 行 → 预计 350-400 行（增加 filter 逻辑）

2. **`agentos/webui/static/css/views/config.css`**（如果存在）
   - 检查是否需要调整样式
   - 确保和 `runtime.css` / `providers.css` 一致

3. **`agentos/webui/api/config.py`**（可选）
   - 如果需要后端支持分类 hint，可扩展 API
   - 当前无需修改

### 参考文件

- `agentos/webui/static/js/views/RuntimeView.js`（视觉风格参考）
- `agentos/webui/static/js/views/ProvidersView.js`（Modal 实现参考）

---

## 🚀 实施建议

### 分阶段提交

**Commit 1: 移除 Tab 系统，Raw JSON 改为 Modal**
- P0-1, P0-2, P0-3
- 影响：结构大调整，建议单独提交

**Commit 2: Application Settings 改为 Property Grid**
- P0-4
- 影响：视觉变化，可独立验证

**Commit 3: Environment Variables 过滤与分页**
- P1-5
- 影响：交互增强，可独立测试

**Commit 4: 视觉风格统一**
- P1-6
- 影响：CSS 调整，可最后统一

### 回归测试

- [ ] 测试所有其他 View（确保没有引入 CSS 冲突）
- [ ] 测试移动端响应式（如果支持）
- [ ] 测试 dark mode（如果支持）

---

## ✅ 完成标准

Config 页面改造完成的标志：

1. **结构清晰**：Structured View 为主，Raw JSON 为 Modal
2. **信息易读**：Property Grid + 过滤表格，无技术 dump 感
3. **视觉统一**：和 Runtime / Providers 页面一眼看上去是同一产品
4. **交互流畅**：Filter、Show all、Modal 交互无卡顿
5. **语义明确**：read-only 提示清晰，用户知道这是"查看"不是"编辑"

---

**预计工作量**：2-4 小时（含测试）

**优先级**：High（Config 是 Control Surface 的核心入口之一）

**影响范围**：仅 Config 页面，无其他页面依赖

---

## 📞 需要帮助？

如果实施过程中遇到问题：

1. **结构不确定**：参考 `config_view_refactor_skeleton.js`
2. **样式冲突**：对比 RuntimeView 和 ProvidersView 的 CSS
3. **Modal 实现**：直接复用 ProvidersView 的 Modal 代码
4. **Filter 逻辑**：使用 `data-*` 属性 + `display: none`（最简单）

祝改造顺利！🎉
