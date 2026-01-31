# Phase 4 WebUI 快速参考指南

## 新增文件

### JavaScript 组件
```
agentos/webui/static/js/components/CreateTaskWizard.js
```
- 4步任务创建向导
- 自动加载项目和仓库
- 验收标准动态管理
- 规格冻结功能

### CSS 样式
```
agentos/webui/static/css/project-v31.css
```
- 向导样式（步骤指示器、表单）
- 项目信息框和状态 badge
- 响应式布局
- 模态框和 Tabs

## 修改文件

### TasksView.js
**修改内容**:
1. `createTask()` 方法 - 使用新向导替代旧表单
2. `renderTaskDetail()` - 添加项目信息和规格状态显示
3. `setupTaskDetailActions()` - 添加冻结规格和标记 ready 按钮
4. 新增方法:
   - `freezeTaskSpec(taskId)` - 冻结任务规格
   - `markTaskReady(taskId)` - 标记任务为 ready
   - `escapeHtml(text)` - HTML 转义

### index.html
**修改内容**:
1. 添加 CSS: `<link href="/static/css/project-v31.css?v=1">`
2. 添加 JS: `<script src="/static/js/components/CreateTaskWizard.js?v=1">`

## 使用方法

### 创建任务（向导模式）

```javascript
// 在 TasksView 中
this.container.querySelector('#tasks-create').addEventListener('click', () => {
    this.createTask();
});

// createTask() 自动使用向导
async createTask() {
    const wizard = new CreateTaskWizard(wizardContainer, {
        defaultProjectId: this.currentFilters.project_id,
        onComplete: (taskId) => {
            showToast('Task created', 'success');
            this.loadTasks(true);
        },
        onCancel: () => {
            backdrop.remove();
        }
    });
}
```

### 冻结规格

```javascript
// 在任务详情中
async freezeTaskSpec(taskId) {
    const result = await apiClient.post(
        `/api/tasks/${taskId}/spec/freeze`,
        null,
        { requestId: `freeze-spec-${taskId}` }
    );
    if (result.ok) {
        showToast('Specification frozen', 'success');
        await this.showTaskDetail(taskId);
    }
}
```

### 标记为 Ready

```javascript
async markTaskReady(taskId) {
    const result = await apiClient.patch(
        `/api/tasks/${taskId}`,
        { status: 'ready' },
        { requestId: `mark-ready-${taskId}` }
    );
    if (result.ok) {
        showToast('Task marked as ready', 'success');
        await this.showTaskDetail(taskId);
    }
}
```

## 向导步骤

### Step 1: 基本信息
- **标题** (必填): 任务名称
- **意图** (可选): 详细描述
- **项目** (必填): 选择所属项目

### Step 2: 仓库绑定
- **仓库** (可选): 选择项目中的仓库
- **工作目录** (可选): 相对路径

### Step 3: 验收标准
- 添加验收条件（至少 1 条）
- 可动态添加/删除

### Step 4: 冻结规格
- 查看任务摘要
- 点击 "Freeze Spec" 完成创建

## API 端点

### 任务相关
```
POST   /api/tasks                    创建任务
POST   /api/tasks/{id}/spec/freeze   冻结规格
PATCH  /api/tasks/{id}               更新任务（含状态）
GET    /api/tasks?project_id=xxx     按项目过滤
```

### 项目相关
```
GET    /api/projects                 列出项目
GET    /api/projects/{id}            项目详情
POST   /api/projects                 创建项目
GET    /api/projects/{id}/repos      项目仓库
```

## CSS 类名

### 向导样式
```css
.wizard-container          向导容器
.wizard-steps              步骤指示器
.wizard-step               单个步骤
.wizard-step.active        当前步骤
.wizard-step.completed     已完成步骤
.wizard-body               向导内容区
.wizard-footer             向导底部按钮
```

### 表单样式
```css
.form-group               表单组
.form-control             输入框/选择框
.form-hint                提示文本
.form-error               错误提示
```

### 状态样式
```css
.spec-status-badge        规格状态徽章
.spec-status-badge.frozen 已冻结
.spec-status-badge.draft  草稿
.project-info-box         项目信息框
.project-info-item        信息项
```

### 按钮样式
```css
.btn-freeze-spec          冻结规格按钮
.btn-mark-ready           标记 ready 按钮
.btn-primary              主按钮
.btn-secondary            次按钮
```

## 浏览器测试

### 打开向导
1. 访问 `http://localhost:8000`
2. 导航到 Tasks 视图
3. 点击 "Create Task" 按钮
4. 查看向导是否正常显示

### 创建任务
1. 填写标题（必填）
2. 选择项目（必填）
3. 点击 "Next"
4. 跳过仓库绑定或选择仓库
5. 添加验收标准
6. 查看摘要
7. 点击 "Freeze Spec & Complete"
8. 验证任务创建成功

### 验证规格冻结
1. 打开刚创建的任务详情
2. 查看 "Project & Specification" 部分
3. 确认显示 "Spec Version: v1" 和 "Frozen" badge
4. 确认 "Freeze Specification" 按钮不显示
5. 如果 status=planned，查看是否显示 "Mark as Ready" 按钮

## 故障排查

### 向导不显示
**原因**: JS 未加载或 CSS 冲突
**解决**:
```bash
# 检查控制台错误
# 确认文件加载: /static/js/components/CreateTaskWizard.js
# 确认文件加载: /static/css/project-v31.css
```

### API 调用失败
**原因**: 后端未启动或端点不存在
**解决**:
```bash
# 确认后端运行
python -m agentos.webui.app

# 检查 API 端点
curl http://localhost:8000/api/projects
curl http://localhost:8000/api/tasks
```

### 项目选择器为空
**原因**: 没有项目或 API 错误
**解决**:
```bash
# 创建测试项目
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Project"}'

# 检查项目列表
curl http://localhost:8000/api/projects
```

### 冻结规格失败
**原因**: 任务状态不正确或规格已冻结
**解决**:
- 确认任务 status=draft
- 确认规格未冻结（spec_frozen_at=null）
- 查看服务端错误日志

## 开发提示

### 添加新步骤
```javascript
// 在 CreateTaskWizard.js 中
renderCurrentStep() {
    switch (this.step) {
        case 1: return this.renderStep1();
        case 2: return this.renderStep2();
        case 3: return this.renderStep3();
        case 4: return this.renderStep4();
        case 5: return this.renderStep5(); // 新增
    }
}
```

### 自定义验证
```javascript
validateCurrentStep() {
    switch (this.step) {
        case 1:
            if (!this.formData.title) {
                showToast('Title required', 'error');
                return false;
            }
            return true;
        // 添加更多验证...
    }
}
```

### 修改样式主题
```css
/* 修改主色调 */
:root {
    --primary-color: #3b82f6;
    --success-color: #10b981;
    --danger-color: #ef4444;
}

.btn-primary {
    background: var(--primary-color);
}
```

## 相关资源

- **API 文档**: `docs/api/V31_API_REFERENCE.md`
- **架构文档**: `docs/architecture/ADR_V04_PROJECT_AWARE_TASK_OS.md`
- **完整报告**: `PHASE4_WEBUI_IMPLEMENTATION_REPORT.md`
- **示例代码**: `test_projects_api_integration.py`

---

**最后更新**: 2026-01-29
**版本**: v1.0
