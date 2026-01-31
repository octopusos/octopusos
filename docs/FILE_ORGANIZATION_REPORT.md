# 项目文件整理报告

**整理时间**: 2026-01-30

## 整理概况

根目录从 **463 个零散文件** 减少到 **13 个核心文件**，清理率达到 **97.2%**。

## 整理统计

### 文件移动统计

| 目标目录 | 文件数量 | 说明 |
|---------|---------|------|
| `docs/archive/` | 391 | Markdown 文档、文本文件 |
| `tests/manual/` | 26 | Python 测试脚本 |
| `tests/manual/html/` | 12 | HTML 测试页面 |
| `scripts/` | 96 | Shell 脚本及子目录 |
| `scripts/tools/` | 27 | Python 工具脚本、JS 脚本 |
| `scripts/migrations/` | 7 | SQL 数据库迁移脚本 |
| `logs/archive/` | 1 | 日志文件 |
| `reports/coverage/` | 570 | 覆盖率报告和 htmlcov 目录 |
| `exports/` | - | ZIP 压缩包 |
| `tmp/` | - | 临时和示例数据库 |
| **删除** | ~20 | 空文件、临时数据库文件 |

### 根目录保留文件（13个）

根目录现在只保留以下核心文件：

#### 项目配置文件
- `pyproject.toml` - Python 项目配置
- `jest.config.js` - Jest 测试配置
- `playwright.config.js` - Playwright E2E 测试配置
- `docker-compose.yml` - Docker 编排配置
- `Dockerfile.pipeline` - Pipeline Docker 配置
- `AgentOS.sln` - Visual Studio 解决方案文件
- `uv.lock` - UV 包管理器锁文件

#### 文档文件
- `README.md` - 项目说明
- `LICENSE` - 开源协议
- `NOTICE.md` - 版权声明
- `SECURITY.md` - 安全政策
- `CONTRIBUTING.md` - 贡献指南

#### 版本文件
- `VERSION` - 版本号

## 整理规则

### 1. Markdown 文档 (.md)
- **目标**: `docs/archive/`
- **保留**: README.md, LICENSE, NOTICE.md, SECURITY.md, CONTRIBUTING.md
- **包含**: 所有报告、指南、说明文档

### 2. 测试脚本 (test_*.py)
- **目标**: `tests/manual/`
- **说明**: 手动测试和验证脚本

### 3. 测试页面 (test_*.html, demo_*.html)
- **目标**: `tests/manual/html/`
- **说明**: HTML 测试页面和演示页面

### 4. Shell 脚本 (*.sh)
- **目标**: `scripts/`
- **说明**: 各类 Shell 脚本

### 5. Python 工具 (*.py, 非 test_*.py)
- **目标**: `scripts/tools/`
- **说明**: 工具脚本、数据处理脚本

### 6. SQL 脚本 (*.sql)
- **目标**: `scripts/migrations/`
- **说明**: 数据库迁移和修复脚本

### 7. JavaScript 文件 (*.js)
- **目标**: `scripts/tools/`
- **保留**: jest.config.js, playwright.config.js
- **说明**: 工具和验证脚本

### 8. 日志文件 (*.log)
- **目标**: `logs/archive/`
- **说明**: 历史日志文件

### 9. 覆盖率报告
- **目标**: `reports/coverage/`
- **包含**: coverage*.xml, htmlcov* 目录

### 10. 压缩包 (*.zip)
- **目标**: `exports/`
- **说明**: 导出的扩展包

### 11. 删除规则
- 空文件 (0 字节)
- 临时数据库文件 (*.db-shm, *.db-wal)
- 奇怪的文件名 (如 `<sqlite3.Connection object at ...>`)
- 测试数据库 (test_*.db) → 移至 tmp/

## 目录结构

整理后的项目目录结构更加清晰：

```
AgentOS/
├── agentos/              # 核心代码
├── tests/                # 测试代码
│   └── manual/          # 手动测试脚本
│       └── html/        # HTML 测试页面
├── docs/                 # 文档
│   └── archive/         # 历史文档和报告
├── scripts/              # 脚本
│   ├── tools/           # 工具脚本
│   └── migrations/      # SQL 迁移脚本
├── logs/                 # 日志
│   └── archive/         # 历史日志
├── reports/              # 报告
│   └── coverage/        # 覆盖率报告
├── exports/              # 导出文件
├── tmp/                  # 临时文件
├── pyproject.toml        # Python 项目配置
├── README.md             # 项目说明
└── ...                   # 其他核心配置文件
```

## 维护建议

### 1. 防止根目录污染
- 测试脚本应该放在 `tests/manual/`
- 工具脚本应该放在 `scripts/tools/`
- 文档应该放在 `docs/` 或 `docs/archive/`
- 日志应该放在 `logs/`

### 2. 临时文件处理
- 使用 `tmp/` 目录存放临时文件
- 定期清理 `tmp/` 目录
- 在 `.gitignore` 中忽略临时文件

### 3. 报告和文档
- 开发过程中的报告放在 `docs/archive/`
- 用户文档放在 `docs/`
- API 文档可以考虑放在 `docs/api/`

### 4. 测试相关
- 单元测试保持在 `tests/`
- 手动测试脚本放在 `tests/manual/`
- 集成测试可以考虑 `tests/integration/`

## 自动整理

已创建自动整理脚本：`scripts/organize_files.sh`

可以定期运行此脚本来保持根目录整洁：

```bash
bash scripts/organize_files.sh
```

## 注意事项

1. **备份**: 整理前已有 git 版本控制保护
2. **配置文件**: 根目录配置文件已正确保留
3. **数据库**: 临时和测试数据库已移至 tmp/
4. **覆盖率**: 所有覆盖率报告已整理到 reports/coverage/

## 下一步

建议添加以下规则到开发流程：

1. 代码审查时检查是否有文件放在根目录
2. CI/CD 中添加检查，警告根目录有新增非配置文件
3. 更新 `.gitignore` 忽略常见的临时文件模式
4. 在开发文档中明确文件放置规则

## 总结

通过这次整理：
- ✅ 根目录清理了 97.2% 的文件
- ✅ 文件按类型分类存放
- ✅ 删除了临时和空文件
- ✅ 保留了所有重要文件
- ✅ 创建了清晰的目录结构
- ✅ 建立了未来的维护规则

项目目录现在更加整洁和易于维护！
