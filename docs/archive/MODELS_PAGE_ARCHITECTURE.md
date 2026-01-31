# Models 管理页面 - 技术架构

## 🏗️ 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户浏览器                                │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  ModelsView.js (视图层)                                   │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐         │   │
│  │  │ 模型列表    │  │ 下载管理    │  │ 服务状态    │         │   │
│  │  │ 展示        │  │ 进度追踪    │  │ 监控        │         │   │
│  │  └────────────┘  └────────────┘  └────────────┘         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            ↕ HTTP/WebSocket                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      AgentOS WebUI Server                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  models.py (FastAPI 路由)                                 │   │
│  │                                                            │   │
│  │  GET  /api/models/list           → list_models()         │   │
│  │  GET  /api/models/available      → get_available()       │   │
│  │  POST /api/models/pull           → pull_model()          │   │
│  │  GET  /api/models/pull/{id}      → get_progress()        │   │
│  │  DEL  /api/models/{provider}/{m} → delete_model()        │   │
│  │  GET  /api/models/status         → get_status()          │   │
│  │                                                            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            ↕                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  ProviderChecker (CLI 层)                                 │   │
│  │                                                            │   │
│  │  - check_ollama()         检查 Ollama 服务状态            │   │
│  │  - get_ollama_models()    获取已安装模型列表              │   │
│  │  - pull_ollama_model()    下载模型 (阻塞调用)             │   │
│  │  - start_ollama()         启动 Ollama 服务                │   │
│  │                                                            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            ↕                                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      Ollama / llama.cpp                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────┐      ┌──────────────────────┐         │
│  │  Ollama Server       │      │  llama.cpp           │         │
│  │  (localhost:11434)   │      │  (本地二进制)        │         │
│  │                      │      │                      │         │
│  │  - API: /api/tags    │      │  - llama-server      │         │
│  │  - API: /api/pull    │      │  - llama-cli         │         │
│  │  - API: /api/delete  │      │                      │         │
│  └──────────────────────┘      └──────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

## 🔄 数据流图

### 1. 查看模型列表
```
用户打开 Models 页面
    ↓
ModelsView.render()
    ↓
ModelsView.loadModels()
    ↓
GET /api/models/list ──→ models.list_models()
                             ↓
                         ProviderChecker.get_ollama_models()
                             ↓
                         GET http://localhost:11434/api/tags
                             ↓
                         返回模型列表
    ↓
ModelsView.renderModelCard() × N
    ↓
页面显示模型卡片
```

### 2. 下载模型（核心流程）
```
用户点击 [Download Model]
    ↓
ModelsView.showDownloadModal()
    ↓
用户选择模型 "qwen2.5:7b"
    ↓
ModelsView.pullModel("qwen2.5:7b")
    ↓
POST /api/models/pull
    body: { "model_name": "qwen2.5:7b" }
    ↓
models.pull_model()
    ├─→ 生成 pull_id = "pull_abc123"
    ├─→ 记录到 _pull_progress[pull_id]
    └─→ 启动后台线程: _pull_model_background()
    ↓
立即返回 { "pull_id": "pull_abc123", "status": "PULLING" }
    ↓
ModelsView.showPullProgress("pull_abc123")
    ├─→ 显示进度条 UI
    └─→ 开始轮询: ModelsView.pollPullProgress()

┌──────────────────────────────────────────────────────────┐
│ 后台线程 _pull_model_background("pull_abc123", ...)     │
│                                                          │
│  subprocess.Popen(["ollama", "pull", "qwen2.5:7b"])    │
│      ↓                                                   │
│  解析 stdout 输出                                        │
│      ↓                                                   │
│  更新 _pull_progress[pull_id]:                          │
│    - progress: 0 → 25 → 50 → 75 → 100                  │
│    - current_status: "pulling manifest" ...             │
│                                                          │
└──────────────────────────────────────────────────────────┘
                            ↕
┌──────────────────────────────────────────────────────────┐
│ 前端轮询 (每 500ms)                                      │
│                                                          │
│  GET /api/models/pull/pull_abc123                       │
│      ↓                                                   │
│  models.get_pull_progress("pull_abc123")               │
│      ↓                                                   │
│  返回 _pull_progress["pull_abc123"]                     │
│      ↓                                                   │
│  ModelsView.updateProgressBar(75%)                      │
│                                                          │
└──────────────────────────────────────────────────────────┘

下载完成 (status = "COMPLETED")
    ↓
停止轮询
    ↓
显示成功通知
    ↓
刷新模型列表 (自动显示新模型)
```

### 3. 删除模型
```
用户点击 [Delete] 按钮
    ↓
ModelsView.showDeleteConfirmModal()
    ↓
用户确认删除
    ↓
ModelsView.deleteModel("qwen2.5:7b")
    ↓
DELETE /api/models/ollama/qwen2.5:7b
    ↓
models.delete_model("ollama", "qwen2.5:7b")
    ↓
ProviderChecker.delete_ollama_model()  (需要实现)
    ↓
执行: ollama rm qwen2.5:7b
    ↓
返回删除结果
    ↓
显示成功通知
    ↓
刷新模型列表
```

## 📊 状态管理

### 全局状态 (后端)
```python
# 下载进度追踪
_pull_progress = {
    "pull_abc123": {
        "pull_id": "pull_abc123",
        "model_name": "qwen2.5:7b",
        "status": "PULLING",  # PULLING, COMPLETED, FAILED
        "progress": 75,
        "current_layer": 3,
        "total_layers": 4,
        "downloaded_bytes": 3543891968,
        "total_bytes": 4726735872,
        "current_status": "pulling layer sha256:...",
        "started_at": "2024-01-15T10:30:00Z",
        "error": null
    }
}
```

### 组件状态 (前端)
```javascript
class ModelsView {
    constructor() {
        this.currentModels = [];           // 当前模型列表
        this.activePulls = new Set();      // 活跃的下载任务
        this.pullIntervalId = null;        // 轮询定时器
        this.statusCheckInterval = null;   // 服务状态检查定时器
    }
}
```

## 🎯 关键技术点

### 1. 后台下载进度追踪

**挑战**: Ollama pull 是阻塞调用，如何实时获取进度？

**解决方案**: 解析 stdout 输出 + 后台线程

```python
def _pull_model_background(pull_id: str, model_name: str):
    """后台线程下载模型并追踪进度"""
    process = subprocess.Popen(
        ["ollama", "pull", model_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1  # 行缓冲
    )

    total_layers = 0
    current_layer = 0

    for line in process.stdout:
        line = line.strip()

        # 解析 Ollama 输出格式
        # pulling manifest
        # pulling sha256:abc123... 100% ████████████ 1.2 GB/1.2 GB
        # verifying sha256:abc123...
        # writing manifest
        # success

        if "pulling" in line and "%" in line:
            # 提取百分比
            match = re.search(r'(\d+)%', line)
            if match:
                layer_progress = int(match.group(1))
                overall_progress = (current_layer * 100 + layer_progress) / total_layers

                _pull_progress[pull_id]["progress"] = int(overall_progress)
                _pull_progress[pull_id]["current_status"] = line

        elif "pulling sha256:" in line:
            current_layer += 1
            if "pulling manifest" not in line:
                total_layers = max(total_layers, current_layer)

    # 完成或失败
    if process.returncode == 0:
        _pull_progress[pull_id]["status"] = "COMPLETED"
        _pull_progress[pull_id]["progress"] = 100
    else:
        _pull_progress[pull_id]["status"] = "FAILED"
```

### 2. 前端轮询优化

**挑战**: 如何避免轮询造成的性能问题？

**解决方案**:
- 仅在有活跃下载时轮询
- 下载完成后立即停止轮询
- 使用较短的轮询间隔（500ms）保证实时性

```javascript
class ModelsView {
    async pullModel(modelName) {
        const response = await fetch('/api/models/pull', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_name: modelName })
        });

        const { pull_id } = await response.json();

        // 记录活跃下载
        this.activePulls.add(pull_id);

        // 显示进度 UI
        this.showPullProgress(pull_id, modelName);

        // 开始轮询（如果尚未启动）
        if (!this.pullIntervalId) {
            this.startPollingPulls();
        }
    }

    startPollingPulls() {
        this.pullIntervalId = setInterval(async () => {
            // 批量查询所有活跃下载的进度
            for (const pullId of this.activePulls) {
                await this.updatePullProgress(pullId);
            }

            // 如果没有活跃下载，停止轮询
            if (this.activePulls.size === 0) {
                clearInterval(this.pullIntervalId);
                this.pullIntervalId = null;
            }
        }, 500);
    }

    async updatePullProgress(pullId) {
        const response = await fetch(`/api/models/pull/${pullId}`);
        const data = await response.json();

        // 更新进度 UI
        this.updateProgressBar(pullId, data.progress);

        // 检查是否完成
        if (data.status === 'COMPLETED' || data.status === 'FAILED') {
            this.activePulls.delete(pullId);
            this.handlePullComplete(pullId, data);
        }
    }
}
```

### 3. 服务状态监控

**挑战**: 如何实时显示 Ollama 服务状态？

**解决方案**: 定时轮询 + 健康检查

```javascript
class ModelsView {
    async render(container) {
        // ... 渲染页面

        // 启动服务状态检查
        this.startStatusCheck();
    }

    startStatusCheck() {
        // 立即检查一次
        this.updateServiceStatus();

        // 每 5 秒检查一次
        this.statusCheckInterval = setInterval(async () => {
            await this.updateServiceStatus();
        }, 5000);
    }

    async updateServiceStatus() {
        try {
            const response = await fetch('/api/models/status');
            const data = await response.json();

            // 更新状态指示器
            const ollamaIndicator = document.getElementById('ollama-status');
            if (data.ollama.running) {
                ollamaIndicator.className = 'status-indicator status-running';
                ollamaIndicator.title = `Running (${data.ollama.version})`;
            } else {
                ollamaIndicator.className = 'status-indicator status-stopped';
                ollamaIndicator.title = 'Stopped';
            }
        } catch (error) {
            console.error('Failed to check service status:', error);
        }
    }

    destroy() {
        // 清理定时器
        if (this.statusCheckInterval) {
            clearInterval(this.statusCheckInterval);
        }
        if (this.pullIntervalId) {
            clearInterval(this.pullIntervalId);
        }
    }
}
```

## 🔧 扩展点设计

### 1. 支持多 Provider
```python
# 抽象 Provider 接口
class ModelProvider(ABC):
    @abstractmethod
    def list_models(self) -> List[Model]:
        pass

    @abstractmethod
    def pull_model(self, model_name: str) -> str:  # 返回 pull_id
        pass

    @abstractmethod
    def get_pull_progress(self, pull_id: str) -> PullProgress:
        pass

    @abstractmethod
    def delete_model(self, model_name: str) -> bool:
        pass

# 实现
class OllamaProvider(ModelProvider):
    ...

class LlamaCppProvider(ModelProvider):
    ...

# 在 API 中使用
providers = {
    "ollama": OllamaProvider(),
    "llama_cpp": LlamaCppProvider()
}

@router.post("/api/models/pull")
async def pull_model(request: PullRequest):
    provider = providers[request.provider]
    pull_id = provider.pull_model(request.model_name)
    return {"pull_id": pull_id}
```

### 2. WebSocket 实时推送（可选优化）

替代轮询，使用 WebSocket 实时推送进度：

```python
# 后端
@router.websocket("/ws/models/pull/{pull_id}")
async def pull_progress_ws(websocket: WebSocket, pull_id: str):
    await websocket.accept()
    try:
        while True:
            progress = _pull_progress.get(pull_id)
            if progress:
                await websocket.send_json(progress)

                if progress["status"] in ["COMPLETED", "FAILED"]:
                    break

            await asyncio.sleep(0.5)
    finally:
        await websocket.close()
```

```javascript
// 前端
async pullModel(modelName) {
    const response = await fetch('/api/models/pull', { ... });
    const { pull_id } = await response.json();

    // 使用 WebSocket 接收进度
    const ws = new WebSocket(`ws://localhost:8000/ws/models/pull/${pull_id}`);

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        this.updateProgressBar(pull_id, data.progress);

        if (data.status === 'COMPLETED') {
            ws.close();
            this.handlePullComplete(pull_id, data);
        }
    };
}
```

## 📦 推荐的项目结构

```
agentos/
├── webui/
│   ├── api/
│   │   ├── models.py              # Models API 路由 (新增)
│   │   ├── extensions.py          # Extensions API (参考)
│   │   └── ...
│   ├── static/
│   │   ├── css/
│   │   │   ├── models.css         # Models 样式 (新增)
│   │   │   ├── extensions.css     # Extensions 样式 (参考)
│   │   │   └── ...
│   │   └── js/
│   │       └── views/
│   │           ├── ModelsView.js       # Models 视图 (新增)
│   │           ├── ExtensionsView.js   # Extensions 视图 (参考)
│   │           └── ...
│   └── templates/
│       └── index.html             # 主页面 (修改)
├── cli/
│   └── provider_checker.py        # Provider 检测 (扩展)
└── core/
    └── models/                     # 可选：模型管理核心逻辑
        ├── __init__.py
        ├── base.py                # Provider 抽象接口
        ├── ollama.py              # Ollama Provider
        └── llamacpp.py            # llama.cpp Provider
```

## 🧪 测试策略

### 单元测试
```python
# tests/unit/api/test_models_api.py
def test_list_models_empty():
    """测试空模型列表"""
    # Mock ProviderChecker.get_ollama_models() 返回 []
    response = client.get("/api/models/list")
    assert response.json() == {"models": []}

def test_pull_model_creates_background_task():
    """测试下载模型启动后台任务"""
    response = client.post("/api/models/pull", json={
        "model_name": "test:model"
    })
    assert "pull_id" in response.json()
```

### 集成测试
```python
# tests/integration/test_models_e2e.py
@pytest.mark.asyncio
async def test_pull_model_e2e():
    """端到端测试模型下载"""
    # 1. 发起下载
    pull_response = client.post("/api/models/pull", json={
        "model_name": "llama3.2:1b"
    })
    pull_id = pull_response.json()["pull_id"]

    # 2. 轮询进度直到完成
    for _ in range(60):  # 最多等待 60 秒
        progress_response = client.get(f"/api/models/pull/{pull_id}")
        data = progress_response.json()

        if data["status"] == "COMPLETED":
            break

        await asyncio.sleep(1)

    # 3. 验证模型出现在列表中
    list_response = client.get("/api/models/list")
    models = list_response.json()["models"]
    assert any(m["name"] == "llama3.2:1b" for m in models)
```

### 前端测试 (Playwright)
```javascript
// tests/e2e/test_models_page.spec.js
test('download model from UI', async ({ page }) => {
    // 1. 打开 Models 页面
    await page.goto('http://localhost:8000');
    await page.click('a[data-view="models"]');

    // 2. 点击下载按钮
    await page.click('#btnDownloadModel');

    // 3. 选择模型
    await page.click('input[value="llama3.2:1b"]');
    await page.click('button:has-text("Download")');

    // 4. 等待进度条出现
    await page.waitForSelector('.download-progress');

    // 5. 等待下载完成
    await page.waitForSelector('.model-card:has-text("llama3.2:1b")', {
        timeout: 120000  // 2 分钟超时
    });
});
```

## 🚀 部署和监控

### 健康检查
```python
@router.get("/api/models/health")
async def health_check():
    """健康检查端点"""
    ollama_ok, _ = ProviderChecker().check_ollama()
    return {
        "status": "healthy" if ollama_ok else "degraded",
        "providers": {
            "ollama": ollama_ok
        }
    }
```

### 日志记录
```python
import logging

logger = logging.getLogger(__name__)

@router.post("/api/models/pull")
async def pull_model(request: PullRequest):
    logger.info(f"Starting model pull: {request.model_name}")

    try:
        pull_id = await _start_pull(request.model_name)
        logger.info(f"Model pull started successfully: {pull_id}")
        return {"pull_id": pull_id}
    except Exception as e:
        logger.error(f"Failed to start model pull: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

## 📊 性能指标

### 目标性能
- 页面加载时间: < 2 秒
- 模型列表刷新: < 500ms
- 进度更新延迟: < 1 秒
- 并发下载支持: >= 2 个模型

### 监控指标
```python
from prometheus_client import Counter, Histogram

# 下载计数器
model_pull_counter = Counter(
    'models_pull_total',
    'Total number of model pulls',
    ['model_name', 'status']
)

# 下载时长分布
model_pull_duration = Histogram(
    'models_pull_duration_seconds',
    'Model pull duration in seconds',
    ['model_name']
)
```

---

**总结**: 本架构设计遵循 "简单优先" 原则，核心功能使用轮询实现，易于理解和调试。后续可根据需要优化为 WebSocket 推送。
