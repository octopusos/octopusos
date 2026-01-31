# Database Migration Verification Checklist

## 迁移前检查清单

### 环境准备
- [ ] Python 3.13+ 已安装
- [ ] psycopg2-binary 已安装 (`pip install psycopg2-binary`)
- [ ] PostgreSQL 15+ 已安装或 Docker 可用
- [ ] 备份现有 SQLite 数据库 (`cp store/registry.sqlite backup.sqlite`)

### 配置文件准备
- [ ] 复制 `.env.example` 到 `.env`
- [ ] 设置 `DATABASE_PASSWORD`
- [ ] 验证所有环境变量正确

### PostgreSQL 准备
- [ ] PostgreSQL 服务运行中
- [ ] 数据库和用户已创建
- [ ] 连接测试成功
- [ ] Schema 已创建

## 迁移执行清单

### 数据迁移
- [ ] 停止 AgentOS 应用
- [ ] 运行数据迁移脚本
- [ ] 验证迁移日志无错误
- [ ] 检查所有表已迁移
- [ ] 验证行数一致

### 应用切换
- [ ] 更新 `.env` 设置 `DATABASE_TYPE=postgresql`
- [ ] 重启 AgentOS 应用
- [ ] 测试基本功能（创建任务、查询任务）
- [ ] 检查应用日志无错误

## 迁移后验证清单

### 功能验证
- [ ] 创建新任务成功
- [ ] 查询任务列表成功
- [ ] 任务状态更新成功
- [ ] WebUI 正常工作
- [ ] API 端点响应正常

### 性能验证
- [ ] 并发写入无 "database locked" 错误
- [ ] 查询响应时间正常
- [ ] 应用启动时间正常

### 数据完整性验证
- [ ] 任务数量一致
- [ ] 审计日志完整
- [ ] 项目配置保留
- [ ] WebUI 会话恢复

## 回滚清单（如需回滚）

- [ ] 停止 AgentOS 应用
- [ ] 恢复 `.env` 设置 `DATABASE_TYPE=sqlite`
- [ ] 恢复 SQLite 备份（如需要）
- [ ] 重启 AgentOS 应用
- [ ] 验证功能正常

## 监控清单（迁移后 24 小时）

### 系统健康
- [ ] 应用无崩溃
- [ ] 错误日志无异常
- [ ] 内存使用正常
- [ ] CPU 使用正常

### 数据库健康
- [ ] 连接池工作正常
- [ ] 慢查询日志检查
- [ ] 磁盘使用正常
- [ ] 备份正常运行

### 性能指标
- [ ] 响应时间 < 迁移前的 1.5x
- [ ] 并发处理能力提升
- [ ] 错误率 < 1%

## 问题排查清单

### 连接问题
- [ ] 检查 PostgreSQL 服务状态
- [ ] 检查防火墙配置
- [ ] 检查环境变量配置
- [ ] 检查 pg_hba.conf 配置

### 性能问题
- [ ] 检查连接池配置
- [ ] 检查索引是否创建
- [ ] 运行 VACUUM ANALYZE
- [ ] 检查 postgresql.conf 配置

### 数据问题
- [ ] 对比行数
- [ ] 检查外键约束
- [ ] 验证 JSON 字段
- [ ] 检查字符编码

## 成功标准

迁移成功的标志：

✅ **数据完整性**
- 所有表数据已迁移
- 行数 100% 一致
- 外键关系保留

✅ **功能正常**
- 所有 API 正常工作
- WebUI 正常访问
- 任务创建和查询成功

✅ **性能提升**
- 并发写入无锁错误
- 查询响应时间改善
- 高并发场景稳定

✅ **系统稳定**
- 运行 24 小时无崩溃
- 错误日志无异常
- 资源使用正常

## 签核

- [ ] 迁移执行者签名：__________ 日期：__________
- [ ] 验证人员签名：__________ 日期：__________
- [ ] 技术负责人签名：__________ 日期：__________

---

## 附录：快速命令参考

```bash
# 启动 PostgreSQL (Docker)
docker-compose up -d postgres

# 检查服务状态
docker-compose ps postgres

# 创建数据库
psql -h localhost -U postgres -c "CREATE DATABASE agentos;"

# 运行迁移
python scripts/migrate_sqlite_to_postgresql.py --pg-password password

# 验证表数量
psql -h localhost -U agentos -d agentos -c "\dt"

# 检查行数
psql -h localhost -U agentos -d agentos -c "SELECT COUNT(*) FROM tasks;"

# 测试连接
psql -h localhost -U agentos -d agentos -c "SELECT version();"

# 查看日志
docker-compose logs -f postgres
```

## 联系支持

如遇到问题，请参考：
- [故障排查指南](DATABASE_MIGRATION.md#故障排查)
- [快速参考](DATABASE_QUICK_REFERENCE.md)
- GitHub Issues: https://github.com/seacow-technology/agentos/issues
