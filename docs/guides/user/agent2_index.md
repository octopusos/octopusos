# Agent2 文档索引

Agent2 是 AgentOS WebUI 的健康监控和自动修复组件。本索引帮助你快速找到所需文档。

## 文档导航

### 🚀 快速开始

| 文档 | 用途 | 阅读时间 |
|------|------|---------|
| [快速启动指南](./agent2_quickstart.md) | 5 分钟快速上手 | 5 分钟 |
| [AGENT2_README](./AGENT2_README.md) | 综合说明文档 | 15 分钟 |

**适合人群**: 新用户，想快速开始使用 Agent2

**内容概要**:
- 安装依赖
- 启动服务
- 基本操作
- 常见问题

### 📚 完整文档

| 文档 | 用途 | 阅读时间 |
|------|------|---------|
| [完整技术文档](./agent2_monitor.md) | 详细功能说明和配置 | 30 分钟 |
| [架构设计文档](./agent2_architecture.md) | 系统架构和设计原理 | 20 分钟 |

**适合人群**: 开发者，需要深入了解 Agent2

**内容概要**:
- 功能特性详解
- 监控逻辑和修复策略
- 状态文件格式
- 与 Agent1 协同工作
- 架构图和数据流
- 时序图和错误处理

### 🛠️ 运维指南

| 文档 | 用途 | 阅读时间 |
|------|------|---------|
| [最佳实践指南](./agent2_best_practices.md) | 部署和运维最佳实践 | 25 分钟 |

**适合人群**: 运维人员，生产环境部署

**内容概要**:
- 开发/测试/生产环境配置
- systemd/launchd 配置
- 日志监控和轮转
- 告警集成（邮件/Slack/PagerDuty）
- 性能调优
- 故障排查流程
- 维护清单

### 📋 参考文档

| 文档 | 用途 |
|------|------|
| [AGENT2_SUMMARY.md](../AGENT2_SUMMARY.md) | 实现总结和文件清单 |
| 脚本源码 | [scripts/](../scripts/) |
| 核心代码 | [agentos/webui/agent2_monitor.py](../agentos/webui/agent2_monitor.py) |

## 按场景查找

### 我是新用户，刚开始使用

1. 阅读 [快速启动指南](./agent2_quickstart.md)
2. 运行 `bash scripts/start_agent2.sh`
3. 查看 [常见问题](#常见问题快速跳转)

### 我要在生产环境部署

1. 阅读 [最佳实践指南](./agent2_best_practices.md) - 生产环境部分
2. 配置 systemd/launchd
3. 设置日志轮转
4. 配置告警通知

### 我遇到了问题

1. 查看 [故障排查流程](./agent2_best_practices.md#故障排查流程)
2. 检查日志: `tail -f ~/.agentos/multi_agent/agent2.log`
3. 查看状态: `bash scripts/status_agent2.sh`
4. 参考 [常见问题](#常见问题快速跳转)

### 我要修改或扩展 Agent2

1. 阅读 [架构设计文档](./agent2_architecture.md)
2. 查看 [扩展开发](#扩展开发快速跳转)
3. 参考核心代码: `agentos/webui/agent2_monitor.py`

### 我要理解工作原理

1. 阅读 [架构设计文档](./agent2_architecture.md)
2. 查看架构图和数据流图
3. 理解时序图
4. 阅读 [完整技术文档](./agent2_monitor.md)

## 常见问题快速跳转

### 启动和运行

| 问题 | 文档位置 |
|------|---------|
| 如何启动 Agent2? | [快速启动 - 启动服务](./agent2_quickstart.md#2-启动-agent2) |
| 如何查看状态? | [快速启动 - 验证运行](./agent2_quickstart.md#4-验证运行状态) |
| 如何停止 Agent2? | [快速启动 - 常用命令](./agent2_quickstart.md#常用命令) |
| Agent2 启动失败? | [README - 常见问题 Q1](./AGENT2_README.md#q1-agent2-启动后立即退出) |

### 监控和诊断

| 问题 | 文档位置 |
|------|---------|
| Agent2 监控哪些指标? | [完整文档 - 监控检查项](./agent2_monitor.md#监控检查项) |
| 如何查看实时日志? | [README - 查看日志](./AGENT2_README.md#4-查看日志) |
| 状态文件格式? | [README - 状态文件格式](./AGENT2_README.md#状态文件格式) |
| 一直报告 down 状态? | [README - 常见问题 Q2](./AGENT2_README.md#q2-agent2-一直报告-down-状态) |

### 配置和调优

| 问题 | 文档位置 |
|------|---------|
| 如何调整监控频率? | [README - 配置调优](./AGENT2_README.md#调整监控频率) |
| 如何调整失败阈值? | [README - 配置调优](./AGENT2_README.md#调整故障阈值) |
| 性能影响如何? | [README - 性能影响](./AGENT2_README.md#性能影响) |
| 生产环境配置? | [最佳实践 - 生产环境](./agent2_best_practices.md#生产环境) |

### 扩展开发快速跳转

| 主题 | 文档位置 |
|------|---------|
| 添加自定义检查 | [README - 扩展开发](./AGENT2_README.md#添加自定义检查) |
| 添加告警通知 | [最佳实践 - 告警集成](./agent2_best_practices.md#告警集成) |
| 理解架构设计 | [架构文档](./agent2_architecture.md) |
| 修改修复策略 | [架构文档 - 修复模块](./agent2_architecture.md#4-修复模块-fix-module) |

## 文档关系图

```
agent2_index.md (本文档)
    │
    ├─── 快速开始
    │       ├─ agent2_quickstart.md    (5 分钟上手)
    │       └─ AGENT2_README.md        (综合说明)
    │
    ├─── 深入理解
    │       ├─ agent2_monitor.md       (完整功能文档)
    │       └─ agent2_architecture.md  (架构设计)
    │
    ├─── 运维部署
    │       └─ agent2_best_practices.md (最佳实践)
    │
    └─── 参考资料
            └─ AGENT2_SUMMARY.md       (实现总结)
```

## 脚本索引

### 管理脚本

| 脚本 | 功能 | 文档参考 |
|------|------|---------|
| `scripts/start_agent2.sh` | 启动 Agent2 | [快速启动](./agent2_quickstart.md) |
| `scripts/stop_agent2.sh` | 停止 Agent2 | [快速启动](./agent2_quickstart.md) |
| `scripts/status_agent2.sh` | 查看状态 | [快速启动](./agent2_quickstart.md) |
| `scripts/test_agent2.sh` | 功能测试 | [快速启动](./agent2_quickstart.md) |
| `scripts/manage_multi_agent.sh` | 多 Agent 管理 | [README](./AGENT2_README.md) |

### 脚本使用示例

```bash
# 基本操作
bash scripts/start_agent2.sh       # 启动
bash scripts/status_agent2.sh      # 查看状态
bash scripts/stop_agent2.sh        # 停止

# 统一管理
bash scripts/manage_multi_agent.sh start all    # 启动所有
bash scripts/manage_multi_agent.sh status all   # 查看所有状态
bash scripts/manage_multi_agent.sh restart all  # 重启所有

# 测试和验证
bash scripts/test_agent2.sh        # 运行测试
```

## 代码索引

### 核心代码

| 文件 | 说明 | 行数 |
|------|------|------|
| `agentos/webui/agent2_monitor.py` | Agent2 主程序 | ~280 |

### 关键类和方法

```python
class WebUIMonitor:
    # 初始化
    def __init__(self)

    # 监控循环
    def run(self)
    def _run_monitoring_cycle(self)

    # 诊断
    def _diagnose(self) -> Dict[str, Any]
    def _check_process_alive(self) -> bool
    def _check_port_listening(self) -> bool
    def _check_health_api(self) -> tuple

    # 修复
    def _fix_issue(self, diagnosis) -> Dict[str, Any]
    def _create_restart_signal(self, reason)

    # 状态管理
    def _update_status(self, status, health_status, fix_record=None)
```

## 学习路径

### 路径 1: 快速使用 (30 分钟)

```
1. 快速启动指南 (5 分钟)
   └─ 安装、启动、验证

2. 常用命令 (10 分钟)
   └─ 启动、停止、查看状态、日志

3. 基本故障排查 (15 分钟)
   └─ 查看日志、检查状态、重启服务
```

### 路径 2: 深入理解 (2 小时)

```
1. 快速启动指南 (5 分钟)
   └─ 基本操作

2. 完整技术文档 (30 分钟)
   └─ 功能详解、监控逻辑、修复策略

3. 架构设计文档 (45 分钟)
   └─ 系统架构、数据流、时序图

4. 实践操作 (40 分钟)
   └─ 运行测试、模拟故障、验证修复
```

### 路径 3: 生产部署 (3 小时)

```
1. 快速启动指南 (5 分钟)
   └─ 基本概念

2. 最佳实践指南 (1 小时)
   └─ 生产环境配置、systemd 设置、日志轮转

3. 告警集成 (1 小时)
   └─ 配置邮件/Slack/PagerDuty 告警

4. 测试和验证 (1 小时)
   └─ 功能测试、压力测试、故障演练
```

### 路径 4: 扩展开发 (4 小时)

```
1. 架构设计文档 (1 小时)
   └─ 理解系统架构和设计

2. 核心代码阅读 (1.5 小时)
   └─ 阅读 agent2_monitor.py

3. 扩展开发 (1 小时)
   └─ 添加自定义检查、修复策略

4. 测试和验证 (0.5 小时)
   └─ 单元测试、集成测试
```

## 版本信息

- **当前版本**: 1.0
- **创建日期**: 2026-01-27
- **最后更新**: 2026-01-27
- **维护状态**: 活跃维护

## 文档更新历史

| 日期 | 版本 | 变更内容 |
|------|------|---------|
| 2026-01-27 | 1.0 | 初始版本，包含所有核心文档 |

## 贡献指南

如需改进文档：

1. 阅读现有文档
2. 识别改进点
3. 更新相关文档
4. 更新本索引（如有新文档）
5. 提交更改

## 反馈和支持

遇到文档问题？

1. 检查本索引是否有相关文档
2. 搜索文档内容
3. 查看常见问题
4. 提交 Issue 或 PR

## 相关资源

- **项目主页**: AgentOS
- **核心组件**:
  - Agent1（进程管理器，待文档化）
  - Agent2（健康监控器，当前文档）
  - WebUI（Web 界面）
- **依赖项**:
  - FastAPI
  - psutil
  - requests

---

**提示**: 善用浏览器的"在页面中查找"功能（Ctrl+F 或 Cmd+F）快速定位内容。
