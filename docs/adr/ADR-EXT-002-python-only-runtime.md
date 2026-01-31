# ADR-EXT-002: Python-Only Runtime for Extensions

## Status
Accepted (2026-01-30)

## Context
AgentOS 扩展系统需要在安全性、可维护性和灵活性之间取得平衡。允许扩展依赖外部二进制文件会带来以下风险：

1. **供应链安全**：外部二进制文件难以审计和验证
2. **跨平台一致性**：不同操作系统和架构需要不同的二进制文件
3. **权限管理复杂度**：二进制安装通常需要提升权限
4. **不确定性**：外部安装脚本可能失败或产生副作用

## Decision
在当前阶段，AgentOS 扩展系统将强制执行 Python-only runtime 策略：

1. 所有扩展必须声明 `runtime: "python"`
2. 扩展必须包含 `external_bins: []`（空数组）
3. 扩展只能使用 Python 代码和 PyPI 依赖
4. 安装时进行 preflight policy check，拒绝违规扩展

### Extension Tiers
- **Tier 0 (当前支持)**: Pure Python，无外部依赖
- **Tier 1 (规划中)**: 调用外部 API/服务
- **Tier 2 (未来支持)**: 需要本地二进制文件，需管理员审批

## Consequences

### Positive
- ✅ 确定性安装：纯 Python 环境可预测
- ✅ 最小权限：无需 sudo 或系统级安装
- ✅ 跨平台一致性：Python 代码在所有平台运行
- ✅ 可审计性：代码可被完全审查
- ✅ 供应链安全：依赖来自 PyPI 官方源

### Negative
- ❌ 功能限制：无法直接集成需要二进制的工具
- ❌ 性能约束：某些场景 Python 性能不如原生代码

### Mitigation
- 为真正需要二进制的场景设计 Tier 2 exception 机制
- 提供 Python 包装器库来与外部服务通信
- 鼓励使用 API-based 集成（Tier 1）

## Implementation
- PolicyChecker 模块实现策略检查
- Validator 在安装时执行 preflight check
- 清晰的错误消息指导用户
- 文档说明策略和例外流程

## References
- ADR-EXT-001: Declarative Extensions Only
- F-EXT-1.2: Executable File Restrictions
- 扩展开发指南: docs/extensions/

## Review Schedule
- Next Review Date: 2026-02-28
- Reviewer: Security Team & Extension Working Group
