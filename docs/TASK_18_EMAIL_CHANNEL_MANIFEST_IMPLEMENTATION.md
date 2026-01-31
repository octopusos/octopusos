# Task #18: Email Channel Manifest and Provider Architecture - Implementation Report

**Status:** ✅ Completed
**Date:** 2026-02-01
**Assignee:** Claude Sonnet 4.5

---

## Executive Summary

Successfully implemented the Email Channel Manifest and Provider Architecture for AgentOS CommunicationOS Phase A. This implementation provides a complete specification for email communication through multiple providers (Gmail OAuth, Outlook OAuth, Generic SMTP/IMAP) with proper email threading support based on RFC 5322 standards.

## Deliverables

### 1. Email Channel Manifest
**File:** `/agentos/communicationos/channels/email/manifest.json`

**Key Features:**
- Multi-provider support (Gmail, Outlook, SMTP/IMAP)
- Conditional config fields based on selected provider
- Polling mode configuration (30-3600 second intervals)
- Thread-aware conversation tracking
- Comprehensive setup instructions for all providers
- OAuth 2.0 flow documentation

**Capabilities Declared:**
- `inbound_text` - Receive text emails
- `outbound_text` - Send text emails
- `threads` - Email thread tracking
- `attachments` - Email attachments (future)
- `html_formatting` - HTML email support

**Session Scope:**
- `session_scope: "user_conversation"`
- `user_key`: Sender email address (normalized lowercase)
- `conversation_key`: Thread root Message-ID (from References/In-Reply-To)
- `message_id`: RFC 5322 Message-ID with "email_" prefix

### 2. Provider Protocol Interface
**File:** `/agentos/communicationos/providers/email/__init__.py`

**Components:**

#### IEmailProvider Protocol
```python
class IEmailProvider(Protocol):
    def validate_credentials() -> ValidationResult
    def fetch_messages(folder, since, limit) -> List[EmailEnvelope]
    def send_message(to_addresses, subject, ...) -> SendResult
    def mark_as_read(provider_message_id) -> bool
```

**Methods:**
- `validate_credentials()`: Verify provider credentials work
- `fetch_messages()`: Poll for new messages (polling mode)
- `send_message()`: Send email with threading headers
- `mark_as_read()`: Mark message as read (optional)

#### EmailEnvelope Data Model
```python
class EmailEnvelope(BaseModel):
    provider_message_id: str  # Provider-specific ID
    message_id: str           # RFC 5322 Message-ID
    in_reply_to: Optional[str]
    references: Optional[str]
    from_address: str
    from_name: Optional[str]
    to_addresses: List[str]
    subject: str
    date: datetime
    text_body: Optional[str]
    html_body: Optional[str]
    thread_hint: Optional[str]
```

**Key Methods:**
- `compute_thread_root()`: Implements thread detection algorithm
- `get_reply_headers()`: Generates proper In-Reply-To and References headers

#### Supporting Models
- `ValidationResult`: Credential validation results
- `SendResult`: Email send operation results
- `EmailProviderType`: Enum of supported providers

**Helper Functions:**
- `parse_email_address()`: Parse email with display name
- `compute_conversation_key()`: Compute conversation key from envelope

### 3. Key Mapping Rules Documentation
**File:** `/agentos/communicationos/channels/email/KEY_MAPPING_RULES.md`

**Content:**
- Complete explanation of user_key, conversation_key, message_id mapping
- Thread detection algorithm with examples
- Edge case handling (missing headers, forwarded emails)
- Comparison with other channels (Telegram, Slack)
- Implementation considerations (polling, deduplication, reply headers)
- Testing checklist
- RFC references

### 4. Channel Module Initialization
**File:** `/agentos/communicationos/channels/email/__init__.py`

**Content:**
- Module documentation
- Architecture overview
- Threading model explanation
- Session scope documentation
- References to related files

## Architecture Decisions

### 1. Multi-Provider Design
**Decision:** Use conditional config fields with `visible_when` to show provider-specific fields.

**Rationale:**
- Single manifest for all email providers
- Clean UI (only show relevant fields)
- Consistent setup flow across providers

**Alternatives Considered:**
- Separate manifests per provider (rejected: too much duplication)
- Flat config with all fields (rejected: confusing UX)

### 2. Polling Mode vs Webhooks
**Decision:** Implement polling mode for email (30-3600 second intervals).

**Rationale:**
- Email is inherently asynchronous (not real-time)
- Webhooks require complex email forwarding setup
- Most email providers support IMAP IDLE or push notifications, but not all
- Polling is simple, reliable, and provider-agnostic

**Trade-offs:**
- Latency: 30-60 second delay typical
- Resource: Periodic polling vs. instant webhooks
- Simplicity: Much easier setup for users

### 3. Thread Detection Algorithm
**Decision:** Use RFC 5322 References header (first Message-ID) as thread root.

**Rationale:**
- Standard: RFC 5322 is universal
- Reliable: All email clients support these headers
- Accurate: References contains full thread history

**Algorithm:**
```
1. If References exists → use FIRST Message-ID (thread root)
2. Else if In-Reply-To exists → use that (direct parent)
3. Else → current Message-ID (new thread)
```

**Edge Cases Handled:**
- Missing References → fall back to In-Reply-To
- Missing both → treat as new thread
- Malformed headers → safe parsing with .strip('<>')

### 4. Provider-Specific IDs
**Decision:** Use `provider_message_id` separate from RFC 5322 `message_id`.

**Rationale:**
- Provider operations (mark as read, delete) need provider IDs
- RFC 5322 Message-ID is for threading, not provider operations
- Separating concerns makes code clearer

**Examples:**
- Gmail: `provider_message_id = "18d4c2f1a2b3c4d5"` (hex ID)
- IMAP: `provider_message_id = "12345"` (UID)
- RFC 5322: `message_id = "<CABcD1234567890@mail.gmail.com>"`

## Comparison with Phase A Reference Channels

### Telegram Manifest
**Similarities:**
- session_scope: "user_conversation"
- capabilities: ["inbound_text", "outbound_text"]
- security_defaults structure
- setup_steps with checklists

**Differences:**
- Email has multi-provider support (Telegram has single provider)
- Email uses polling (Telegram uses webhooks)
- Email has conditional config fields (Telegram has fixed fields)
- Email has explicit thread tracking (Telegram uses chat_id)

### Slack Manifest
**Similarities:**
- Complex setup flow with OAuth
- Thread support (Slack: thread_ts, Email: Message-ID)
- Trigger policy concept (Slack: dm_only/mention_or_dm, Email: folder selection)

**Differences:**
- Slack has URL verification challenge (Email doesn't)
- Slack has real-time events (Email polls)
- Email has simpler authentication (SMTP/IMAP option)

## Email Threading Example

### Scenario: Three-Message Conversation

**Message 1: User Initial Email**
```yaml
From: john@example.com
To: agent@example.com
Subject: Question about pricing
Message-ID: <msg-001@example.com>

→ user_key: "john@example.com"
→ conversation_key: "msg-001@example.com"
→ message_id: "email_msg-001@example.com"
```

**Message 2: Agent Reply**
```yaml
From: agent@example.com
To: john@example.com
Subject: Re: Question about pricing
Message-ID: <msg-002@agent.example.com>
In-Reply-To: <msg-001@example.com>
References: <msg-001@example.com>

→ user_key: "agent@example.com"
→ conversation_key: "msg-001@example.com"  ✓ Same thread
→ message_id: "email_msg-002@agent.example.com"
```

**Message 3: User Follow-up**
```yaml
From: john@example.com
To: agent@example.com
Subject: Re: Question about pricing
Message-ID: <msg-003@example.com>
In-Reply-To: <msg-002@agent.example.com>
References: <msg-001@example.com> <msg-002@agent.example.com>

→ user_key: "john@example.com"
→ conversation_key: "msg-001@example.com"  ✓ Same thread
→ message_id: "email_msg-003@example.com"
```

**Result:** All three messages share the same `conversation_key`, maintaining full context.

## Provider Implementation Guide

Future tasks will implement concrete providers:

### GmailProvider (Task #20)
- Use Gmail API with OAuth 2.0
- Implement `users.messages.list()` for fetch_messages()
- Implement `users.messages.send()` for send_message()
- Use Gmail native threading (thread_id)

### OutlookProvider (Task #20)
- Use Microsoft Graph API with OAuth 2.0
- Implement `/me/messages` for fetch_messages()
- Implement `/me/sendMail` for send_message()
- Use conversationId for threading

### SmtpImapProvider (Task #20)
- Use Python's `smtplib` for sending
- Use Python's `imaplib` for fetching
- Parse RFC 5322 headers manually
- Support STARTTLS and SSL/TLS

## Testing Strategy

### Unit Tests
- [ ] EmailEnvelope validation
- [ ] Thread root computation (with various header combinations)
- [ ] Reply header generation
- [ ] Email address parsing
- [ ] Provider type enum

### Integration Tests
- [ ] Provider credential validation
- [ ] Fetch messages with various filters
- [ ] Send message with threading
- [ ] Mark as read operation
- [ ] Error handling

### E2E Tests
- [ ] Complete email conversation flow
- [ ] Thread isolation (multiple threads with same user)
- [ ] Polling and deduplication
- [ ] OAuth refresh token handling

## Acceptance Criteria

- [x] Email manifest.json created with all required fields
- [x] Multi-provider support (Gmail, Outlook, SMTP/IMAP)
- [x] IEmailProvider protocol defined
- [x] EmailEnvelope data model with threading support
- [x] ValidationResult and SendResult models
- [x] Thread detection algorithm implemented
- [x] Key mapping rules documented
- [x] Helper functions provided
- [x] Module initialization files created
- [x] Comparison with Telegram/Slack manifests
- [x] Setup instructions for all providers
- [x] Edge cases documented
- [x] Task #18 marked as completed

## Next Steps

### Task #19: Email Channel Adapter (Polling Mode)
Implement `EmailAdapter` class that:
- Initializes provider based on config
- Runs polling loop
- Converts EmailEnvelope to InboundMessage
- Converts OutboundMessage to email send
- Handles deduplication

### Task #20: Gmail Provider Implementation
Implement `GmailProvider` class:
- OAuth 2.0 authentication
- Gmail API integration
- Message fetching and sending
- Thread tracking

### Task #21: Email Channel Testing and Acceptance
- Write unit tests for all components
- Write integration tests for providers
- Write E2E tests for complete flows
- Manual testing with real email accounts

## References

### Standards
- [RFC 5322: Internet Message Format](https://datatracker.ietf.org/doc/html/rfc5322)
- [RFC 2822: Message-ID](https://datatracker.ietf.org/doc/html/rfc2822#section-3.6.4)
- [RFC 5256: Email Threading](https://datatracker.ietf.org/doc/html/rfc5256)

### Provider APIs
- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [Microsoft Graph API](https://learn.microsoft.com/en-us/graph/api/resources/message)
- [Python smtplib](https://docs.python.org/3/library/smtplib.html)
- [Python imaplib](https://docs.python.org/3/library/imaplib.html)

### Internal Docs
- `KEY_MAPPING_RULES.md`: Thread detection and key mapping
- `manifest.json`: Channel configuration
- `providers/email/__init__.py`: Provider protocol

## Conclusion

Task #18 has been successfully completed. The Email Channel Manifest and Provider Architecture provides a solid foundation for implementing email communication in AgentOS CommunicationOS. The design follows Phase A patterns (similar to Telegram and Slack) while adapting to email's unique characteristics (polling mode, RFC 5322 threading, multi-provider support).

The implementation is ready for Task #19 (Adapter implementation) and Task #20 (Provider implementations).

---

**Signed:** Claude Sonnet 4.5
**Date:** 2026-02-01
