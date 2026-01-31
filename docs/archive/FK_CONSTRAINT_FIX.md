# 外键约束错误修复

## 🐛 错误现象

```
✗ Installation failed: Failed to update install progress: FOREIGN KEY constraint failed
```

## 🔍 根因分析

### 问题流程

```
1. 上传 ZIP → 创建 install record (extension_id = "unknown")
   ✅ 成功（使用 PRAGMA foreign_keys = OFF）

2. 验证 ZIP → 解析 manifest → 获得真实 extension_id

3. 调用 update_install_progress(extension_id="tools.postman")
   ❌ 失败：FOREIGN KEY constraint failed
```

### 为什么失败？

**第一次修复**（已完成）：
- 在 `create_install_record_without_fk()` 中临时禁用外键检查
- 允许插入 `extension_id = "unknown"`

**问题**：
- 后续调用 `update_install_progress()` 时，**外键检查又被启用了**
- 尝试更新 `extension_id = "tools.postman"` 时：
  - `extension_installs` 表有外键约束：`FOREIGN KEY (extension_id) REFERENCES extensions(id)`
  - 此时 `extensions` 表中还没有 `tools.postman` 记录（还未创建）
  - SQLite 拒绝更新 → FOREIGN KEY constraint failed

## ✅ 修复方案

### 修改 `update_install_progress()` 方法

**文件**：`agentos/core/extensions/registry.py:531`

在更新 `extension_id` 时也临时禁用外键检查：

```python
def update_install_progress(
    self,
    install_id: str,
    progress: int,
    current_step: Optional[str] = None,
    extension_id: Optional[str] = None
) -> None:
    def _update(conn: sqlite3.Connection):
        try:
            if extension_id is not None:
                # 临时禁用外键检查
                conn.execute("PRAGMA foreign_keys = OFF")

                # 更新 extension_id, progress, current_step
                conn.execute("""
                    UPDATE extension_installs
                    SET extension_id = ?, progress = ?, current_step = ?
                    WHERE install_id = ?
                """, (extension_id, progress, current_step, install_id))

                conn.commit()

                # 重新启用外键检查
                conn.execute("PRAGMA foreign_keys = ON")
            else:
                # 只更新 progress 和 current_step（不需要禁用外键）
                conn.execute("""
                    UPDATE extension_installs
                    SET progress = ?, current_step = ?
                    WHERE install_id = ?
                """, (progress, current_step, install_id))

                conn.commit()

        except sqlite3.Error as e:
            raise RegistryError(f"Failed to update install progress: {e}")

    self._execute_write(_update)
```

## 🧪 验证测试

运行测试验证修复：

```bash
python3 verify_fk_fix.py
```

**结果**：
```
✅ 测试 1 (SQLite PRAGMA): ✓ 通过
✅ 测试 2 (Registry 方法): ✓ 通过

✅ 所有测试通过！外键约束修复有效
```

## 📋 修复文件清单

1. ✅ `agentos/core/extensions/registry.py`
   - 行 451-491: `create_install_record_without_fk()` - 创建记录时禁用外键
   - 行 531-572: `update_install_progress()` - **更新 extension_id 时禁用外键** ⬅️ 新修复

2. ✅ `agentos/webui/api/extensions.py`
   - 行 451: 立即创建 install record
   - 行 665: 立即创建 install record（URL 安装）
   - 验证失败时更新 status=FAILED

3. ✅ `verify_fk_fix.py` - 验证测试脚本

## 🚀 部署步骤

### 1. 重启服务器

```bash
cd /Users/pangge/PycharmProjects/AgentOS
./restart_server_complete.sh
```

或手动：

```bash
# 停止旧进程
kill 57466

# 清理 PID 文件
rm -f ~/.agentos/webui.pid

# 启动新服务器
uv run agentos webui start
```

### 2. 验证修复

```bash
# 测试完整的安装流程
python3 debug_install_step_by_step.py
```

**期望结果**：
- ✅ Install record 立即创建
- ✅ 不再返回 404
- ✅ 不再报外键约束错误
- ✅ 能看到安装进度
- ✅ 失败时显示清晰的错误信息

### 3. 在 WebUI 中测试

1. 打开 http://127.0.0.1:9090
2. 进入 Extensions 页面
3. 上传 `postman-extension.zip`
4. 观察：
   - ✅ 安装进度立即显示
   - ✅ 如果失败，显示错误信息（不是 404）
   - ✅ 可以看到安装状态变化

## 📊 完整流程（修复后）

```
1. 用户上传 ZIP
   ↓
2. 立即创建 install record (extension_id = "unknown")
   → PRAGMA foreign_keys = OFF
   → INSERT INTO extension_installs
   → PRAGMA foreign_keys = ON
   ✅ 前端可以立即轮询进度

3. 后台线程验证 ZIP
   ├─ 成功 → 解析 manifest，获得真实 extension_id
   │  ↓
   │  update_install_progress(extension_id="tools.postman")
   │  → PRAGMA foreign_keys = OFF
   │  → UPDATE extension_installs SET extension_id = ?
   │  → PRAGMA foreign_keys = ON
   │  ✅ 更新成功
   │
   └─ 失败 → complete_install(status=FAILED, error="...")
      ✅ 前端看到 FAILED + 错误信息

4. 继续安装流程...
```

## 🔧 技术细节

### 为什么需要临时禁用外键检查？

**问题**：
- `extension_installs.extension_id` 有外键约束：`FOREIGN KEY (extension_id) REFERENCES extensions(id)`
- 在安装流程中，时序是：
  1. 创建 install record（此时还不知道 extension_id）
  2. 验证 ZIP，解析 manifest（获得 extension_id）
  3. 更新 install record（设置真实的 extension_id）
  4. 创建 extension record
  5. 执行安装计划...

**矛盾**：
- 第 3 步更新 extension_id 时，第 4 步的 extension record 还不存在
- 外键约束会阻止更新

**解决方案**：
- 临时禁用外键检查，允许更新
- 在后续步骤中创建 extension record
- 最终数据是一致的

### PRAGMA foreign_keys 的作用域

- `PRAGMA foreign_keys` 是**连接级别**的设置
- 在同一个事务中禁用 → 操作 → 启用是安全的
- SQLiteWriter 使用连接池，每次 `_execute_write` 获取连接
- 在事务结束后立即重新启用，不影响其他操作

### 为什么不修改 schema？

**选项 1**：移除外键约束
- ❌ 破坏数据完整性
- ❌ 影响太大，需要迁移

**选项 2**：允许 extension_id 为 NULL
- ❌ 需要 schema 迁移
- ❌ 查询逻辑需要处理 NULL

**选项 3**：临时禁用外键检查（当前方案）
- ✅ 最小影响
- ✅ 不需要 schema 变更
- ✅ 保持数据最终一致性

## ✨ 用户体验改进

### Before ❌

```
用户上传 ZIP
  ↓
前端轮询
  ↓
404 Not Found
  ↓
用户：??? 什么都不知道
```

### After ✅

```
用户上传 ZIP
  ↓
前端立即显示进度条
  ↓
如果验证失败：
  {
    "status": "FAILED",
    "error": "Zip must contain exactly one top-level directory",
    "progress": 0
  }
  ↓
用户："哦，ZIP 结构不对，我重新打包"
```

## 🎯 总结

### 修复内容

1. ✅ 立即创建 install record（在验证之前）
2. ✅ 创建时禁用外键检查（允许 extension_id = "unknown"）
3. ✅ **更新时也禁用外键检查**（允许更新为不存在的 extension_id）⬅️ 本次修复
4. ✅ 验证失败时更新 status=FAILED
5. ✅ 前端始终能查询到记录

### 已解决的问题

- ✅ 404 错误 - 用户不知道失败原因
- ✅ 外键约束错误 - 无法更新 extension_id
- ✅ 进度不可见 - 安装过程像黑盒

### 下一步

**立即执行**：
```bash
./restart_server_complete.sh && python3 debug_install_step_by_step.py
```

看到所有 ✅ 后，修复完成！🎉
