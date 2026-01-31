# 双覆盖率系统快速参考

## 一键命令

```bash
# 测量Scope Coverage (Task模块，84%目标)
./scripts/coverage_scope_task.sh

# 测量Project Coverage (全代码库，29%参考)
./scripts/coverage_project.sh

# 一次性测量两个
./scripts/coverage_both.sh
```

## 报告位置

```
Scope Coverage (Task模块专用):
├── coverage-scope.xml          # XML报告
└── htmlcov-scope/index.html    # HTML报告

Project Coverage (全代码库):
├── coverage-project.xml        # XML报告
└── htmlcov-project/index.html  # HTML报告
```

## 查看报告

```bash
# macOS
open htmlcov-scope/index.html
open htmlcov-project/index.html

# Linux
xdg-open htmlcov-scope/index.html
xdg-open htmlcov-project/index.html
```

## 两种覆盖率的区别

| 维度 | Scope Coverage | Project Coverage |
|------|----------------|------------------|
| **测量范围** | agentos/core/task/** | agentos/** |
| **测试范围** | tests/unit/task/** | tests/unit/** |
| **目标值** | 84%+ (交付验收) | 29%+ (趋势跟踪) |
| **用途** | 状态机质量门禁 | 整体成熟度监控 |
| **CI集成** | Pre-merge blocking | Nightly monitoring |

## 为什么需要两个指标？

- **Scope Coverage (84%)** 回答: "交付的状态机是否经过充分测试？"
- **Project Coverage (29%)** 回答: "整个代码库的测试成熟度如何？"

两者都是有效指标，但不应混淆。

## 下一步：Gate检查

即将创建的gate脚本：

```bash
# 检查Scope Coverage是否达标 (85%阈值)
python3 scripts/gate_coverage_scope.py

# 验证Project Coverage报告存在
python3 scripts/gate_coverage_project.py

# 一次性运行两个gate检查
./scripts/gate_coverage_all.sh
```

## 完整文档

详细文档请参考：`scripts/README_DUAL_COVERAGE.md`
