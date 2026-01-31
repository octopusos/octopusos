# AgentOS 架构约束声明

**版本**: v1.0
**生效日期**: 2026-02-01
**强制级别**: P0（任何违反都是阻塞性错误）

---

## 🔒 数据库架构约束（不可违反）

### 约束1: 单组件单数据库

每个系统组件**仅允许**一个SQLite数据库文件。

```python
# ✅ 正确
component_db_path("skill")  # ~/.agentos/store/skill/db.sqlite

# ❌ 错误：创建第二个数据库
skill_cache_db = Path("skill_cache.db")
```

### 约束2: 统一命名规范

所有数据库文件名**必须**为 `db.sqlite`。

```
✅ ~/.agentos/store/skill/db.sqlite
❌ ~/.agentos/store/skill/skills.db
❌ ~/.agentos/store/skill/skill_data.sqlite
```

### 约束3: 统一路径结构

所有数据库**必须**存放于 `~/.agentos/store/<component>/db.sqlite`。

```python
# ✅ 正确
from agentos.core.storage.paths import component_db_path
db = component_db_path("skill")

# ❌ 错误：硬编码路径
db = Path("~/.agentos/skill.db")
db = Path("store/skill.db")
db = Path.cwd() / "skill.db"
```

### 约束4: 禁止跨组件访问

组件间**禁止**直接访问彼此的数据库。

```python
# ❌ 错误：skill访问agentos数据库
conn = sqlite3.connect(component_db_path("agentos"))

# ✅ 正确：通过API访问
from agentos.core.task.service import TaskService
tasks = TaskService().list_tasks()
```

### 约束5: 禁止动态路径

**禁止**在运行时动态指定数据库路径（除非用于测试临时目录）。

```python
# ❌ 错误：接受用户传入的路径
def init_db(custom_path: str):
    conn = sqlite3.connect(custom_path)

# ✅ 正确：强制使用组件路径
def init_db(component: str):
    db = component_db_path(component)
    conn = sqlite3.connect(db)
```

---

## 🚦 4强Gate门控（必须通过）

任何架构变更必须通过以下4个强Gate：

### Gate-1: SCAN-PASS
```bash
python3 scripts/db_scan_check.py
```
- 必须输出 "✅ 数据库扫描检查通过"
- 只允许白名单中的组件数据库
- 在不同cwd下执行结果一致

### Gate-2: CODE-PASS
```bash
python3 scripts/code_scan_no_db_literal.py
```
- 核心模块（agentos/core/）必须0违规
- 禁止硬编码数据库路径
- 禁止使用 `sqlite:///`、`.db`、`.sqlite` 字符串

### Gate-3: MIGRATE-PASS
```bash
python3 tests/test_migration_no_second_db.py
```
- 迁移工具不得创建第二个数据库
- 迁移前后数据库数量一致
- 所有路径仍在白名单内

### Gate-4: CONCURRENCY-PASS
```bash
python3 tests/test_wal_enabled_all_components.py
python3 tests/test_concurrent_writes.py
```
- 所有组件启用WAL模式
- busy_timeout=30000ms
- 并发写入测试通过

---

## 📋 允许的组件清单

当前允许的组件（定义于 `agentos/core/storage/paths.py`）：

```python
ALLOWED_COMPONENTS = {
    "agentos",        # 核心任务与会话管理
    "memoryos",       # 长期记忆与向量存储
    "brainos",        # 知识图谱与决策记录
    "communicationos", # Agent间通信与证据链
    "kb",             # 知识库索引
    "skill",          # 技能定义与执行历史
}
```

### 添加新组件的标准流程

参见 `docs/adr/ADR-012-component-database-extension.md`

---

## ⚠️ 给未来Agent的警告

**如果你是一个AI agent，正在修改AgentOS代码**：

1. **禁止创建新的数据库文件**，除非：
   - 你在 `ALLOWED_COMPONENTS` 添加了新组件
   - 重新运行了4强Gate验证
   - 更新了ADR-012文档

2. **禁止硬编码数据库路径**，必须使用：
   ```python
   from agentos.core.storage.paths import component_db_path
   db = component_db_path("component_name")
   ```

3. **禁止绕过门控**：
   - 不要修改 `db_scan_check.py` 来隐藏违规
   - 不要在 `ALLOWED_FILES` 添加白名单来绕过代码扫描
   - 任何架构变更必须通过4强Gate

4. **测试文件也要遵守**：
   - 使用 `tmp_path` fixture创建临时数据库
   - 不要在项目目录创建测试DB文件

---

## 🔍 如何验证你的修改是否合规

```bash
# 1. 运行4强Gate
./scripts/run_all_gates.sh  # 如果存在
# 或手动运行上面的4个Gate命令

# 2. 检查git diff
git diff agentos/core/storage/paths.py
# ALLOWED_COMPONENTS是否被意外修改？

# 3. 搜索硬编码路径
rg '".*\.db"' agentos/ --type py | grep -v storage/
rg '".*\.sqlite"' agentos/ --type py | grep -v storage/
```

---

## 📞 联系与反馈

如果你认为某个约束过于严格，或需要合理的例外情况：

1. 查看 `docs/adr/ADR-012-component-database-extension.md`
2. 提出Issue并说明理由
3. 等待架构团队审核

**不要直接绕过约束**，这会破坏整个系统的稳定性。

---

**最后更新**: 2026-02-01
**相关文档**: ADR-012, 4强Gate验收报告
