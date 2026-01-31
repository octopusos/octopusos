# NetworkOS + SMS 双向 E2E 验证清单（30分钟）

**目标**：在真实环境中证明 NetworkOS + Twilio SMS 双向通信完整可用。

**前置条件**：
- [ ] 已部署 AgentOS（运行在 http://127.0.0.1:8000）
- [ ] 有 Cloudflare 账号（Zero Trust 计划）
- [ ] 有 Twilio 账号（电话号码已购买）
- [ ] 有一个域名（DNS 配置权限）
- [ ] 有测试手机（可发送/接收短信）

**预计时间**：30分钟
**验证日期**：________
**验证者**：________

---

## Step A：NetworkOS 启动 Tunnel（5分钟）

### A1. 检查 cloudflared 可用

```bash
cloudflared --version
# 预期：显示版本号（如 2024.x.x）
```

- [ ] cloudflared 已安装

### A2. 创建 Tunnel

```bash
# 从 Cloudflare Dashboard 获取 token
# Zero Trust → Networks → Tunnels → Create a Tunnel → 复制 token

agentos networkos create \
  --name sms-e2e-test \
  --hostname sms.your-domain.com \
  --target http://127.0.0.1:8000 \
  --token YOUR_CLOUDFLARE_TOKEN

# 记录 tunnel_id
TUNNEL_ID=___________________
```

- [ ] Tunnel 已创建
- [ ] 记录 tunnel_id

### A3. 启动 Tunnel

```bash
agentos networkos start $TUNNEL_ID

# 验证状态
agentos networkos status $TUNNEL_ID
# 预期：health_status=up, is_enabled=1
```

- [ ] Tunnel 状态为 `up`
- [ ] 可访问 https://sms.your-domain.com/api/health

### A4. 验证事件日志

```bash
agentos networkos logs $TUNNEL_ID
# 预期：看到 tunnel_start, health_up 事件
```

- [ ] 事件日志包含 `tunnel_start`
- [ ] 事件日志包含 `health_up`

**Step A 完成时间**：________ （目标：5分钟）

---

## Step B：配置 Twilio Webhook（5分钟）

### B1. 生成 Webhook Path Token

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# 输出：abc123_XyZ789_RandomToken_32PlusChars

PATH_TOKEN=___________________
```

- [ ] Path token 已生成（≥32字符）
- [ ] 记录 path_token

### B2. 配置 SMS Channel

在 AgentOS 配置 SMS channel：
- `account_sid`: ___________________
- `auth_token`: ___________________
- `from_number`: ___________________
- `webhook_path_token`: [上面生成的token]

- [ ] SMS channel 已配置
- [ ] webhook_path_token 已设置

### B3. 配置 Twilio Console

1. 登录 https://console.twilio.com/
2. 进入 Phone Numbers → Manage → Active Numbers
3. 点击你的电话号码
4. Messaging Configuration:
   - **Webhook URL**: `https://sms.your-domain.com/api/channels/sms/twilio/webhook/YOUR_PATH_TOKEN`
   - **HTTP Method**: POST ✅
5. 点击 Save

完整 Webhook URL：
```
https://sms.your-domain.com/api/channels/sms/twilio/webhook/YOUR_PATH_TOKEN
```

- [ ] Twilio Webhook URL 已配置
- [ ] HTTP Method 设为 POST
- [ ] 配置已保存

**Step B 完成时间**：________ （目标：5分钟）

---

## Step C：发送真实短信（5分钟）

### C1. 发送 Inbound 短信

从测试手机发送短信到 Twilio 号码：

```
To: YOUR_TWILIO_NUMBER
Body: Hello AgentOS E2E Test
```

- [ ] 已发送测试短信
- [ ] 发送时间：________

### C2. 观察证据链

#### C2.1 Twilio 日志
访问：Twilio Console → Monitor → Logs → Messaging

- [ ] 看到 inbound 短信记录
- [ ] Webhook POST 状态：200 OK
- [ ] Response time: ________ ms （预期：<3000ms）

#### C2.2 AgentOS 日志
```bash
tail -f logs/agentos.log | grep -i "sms\|webhook"
```

预期看到：
- `Received webhook from Twilio`
- `MessageSid: SM...`
- `Signature verified: True`
- `Processing inbound SMS`

- [ ] 日志显示 webhook 收到
- [ ] 签名验证通过
- [ ] MessageSid: ___________________

#### C2.3 NetworkOS 事件
```bash
agentos networkos logs $TUNNEL_ID --last 10
```

- [ ] 事件记录 webhook 访问（如有）

### C3. 验证回复

检查测试手机：

- [ ] 收到 AgentOS 自动回复
- [ ] 回复时间：________
- [ ] 回复内容：___________________

**Step C 完成时间**：________ （目标：5分钟）

---

## Step D：安全与幂等验证（10分钟）

### D1. 重放攻击测试

#### D1.1 复制 Twilio Webhook Payload

从 Twilio Logs 复制完整的 webhook payload：
```json
{
  "MessageSid": "SM...",
  "From": "+1234567890",
  "To": "+0987654321",
  "Body": "Hello AgentOS E2E Test"
}
```

#### D1.2 重放请求

```bash
curl -X POST \
  https://sms.your-domain.com/api/channels/sms/twilio/webhook/YOUR_PATH_TOKEN \
  -H "X-Twilio-Signature: ORIGINAL_SIGNATURE" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "MessageSid=SM...&From=+1234567890&To=+0987654321&Body=Hello+AgentOS+E2E+Test"
```

预期结果：
- HTTP 200 OK（接受请求）
- **但不发送重复回复**（去重生效）

验证：
```bash
grep "Duplicate MessageSid" logs/agentos.log
# 应该看到：Duplicate MessageSid detected: SM... - ignoring
```

- [ ] 重放请求返回 200
- [ ] 日志显示 "Duplicate MessageSid"
- [ ] **未收到第二条回复短信** ✅

**D1 完成时间**：________ （目标：5分钟）

---

### D2. 签名伪造测试

#### D2.1 伪造签名

```bash
curl -X POST \
  https://sms.your-domain.com/api/channels/sms/twilio/webhook/YOUR_PATH_TOKEN \
  -H "X-Twilio-Signature: FAKE_SIGNATURE_abc123xyz789" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "MessageSid=SM_FAKE&From=+1111111111&To=+2222222222&Body=Fake+message"
```

预期结果：
- HTTP 401 Unauthorized

验证：
```bash
grep "Invalid.*signature\|Unauthorized" logs/agentos.log
# 应该看到：Invalid Twilio signature
```

- [ ] 请求返回 401
- [ ] 日志显示签名验证失败
- [ ] **未收到任何短信** ✅

#### D2.2 篡改数据

使用原始签名 + 修改后的数据：

```bash
# 原始签名（从真实请求复制）
ORIGINAL_SIGNATURE="..."

# 修改 Body
curl -X POST \
  https://sms.your-domain.com/api/channels/sms/twilio/webhook/YOUR_PATH_TOKEN \
  -H "X-Twilio-Signature: $ORIGINAL_SIGNATURE" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "MessageSid=SM_ORIGINAL&From=+1234567890&To=+0987654321&Body=TAMPERED_DATA"
```

预期结果：
- HTTP 401 Unauthorized（签名不匹配）

- [ ] 请求返回 401
- [ ] 签名验证失败（数据被篡改）

**D2 完成时间**：________ （目标：5分钟）

---

## Step E：证据快照（5分钟）

### E1. 收集关键指标

| 指标 | 值 |
|------|-----|
| 验证日期时间 | ________ |
| AgentOS 版本 | ________ |
| Cloudflare Tunnel ID | ________ |
| Twilio 号码 | ________ |
| 测试手机号 | ________ |
| Inbound 短信成功 | ✅ / ❌ |
| 自动回复成功 | ✅ / ❌ |
| 重放被阻断 | ✅ / ❌ |
| 签名伪造被阻断 | ✅ / ❌ |
| 数据篡改被阻断 | ✅ / ❌ |

### E2. 截图证据

收集以下截图：
- [ ] Twilio Console - Webhook 日志（显示 200 OK）
- [ ] 测试手机 - 收到的回复短信
- [ ] AgentOS 日志 - 签名验证通过
- [ ] NetworkOS 状态 - Tunnel running

### E3. 完成证据文档

将以上信息填写到：`docs/NETWORKOS_SMS_E2E_PROOF.md`

**E 完成时间**：________ （目标：5分钟）

---

## 总结

**总耗时**：________ （目标：30分钟）

**验收结果**：
- [ ] ✅ 所有步骤通过
- [ ] ⚠️  部分步骤失败（记录原因）
- [ ] ❌ 无法完成验证

**失败原因**（如有）：
________________________________

**签名**：________
**日期**：________

---

## 故障排查（如需要）

### Tunnel 无法启动
- 检查 cloudflared 版本
- 检查 token 是否正确
- 运行：`agentos networkos logs $TUNNEL_ID`

### Webhook 404/503
- 检查 Tunnel 状态（must be `up`）
- 检查 path_token 是否一致
- 检查 URL 拼写

### 签名验证失败
- 检查 Twilio auth_token 是否正确
- 检查 webhook URL 是否完全一致（含协议、域名、路径）

### 未收到回复
- 检查 MessageBus 处理日志
- 检查 Twilio account 余额
- 检查 from_number 配置
