# Models 管理页面 - 快速开始指南

## 🎯 目标

在 WebUI 添加 Models 页面，实现 Ollama/llama.cpp 模型的下载和管理。

## 📋 实现检查清单

### Phase 1: 基础结构 (1-2小时)

#### 1. 后端 API 层
- [ ] **创建 API 路由文件**
  ```bash
  touch agentos/webui/api/models.py
  ```

- [ ] **实现核心 API 端点**
  - [ ] `GET /api/models/list` - 获取已安装模型
  - [ ] `GET /api/models/available` - 获取推荐模型列表
  - [ ] `POST /api/models/pull` - 下载模型
  - [ ] `GET /api/models/pull/{pull_id}` - 查询下载进度
  - [ ] `DELETE /api/models/{provider}/{model_name}` - 删除模型
  - [ ] `GET /api/models/status` - 获取服务状态

- [ ] **注册 API 路由**
  在 `agentos/webui/app.py` 中添加：
  ```python
  from agentos.webui.api import models
  app.include_router(models.router)
  ```

#### 2. 前端视图层
- [ ] **创建视图 JavaScript 文件**
  ```bash
  touch agentos/webui/static/js/views/ModelsView.js
  ```

- [ ] **创建样式文件**
  ```bash
  touch agentos/webui/static/css/models.css
  ```

- [ ] **添加样式引用**
  在 `index.html` 的 `<head>` 中添加：
  ```html
  <link rel="stylesheet" href="/static/css/models.css?v=1">
  ```

#### 3. 导航菜单
- [ ] **添加 Models 菜单项**
  在 `index.html` Settings 部分（Extensions 下方）添加：
  ```html
  <a href="#" class="nav-item" data-view="models">
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
      </svg>
      <span>Models</span>
  </a>
  ```

- [ ] **注册视图路由**
  在 `main.js` 的 `loadView()` 函数中添加：
  ```javascript
  case 'models':
      const ModelsView = window.ModelsView;
      state.currentViewInstance = new ModelsView();
      await state.currentViewInstance.render(container);
      break;
  ```

### Phase 2: 核心功能 (2-3小时)

#### 4. 模型列表展示
- [ ] 实现 `ModelsView.loadModels()` - 获取并渲染模型列表
- [ ] 实现 `ModelsView.renderModelCard()` - 渲染单个模型卡片
- [ ] 实现空状态提示（无模型时）

#### 5. 模型下载
- [ ] 实现下载对话框 `showDownloadModal()`
- [ ] 实现推荐模型列表渲染
- [ ] 实现自定义模型名输入
- [ ] 实现 `pullModel()` - 发起下载请求
- [ ] 实现 `showPullProgress()` - 显示进度条
- [ ] 实现 `pollPullProgress()` - 轮询下载进度

#### 6. 服务状态监控
- [ ] 实现 `loadServiceStatus()` - 获取服务状态
- [ ] 实现状态指示器渲染
- [ ] 实现定时刷新（每5秒）

### Phase 3: 增强功能 (1-2小时)

#### 7. 模型管理
- [ ] 实现删除确认对话框
- [ ] 实现 `deleteModel()` - 删除模型
- [ ] 实现模型详情查看

#### 8. 用户体验优化
- [ ] 添加 loading 状态
- [ ] 添加错误提示
- [ ] 添加成功通知
- [ ] 实现响应式布局

## 🚀 快速测试

### 1. 启动服务
```bash
# 终端 1: 启动 Ollama
ollama serve

# 终端 2: 启动 AgentOS WebUI
agentos webui
```

### 2. 访问页面
打开浏览器: http://localhost:8000
点击 Settings → Models

### 3. 测试下载
- 点击 [+ Download Model]
- 选择 `llama3.2:1b` (最小模型，约1.3GB)
- 观察下载进度
- 验证下载完成后模型出现在列表中

### 4. 测试删除
- 点击模型卡片的 [Delete] 按钮
- 确认删除
- 验证模型从列表中消失

## 📦 核心代码示例

### 后端 API (models.py)
```python
from fastapi import APIRouter
from agentos.cli.provider_checker import ProviderChecker

router = APIRouter()
checker = ProviderChecker()

@router.get("/api/models/list")
async def list_models():
    """获取已安装的模型列表"""
    models = checker.get_ollama_models()
    return {
        "models": [
            {
                "name": model,
                "provider": "ollama",
                "size": "Unknown"  # 需要调用 ollama api 获取详情
            }
            for model in models
        ]
    }

@router.post("/api/models/pull")
async def pull_model(request: dict):
    """下载模型（后台线程）"""
    model_name = request["model_name"]
    pull_id = f"pull_{uuid.uuid4().hex[:12]}"

    # 在后台线程中下载
    threading.Thread(
        target=_pull_model_background,
        args=(pull_id, model_name),
        daemon=True
    ).start()

    return {"pull_id": pull_id, "status": "PULLING"}
```

### 前端视图 (ModelsView.js)
```javascript
class ModelsView {
    async render(container) {
        container.innerHTML = `
            <div class="models-view">
                <div class="view-header">
                    <h1>Models</h1>
                    <button class="btn-primary" id="btnDownloadModel">
                        Download Model
                    </button>
                </div>
                <div id="modelsGrid" class="models-grid"></div>
            </div>
        `;

        document.getElementById('btnDownloadModel')
            .addEventListener('click', () => this.showDownloadModal());

        await this.loadModels();
    }

    async loadModels() {
        const response = await fetch('/api/models/list');
        const data = await response.json();

        const grid = document.getElementById('modelsGrid');
        grid.innerHTML = data.models
            .map(model => this.renderModelCard(model))
            .join('');
    }

    renderModelCard(model) {
        return `
            <div class="model-card">
                <h3>${model.name}</h3>
                <p>${model.size}</p>
                <button onclick="deleteModel('${model.name}')">
                    Delete
                </button>
            </div>
        `;
    }
}

window.ModelsView = ModelsView;
```

## 🎨 推荐模型列表

在 `GET /api/models/available` 中返回：

```json
{
  "recommended": [
    {
      "name": "qwen2.5:7b",
      "display_name": "Qwen 2.5 (7B)",
      "description": "中文优化的大语言模型",
      "size": "4.7 GB",
      "tags": ["chat", "code", "chinese"]
    },
    {
      "name": "llama3.2:3b",
      "display_name": "Llama 3.2 (3B)",
      "description": "快速响应，适合日常对话",
      "size": "2.0 GB",
      "tags": ["chat", "fast"]
    },
    {
      "name": "llama3.2:1b",
      "display_name": "Llama 3.2 (1B)",
      "description": "超轻量级，快速响应",
      "size": "1.3 GB",
      "tags": ["chat", "fast", "lightweight"]
    }
  ]
}
```

## 🐛 常见问题

### 1. Ollama 服务未运行
**现象**: 页面显示 "Service not available"
**解决**:
```bash
# 启动 Ollama 服务
ollama serve
```

### 2. 下载进度不更新
**原因**: 轮询间隔太长或后台线程未正确更新进度
**检查**:
- 确认 `_pull_progress` 全局字典正确更新
- 确认前端轮询间隔为 500ms
- 查看浏览器控制台是否有错误

### 3. 模型删除后仍显示
**原因**: 前端未刷新列表
**解决**: 在删除成功回调中调用 `this.loadModels()`

## 📚 参考文档

- 完整实现方案: `docs/features/MODELS_PAGE_IMPLEMENTATION_PLAN.md`
- Ollama API: https://github.com/ollama/ollama/blob/main/docs/api.md
- Extensions 页面参考: `agentos/webui/static/js/views/ExtensionsView.js`

## ⏱️ 预估时间

- **基础功能 (MVP)**: 4-6 小时
- **完整功能**: 8-10 小时
- **测试和优化**: 2-3 小时

**总计**: 约 1-2 个工作日完成完整功能

## 🎯 验收标准

- [x] 能够查看已安装的模型列表
- [x] 能够从推荐列表下载模型
- [x] 下载过程中实时显示进度
- [x] 能够删除已安装的模型
- [x] 页面样式与 Extensions 保持一致
- [x] 移动端响应式布局正常
- [x] 错误处理完善（服务未运行、下载失败等）
