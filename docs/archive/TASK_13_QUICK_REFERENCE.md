# Task #13: Extension Template Wizard - Quick Reference

## 🚀 Quick Start

### For End Users

1. Open AgentOS WebUI: http://localhost:8000
2. Navigate to **Extensions** page
3. Click **"Create Extension Template"** (purple button)
4. Follow the 4-step wizard:
   - **Step 1**: Enter basic info (ID, name, description, author)
   - **Step 2**: Add capabilities (slash commands, tools, etc.)
   - **Step 3**: Select permissions needed
   - **Step 4**: Review and download
5. Extract the ZIP and start developing!

### For Developers

```python
from agentos.core.extensions.template_generator import create_template

# Generate a template programmatically
zip_content = create_template(
    extension_id='tools.myext',
    extension_name='My Extension',
    description='What my extension does',
    author='Your Name',
    capabilities=[
        {
            'type': 'slash_command',
            'name': '/mycommand',
            'description': 'My command description'
        }
    ],
    permissions=['network', 'exec']
)

# Save to file
with open('tools.myext.zip', 'wb') as f:
    f.write(zip_content)
```

## 📋 API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/extensions/templates` | List template types |
| GET | `/api/extensions/templates/permissions` | List available permissions |
| GET | `/api/extensions/templates/capability-types` | List capability types |
| POST | `/api/extensions/templates/generate` | Generate template ZIP |

### Example: Generate Template

```bash
curl -X POST http://localhost:8000/api/extensions/templates/generate \
  -H "Content-Type: application/json" \
  -d '{
    "extension_id": "tools.myext",
    "extension_name": "My Extension",
    "description": "My custom extension",
    "author": "Your Name",
    "capabilities": [
      {
        "type": "slash_command",
        "name": "/mycommand",
        "description": "My command"
      }
    ],
    "permissions": ["network"]
  }' \
  --output myext.zip
```

## 📦 Generated Template Structure

```
tools.myext/
├── manifest.json          # Extension configuration
├── handlers.py            # Capability implementations
├── install/
│   └── plan.yaml         # Installation steps
├── docs/
│   └── USAGE.md          # Usage documentation
├── README.md             # Main documentation
├── icon.svg              # Extension icon
└── .gitignore            # Git ignore rules
```

## ✅ Validation Rules

### Extension ID Format
- **Valid**: `tools.myext`, `custom.extension`, `dev.test123`
- **Invalid**: `Invalid` (no dot), `Tools.MyExt` (uppercase), `tools.my-ext` (hyphen)
- **Pattern**: `[a-z0-9]+\.[a-z0-9]+`

### Required Fields
- ✅ extension_id
- ✅ extension_name
- ✅ description
- ✅ author
- ✅ capabilities (at least 1)

### Optional Fields
- permissions (can be empty array)
- capability config

## 🎨 Capability Types

| Type | ID | Example Name | Use Case |
|------|-----|--------------|----------|
| Slash Command | `slash_command` | `/mycommand` | Chat interface commands |
| Tool | `tool` | `my_tool` | Agent task execution |
| Agent | `agent` | `my_agent` | Custom agent implementations |
| Workflow | `workflow` | `my_workflow` | Task orchestration |

## 🔒 Available Permissions

| Permission ID | Purpose |
|---------------|---------|
| `network` | HTTP/HTTPS requests |
| `exec` | Execute system commands |
| `filesystem.read` | Read files |
| `filesystem.write` | Write files |
| `database` | Access database |
| `secrets` | Access secrets/credentials |
| `sessions` | Access chat sessions |
| `tasks` | Create/manage tasks |

## 🧪 Testing

### Run Unit Tests
```bash
python3 -m pytest tests/unit/core/extensions/test_template_generator.py -v
```

### Run Integration Tests
```bash
# Start server first: uvicorn agentos.webui.app:app --reload
python3 -m pytest tests/integration/extensions/test_template_api.py -v
```

### Run Acceptance Tests
```bash
# Start server first
python3 -m pytest tests/acceptance/test_task_13_template_wizard.py -v
```

### Quick Manual Test
```bash
python3 test_template_wizard.py
```

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| Wizard button not visible | Clear cache, reload page |
| Extension ID validation fails | Use lowercase, one dot, no special chars |
| Download fails | Check server logs, verify API registration |
| ZIP corrupted | Check file size, try different browser |

## 📝 Next Steps After Template Download

1. **Extract the ZIP**
   ```bash
   unzip tools.myext.zip -d tools.myext/
   cd tools.myext/
   ```

2. **Implement Handlers**
   Edit `handlers.py` and replace TODO comments with actual logic

3. **Customize Manifest**
   Update `manifest.json` if needed

4. **Test Locally**
   ```bash
   zip -r tools.myext.zip .
   # Upload via WebUI Extensions page
   ```

5. **Develop & Iterate**
   - Test in AgentOS chat interface
   - Add more capabilities as needed
   - Update documentation

## 💡 Tips & Best Practices

1. **Extension ID**: Use descriptive namespace (e.g., `tools.`, `integrations.`)
2. **Capability Names**: Use clear, action-oriented names (`/search`, `/analyze`)
3. **Permissions**: Request only what you need (principle of least privilege)
4. **Documentation**: Keep README.md and USAGE.md up to date
5. **Version**: Bump version in manifest.json for each release
6. **Testing**: Test your extension before distributing

## 🔗 Related Documentation

- Extension System Overview: `docs/extensions/README.md`
- Extension Development Guide: `docs/extensions/DEVELOPMENT.md`
- API Reference: `docs/api/extensions.md`
- Testing Guide: `TASK_13_TESTING_GUIDE.md`

## 📊 Key Metrics

- **Template Generation Time**: < 100ms
- **ZIP File Size**: 5-15 KB (typical)
- **Files Generated**: 7 files
- **API Response Time**: < 200ms
- **Wizard Steps**: 4 steps
- **Unit Tests**: 20 tests
- **Integration Tests**: 14 tests
- **Acceptance Tests**: 12 tests

## 🆘 Support

If you encounter issues:

1. Check the testing guide: `TASK_13_TESTING_GUIDE.md`
2. Review completion report: `TASK_13_COMPLETION_REPORT.md`
3. Run unit tests to verify installation
4. Check server logs for API errors
5. Use browser dev tools to debug frontend issues

---

**Last Updated**: 2025-01-30
**Task Status**: ✅ Completed
**Version**: 1.0.0
