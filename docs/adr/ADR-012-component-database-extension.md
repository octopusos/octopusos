# ADR-012: 组件数据库扩展标准流程

**状态**: 已接受（Accepted）
**日期**: 2026-02-01
**决策者**: Architecture Team
**相关ADR**: ADR-011 (时间戳契约)

---

## 背景

AgentOS采用"单组件单数据库"架构原则，每个系统组件拥有独立的SQLite数据库文件，存放于统一路径结构下。随着系统功能扩展，需要明确组件级数据库扩展的标准流程，确保架构约束在横向扩展时仍然有效。

Skill组件的引入是首个按标准流程执行的案例。

---

## 决策

### 核心约束（不可违反）

所有组件数据库必须遵循以下约束：

1. **单组件单数据库**：每个组件仅允许一个SQLite数据库文件
2. **统一命名**：数据库文件名必须为 `db.sqlite`
3. **统一路径**：所有数据库存放于 `~/.agentos/store/<component>/db.sqlite`
4. **禁止共享**：组件间不允许共享数据库或跨组件访问
5. **禁止第二DB**：禁止在任何其他路径创建数据库文件

### 扩展标准流程

#### 步骤1：更新白名单（必须）

修改 `agentos/core/storage/paths.py`：

```python
ALLOWED_COMPONENTS = {
    "agentos",       # 核心任务与会话管理
    "memoryos",      # 长期记忆与向量存储
    "brainos",       # 知识图谱与决策记录
    "communicationos", # Agent间通信与证据链
    "kb",            # 知识库索引
    "skill",         # 技能定义与执行历史（新增）
    # 未来组件在此添加
}
```

#### 步骤2：验证4强Gate（必须）

执行以下测试，确保新组件自动纳入门控：

```bash
# Gate-1: 文件系统扫描
python3 scripts/db_scan_check.py

# Gate-2: 代码扫描
python3 scripts/code_scan_no_db_literal.py

# Gate-3: 迁移测试
python3 tests/test_migration_no_second_db.py

# Gate-4: WAL并发测试
python3 tests/test_wal_enabled_all_components.py
python3 tests/test_concurrent_writes.py
```

所有Gate必须PASS。

#### 步骤3：初始化数据库Schema（按需）

如果组件需要特定表结构，在 `agentos/store/migrations/` 创建迁移脚本：

```sql
-- schema_v{N}_{component}_init.sql
CREATE TABLE IF NOT EXISTS {component}_data (
    id TEXT PRIMARY KEY,
    created_at INTEGER NOT NULL,  -- epoch_ms
    -- 其他字段
);
```

#### 步骤4：更新文档（必须）

在组件README或API文档中说明：
- 数据库路径
- Schema版本
- 访问方式（通过 `component_db_path("component")` 或 `get_engine("component")`）

---

## 当前组件清单

| 组件 | 数据库路径 | 用途 | 状态 |
|------|-----------|------|------|
| agentos | `~/.agentos/store/agentos/db.sqlite` | 核心任务、会话、事件 | Active |
| memoryos | `~/.agentos/store/memoryos/db.sqlite` | 长期记忆、向量存储 | Active |
| brainos | `~/.agentos/store/brainos/db.sqlite` | 知识图谱、决策记录 | Active |
| communicationos | `~/.agentos/store/communicationos/db.sqlite` | Agent通信、证据链 | Active |
| kb | `~/.agentos/store/kb/db.sqlite` | 知识库索引 | Active |
| skill | `~/.agentos/store/skill/db.sqlite` | 技能定义与执行历史 | Active |

---

## 未来扩展示例

假设需要添加 `ToolOS` 组件：

1. 在 `paths.py` 的 `ALLOWED_COMPONENTS` 添加 `"toolos"`
2. 运行4强Gate验证
3. 创建迁移脚本 `schema_v{N}_toolos_init.sql`
4. 更新本ADR的组件清单表

**无需修改**：
- `db_scan_check.py`（自动枚举白名单）
- `test_wal_enabled_all_components.py`（自动枚举组件）
- `test_migration_no_second_db.py`（自动枚举组件）
- `engines.py`（Engine单例逻辑）

---

## 反模式（禁止）

以下操作违反架构约束：

❌ **创建第二个数据库文件**
```python
# 错误
db_path = Path("skill_temp.db")
```

❌ **硬编码数据库路径**
```python
# 错误
db_path = "~/.agentos/skill.db"
```

❌ **跨组件直接访问数据库**
```python
# 错误：brainos访问agentos的数据库
conn = sqlite3.connect(component_db_path("agentos"))
```

✅ **正确做法**
```python
from agentos.core.storage.paths import component_db_path
from agentos.core.storage.engines import get_engine

# 访问本组件数据库
db_path = component_db_path("skill")
engine = get_engine("skill")
```

---

## 自动化保障

以下机制确保架构约束在扩展时自动生效：

1. **代码扫描Gate**：CI/CD自动检查硬编码路径
2. **文件系统扫描Gate**：检测非法数据库文件
3. **迁移测试Gate**：验证迁移工具不创建第二DB
4. **WAL并发测试Gate**：验证所有组件并发安全

---

## 参考

- `agentos/core/storage/paths.py` - 路径管理与白名单
- `agentos/core/storage/engines.py` - Engine单例管理
- `scripts/db_scan_check.py` - 文件系统扫描工具
- `scripts/code_scan_no_db_literal.py` - 代码扫描工具
- ADR-011 - 时间戳契约（epoch_ms规范）

---

## 变更历史

- 2026-02-01: 初始版本，定义标准流程
- 2026-02-01: Skill组件扩展（首个标准化案例）
