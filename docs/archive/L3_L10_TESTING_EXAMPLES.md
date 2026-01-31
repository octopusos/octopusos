# L-3 to L-10 Testing Examples

## Manual Testing with curl

### Prerequisites
```bash
# Start AgentOS server
cd /Users/pangge/PycharmProjects/AgentOS
source .venv/bin/activate
python -m agentos.webui.app

# Server should be running on http://localhost:8000
```

---

## L-3: Payload Size Tests

### Test 1: Normal Payload (Should Pass)
```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $(curl -s http://localhost:8000/api/sessions | grep -o 'csrf_token=[^;]*' | cut -d= -f2)" \
  -d '{
    "title": "Normal Session",
    "tags": ["test"],
    "metadata": {"key": "value"}
  }'

# Expected: 200 OK
# Response: {"id": "...", "title": "Normal Session", ...}
```

### Test 2: Large Payload Under Limit (Should Pass)
```bash
# Create a 900KB payload (under 1MB limit)
python3 << 'EOF'
import requests
import json

# Generate large payload
large_data = "x" * 900000  # 900KB
payload = {
    "title": "Large Session",
    "metadata": {"large_field": large_data}
}

response = requests.post(
    "http://localhost:8000/api/sessions",
    json=payload,
    headers={"X-CSRF-Token": "..."}  # Get from cookie
)
print(f"Status: {response.status_code}")
print(f"Size: {len(json.dumps(payload))} bytes")
EOF

# Expected: 200 OK or 413 (depends on total JSON size)
```

### Test 3: Oversized Payload (Should Reject with 413)
```bash
# Create a 2MB payload (over 1MB limit)
python3 << 'EOF'
import requests
import json

# Generate oversized payload
huge_data = "x" * (2 * 1024 * 1024)  # 2MB
payload = {
    "title": "Oversized Session",
    "metadata": {"huge_field": huge_data}
}

response = requests.post(
    "http://localhost:8000/api/sessions",
    json=payload,
    headers={"X-CSRF-Token": "..."}
)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
EOF

# Expected: 413 Payload Too Large
# Response: {
#   "ok": false,
#   "error": "Payload too large",
#   "hint": "Request body must be less than 1.0 MB. Received: 2.0 MB",
#   "reason_code": "PAYLOAD_TOO_LARGE"
# }
```

---

## L-4: Title Length Tests

### Test 1: Normal Title (Should Pass)
```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: ..." \
  -d '{
    "title": "Normal Title"
  }'

# Expected: 200 OK
```

### Test 2: Max Length Title (Should Pass)
```bash
# 500-character title (exactly at limit)
python3 << 'EOF'
import requests

title = "A" * 500  # Exactly 500 characters
response = requests.post(
    "http://localhost:8000/api/sessions",
    json={"title": title},
    headers={"X-CSRF-Token": "..."}
)
print(f"Status: {response.status_code}")
print(f"Title length: {len(title)}")
EOF

# Expected: 200 OK
```

### Test 3: Oversized Title (Should Reject with 422)
```bash
# 501-character title (over limit)
python3 << 'EOF'
import requests

title = "A" * 501  # Over 500 character limit
response = requests.post(
    "http://localhost:8000/api/sessions",
    json={"title": title},
    headers={"X-CSRF-Token": "..."}
)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
EOF

# Expected: 422 Unprocessable Entity
# Response: {
#   "ok": false,
#   "error_code": "VALIDATION_ERROR",
#   "message": "Request validation failed",
#   "details": {
#     "errors": [{
#       "field": "body -> title",
#       "message": "String should have at most 500 characters",
#       "type": "string_too_long"
#     }]
#   }
# }
```

---

## L-5: Content Length Tests

### Test 1: Normal Content (Should Pass)
```bash
# First create a session
SESSION_ID=$(curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: ..." \
  -d '{"title": "Test"}' | jq -r '.id')

# Add normal message
curl -X POST http://localhost:8000/api/sessions/$SESSION_ID/messages \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: ..." \
  -d '{
    "role": "user",
    "content": "Hello, this is a normal message!"
  }'

# Expected: 200 OK
```

### Test 2: Max Length Content (Should Pass)
```bash
# 50,000-character content (exactly at limit)
python3 << 'EOF'
import requests

# Create session
session_response = requests.post(
    "http://localhost:8000/api/sessions",
    json={"title": "Test"},
    headers={"X-CSRF-Token": "..."}
)
session_id = session_response.json()["id"]

# Add message with max content
content = "A" * 50000  # Exactly 50,000 characters
message_response = requests.post(
    f"http://localhost:8000/api/sessions/{session_id}/messages",
    json={"role": "user", "content": content},
    headers={"X-CSRF-Token": "..."}
)
print(f"Status: {message_response.status_code}")
print(f"Content length: {len(content)}")
EOF

# Expected: 200 OK
```

### Test 3: Oversized Content (Should Reject with 422)
```bash
# 50,001-character content (over limit)
python3 << 'EOF'
import requests

# Create session
session_response = requests.post(
    "http://localhost:8000/api/sessions",
    json={"title": "Test"},
    headers={"X-CSRF-Token": "..."}
)
session_id = session_response.json()["id"]

# Try to add oversized content
content = "A" * 50001  # Over 50,000 character limit
message_response = requests.post(
    f"http://localhost:8000/api/sessions/{session_id}/messages",
    json={"role": "user", "content": content},
    headers={"X-CSRF-Token": "..."}
)
print(f"Status: {message_response.status_code}")
print(f"Response: {message_response.json()}")
EOF

# Expected: 422 Unprocessable Entity
```

---

## L-6: Unicode Support Tests

### Test 1: Chinese Characters
```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: ..." \
  -d '{
    "title": "测试会话 (Test Session)"
  }'

# Expected: 200 OK
# Response should preserve Chinese characters
```

### Test 2: Japanese Characters
```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: ..." \
  -d '{
    "title": "テストセッション (Test Session)"
  }'

# Expected: 200 OK
```

### Test 3: Arabic Characters
```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: ..." \
  -d '{
    "title": "جلسة اختبار (Test Session)"
  }'

# Expected: 200 OK
```

### Test 4: Mixed Unicode
```bash
SESSION_ID=$(curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: ..." \
  -d '{"title": "Test"}' | jq -r '.id')

curl -X POST http://localhost:8000/api/sessions/$SESSION_ID/messages \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: ..." \
  -d '{
    "role": "user",
    "content": "Hello 你好 こんにちは مرحبا 🌍"
  }'

# Expected: 200 OK
# All characters should be preserved
```

---

## L-7: Special Character Tests

### Test 1: Quotes in Title
```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: ..." \
  -d '{
    "title": "Session with \"quotes\" and '\''apostrophes'\''"
  }'

# Expected: 200 OK
# Note: Quotes may be HTML-escaped (&quot; or &#x27;)
```

### Test 2: Brackets in Title
```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: ..." \
  -d '{
    "title": "Session [with] {brackets} <and> (parens)"
  }'

# Expected: 200 OK
```

### Test 3: Special Symbols in Content
```bash
SESSION_ID=$(curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: ..." \
  -d '{"title": "Test"}' | jq -r '.id')

curl -X POST http://localhost:8000/api/sessions/$SESSION_ID/messages \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: ..." \
  -d '{
    "role": "user",
    "content": "Symbols: @#$%^&*()_+-=[]{}|;:'\'',.<>?/~`"
  }'

# Expected: 200 OK
```

---

## L-8: Emoji Support Tests

### Test 1: Basic Emojis in Title
```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: ..." \
  -d '{
    "title": "Session 🚀 with emojis 😊 🎉"
  }'

# Expected: 200 OK
```

### Test 2: Emojis in Content
```bash
SESSION_ID=$(curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: ..." \
  -d '{"title": "Test"}' | jq -r '.id')

curl -X POST http://localhost:8000/api/sessions/$SESSION_ID/messages \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: ..." \
  -d '{
    "role": "user",
    "content": "Hello! 👋 Let'\''s test emojis: 🔥 💯 ✨ 🎯 🌟"
  }'

# Expected: 200 OK
```

### Test 3: Complex Emoji Sequences
```bash
curl -X POST http://localhost:8000/api/sessions/$SESSION_ID/messages \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: ..." \
  -d '{
    "role": "user",
    "content": "Complex: 👨‍👩‍👧‍👦 🇺🇸 🇨🇳 👍🏾 🧑‍💻"
  }'

# Expected: 200 OK
```

---

## L-9: Newline Preservation Tests

### Test 1: Multiline Content
```bash
curl -X POST http://localhost:8000/api/sessions/$SESSION_ID/messages \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: ..." \
  -d '{
    "role": "user",
    "content": "Line 1\nLine 2\nLine 3\n\nLine 5 (after blank)"
  }'

# Expected: 200 OK
# Newlines should be preserved
```

### Test 2: Code Block
```bash
curl -X POST http://localhost:8000/api/sessions/$SESSION_ID/messages \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: ..." \
  -d '{
    "role": "user",
    "content": "```python\ndef hello():\n    print(\"Hello, World!\")\n    return True\n```"
  }'

# Expected: 200 OK
# Code formatting should be preserved
```

---

## L-10: SQL Injection Protection Tests

### Test 1: SQL Injection in Title
```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: ..." \
  -d '{
    "title": "Test '\''; DROP TABLE sessions; --"
  }'

# Expected: 200 OK
# Should be stored safely, no SQL execution
```

### Test 2: SQL Injection in Content
```bash
curl -X POST http://localhost:8000/api/sessions/$SESSION_ID/messages \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: ..." \
  -d '{
    "role": "user",
    "content": "'\''; DELETE FROM chat_messages WHERE '\''1'\''='\''1'\''; --"
  }'

# Expected: 200 OK
# Should be stored as user data, no SQL execution
```

### Test 3: Null Byte Injection
```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: ..." \
  -d $'{
    "title": "Test\x00Truncated"
  }'

# Expected: 200 OK or 400 (sanitized or rejected)
```

---

## Automated Test Runner

### Python Script for All Tests
```python
#!/usr/bin/env python3
"""
Automated test runner for L-3 to L-10 validation.
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def get_csrf_token():
    """Get CSRF token from cookie."""
    response = requests.get(f"{BASE_URL}/api/sessions")
    return response.cookies.get("csrf_token")

def test_l3_payload_size():
    """Test L-3: Payload size limits."""
    csrf_token = get_csrf_token()

    # Test 1: Normal payload
    response = requests.post(
        f"{BASE_URL}/api/sessions",
        json={"title": "Normal"},
        headers={"X-CSRF-Token": csrf_token}
    )
    assert response.status_code == 200, "Normal payload should pass"

    # Test 2: Oversized payload
    huge_data = "x" * (2 * 1024 * 1024)  # 2MB
    response = requests.post(
        f"{BASE_URL}/api/sessions",
        json={"title": "Oversized", "metadata": {"huge": huge_data}},
        headers={"X-CSRF-Token": csrf_token}
    )
    assert response.status_code == 413, "Oversized payload should be rejected"
    print("✅ L-3: Payload size limits working")

def test_l4_title_length():
    """Test L-4: Title length limits."""
    csrf_token = get_csrf_token()

    # Test 1: Max length title
    title_500 = "A" * 500
    response = requests.post(
        f"{BASE_URL}/api/sessions",
        json={"title": title_500},
        headers={"X-CSRF-Token": csrf_token}
    )
    assert response.status_code == 200, "500-char title should pass"

    # Test 2: Oversized title
    title_501 = "A" * 501
    response = requests.post(
        f"{BASE_URL}/api/sessions",
        json={"title": title_501},
        headers={"X-CSRF-Token": csrf_token}
    )
    assert response.status_code == 422, "501-char title should be rejected"
    print("✅ L-4: Title length limits working")

def test_l5_content_length():
    """Test L-5: Content length limits."""
    csrf_token = get_csrf_token()

    # Create session
    session_response = requests.post(
        f"{BASE_URL}/api/sessions",
        json={"title": "Test"},
        headers={"X-CSRF-Token": csrf_token}
    )
    session_id = session_response.json()["id"]

    # Test 1: Max length content
    content_50k = "A" * 50000
    response = requests.post(
        f"{BASE_URL}/api/sessions/{session_id}/messages",
        json={"role": "user", "content": content_50k},
        headers={"X-CSRF-Token": csrf_token}
    )
    assert response.status_code == 200, "50KB content should pass"

    # Test 2: Oversized content
    content_50k_plus = "A" * 50001
    response = requests.post(
        f"{BASE_URL}/api/sessions/{session_id}/messages",
        json={"role": "user", "content": content_50k_plus},
        headers={"X-CSRF-Token": csrf_token}
    )
    assert response.status_code == 422, "50KB+ content should be rejected"
    print("✅ L-5: Content length limits working")

def test_l6_unicode():
    """Test L-6: Unicode support."""
    csrf_token = get_csrf_token()

    response = requests.post(
        f"{BASE_URL}/api/sessions",
        json={"title": "测试 テスト جلسة"},
        headers={"X-CSRF-Token": csrf_token}
    )
    assert response.status_code == 200, "Unicode should be supported"
    print("✅ L-6: Unicode support working")

def test_l8_emoji():
    """Test L-8: Emoji support."""
    csrf_token = get_csrf_token()

    response = requests.post(
        f"{BASE_URL}/api/sessions",
        json={"title": "Session 🚀 😊 🎉"},
        headers={"X-CSRF-Token": csrf_token}
    )
    assert response.status_code == 200, "Emojis should be supported"
    print("✅ L-8: Emoji support working")

if __name__ == "__main__":
    print("Running L-3 to L-10 validation tests...")
    test_l3_payload_size()
    test_l4_title_length()
    test_l5_content_length()
    test_l6_unicode()
    test_l8_emoji()
    print("\n🎉 All manual tests passed!")
```

### Running the Script
```bash
chmod +x test_validation.py
python3 test_validation.py
```

---

## Expected Results Summary

| Test | Expected Status | Expected Behavior |
|------|----------------|-------------------|
| Normal payload | 200 OK | Session created |
| 900KB payload | 200 OK | Session created |
| 2MB payload | 413 | Rejected: Payload too large |
| Normal title | 200 OK | Session created |
| 500-char title | 200 OK | Session created |
| 501-char title | 422 | Rejected: Title too long |
| Normal content | 200 OK | Message added |
| 50KB content | 200 OK | Message added |
| 50KB+ content | 422 | Rejected: Content too long |
| Unicode chars | 200 OK | Preserved |
| Emojis | 200 OK | Preserved |
| Newlines | 200 OK | Preserved |
| SQL injection | 200 OK | Stored safely, no execution |

---

## Troubleshooting

### Issue: 403 CSRF Token Invalid
**Solution**: Make sure to get CSRF token from cookies first:
```bash
# Get token
TOKEN=$(curl -s http://localhost:8000/api/sessions -c cookies.txt | grep csrf_token)
# Use token in subsequent requests
curl -b cookies.txt -H "X-CSRF-Token: $TOKEN" ...
```

### Issue: Connection Refused
**Solution**: Make sure server is running:
```bash
ps aux | grep "agentos.webui.app"
# If not running:
python -m agentos.webui.app
```

### Issue: Unicode Characters Not Working
**Solution**: Make sure curl uses UTF-8:
```bash
export LANG=en_US.UTF-8
curl --header "Content-Type: application/json; charset=utf-8" ...
```

---

## Additional Resources

- **Full Test Suite**: `tests/security/test_session_input_limits.py`
- **Implementation Report**: `L3_L10_INPUT_VALIDATION_FIX_REPORT.md`
- **Quick Reference**: `L3_L10_QUICK_REFERENCE.md`
- **API Documentation**: Check `/api/docs` endpoint for OpenAPI spec
