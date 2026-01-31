# Import Conflict Fix - app.py

## Problem
`agentos/webui/app.py` had an import conflict that caused the application to fail to start:

```python
import secrets  # Standard library - Line 20
from agentos.webui.api import secrets  # API router - Line 251 (old)
```

### Error Message
```
AttributeError: module 'secrets' has no attribute 'generate_csrf_token'
```

### Root Cause
The import of the `secrets` API router module on line 251 was overwriting the standard library `secrets` module imported on line 20. When the code tried to use `secrets.token_urlsafe(32)` on line 207, it was attempting to call this method on the API router module instead of the standard library module.

## Solution
Changed the API router import to use an alias to avoid the naming conflict:

**Before:**
```python
from agentos.webui.api import secrets
# ...
app.include_router(secrets.router, tags=["secrets"])
```

**After:**
```python
from agentos.webui.api import secrets as secrets_api  # Avoid conflict with stdlib secrets
# ...
app.include_router(secrets_api.router, tags=["secrets"])
```

## Changes Made

### File: `agentos/webui/app.py`

1. **Line 44-46**: Split the long import statement and added alias for secrets
   ```python
   # Import API routers
   from agentos.webui.api import health, sessions, tasks, ..., communication, mcp
   from agentos.webui.api import secrets as secrets_api  # Avoid conflict with stdlib secrets
   ```

2. **Line 252**: Updated router registration to use the new alias
   ```python
   app.include_router(secrets_api.router, tags=["secrets"])
   ```

## Verification

### Import Structure
- ✓ Standard library `secrets` imported at line 20
- ✓ API router `secrets` imported as `secrets_api` at line 46
- ✓ No naming conflict

### Usage
- ✓ Line 208: `secrets.token_urlsafe(32)` - Uses stdlib secrets
- ✓ Line 252: `secrets_api.router` - Uses API router

### Tests
- ✓ AST parsing confirms no import conflicts
- ✓ All usages verified correct
- ✓ No other import conflicts detected

## Impact
- **Risk**: Low - Only affects import naming, no functional changes
- **Breaking Changes**: None - Internal change only
- **Dependencies**: None

## Future Recommendations
1. Consider using more specific import names for API routers to avoid conflicts with common Python modules
2. Add a pre-commit hook or linting rule to detect stdlib name conflicts in imports
3. Document naming conventions for API router modules

## Testing
Run the verification script:
```bash
python3 test_import_fix.py
```

Expected output:
```
✓ ALL CHECKS PASSED - Import conflict is resolved!
```
