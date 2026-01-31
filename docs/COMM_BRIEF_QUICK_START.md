# /comm brief Quick Start Guide

## Basic Usage

```bash
# Generate AI news brief
/comm brief ai

# With today filter
/comm brief ai --today

# Limit to 5 items
/comm brief ai --max-items 5

# Combine flags
/comm brief ai --today --max-items 10
```

## What You Get

```markdown
# 今日 AI 相关新闻简报（2026-01-30）

**生成时间**：2026-01-30T12:00:00
**来源**：CommunicationOS（search + fetch）
**范围**：AI / Policy / Industry / Security

---

## 1) Article Title
- **要点**：One-sentence summary
- **为什么重要**：Why this matters
- **来源**：[domain.com](url)
- **抓取时间**：2026-01-30T12:00:00Z
- **Trust Tier**：`external_source`

[... 4-6 more articles ...]

## 统计信息
- 搜索查询：4 个
- 候选结果：14 条
- 验证来源：5 条
- 生成耗时：6.23s
```

## How It Works

1. **Search** - Runs 4 queries on DuckDuckGo
2. **Filter** - Deduplicates and limits to 14 candidates
3. **Fetch** - Verifies top 5-7 URLs (with SSRF protection)
4. **Format** - Generates Markdown brief

**Total time: ~5-10 seconds**

## Error Handling

### Planning Phase Block
```
🚫 Command blocked: comm.* commands are forbidden in planning phase
```
**Solution**: Only use in execution phase

### SSRF Protection
```
🛡️ SSRF 防护
该 URL 被安全策略阻止(内网地址或 localhost)
```
**Solution**: Only public HTTPS URLs allowed

### No Results
```
❌ 生成简报失败：无法验证任何来源
请稍后重试或使用 /comm search 手动搜索。
```
**Solution**: Retry or check network connectivity

## Testing

### Run Unit Tests
```bash
python3 -m pytest test_comm_brief.py -v
```

### Run E2E Test (Mock)
```bash
python3 test_comm_brief_e2e.py
```

### Run E2E Test (Live)
```bash
python3 test_comm_brief_e2e.py --live
```

## Architecture

```
User → Chat → /comm brief ai
           ↓
    CommCommandHandler.handle_brief()
           ↓
    ┌──────────────────────┐
    │ 1. Multi-Query       │  4 queries × 5 results
    │    Search            │
    └──────────┬───────────┘
               ↓
    ┌──────────────────────┐
    │ 2. Candidate         │  URL/domain dedup
    │    Filtering         │
    └──────────┬───────────┘
               ↓
    ┌──────────────────────┐
    │ 3. Fetch & Verify    │  3 concurrent fetches
    │                      │
    └──────────┬───────────┘
               ↓
    ┌──────────────────────┐
    │ 4. Markdown          │  Frozen template
    │    Generation        │
    └──────────┬───────────┘
               ↓
           Markdown brief
```

## Search Queries

The pipeline uses 4 carefully designed queries:

1. **"AI news today"** - Recent developments
2. **"artificial intelligence regulation"** - Policy/legal
3. **"AI chips policy"** - Hardware/infrastructure
4. **"AI research breakthrough"** - Technical advances

These provide diverse coverage of AI news.

## Trust Tiers

- `search_result` - From search, not verified
- `external_source` - Verified fetch, public URL
- `authoritative_source` - Government/academic (.gov, .edu)
- `primary_source` - Direct from source

All items in brief are verified (not `search_result`).

## Performance

- **Search**: ~2-4s (4 queries)
- **Filter**: <0.1s
- **Fetch**: ~2-5s (3 concurrent)
- **Format**: <0.1s

**Total: ~5-10 seconds**

## Limitations

### Current
- Only "ai" topic supported
- English search only
- No date filtering (--today not yet implemented)
- Simple rule-based importance

### Future
- More topics (policy, security, hardware)
- Multi-language support
- Smart date filtering
- LLM-based importance and summarization

## Troubleshooting

### Slow Performance
- Check network connectivity
- Verify no rate limiting
- Some sites may be slow to fetch

### Empty Results
- Rare, but possible if all fetches fail
- Retry usually resolves
- Check logs for specific errors

### SSRF Errors
- Only occurs if connector tries private IPs
- This is by design (security)
- Use public URLs only

## Security

- ✅ Phase gate enforcement
- ✅ SSRF protection
- ✅ Content sanitization
- ✅ Trust tier tracking
- ✅ Audit logging

All operations are logged and auditable.

## Support

For issues or questions:
1. Check logs: `agentos/logs/`
2. Run tests: `pytest test_comm_brief.py -v`
3. Check audit trail: Look for `[COMM_AUDIT]` in logs
