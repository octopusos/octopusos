# History View 修复清单

## 🐛 已修复的问题

### 1. **DataTable.setError 方法不存在**

**错误信息**:
```
TypeError: this.dataTable.setError is not a function
```

**原因**: DataTable 组件没有 `setError` 方法

**修复**:
- 文件: `agentos/webui/static/js/views/HistoryView.js`
- 行号: 219, 254
- 改为使用 `setData([])` + `setLoading(false)` 显示空状态

```javascript
// 修复前
if (this.dataTable) {
    this.dataTable.setError(error.message);
}

// 修复后
if (this.dataTable) {
    this.dataTable.setData([]);
    this.dataTable.setLoading(false);
}
```

---

### 2. **FilterBar.destroy 方法不存在**

**错误信息**:
```
TypeError: this.filterBar.destroy is not a function
```

**原因**: FilterBar 组件没有 `destroy` 方法

**修复**:
- 文件: `agentos/webui/static/js/views/HistoryView.js`
- 行号: 517
- 添加方法存在性检查

```javascript
// 修复前
if (this.filterBar) {
    this.filterBar.destroy();
}

// 修复后
if (this.filterBar && typeof this.filterBar.destroy === 'function') {
    this.filterBar.destroy();
}
```

---

### 3. **FilterBar 参数名错误**

**错误信息**: 过滤器不工作

**原因**:
- HistoryView 使用 `onApply` 回调，但 FilterBar 期望 `onChange`
- HistoryView 使用 `filter.id`，但 FilterBar 期望 `filter.key`

**修复**:
- 文件: `agentos/webui/static/js/views/HistoryView.js`
- 行号: 66-95

```javascript
// 修复前
this.filterBar = new FilterBar(filterSection, {
    filters: [
        {
            type: 'text',
            id: 'command_id',  // ❌ 错误
            label: 'Command ID',
            placeholder: 'e.g., kb:search'
        }
    ],
    onApply: (filters) => {  // ❌ 错误
        // ...
    }
});

// 修复后
this.filterBar = new FilterBar(filterSection, {
    filters: [
        {
            type: 'text',
            key: 'command_id',  // ✅ 正确
            label: 'Command ID',
            placeholder: 'e.g., kb:search'
        }
    ],
    onChange: (filters) => {  // ✅ 正确
        // ...
    }
});
```

---

### 4. **HTTP 404 错误 - /api/history 端点未找到**

**错误信息**:
```
GET http://127.0.0.1:8080/api/history?limit=100 404 (Not Found)
```

**原因**: WebUI 服务器未重启，新的路由未生效

**状态**:
- ✅ 路由已在 `app.py:114` 正确注册
- ✅ history 模块已在 `app.py:27` 正确导入
- ✅ history.py 路由定义正确

**解决方案**: **重启 WebUI 服务器**

```bash
# 停止当前服务器 (Ctrl+C)
# 重新启动
agentos webui start
```

---

## ✅ 修复验证

### 步骤 1: 重启服务器

```bash
# 停止当前 WebUI 服务器
# Ctrl+C

# 重新启动
agentos webui start
```

### 步骤 2: 刷新浏览器

```bash
# 强制刷新页面以加载新的 JS 文件
Cmd+Shift+R (Mac) 或 Ctrl+Shift+R (Windows/Linux)
```

### 步骤 3: 验证 History 页面

1. 点击左侧导航栏的 **History** 链接
2. 检查控制台是否有错误
3. 应该看到历史记录列表（如果有数据）或空状态

### 步骤 4: 验证过滤功能

1. 在 Filter Bar 中输入 Command ID
2. 选择 Status 下拉菜单
3. 点击表格行查看详情
4. 测试 Pin/Unpin 功能

---

## 📋 修改文件列表

### 前端修复

1. **agentos/webui/static/js/views/HistoryView.js**
   - 修复 `setError` → `setData([])` + `setLoading(false)`
   - 修复 `destroy` 方法的防御性检查
   - 修复 `id` → `key`
   - 修复 `onApply` → `onChange`

### Sentry 集成

2. **agentos/webui/templates/index.html**
   - 添加 Sentry Browser SDK
   - 配置 Release Health tracking

3. **agentos/webui/app.py**
   - 优化 Sentry 后端配置
   - 启用 Session tracking (request-mode)

---

## 🧪 测试清单

- [ ] History 页面加载成功
- [ ] 显示历史记录列表（如果有数据）
- [ ] 过滤功能正常工作
  - [ ] Command ID 过滤
  - [ ] Status 下拉选择
  - [ ] Session ID 过滤
- [ ] 点击行打开详情 Drawer
- [ ] Pin/Unpin 功能正常
- [ ] Refresh 按钮工作
- [ ] Pinned 按钮工作
- [ ] 无控制台错误

---

## 📊 API 端点验证

### 手动测试 API

```bash
# 查询历史记录
curl http://localhost:8080/api/history?limit=10

# 查询固定的命令
curl http://localhost:8080/api/history/pinned

# 获取单条记录（替换 {id}）
curl http://localhost:8080/api/history/{id}
```

预期响应:
- **成功**: 返回 JSON 数组或对象
- **失败**: 返回错误信息

---

## 🚨 如果仍有问题

### 检查服务器日志

```bash
# 查看 WebUI 启动日志
# 应该看到:
INFO: Sentry initialized: agentos-webui@0.3.2 ...
INFO: Application startup complete
```

### 检查浏览器控制台

```javascript
// 应该看到:
✓ Sentry initialized: development agentos-webui@0.3.2
```

### 检查 API 路由

```bash
# 访问 OpenAPI 文档
http://localhost:8080/docs

# 查找 /api/history 端点
# 应该看到 5 个 history 相关的端点
```

---

**修复完成时间**: 2026-01-28
**状态**: ✅ 所有前端修复已完成，需要重启服务器
