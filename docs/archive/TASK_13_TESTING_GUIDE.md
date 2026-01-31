# Task #13: Extension Template Wizard - Testing Guide

## Overview

This guide provides instructions for testing the Extension Template Wizard functionality implemented in Task #13.

## Features Implemented

### Backend
1. **Template Generator** (`agentos/core/extensions/template_generator.py`)
   - Generates complete extension templates with all necessary files
   - Validates extension ID format (namespace.name)
   - Creates manifest.json, handlers.py, README.md, install plan, docs, and icon

2. **API Endpoints** (`agentos/webui/api/extension_templates.py`)
   - `GET /api/extensions/templates` - List template types
   - `GET /api/extensions/templates/permissions` - List available permissions
   - `GET /api/extensions/templates/capability-types` - List capability types
   - `POST /api/extensions/templates/generate` - Generate and download template ZIP

### Frontend
1. **Wizard UI** (ExtensionsView.js)
   - 4-step wizard modal
   - Step 1: Basic information (ID, name, description, author)
   - Step 2: Capability configuration (add/remove capabilities)
   - Step 3: Permission selection
   - Step 4: Review and download

2. **UI Components** (extension-wizard.css)
   - Wizard progress indicator
   - Form inputs with validation
   - Responsive design

## Manual Testing Steps

### 1. Start the WebUI

```bash
cd /Users/pangge/PycharmProjects/AgentOS
uvicorn agentos.webui.app:app --reload --port 8000
```

### 2. Access the Extensions Page

1. Open browser: http://localhost:8000
2. Navigate to Extensions page
3. Look for "Create Extension Template" button (purple gradient)

### 3. Test the Wizard

#### Step 1: Basic Information
- Click "Create Extension Template" button
- Fill in:
  - Extension ID: `tools.mytest` (must be lowercase, format: namespace.name)
  - Extension Name: `My Test Extension`
  - Description: `A test extension for demonstration`
  - Author: `Your Name`
- Click "Next"

#### Step 2: Capabilities
- Click "Add Capability"
- Fill in first capability:
  - Type: `slash_command`
  - Name: `/mycommand`
  - Description: `My custom command`
- Add another capability:
  - Type: `tool`
  - Name: `my_tool`
  - Description: `A useful tool`
- Click "Next"

#### Step 3: Permissions
- Select permissions needed:
  - ☑ Network Access
  - ☑ Execute Commands
- Click "Next"

#### Step 4: Review & Download
- Review all information
- Click "Download Template"
- Verify ZIP file is downloaded: `tools.mytest.zip`

### 4. Verify Generated Template

Extract the downloaded ZIP and verify it contains:

```
tools.mytest/
├── manifest.json          # Extension metadata
├── handlers.py            # Capability handlers
├── install/
│   └── plan.yaml         # Installation plan
├── docs/
│   └── USAGE.md          # Usage documentation
├── README.md             # Main documentation
├── icon.svg              # Extension icon
└── .gitignore            # Git ignore rules
```

### 5. Verify File Contents

#### manifest.json
- Check extension ID, name, version
- Verify capabilities are listed
- Verify permissions are listed

#### handlers.py
- Check that handler functions are generated for each capability
- Verify HANDLERS dictionary maps capability names to functions

#### README.md
- Check extension information is present
- Verify capabilities and permissions are documented

## API Testing

Use the provided test script:

```bash
python3 test_template_wizard.py
```

Or use curl:

### List Template Types
```bash
curl http://localhost:8000/api/extensions/templates
```

### List Permissions
```bash
curl http://localhost:8000/api/extensions/templates/permissions
```

### List Capability Types
```bash
curl http://localhost:8000/api/extensions/templates/capability-types
```

### Generate Template
```bash
curl -X POST http://localhost:8000/api/extensions/templates/generate \
  -H "Content-Type: application/json" \
  -d '{
    "extension_id": "tools.mytest",
    "extension_name": "My Test Extension",
    "description": "A test extension",
    "author": "Test User",
    "capabilities": [
      {
        "type": "slash_command",
        "name": "/mycommand",
        "description": "My command"
      }
    ],
    "permissions": ["network"]
  }' \
  --output mytest.zip
```

## Unit Tests

Run the unit tests:

```bash
# Test template generator
python3 -m pytest tests/unit/core/extensions/test_template_generator.py -v

# Test API endpoints (requires server running)
python3 -m pytest tests/integration/extensions/test_template_api.py -v
```

## Edge Cases to Test

### Extension ID Validation
- ✅ Valid: `tools.myext`, `custom.extension`, `dev.test123`
- ❌ Invalid: `invalid` (no dot), `Invalid.Ext` (uppercase), `tools.my-ext` (hyphen)

### Multiple Capabilities
- Add 3+ capabilities of different types
- Verify all are included in manifest and handlers

### No Permissions
- Create extension with empty permissions list
- Verify manifest has empty array

### Long Names/Descriptions
- Test with very long extension names (100+ chars)
- Test with unicode in descriptions (中文, emoji)

### Capability Name Edge Cases
- Slash commands: `/my-command`, `/command_name`
- Tools: `tool_name`, `ToolName`
- Verify special characters are handled correctly in handler function names

## Troubleshooting

### Wizard Button Not Visible
- Clear browser cache
- Check console for JavaScript errors
- Verify extension-wizard.css is loaded

### Download Fails
- Check server logs for errors
- Verify API endpoint is registered in app.py
- Check network tab in browser dev tools

### Invalid Extension ID Error
- Ensure format is `namespace.name` (lowercase only)
- No hyphens or underscores
- Only one dot separator

### Handler Function Names
- Special characters in capability names are replaced with underscores
- Leading slashes are removed
- Consecutive underscores are collapsed

## Success Criteria

- ✅ Wizard opens and displays 4 steps
- ✅ All form validations work
- ✅ Can add/remove capabilities dynamically
- ✅ Can select multiple permissions
- ✅ Review step shows all entered data
- ✅ Download generates valid ZIP file
- ✅ Generated template can be installed as an extension
- ✅ All unit tests pass (20/20)
- ✅ All integration tests pass

## Next Steps

After testing:

1. Install the generated template to verify it works end-to-end
2. Customize the handlers.py to implement actual logic
3. Test the extension in AgentOS chat interface
4. Share the template with other developers

## Known Limitations

1. Icon is auto-generated (simple SVG with first letter)
2. Handler implementations are placeholders (TODO comments)
3. No validation of capability names against existing extensions
4. No conflict detection for slash commands

## Future Enhancements

1. Add more template types (API wrapper, data processor, etc.)
2. Support for custom configuration schemas
3. Visual icon editor
4. Template preview before download
5. Import existing extension to generate template
6. Template marketplace integration
