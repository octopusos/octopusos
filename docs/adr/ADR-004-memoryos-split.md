# ADR-004: MemoryOS 独立化

**状态**: ✅ 已接受  
**日期**: 2026-01-25  
**决策者**: AgentOS 架构团队

## 背景

AgentOS v0.2 中，Memory 作为内部模块与 AgentOS 紧密耦合：
- 直接访问 `memory_items` 表
- CLI 命令在 `agentos memory` 下
- 无法独立部署或跨项目复用

随着 Memory 规模增长和多项目需求，需要将其独立化为独立系统。

## 决策

将 MemoryOS 从 AgentOS 中分离，成为独立的系统/包：

1. **新包结构**: `memoryos/` 作为独立 Python 包
2. **抽象接口**: `MemoryStore` 接口，支持多后端
3. **API 边界**: AgentOS 通过 `MemoryClient` 消费，不直接访问数据库
4. **独立 CLI**: `memoryos` 命令，支持 init/migrate/export/import

## 架构

```
┌─────────────────────────────────────┐
│          AgentOS v0.3               │
│                                     │
│  ┌──────────────────────────────┐  │
│  │    MemoryClient (API)        │  │
│  └──────────┬───────────────────┘  │
│             │                       │
└─────────────┼───────────────────────┘
              │ API 边界
┌─────────────┼───────────────────────┐
│             ▼                       │
│  ┌──────────────────────────────┐  │
│  │    MemoryOS Core             │  │
│  │  ┌────────────────────────┐  │  │
│  │  │  MemoryStore Interface │  │  │
│  │  └─────────┬──────────────┘  │  │
│  │            │                 │  │
│  │  ┌─────────▼─────────────┐  │  │
│  │  │ SqliteMemoryStore     │  │  │
│  │  └───────────────────────┘  │  │
│  │  ┌───────────────────────┐  │  │
│  │  │ RemoteMemoryStore     │  │  │
│  │  │ (HTTP/gRPC stub)      │  │  │
│  │  └───────────────────────┘  │  │
│  └──────────────────────────────┘  │
│          MemoryOS                   │
└─────────────────────────────────────┘
```

## 协议

### memory_query.schema.json (新增)

```json
{
  "query": "search text",
  "filters": {
    "scope": "project",
    "type": "convention",
    "tags": ["frontend"],
    "confidence_min": 0.5
  },
  "top_k": 20,
  "include_expired": false
}
```

### memory_context.schema.json (新增)

```json
{
  "context_blocks": [
    {
      "type": "global",
      "memories": [...]
    },
    {
      "type": "project",
      "memories": [...]
    }
  ],
  "metadata": {
    "total_memories": 42,
    "build_time_ms": 150
  }
}
```

## 迁移路径

1. **Phase 1**: 创建 `memoryos/` 包，保持 AgentOS 双写（同时写新旧）
2. **Phase 2**: AgentOS 切换到只读新 API
3. **Phase 3**: 删除 AgentOS 中的 Memory 直接访问代码

## 兼容性保证

**不变量（Invariants）**:
- 无 MemoryPack 不允许执行（v0.2 护城河 #1）
- MemoryItem schema 向后兼容
- 现有 memory_items 数据可迁移

**版本控制**:
- `memoryos_version`: 独立版本号
- `agentos_version`: 记录兼容的 AgentOS 版本

## 后果

**优势**:
- Memory 可独立部署、扩展
- 支持多后端（SQLite/Postgres/远程）
- 跨项目复用 Memory
- 独立测试和发布

**劣势**:
- 增加系统复杂度
- 需要维护 API 边界
- 迁移成本

## 验收标准

- [ ] MemoryOS 可独立运行（init/migrate/search）
- [ ] AgentOS 通过 MemoryClient 访问，无直接数据库访问
- [ ] 所有 v0.2 Memory 测试通过
- [ ] 数据迁移脚本完整
- [ ] API 有完整的 schema 定义

---

**相关**: ADR-005, ADR-006
