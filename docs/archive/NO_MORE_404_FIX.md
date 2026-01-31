# 彻底解决 Extension 安装 404 问题

## 问题本质

用户说得对：**404 让用户完全不知道发生了什么。**

### 之前的流程（有问题）

```
1. 前端上传 ZIP → POST /api/extensions/install
2. 后端返回 {"install_id": "inst_xxx", "status": "INSTALLING"}
3. 前端开始轮询 GET /api/extensions/install/inst_xxx
4. 后台线程开始
5. 验证 ZIP 失败 ❌ (在创建 install record 之前)
6. 前端轮询 → 404 (记录不存在)
7. 用户只看到 404，不知道为什么失败 😔
```

**问题**:
- Install record 在验证成功后才创建
- 如果验证失败，record 永远不会被创建
- 前端轮询时得到 404，无法获取失败原因

## 解决方案

### 核心思路

**立即创建 install record，即使还不知道 extension_id**

### 新流程

```
1. 前端上传 ZIP → POST /api/extensions/install
2. 后端立即创建 install record:
   - install_id: inst_xxx
   - extension_id: "unknown"
   - status: INSTALLING
3. 后端返回 {"install_id": "inst_xxx", "status": "INSTALLING"}
4. 前端开始轮询 ✅ (记录已存在)
5. 后台线程开始
6. 验证 ZIP:
   ├─ 成功 ✅ → 更新 extension_id，继续安装
   └─ 失败 ❌ → 更新 status=FAILED, error="原因"
7. 前端轮询 → 200 OK:
   {
     "status": "FAILED",
     "error": "Zip must contain exactly one top-level directory",
     "progress": 0
   }
8. 用户看到清晰的错误信息 ✅
```

## 代码修改

### 修改 1: 添加无外键检查的创建方法

**文件**: `agentos/core/extensions/registry.py`

```python
def create_install_record_without_fk(
    self,
    install_id: str,
    extension_id: str = "unknown",
    status: InstallStatus = InstallStatus.INSTALLING
) -> None:
    """
    Create installation record without foreign key constraint
    (for early creation before extension is validated)
    """
    def _insert(conn: sqlite3.Connection):
        # Temporarily disable foreign key checks
        conn.execute("PRAGMA foreign_keys = OFF")

        conn.execute("""
            INSERT INTO extension_installs (...)
            VALUES (?, ?, ?, ?, ?)
        """, (...))

        conn.commit()

        # Re-enable foreign key checks
        conn.execute("PRAGMA foreign_keys = ON")

    self._execute_write(_insert)
```

**为什么这样做**:
- `extension_installs` 表有外键约束: `FOREIGN KEY (extension_id) REFERENCES extensions(id)`
- 在验证之前不知道 extension_id
- 临时禁用外键检查，允许插入 "unknown"

### 修改 2: 上传 API 立即创建 record

**文件**: `agentos/webui/api/extensions.py`

#### 变更 1: 立即创建 record

```python
@router.post("/api/extensions/install")
async def install_extension_upload(file: UploadFile = File(...)):
    # ...保存临时文件...

    install_id = f"inst_{uuid.uuid4().hex[:12]}"

    # 立即创建 install record (在后台线程之前)
    registry = get_registry()
    registry.create_install_record_without_fk(
        install_id=install_id,
        extension_id="unknown",
        status=InstallStatus.INSTALLING
    )

    # 启动后台线程
    def run_installation():
        ...

    thread.start()

    return {"install_id": install_id, "status": "INSTALLING"}
```

#### 变更 2: 验证失败时更新 record

```python
def run_installation():
    try:
        # 验证 ZIP
        try:
            manifest, sha256, install_dir = installer.install_from_upload(...)
        except Exception as validation_error:
            # 验证失败 - 更新 install record
            registry.update_install_progress(
                install_id=install_id,
                progress=0,
                current_step="Validation failed"
            )
            registry.complete_install(
                install_id=install_id,
                status=InstallStatus.FAILED,
                error=str(validation_error)  # ← 保存错误信息
            )
            return  # 提前退出

        # 验证成功 - 更新 extension_id
        registry.update_install_progress(
            install_id=install_id,
            progress=10,
            current_step="Extension validated",
            extension_id=manifest.id  # ← 更新真实 ID
        )

        # 继续后续步骤...
```

#### 变更 3: 任何异常都更新 record

```python
except Exception as e:
    logger.error(f"Installation failed: {e}", exc_info=True)

    # 确保 install record 被标记为 FAILED
    try:
        registry.complete_install(
            install_id=install_id,
            status=InstallStatus.FAILED,
            error=str(e)  # ← 保存异常信息
        )
        logger.info(f"Install record marked as FAILED: {install_id}")
    except Exception as completion_error:
        logger.error(f"CRITICAL: Failed to complete install record: {completion_error}")
```

### 修改 3: URL 安装同样处理

**文件**: `agentos/webui/api/extensions.py`

应用同样的模式到 `install_extension_url`:
- ✅ 立即创建 install record
- ✅ 验证失败时更新 status=FAILED
- ✅ 任何异常都更新 record

## 效果对比

### Before ❌

```
用户上传错误的 ZIP
  ↓
前端轮询
  ↓
404 Not Found
  ↓
用户: "???" (不知道发生了什么)
```

### After ✅

```
用户上传错误的 ZIP
  ↓
前端轮询
  ↓
200 OK
{
  "status": "FAILED",
  "error": "Zip must contain exactly one top-level directory",
  "progress": 0,
  "current_step": "Validation failed"
}
  ↓
前端显示:
"✗ Installation failed: Zip must contain exactly one top-level directory"
  ↓
用户: "明白了，ZIP 结构不对" (知道如何修复)
```

## 错误信息示例

### 1. ZIP 结构错误
```json
{
  "status": "FAILED",
  "error": "Zip must contain exactly one top-level directory, found: {'manifest.json', 'install', 'docs'}",
  "progress": 0
}
```

### 2. Manifest 验证失败
```json
{
  "status": "FAILED",
  "error": "Manifest capability schema validation failed: missing required field 'command'",
  "progress": 0
}
```

### 3. 扩展已安装
```json
{
  "status": "FAILED",
  "error": "Extension 'tools.postman' is already installed. Please uninstall it first.",
  "progress": 10
}
```

### 4. 安装计划执行失败
```json
{
  "status": "FAILED",
  "error": "Command failed with exit code 127: postman: command not found",
  "progress": 80,
  "current_step": "Step 4/5: Verifying installation"
}
```

## 测试验证

### 测试 1: 错误的 ZIP 结构

```bash
# 创建错误结构的 ZIP（缺少顶层目录）
cd postman
zip -r test-bad.zip .

# 上传
curl -X POST http://localhost:9090/api/extensions/install \
  -F "file=@test-bad.zip"
# 返回: {"install_id": "inst_xxx", "status": "INSTALLING"}

# 轮询（1秒后）
curl http://localhost:9090/api/extensions/install/inst_xxx
# 返回: {"status": "FAILED", "error": "Zip must contain exactly one top-level directory"}
# 不是 404! ✅
```

### 测试 2: 正常的 ZIP

```bash
# 正确打包
zip -r postman-extension.zip postman

# 上传并轮询
# 应该看到进度从 0% 到 100% (或 FAILED)
# 不会出现 404 ✅
```

## 前端体验改进

### UI 显示

**进度条信息**:
```
Installing tools.postman...
Progress: 0%
Status: Validation failed
✗ Installation failed: Zip must contain exactly one top-level directory
```

**通知**:
```
🔴 Installation failed: Zip must contain exactly one top-level directory
```

**卡片显示**:
- 如果验证失败很早，扩展记录不会被创建，所以卡片不显示（正常）
- 如果验证成功但后续失败，卡片会显示，状态为 FAILED

## 技术细节

### 外键约束处理

**问题**: `extension_installs.extension_id` 有外键约束

**解决方案选项**:

1. ❌ 修改 schema 移除外键
   - 影响太大，破坏数据完整性

2. ❌ 允许 extension_id 为 NULL
   - 需要 schema 迁移

3. ✅ 临时禁用外键检查（当前方案）
   - `PRAGMA foreign_keys = OFF`
   - 插入后立即 `PRAGMA foreign_keys = ON`
   - 最小影响

### SQLiteWriter 兼容性

**潜在问题**: 每次新连接 PRAGMA 需要重新设置

**实际情况**:
- `_execute_write` 使用同一个连接
- PRAGMA 在事务内生效
- 测试验证正常工作

### 清理逻辑

旧的 install record 会被自动清理吗？

**不会**，但这是设计的：
- 保留历史记录用于调试
- 可以实现定期清理任务
- 前端只显示 active installs

## 文件清单

修改的文件：

1. ✅ `agentos/core/extensions/registry.py`
   - 添加 `create_install_record_without_fk()`

2. ✅ `agentos/webui/api/extensions.py`
   - `install_extension_upload`: 立即创建 record
   - `install_extension_url`: 立即创建 record
   - 验证失败时更新 record
   - 异常处理确保更新 record

3. ✅ `agentos/webui/static/js/views/ExtensionsView.js`
   - 显示进度容器（之前的修复）
   - 404 处理（之前的修复）

测试文件：
- ✅ `test_404_fix.py` - 验证 404 已修复

## 总结

### 问题

- ❌ 404 让用户不知道失败原因
- ❌ Install record 创建太晚
- ❌ 验证失败时无法查询状态

### 解决

- ✅ 立即创建 install record
- ✅ 验证失败也能查询到
- ✅ 返回清晰的错误信息
- ✅ 用户知道如何修复问题

### 用户体验

Before: "404? 什么都不知道 😔"

After: "哦，ZIP 结构不对，我重新打包一下 😊"

**彻底解决 404 问题！** ✅
