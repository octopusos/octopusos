# Models 管理页面实现方案

## 📋 概述

在 WebUI 的 Settings 部分添加 Models 页面，用于下载和管理本地 AI 模型（Ollama、llama.cpp）。

## 🎯 功能需求

### 核心功能
1. **模型列表展示** - 显示已安装的模型（卡片式布局）
2. **模型下载** - 从推荐列表或自定义名称下载模型
3. **下载进度** - 实时显示下载进度条
4. **模型管理** - 删除、查看详情
5. **服务状态** - 显示 Ollama/llama.cpp 服务运行状态

### 页面交互流程
```
用户打开 Models 页面
    ↓
显示服务状态 + 已安装模型列表
    ↓
点击 [+ Download] 按钮
    ↓
弹出下载对话框（推荐模型 + 自定义输入）
    ↓
选择模型并确认下载
    ↓
显示下载进度条（实时更新）
    ↓
下载完成后自动刷新模型列表
```

## 📂 文件结构

```
agentos/
├── webui/
│   ├── api/
│   │   └── models.py                    # 新建 - Models API 路由
│   ├── static/
│   │   ├── css/
│   │   │   └── models.css              # 新建 - Models 页面样式
│   │   └── js/
│   │       └── views/
│   │           └── ModelsView.js       # 新建 - Models 视图类
│   └── templates/
│       └── index.html                   # 修改 - 添加 Models 菜单项
└── cli/
    └── provider_checker.py              # 已有 - 扩展进度回调功能
```

## 🎨 UI 设计

### 1. 导航菜单项（添加到 Settings 部分）
```html
<!-- 在 Extensions 下方添加 -->
<a href="#" class="nav-item" data-view="models">
    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
    </svg>
    <span>Models</span>
</a>
```

### 2. 页面主体结构
```html
<div class="models-view">
    <!-- Header -->
    <div class="view-header">
        <div>
            <h1>Models</h1>
            <p class="text-sm text-gray-600 mt-1">Download and manage local AI models</p>
        </div>
        <div class="header-actions">
            <button class="btn-primary" id="btnDownloadModel">
                <span class="icon"><span class="material-icons md-18">download</span></span>
                Download Model
            </button>
        </div>
    </div>

    <!-- Service Status Section -->
    <div class="status-section">
        <h2>Service Status</h2>
        <div class="status-grid">
            <!-- Ollama Status -->
            <div class="status-card">
                <div class="status-header">
                    <span class="status-indicator status-running"></span>
                    <h3>Ollama</h3>
                </div>
                <p class="status-info">v0.15.2 (Running)</p>
                <div class="status-actions">
                    <button class="btn-sm btn-secondary">Start</button>
                    <button class="btn-sm btn-secondary">Stop</button>
                </div>
            </div>

            <!-- llama.cpp Status -->
            <div class="status-card">
                <div class="status-header">
                    <span class="status-indicator status-stopped"></span>
                    <h3>llama.cpp</h3>
                </div>
                <p class="status-info">Not Available</p>
            </div>
        </div>
    </div>

    <!-- Download Progress (shown when downloading) -->
    <div id="downloadProgressContainer" style="display: none;"></div>

    <!-- Models Grid -->
    <div class="table-section">
        <h2>Installed Models</h2>
        <div id="modelsGrid" class="models-grid">
            <!-- Model cards will be rendered here -->
        </div>
    </div>
</div>
```

### 3. 模型卡片设计
```html
<div class="model-card">
    <div class="model-card-header">
        <div class="model-icon">🤖</div>
        <div class="model-info">
            <h3>qwen2.5:7b</h3>
            <div class="model-meta">
                <span class="model-params">7B params</span>
                <span class="model-size">4.7 GB</span>
            </div>
        </div>
    </div>
    <div class="model-card-body">
        <p class="model-description">
            Qwen 2.5 - 中文优化的大语言模型，适合中文对话和代码生成
        </p>
        <div class="model-tags">
            <span class="tag">chat</span>
            <span class="tag">code</span>
            <span class="tag">chinese</span>
        </div>
    </div>
    <div class="model-card-actions">
        <button class="btn-primary" data-action="run">Run</button>
        <button class="btn-secondary" data-action="info">Info</button>
        <button class="btn-delete" data-action="delete">Delete</button>
    </div>
</div>
```

## 🔌 API 接口设计

### 1. 获取已安装模型列表
```
GET /api/models/list

Response:
{
    "models": [
        {
            "name": "qwen2.5:7b",
            "provider": "ollama",
            "size": "4.7 GB",
            "size_bytes": 5046586573,
            "params": "7B",
            "family": "qwen2.5",
            "format": "gguf",
            "modified_at": "2024-01-15T10:30:00Z",
            "digest": "sha256:abc123...",
            "details": {
                "parent_model": "",
                "format": "gguf",
                "family": "qwen2.5",
                "families": ["qwen"],
                "parameter_size": "7.6B",
                "quantization_level": "Q4_0"
            }
        }
    ],
    "total": 3
}
```

### 2. 获取可下载模型列表（推荐模型）
```
GET /api/models/available

Response:
{
    "recommended": [
        {
            "name": "qwen2.5:7b",
            "display_name": "Qwen 2.5 (7B)",
            "description": "中文优化的大语言模型，适合中文对话和代码生成",
            "size": "4.7 GB",
            "params": "7B",
            "tags": ["chat", "code", "chinese"],
            "category": "general"
        },
        {
            "name": "llama3.2:3b",
            "display_name": "Llama 3.2 (3B)",
            "description": "快速响应，适合日常对话",
            "size": "2.0 GB",
            "params": "3B",
            "tags": ["chat", "fast"],
            "category": "general"
        },
        {
            "name": "llama3.2:1b",
            "display_name": "Llama 3.2 (1B)",
            "description": "超轻量级，快速响应",
            "size": "1.3 GB",
            "params": "1B",
            "tags": ["chat", "fast", "lightweight"],
            "category": "general"
        },
        {
            "name": "gemma2:2b",
            "display_name": "Gemma 2 (2B)",
            "description": "Google 开源的小型模型",
            "size": "1.6 GB",
            "params": "2B",
            "tags": ["chat"],
            "category": "general"
        },
        {
            "name": "qwen2.5-coder:7b",
            "display_name": "Qwen 2.5 Coder (7B)",
            "description": "代码生成专用模型",
            "size": "4.7 GB",
            "params": "7B",
            "tags": ["code"],
            "category": "coding"
        }
    ]
}
```

### 3. 下载模型
```
POST /api/models/pull

Request:
{
    "model_name": "qwen2.5:7b",
    "provider": "ollama"  // 可选，默认 ollama
}

Response:
{
    "pull_id": "pull_abc123",
    "model_name": "qwen2.5:7b",
    "status": "PULLING"
}
```

### 4. 查询下载进度
```
GET /api/models/pull/{pull_id}

Response:
{
    "pull_id": "pull_abc123",
    "model_name": "qwen2.5:7b",
    "status": "PULLING",  // PULLING, COMPLETED, FAILED
    "progress": 75,
    "current_layer": 3,
    "total_layers": 4,
    "downloaded_bytes": 3543891968,
    "total_bytes": 4726735872,
    "current_status": "pulling manifest",
    "error": null
}
```

### 5. 删除模型
```
DELETE /api/models/{provider}/{model_name}

Response:
{
    "success": true,
    "message": "Model qwen2.5:7b deleted successfully"
}
```

### 6. 获取服务状态
```
GET /api/models/status

Response:
{
    "ollama": {
        "available": true,
        "running": true,
        "version": "0.15.2",
        "host": "http://localhost:11434"
    },
    "llama_cpp": {
        "available": false,
        "running": false,
        "info": "Command not found"
    }
}
```

## 💾 数据库扩展

在 models 表中添加下载记录（可选，用于历史追踪）：

```sql
-- 模型下载记录表
CREATE TABLE IF NOT EXISTS model_pulls (
    pull_id TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    provider TEXT NOT NULL,  -- ollama, llama_cpp
    status TEXT NOT NULL,    -- PULLING, COMPLETED, FAILED
    progress INTEGER DEFAULT 0,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error TEXT,
    metadata JSON
);
```

## 🎯 实现优先级

### Phase 1: 基础功能 (MVP)
- [ ] 创建 ModelsView.js 和 models.css
- [ ] 添加导航菜单项
- [ ] 实现 API 路由（models.py）
- [ ] 实现模型列表展示
- [ ] 实现模型下载功能
- [ ] 实现下载进度显示

### Phase 2: 增强功能
- [ ] 服务状态监控和控制
- [ ] 模型删除功能
- [ ] 模型详情查看
- [ ] 自定义模型下载
- [ ] 批量操作支持

### Phase 3: 高级功能
- [ ] llama.cpp 模型支持
- [ ] 模型性能测试
- [ ] 模型推荐算法
- [ ] 模型版本管理

## 🔧 技术实现细节

### 1. 下载进度追踪机制

使用后台线程 + 轮询机制：

```python
# 后端
import threading
import uuid

# 全局存储下载进度
_pull_progress = {}

def pull_model_background(pull_id: str, model_name: str):
    """后台下载模型"""
    try:
        _pull_progress[pull_id] = {
            "status": "PULLING",
            "progress": 0,
            "model_name": model_name
        }

        # 调用 ollama pull，解析输出进度
        process = subprocess.Popen(
            ["ollama", "pull", model_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        for line in process.stdout:
            # 解析进度（Ollama 输出格式）
            # pulling manifest
            # pulling sha256:... 100% ████████████
            progress = parse_progress(line)
            _pull_progress[pull_id]["progress"] = progress
            _pull_progress[pull_id]["current_status"] = line.strip()

        if process.returncode == 0:
            _pull_progress[pull_id]["status"] = "COMPLETED"
            _pull_progress[pull_id]["progress"] = 100
        else:
            _pull_progress[pull_id]["status"] = "FAILED"

    except Exception as e:
        _pull_progress[pull_id]["status"] = "FAILED"
        _pull_progress[pull_id]["error"] = str(e)
```

```javascript
// 前端
class ModelsView {
    async pullModel(modelName) {
        // 1. 发起下载请求
        const response = await fetch('/api/models/pull', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_name: modelName })
        });

        const { pull_id } = await response.json();

        // 2. 显示进度条
        this.showPullProgress(pull_id, modelName);

        // 3. 开始轮询进度
        this.pollPullProgress(pull_id);
    }

    async pollPullProgress(pullId) {
        const interval = setInterval(async () => {
            const response = await fetch(`/api/models/pull/${pullId}`);
            const data = await response.json();

            // 更新进度条
            this.updateProgressBar(pullId, data.progress);

            // 检查是否完成
            if (data.status === 'COMPLETED') {
                clearInterval(interval);
                this.showNotification('Model downloaded successfully', 'success');
                this.loadModels(); // 刷新列表
            } else if (data.status === 'FAILED') {
                clearInterval(interval);
                this.showNotification(`Download failed: ${data.error}`, 'error');
            }
        }, 500); // 每500ms轮询一次
    }
}
```

### 2. 模型大小格式化

```javascript
function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}
```

### 3. 服务状态实时监控

```javascript
class ModelsView {
    constructor() {
        this.statusCheckInterval = null;
    }

    async render(container) {
        // ...渲染页面

        // 启动状态检查
        this.startStatusCheck();
    }

    startStatusCheck() {
        // 每5秒检查一次服务状态
        this.statusCheckInterval = setInterval(async () => {
            await this.updateServiceStatus();
        }, 5000);
    }

    destroy() {
        if (this.statusCheckInterval) {
            clearInterval(this.statusCheckInterval);
        }
    }

    async updateServiceStatus() {
        const response = await fetch('/api/models/status');
        const data = await response.json();

        // 更新 UI 状态指示器
        this.updateStatusIndicators(data);
    }
}
```

## 🎨 样式规范

遵循 Extensions 页面的样式设计：

```css
/* models.css */

/* 继承 extensions.css 的基础样式 */
.models-view {
    padding: 20px;
}

/* 服务状态部分 */
.status-section {
    margin-bottom: 24px;
    padding: 20px;
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 0.75rem;
}

.status-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1rem;
    margin-top: 1rem;
}

.status-card {
    padding: 1.5rem;
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 0.5rem;
}

.status-indicator {
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    margin-right: 0.5rem;
}

.status-indicator.status-running {
    background: #10b981;
    animation: pulse 2s infinite;
}

.status-indicator.status-stopped {
    background: #6b7280;
}

/* 模型卡片网格 */
.models-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 1.5rem;
}

/* 模型卡片样式（与 extension-card 对齐）*/
.model-card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 0.75rem;
    padding: 1.5rem;
    transition: all 0.2s ease;
    display: flex;
    flex-direction: column;
    height: 100%;
}

.model-card:hover {
    border-color: #3b82f6;
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
}

/* 下载进度样式（与 install-progress 对齐）*/
.download-progress {
    padding: 1.5rem;
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 0.75rem;
    margin-bottom: 2rem;
}

.progress-bar {
    width: 100%;
    height: 8px;
    background: #e5e7eb;
    border-radius: 9999px;
    overflow: hidden;
    margin: 0.75rem 0;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #3b82f6 0%, #8b5cf6 100%);
    transition: width 0.3s ease;
    border-radius: 9999px;
}

/* 响应式设计 */
@media (max-width: 768px) {
    .models-grid {
        grid-template-columns: 1fr;
    }

    .status-grid {
        grid-template-columns: 1fr;
    }
}
```

## 🚀 部署和测试

### 开发环境测试步骤

1. **启动 Ollama 服务**
   ```bash
   ollama serve
   ```

2. **启动 AgentOS WebUI**
   ```bash
   agentos webui
   ```

3. **访问 Models 页面**
   - 打开浏览器: http://localhost:8000
   - 点击 Settings → Models

4. **测试下载功能**
   - 点击 [+ Download Model]
   - 选择 llama3.2:1b (最小模型，快速测试)
   - 观察下载进度
   - 验证下载完成后模型出现在列表中

### 单元测试

```python
# tests/integration/api/test_models_api.py

import pytest
from agentos.webui.api.models import router

def test_list_models():
    """测试获取模型列表"""
    response = client.get("/api/models/list")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data

def test_pull_model():
    """测试下载模型"""
    response = client.post("/api/models/pull", json={
        "model_name": "llama3.2:1b"
    })
    assert response.status_code == 200
    data = response.json()
    assert "pull_id" in data

def test_get_pull_progress():
    """测试查询下载进度"""
    # 先发起下载
    pull_response = client.post("/api/models/pull", json={
        "model_name": "llama3.2:1b"
    })
    pull_id = pull_response.json()["pull_id"]

    # 查询进度
    progress_response = client.get(f"/api/models/pull/{pull_id}")
    assert progress_response.status_code == 200
    data = progress_response.json()
    assert "progress" in data
```

## 📝 后续优化方向

1. **模型推荐系统** - 根据用户硬件配置推荐合适的模型
2. **模型性能测试** - 提供模型性能基准测试功能
3. **模型转换工具** - 支持 GGUF、GGML 格式转换
4. **多 Provider 支持** - 扩展支持 LM Studio、Jan.ai 等
5. **模型市场** - 集成社区模型市场
6. **离线模型导入** - 支持从本地文件导入模型

## 🎯 成功指标

- ✅ 用户能在 3 次点击内完成模型下载
- ✅ 下载进度更新延迟 < 1 秒
- ✅ 页面加载时间 < 2 秒
- ✅ 支持同时下载 2 个以上模型
- ✅ 移动端响应式布局完美适配

## 📚 参考资料

- Ollama API 文档: https://github.com/ollama/ollama/blob/main/docs/api.md
- llama.cpp 文档: https://github.com/ggerganov/llama.cpp
- AgentOS Extensions 设计文档: docs/extensions/
