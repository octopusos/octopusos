# SQLiteWriter 监控指标快速参考

## 快速使用

### 代码中获取指标

```python
from agentos.store import get_writer

writer = get_writer()

# 单个属性
print(f"Queue size: {writer.queue_size}")
print(f"Total writes: {writer.total_writes}")
print(f"Failed writes: {writer.failed_writes}")
print(f"Average latency: {writer.avg_write_latency_ms:.2f}ms")
print(f"Throughput: {writer.throughput_per_second:.2f} ops/s")

# 完整统计
stats = writer.get_stats()
print(stats)
```

### HTTP API

```bash
# 获取统计信息
curl http://localhost:8118/api/health/writer-stats

# 示例响应
{
  "queue_size": 0,
  "queue_high_water_mark": 12,
  "total_writes": 1523,
  "total_retries": 3,
  "failed_writes": 0,
  "avg_write_latency_ms": 0.85,
  "throughput_per_second": 45.2,
  "uptime_seconds": 33.7,
  "status": "ok"
}
```

---

## 监控指标说明

| 指标 | 类型 | 说明 | 健康阈值 |
|------|------|------|----------|
| `queue_size` | int | 当前队列中待处理的写入数量 | < 50 正常<br>50-100 警告<br>> 100 严重 |
| `queue_high_water_mark` | int | 历史最高队列长度 | 用于评估峰值负载 |
| `total_writes` | int | 总写入次数 (成功) | 持续增长说明正常运行 |
| `total_retries` | int | 总重试次数 | 越低越好，> 10% 异常 |
| `failed_writes` | int | 失败的写入次数 | 应该为 0 或接近 0 |
| `avg_write_latency_ms` | float | 平均写入延迟(毫秒) | < 5ms 优秀<br>5-10ms 正常<br>> 10ms 需优化 |
| `throughput_per_second` | float | 每秒写入操作数 | > 100 优秀<br>50-100 正常<br>< 50 可能需要优化 |
| `uptime_seconds` | float | Writer 运行时间(秒) | 用于计算吞吐量 |

---

## 告警规则

### 自动告警

系统会自动输出以下告警:

```python
# 队列积压 - WARNING
if queue_size > 50:
    logger.warning("SQLiteWriter queue backlog: {queue_size} items. "
                   "Consider optimizing write patterns or migrating to PostgreSQL.")

# 队列严重积压 - ERROR
if queue_size > 100:
    logger.error("SQLiteWriter queue critical: {queue_size} items. "
                 "Performance degradation likely. Immediate action required.")
```

### 周期性统计

每 100 次写入自动输出:

```
INFO: SQLiteWriter stats: queue=0, high_water=12, retries=3,
      failed=0, latency=0.85ms, throughput=45.20/s
```

### API 状态码

API 返回的 `status` 字段:

- `"ok"` - 一切正常
- `"warning"` - 有警告，需要关注
- `"critical"` - 严重问题，需要立即处理
- `"unavailable"` - Writer 未初始化
- `"error"` - 获取统计信息失败

---

## 监控集成示例

### Prometheus (需自行实现导出器)

```python
from prometheus_client import Gauge

queue_size_gauge = Gauge('writer_queue_size', 'Current writer queue size')
throughput_gauge = Gauge('writer_throughput', 'Writer operations per second')
latency_gauge = Gauge('writer_latency_ms', 'Average write latency in ms')

def update_prometheus_metrics():
    writer = get_writer()
    stats = writer.get_stats()

    queue_size_gauge.set(stats['queue_size'])
    throughput_gauge.set(stats['throughput_per_second'])
    latency_gauge.set(stats['avg_write_latency_ms'])
```

### 简单监控脚本

```python
import requests
import time

def monitor_writer():
    while True:
        try:
            resp = requests.get("http://localhost:8118/api/health/writer-stats")
            stats = resp.json()

            # 检查告警
            if stats.get("status") == "critical":
                send_alert(f"⚠️ CRITICAL: Queue size = {stats['queue_size']}")

            if stats.get("status") == "warning":
                send_warning(f"⚠️ WARNING: {stats.get('warnings', [])}")

            # 记录指标
            log_metric("writer.queue_size", stats["queue_size"])
            log_metric("writer.throughput", stats["throughput_per_second"])
            log_metric("writer.latency", stats["avg_write_latency_ms"])

        except Exception as e:
            print(f"Monitoring error: {e}")

        time.sleep(60)  # 每分钟检查一次

if __name__ == "__main__":
    monitor_writer()
```

---

## 性能排查手册

### 问题 1: 队列积压 (queue_size 持续增长)

**原因**:
- 写入速度 > 处理速度
- 数据库 I/O 瓶颈
- 锁竞争严重

**解决方案**:
1. 检查磁盘 I/O 性能
2. 优化写入模式 (批量写入)
3. 考虑迁移到 PostgreSQL
4. 增加 `busy_timeout` 配置

```python
# 批量写入优化示例
def batch_insert(records):
    def write_batch(conn):
        conn.executemany(
            "INSERT INTO table (col1, col2) VALUES (?, ?)",
            records
        )
    writer.submit(write_batch)
```

### 问题 2: 延迟过高 (avg_write_latency_ms > 10ms)

**原因**:
- 磁盘 I/O 慢
- 表结构未优化
- 索引过多

**解决方案**:
1. 检查是否启用 WAL 模式
2. 检查磁盘性能 (iostat)
3. 优化索引策略
4. 考虑使用 SSD

```bash
# 检查 WAL 模式
sqlite3 store/registry.sqlite "PRAGMA journal_mode;"
# 应该返回: wal

# 检查磁盘性能
iostat -x 1 10
```

### 问题 3: 高失败率 (failed_writes > 0)

**原因**:
- 数据库锁超时
- 磁盘空间不足
- Schema 错误

**解决方案**:
1. 检查日志查看具体错误
2. 增加 `max_retry` 配置
3. 检查磁盘空间
4. 验证 SQL 语句正确性

```python
# 增加重试次数
writer = SQLiteWriter(
    db_path="store/registry.sqlite",
    max_retry=16,  # 默认 8
    max_delay=1.0  # 默认 0.5
)
```

### 问题 4: 高重试率 (total_retries / total_writes > 0.1)

**原因**:
- 并发写入过多
- 读写并发冲突
- 事务时间过长

**解决方案**:
1. 减少并发写入线程数
2. 使用 WAL 模式 (已默认启用)
3. 优化事务大小
4. 考虑使用 PostgreSQL

---

## 最佳实践

### 1. 定期监控

```python
# 每分钟检查一次
import schedule

def check_writer_health():
    writer = get_writer()
    stats = writer.get_stats()

    if stats["queue_size"] > 50:
        alert_ops(f"Writer queue backlog: {stats['queue_size']}")

    if stats["avg_write_latency_ms"] > 10:
        alert_ops(f"High write latency: {stats['avg_write_latency_ms']:.2f}ms")

schedule.every(1).minutes.do(check_writer_health)

while True:
    schedule.run_pending()
    time.sleep(1)
```

### 2. 性能基准

在负载测试前后记录基准:

```python
# 测试前
before = writer.get_stats()

# 执行负载测试
run_load_test()

# 测试后
after = writer.get_stats()

# 对比
print(f"Writes: {before['total_writes']} -> {after['total_writes']}")
print(f"Latency: {before['avg_write_latency_ms']:.2f}ms -> {after['avg_write_latency_ms']:.2f}ms")
print(f"Throughput: {before['throughput_per_second']:.2f} -> {after['throughput_per_second']:.2f}")
```

### 3. 容量规划

根据指标做容量规划:

```python
stats = writer.get_stats()

# 计算每小时写入量
writes_per_hour = stats["throughput_per_second"] * 3600

# 预估增长
if writes_per_hour > 100000:
    print("⚠️ Consider PostgreSQL migration")
elif writes_per_hour > 50000:
    print("⚠️ Monitor closely, approaching limits")
else:
    print("✓ Capacity sufficient")
```

---

## 测试验证

运行测试验证监控功能:

```bash
# 基础测试
python test_writer_monitoring.py

# 高级测试
python test_writer_monitoring_advanced.py
```

预期输出:
```
======================================================================
SQLiteWriter Monitoring - Advanced Test Suite
======================================================================

=== Test 1: Basic Metrics ===
  Total writes: 11
  Avg latency: 0.08ms
  Throughput: 53.68 ops/s
  ✓ Basic metrics working

...

======================================================================
All advanced tests passed successfully!
======================================================================
```

---

## 更多资源

- **实现报告**: `WRITER_MONITORING_IMPLEMENTATION_REPORT.md`
- **完整代码**: `agentos/core/db/writer.py`
- **API 端点**: `agentos/webui/api/health.py`
- **测试代码**:
  - `test_writer_monitoring.py`
  - `test_writer_monitoring_advanced.py`
