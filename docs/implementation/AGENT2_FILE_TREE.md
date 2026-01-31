# Agent2 文件组织结构

本文档展示了 Agent2 所有相关文件的组织结构。

## 项目文件树

```
AgentOS/
│
├── agentos/
│   └── webui/
│       └── agent2_monitor.py              # 🔥 核心代码（280 行）
│
├── scripts/
│   ├── start_agent2.sh                    # ▶️  启动脚本（60 行）
│   ├── stop_agent2.sh                     # ⏹️  停止脚本（50 行）
│   ├── status_agent2.sh                   # 📊 状态脚本（120 行）
│   ├── test_agent2.sh                     # 🧪 测试脚本（120 行）
│   ├── manage_multi_agent.sh              # 🎛️  统一管理（150 行）
│   └── AGENT2_SCRIPTS_README.md           # 📖 脚本说明（2000 字）
│
├── docs/
│   ├── agent2_monitor.md                  # 📚 完整技术文档（3000 字）
│   ├── agent2_quickstart.md               # 🚀 快速启动指南（2000 字）
│   ├── agent2_architecture.md             # 🏗️  架构设计文档（3500 字）
│   ├── agent2_best_practices.md           # 💡 最佳实践指南（3000 字）
│   ├── agent2_index.md                    # 📑 文档索引（1500 字）
│   └── AGENT2_README.md                   # 📘 综合说明文档（4000 字）
│
├── pyproject.toml                         # ⚙️  项目配置（已添加 requests）
│
├── AGENT2_SUMMARY.md                      # 📝 实现总结
├── AGENT2_DELIVERY.md                     # 📦 交付文档
└── AGENT2_FILE_TREE.md                    # 🌳 本文件
```

## 运行时文件树

```
~/.agentos/
└── multi_agent/
    ├── agent2.pid                         # 📌 进程 ID（运行时）
    ├── agent2.log                         # 📄 监控日志（持续增长）
    ├── agent2_status.json                 # 💾 状态文件（实时更新）
    └── restart_signal                     # 🚨 重启信号（临时文件）
```

## 文件分类视图

### 按类型分类

#### 代码文件（1 个）
```
agentos/webui/
└── agent2_monitor.py                      # Python 代码，~280 行
```

#### 脚本文件（5 个）
```
scripts/
├── start_agent2.sh                        # Bash 脚本，~60 行
├── stop_agent2.sh                         # Bash 脚本，~50 行
├── status_agent2.sh                       # Bash 脚本，~120 行
├── test_agent2.sh                         # Bash 脚本，~120 行
└── manage_multi_agent.sh                  # Bash 脚本，~150 行
```

#### 文档文件（9 个）
```
docs/
├── agent2_monitor.md                      # Markdown，~3000 字
├── agent2_quickstart.md                   # Markdown，~2000 字
├── agent2_architecture.md                 # Markdown，~3500 字
├── agent2_best_practices.md               # Markdown，~3000 字
├── agent2_index.md                        # Markdown，~1500 字
└── AGENT2_README.md                       # Markdown，~4000 字

scripts/
└── AGENT2_SCRIPTS_README.md               # Markdown，~2000 字

./
├── AGENT2_SUMMARY.md                      # Markdown，~500 字
├── AGENT2_DELIVERY.md                     # Markdown，~1000 字
└── AGENT2_FILE_TREE.md                    # Markdown，本文件
```

#### 配置文件（1 个）
```
./
└── pyproject.toml                         # TOML 配置文件
```

### 按功能分类

#### 核心功能
```
agentos/webui/agent2_monitor.py            # 主程序
  ├── WebUIMonitor 类
  │   ├── __init__()                       # 初始化
  │   ├── run()                            # 主循环
  │   ├── _run_monitoring_cycle()          # 监控周期
  │   ├── _diagnose()                      # 诊断
  │   ├── _fix_issue()                     # 修复
  │   └── _update_status()                 # 状态更新
  └── main()                               # 入口函数
```

#### 管理功能
```
scripts/
├── start_agent2.sh                        # 启动管理
│   ├── 检查是否运行
│   ├── 激活虚拟环境
│   ├── 后台启动
│   └── 验证成功
│
├── stop_agent2.sh                         # 停止管理
│   ├── 读取 PID
│   ├── 发送信号
│   ├── 等待退出
│   └── 清理文件
│
├── status_agent2.sh                       # 状态管理
│   ├── 检查进程
│   ├── 解析状态
│   ├── 显示日志
│   └── 格式化输出
│
├── test_agent2.sh                         # 测试管理
│   ├── 运行测试
│   ├── 验证功能
│   └── 报告结果
│
└── manage_multi_agent.sh                  # 统一管理
    ├── start {agent1|agent2|all}
    ├── stop {agent1|agent2|all}
    ├── restart {agent1|agent2|all}
    └── status {agent1|agent2|all}
```

#### 文档功能
```
docs/
├── agent2_quickstart.md                   # 新用户入门
│   ├── 5 分钟快速开始
│   ├── 常用命令
│   └── 常见问题
│
├── agent2_monitor.md                      # 开发者参考
│   ├── 功能说明
│   ├── 配置参数
│   └── API 文档
│
├── agent2_architecture.md                 # 架构设计
│   ├── 系统概览
│   ├── 架构图
│   ├── 数据流图
│   └── 时序图
│
├── agent2_best_practices.md               # 运维指南
│   ├── 部署配置
│   ├── 性能调优
│   ├── 故障排查
│   └── 维护清单
│
├── agent2_index.md                        # 文档导航
│   ├── 按场景查找
│   ├── 快速跳转
│   └── 学习路径
│
└── AGENT2_README.md                       # 综合说明
    ├── 文件清单
    ├── 使用场景
    └── 配置详解
```

## 文件依赖关系图

```
┌──────────────────────────────────────────────────────────┐
│                    依赖关系图                             │
└──────────────────────────────────────────────────────────┘

pyproject.toml
    ↓ (定义依赖)
agentos/webui/agent2_monitor.py
    ↓ (被调用)
scripts/start_agent2.sh ──────┐
    ↓ (启动)                  │
agent2 进程                    │ (管理)
    ↓ (创建)                  │
~/.agentos/multi_agent/        │
├── agent2.pid ←──────────────┤
├── agent2.log                │
├── agent2_status.json        │
└── restart_signal            │
    ↑ (读取/显示)             │
scripts/status_agent2.sh ──────┤
scripts/test_agent2.sh ────────┤
scripts/stop_agent2.sh ────────┘

docs/*.md
    ↓ (引用)
scripts/*.sh + agent2_monitor.py
```

## 文件大小统计

### 代码文件
```
agent2_monitor.py              ~12 KB
start_agent2.sh                ~2 KB
stop_agent2.sh                 ~2 KB
status_agent2.sh               ~4 KB
test_agent2.sh                 ~5 KB
manage_multi_agent.sh          ~6 KB
                              ------
总计（代码）                   ~31 KB
```

### 文档文件
```
agent2_monitor.md              ~15 KB
agent2_quickstart.md           ~12 KB
agent2_architecture.md         ~25 KB
agent2_best_practices.md       ~20 KB
agent2_index.md                ~10 KB
AGENT2_README.md               ~25 KB
AGENT2_SCRIPTS_README.md       ~12 KB
AGENT2_SUMMARY.md              ~5 KB
AGENT2_DELIVERY.md             ~10 KB
AGENT2_FILE_TREE.md            本文件
                              ------
总计（文档）                   ~134 KB
```

### 运行时文件（典型值）
```
agent2.pid                     ~10 bytes
agent2.log                     ~100 KB/天
agent2_status.json             ~2 KB
restart_signal                 ~200 bytes (临时)
```

## 访问路径速查

### 绝对路径

#### 代码
```bash
/Users/pangge/PycharmProjects/AgentOS/agentos/webui/agent2_monitor.py
```

#### 脚本
```bash
/Users/pangge/PycharmProjects/AgentOS/scripts/start_agent2.sh
/Users/pangge/PycharmProjects/AgentOS/scripts/stop_agent2.sh
/Users/pangge/PycharmProjects/AgentOS/scripts/status_agent2.sh
/Users/pangge/PycharmProjects/AgentOS/scripts/test_agent2.sh
/Users/pangge/PycharmProjects/AgentOS/scripts/manage_multi_agent.sh
```

#### 文档
```bash
/Users/pangge/PycharmProjects/AgentOS/docs/agent2_monitor.md
/Users/pangge/PycharmProjects/AgentOS/docs/agent2_quickstart.md
/Users/pangge/PycharmProjects/AgentOS/docs/agent2_architecture.md
/Users/pangge/PycharmProjects/AgentOS/docs/agent2_best_practices.md
/Users/pangge/PycharmProjects/AgentOS/docs/agent2_index.md
/Users/pangge/PycharmProjects/AgentOS/docs/AGENT2_README.md
```

#### 运行时文件
```bash
~/.agentos/multi_agent/agent2.pid
~/.agentos/multi_agent/agent2.log
~/.agentos/multi_agent/agent2_status.json
~/.agentos/multi_agent/restart_signal
```

### 相对路径（从项目根目录）

#### 代码
```bash
agentos/webui/agent2_monitor.py
```

#### 脚本
```bash
scripts/start_agent2.sh
scripts/stop_agent2.sh
scripts/status_agent2.sh
scripts/test_agent2.sh
scripts/manage_multi_agent.sh
```

#### 文档
```bash
docs/agent2_*.md
docs/AGENT2_README.md
AGENT2_*.md
```

## 快速命令

### 查看文件
```bash
# 查看核心代码
cat agentos/webui/agent2_monitor.py

# 查看脚本
cat scripts/start_agent2.sh

# 查看文档
cat docs/agent2_quickstart.md

# 查看状态
cat ~/.agentos/multi_agent/agent2_status.json
```

### 编辑文件
```bash
# 编辑核心代码
vim agentos/webui/agent2_monitor.py

# 编辑脚本
vim scripts/start_agent2.sh

# 编辑文档
vim docs/agent2_monitor.md
```

### 搜索内容
```bash
# 在所有文件中搜索
grep -r "check_health" .

# 在代码中搜索
grep -n "def _diagnose" agentos/webui/agent2_monitor.py

# 在文档中搜索
grep -r "快速启动" docs/
```

## 文件权限

### 推荐权限设置

```bash
# 代码文件（可读写）
chmod 644 agentos/webui/agent2_monitor.py

# 脚本文件（可执行）
chmod 755 scripts/start_agent2.sh
chmod 755 scripts/stop_agent2.sh
chmod 755 scripts/status_agent2.sh
chmod 755 scripts/test_agent2.sh
chmod 755 scripts/manage_multi_agent.sh

# 文档文件（可读写）
chmod 644 docs/agent2_*.md
chmod 644 AGENT2_*.md

# 运行时目录和文件
chmod 755 ~/.agentos/multi_agent
chmod 644 ~/.agentos/multi_agent/*
```

### 批量设置
```bash
# 从项目根目录执行
chmod 644 agentos/webui/agent2_monitor.py
chmod 755 scripts/*.sh
chmod 644 docs/agent2_*.md
chmod 644 AGENT2_*.md
```

## 备份建议

### 重要文件备份
```bash
# 备份核心代码
cp agentos/webui/agent2_monitor.py \
   agentos/webui/agent2_monitor.py.backup

# 备份脚本
tar -czf agent2_scripts_backup.tar.gz scripts/*agent2*.sh

# 备份文档
tar -czf agent2_docs_backup.tar.gz docs/agent2_*.md

# 备份状态文件
cp ~/.agentos/multi_agent/agent2_status.json \
   ~/.agentos/multi_agent/agent2_status.json.backup
```

### 完整备份
```bash
# 创建 Agent2 完整备份
tar -czf agent2_full_backup_$(date +%Y%m%d).tar.gz \
    agentos/webui/agent2_monitor.py \
    scripts/*agent2*.sh \
    scripts/manage_multi_agent.sh \
    docs/agent2_*.md \
    docs/AGENT2_README.md \
    AGENT2_*.md
```

## 文件统计

### 总体统计

| 类型 | 数量 | 总大小 |
|------|------|--------|
| Python 代码 | 1 | ~12 KB |
| Bash 脚本 | 5 | ~19 KB |
| Markdown 文档 | 9 | ~134 KB |
| 配置文件 | 1 | ~1 KB |
| **总计** | **16** | **~166 KB** |

### 代码统计

| 文件 | 行数 | 空行 | 注释 | 代码 |
|------|------|------|------|------|
| agent2_monitor.py | 280 | 40 | 60 | 180 |

### 脚本统计

| 文件 | 行数 | 函数数 |
|------|------|--------|
| start_agent2.sh | 60 | 0 |
| stop_agent2.sh | 50 | 0 |
| status_agent2.sh | 120 | 0 |
| test_agent2.sh | 120 | 0 |
| manage_multi_agent.sh | 150 | 8 |
| **总计** | **500** | **8** |

### 文档统计

| 文件 | 字数 | 章节数 |
|------|------|--------|
| agent2_monitor.md | 3000 | 12 |
| agent2_quickstart.md | 2000 | 10 |
| agent2_architecture.md | 3500 | 8 |
| agent2_best_practices.md | 3000 | 11 |
| agent2_index.md | 1500 | 8 |
| AGENT2_README.md | 4000 | 15 |
| AGENT2_SCRIPTS_README.md | 2000 | 10 |
| AGENT2_SUMMARY.md | 500 | 5 |
| AGENT2_DELIVERY.md | 1000 | 10 |
| **总计** | **~20000** | **89** |

## 版本信息

- **创建日期**: 2026-01-27
- **版本**: 1.0
- **文件数量**: 16
- **总大小**: ~166 KB
- **代码行数**: ~780 行
- **文档字数**: ~20000 字

## 维护说明

### 添加新文件时

1. 更新本文档的文件树
2. 更新文件统计
3. 更新 AGENT2_DELIVERY.md
4. 更新 docs/agent2_index.md

### 删除文件时

1. 从文件树中移除
2. 更新引用该文件的文档
3. 更新文件统计

### 重命名文件时

1. 更新所有引用
2. 更新文件树
3. 测试所有脚本

---

**文档维护**: 请保持本文档与实际文件结构同步。
