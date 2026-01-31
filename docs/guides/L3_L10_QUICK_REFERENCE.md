# L-3 to L-10 Quick Reference Guide

## Input Validation Limits

### L-3: Payload Size - 1MB Maximum
```
Status: 413 Payload Too Large
Limit: 1,048,576 bytes (1 MB)
Applies to: All POST/PUT/PATCH requests
```

### L-4: Session Title - 500 Characters Maximum
```
Status: 422 Unprocessable Entity
Limit: 500 characters
Endpoint: POST /api/sessions
Field: title
```

### L-5: Message Content - 50KB Maximum
```
Status: 422 Unprocessable Entity
Limit: 50,000 characters (~50 KB)
Endpoint: POST /api/sessions/{id}/messages
Field: content
```

---

## Verified Features (Still Working)

### L-6: Unicode Support ✅
- Chinese: 测试会话
- Japanese: テストセッション
- Arabic: جلسة اختبار
- All languages fully supported

### L-7: Special Characters ✅
- Quotes: "text" and 'text' (HTML-escaped)
- Brackets: [text] {text} <text> (text)
- Symbols: @#$%^&*()_+-=[]{}|;:',.<>?/~`

### L-8: Emoji Support ✅
- Basic: 🚀 😊 🎉
- Complex: 👨‍👩‍👧‍👦 🇺🇸 👍🏾 🧑‍💻
- All emojis fully supported

### L-9: Newline Preservation ✅
- Multiline text preserved
- Code blocks preserved
- Formatting maintained

### L-10: SQL Injection Protection ✅
- Parameterized queries prevent injection
- User content stored safely
- No SQL execution from user input

---

## Testing

```bash
# Run all tests
python -m pytest tests/security/test_session_input_limits.py -v

# Expected: 29 passed
```

---

## Configuration

File: `agentos/webui/api/validation.py`

```python
MAX_PAYLOAD_SIZE = 1 * 1024 * 1024  # 1 MB
MAX_TITLE_LENGTH = 500              # 500 characters
MAX_CONTENT_LENGTH = 50000          # 50 KB
```

---

## Error Handling

### Client-Side
```javascript
// Check payload size before sending
if (payloadSize > 1048576) {
  alert('Payload too large. Maximum 1MB allowed.');
  return;
}

// Check title length
if (title.length > 500) {
  alert('Title too long. Maximum 500 characters allowed.');
  return;
}

// Check content length
if (content.length > 50000) {
  alert('Content too long. Maximum 50KB allowed.');
  return;
}
```

### Server Response Handling
```javascript
// Handle 413 Payload Too Large
if (response.status === 413) {
  const data = await response.json();
  console.error(data.error, data.hint);
  // Show user-friendly message
}

// Handle 422 Validation Error
if (response.status === 422) {
  const data = await response.json();
  console.error(data.message, data.details);
  // Show field-specific validation errors
}
```

---

## Migration Guide

### Before (No Limits)
```python
# Any size accepted ❌
POST /api/sessions
{
  "title": "A" * 1000000,  # 1MB title accepted
  "metadata": {...}  # 10MB metadata accepted
}
```

### After (With Limits) ✅
```python
# Reasonable limits enforced
POST /api/sessions
{
  "title": "A" * 500,  # Max 500 chars
  "metadata": {...}  # Total payload max 1MB
}
```

---

## Monitoring

### Metrics to Track
1. Number of 413 responses (oversized payloads)
2. Number of 422 responses (validation errors)
3. Average payload sizes
4. P95/P99 payload sizes

### Alert Thresholds
- High rate of 413 responses → Possible attack or client misconfiguration
- High rate of 422 responses → Client needs updated validation

---

## Security Considerations

✅ **Protected Against**:
- DoS via oversized payloads
- Memory exhaustion attacks
- Storage exhaustion
- XSS (HTML escaping maintained)
- SQL injection (parameterized queries)

⚠️ **Not Protected Against** (Out of Scope):
- Rate limiting (separate feature)
- Authentication bypass
- Authorization issues
- Business logic flaws

---

## Support

For issues or questions:
1. Check error message in response
2. Verify payload/title/content size
3. Review test cases in `tests/security/test_session_input_limits.py`
4. Consult `L3_L10_INPUT_VALIDATION_FIX_REPORT.md`
