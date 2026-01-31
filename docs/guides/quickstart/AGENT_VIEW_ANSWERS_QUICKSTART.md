# Agent-View-Answers Quick Reference

**Quick access guide for developers working with Answers and Auth views**

## 🚀 Quick Start

### Access the Views

1. **Answer Packs:** Navigate to `Agent > Answer Packs` in the WebUI
2. **Auth Profiles:** Navigate to `Agent > Auth Profiles` in the WebUI

### URLs

- Answer Packs: `http://localhost:8000/#answers`
- Auth Profiles: `http://localhost:8000/#auth`

## 📦 Answer Packs

### Create a New Answer Pack

```javascript
// Via API
const response = await apiClient.post('/api/answers/packs', {
    name: "Security Best Practices",
    description: "Common security Q&A for development",
    answers: [
        {
            question: "How should API keys be stored?",
            answer: "Use environment variables or vault services",
            type: "security_answer"
        }
    ]
});
```

### Validate an Answer Pack

```javascript
// Via API
const response = await apiClient.post('/api/answers/packs/{pack_id}/validate', {});
// Returns: { valid: true/false, errors: [], warnings: [] }
```

### Generate Apply Proposal

```javascript
// Via API
const response = await apiClient.post('/api/answers/packs/{pack_id}/apply-proposal', {
    target_intent_id: "intent_001",
    target_type: "intent"
});
// Returns: { proposal_id, target_intent_id, preview, status: "pending" }
```

### Get Related Tasks/Intents

```javascript
// Via API
const response = await apiClient.get('/api/answers/packs/{pack_id}/related');
// Returns: [{ id, type, name, status }, ...]
```

## 🔐 Auth Profiles (Read-Only)

### List Auth Profiles

```javascript
// Via API
const response = await apiClient.get('/api/auth/profiles');
// Returns: [{ id, type, host, status, metadata }, ...]
```

### Validate Auth Profile

```javascript
// Via API
const response = await apiClient.post('/api/auth/profiles/{profile_id}/validate', {});
// Returns: { valid: true/false, message, tested_at }
```

### Add Auth Profile (CLI-ONLY)

```bash
# SSH Key
agentos auth add --type ssh --key ~/.ssh/id_rsa

# Personal Access Token
agentos auth add --type pat --token ghp_xxx --scopes repo,workflow

# netrc
agentos auth add --type netrc --machine gitlab.com --login user --password xxx
```

## 🎨 Component Usage

### Embed AuthReadOnlyCard in Another View

```javascript
// In your view's render method
const authContainer = document.querySelector('#auth-section');
const authCard = new AuthReadOnlyCard(authContainer);

// Store reference for cleanup
this.authCard = authCard;

// Cleanup in destroy()
destroy() {
    if (this.authCard) {
        this.authCard.destroy();
    }
}
```

### Use AnswersPacksView Programmatically

```javascript
// Create view instance
const container = document.querySelector('#view-container');
const answersView = new AnswersPacksView(container);

// Cleanup
answersView.destroy();
```

## 🎯 API Response Formats

### Answer Pack Object

```json
{
    "id": "pack_001",
    "name": "Security Q&A",
    "description": "Security best practices",
    "answers": [
        {
            "question": "...",
            "answer": "...",
            "type": "security_answer"
        }
    ],
    "created_at": "2026-01-29T10:00:00Z",
    "created_by": "admin",
    "status": "valid",
    "question_count": 5
}
```

### Auth Profile Object (Sanitized)

```json
{
    "id": "auth_ssh_001",
    "type": "ssh",
    "host": "github.com",
    "status": "valid",
    "metadata": {
        "fingerprint": "SHA256:abc...",
        "key_path": "~/.ssh/id_rsa",
        "key_type": "RSA 4096"
    },
    "created_at": "2026-01-15T10:00:00Z",
    "last_validated": "2026-01-29T08:00:00Z"
}
```

## 🔒 Security Notes

### Auth Data Sanitization

**What is shown:**
- SSH: Fingerprint, key path, key type (NOT private key)
- PAT: First 4 chars + `****`, scopes, expiration (NOT full token)
- netrc: Host, username (NOT password)

**What is hidden:**
- SSH private keys
- Full PAT tokens
- netrc passwords
- Any sensitive credential data

### CLI-Only Operations

These operations are **intentionally not exposed via WebUI** for security:
- Add auth profile
- Remove auth profile
- Update auth profile credentials

**Why?** Prevents credential exposure via browser/network interception.

## 🎨 Styling

### CSS Files

- `/static/css/answers.css` - Answer packs styling
- `/static/css/auth-card.css` - Auth profiles styling

### Key CSS Classes

**Answer Packs:**
- `.answer-pack-card` - Pack list card
- `.qa-item` - Q&A display
- `.validation-results` - Validation status
- `.apply-proposal-section` - Apply proposal form

**Auth Profiles:**
- `.auth-profile-card` - Profile card
- `.cli-only-banner` - CLI notice banner
- `.auth-metadata` - Sanitized metadata display
- `.auth-type-badge` - Type indicator (SSH/PAT/netrc)

## 🧪 Testing

### Manual Testing

1. **Create Answer Pack:**
   - Navigate to Answer Packs view
   - Click "Create New Pack"
   - Fill in name, description
   - Add Q&A items
   - Save

2. **Validate Pack:**
   - View pack details
   - Click "Validate"
   - Check validation results

3. **Generate Apply Proposal:**
   - View pack details
   - Click "Apply to Intent"
   - Enter intent ID
   - Click "Generate Apply Proposal"
   - Verify preview display

4. **View Auth Profiles:**
   - Navigate to Auth Profiles view
   - Verify data is sanitized
   - Try to click Edit/Delete (should be disabled)
   - Click Validate on a profile

### API Testing

```bash
# List answer packs
curl http://localhost:8000/api/answers/packs

# Create answer pack
curl -X POST http://localhost:8000/api/answers/packs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Pack",
    "description": "Test",
    "answers": [{"question": "Q?", "answer": "A.", "type": "general"}]
  }'

# List auth profiles
curl http://localhost:8000/api/auth/profiles

# Validate auth profile
curl -X POST http://localhost:8000/api/auth/profiles/auth_ssh_001/validate
```

## 🐛 Troubleshooting

### Issue: Views not loading

**Check:**
1. Script includes in `index.html`:
   ```html
   <script src="/static/js/views/AnswersPacksView.js?v=1"></script>
   <script src="/static/js/components/AuthReadOnlyCard.js?v=1"></script>
   ```

2. CSS includes:
   ```html
   <link rel="stylesheet" href="/static/css/answers.css?v=1">
   <link rel="stylesheet" href="/static/css/auth-card.css?v=1">
   ```

3. Route handlers in `main.js`:
   ```javascript
   case 'answers':
       renderAnswerPacksView(container);
       break;
   case 'auth':
       renderAuthProfilesView(container);
       break;
   ```

### Issue: API endpoints not found

**Check:**
1. API imports in `app.py`:
   ```python
   from agentos.webui.api import ..., answers, auth
   ```

2. Router registration:
   ```python
   app.include_router(answers.router, tags=["answers"])
   app.include_router(auth.router, tags=["auth"])
   ```

### Issue: Empty data

**Expected:** Demo data is included in the API files for testing.

**Check:**
- `answers.py`: `_answer_packs` dict has demo data
- `auth.py`: `_auth_profiles` dict has demo data

## 📚 Architecture

### Data Flow

```
User Interaction
    ↓
AnswersPacksView / AuthReadOnlyCard (UI)
    ↓
ApiClient (HTTP)
    ↓
FastAPI Router (answers.router / auth.router)
    ↓
In-Memory Storage (demo) / SQLite (production)
```

### Component Hierarchy

```
AnswersPacksView
├── List View
│   ├── FilterBar
│   ├── Answer Pack Cards
│   └── Create Button
├── Detail View
│   ├── Pack Metadata
│   ├── Q&A List
│   ├── Validation Results
│   ├── Apply Proposal Form
│   └── Related Items
└── Create View
    ├── Pack Info Form
    ├── Q&A Item Editor
    └── JSON Import

AuthReadOnlyCard
├── CLI-Only Banner
├── Filter Bar
└── Profile Cards
    ├── Type Badge
    ├── Status Badge
    ├── Metadata (Sanitized)
    ├── Validate Button
    └── Disabled Edit/Delete
```

## 🔗 Related Documentation

- **API Docs:** See individual API files for endpoint documentation
- **CLI Docs:** See `agentos/cli/auth.py` for auth CLI commands
- **Component Docs:** See component file headers for detailed usage

## 📝 Code Locations

```
API:
  agentos/webui/api/answers.py
  agentos/webui/api/auth.py

Views:
  agentos/webui/static/js/views/AnswersPacksView.js
  agentos/webui/static/js/components/AuthReadOnlyCard.js

Styles:
  agentos/webui/static/css/answers.css
  agentos/webui/static/css/auth-card.css

Routes:
  agentos/webui/static/js/main.js (renderAnswerPacksView, renderAuthProfilesView)
  agentos/webui/templates/index.html (navigation items)
```

---

**Last Updated:** 2026-01-29
**Version:** 1.0
