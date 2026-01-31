# ADR-EXT-001 Enforcement Checklist

This document tracks the enforcement of ADR-EXT-001 (Declarative Extensions Only) in the codebase.

## Enforcement Points

### Validator (agentos/core/extensions/validator.py)

- [x] **Line 135-141**: Check entrypoint == null
  - Validates that manifest.json has `entrypoint: null`
  - Raises ValidationError with ADR reference if not null

- [x] **Line 112-122**: Forbidden file types in root
  - Checks for .py, .js, .sh, .exe, .bat, .cmd, .ps1 in root directory
  - Raises ValidationError with ADR reference if found

- [x] **Line 77-92**: Mandatory files check
  - Ensures required files exist: manifest.json, install/plan.yaml, commands/commands.yaml, docs/USAGE.md
  - Raises ValidationError if missing

- [x] **Line 94-110**: Path traversal and symlink check
  - Rejects `..` and absolute paths in zip
  - Detects and rejects symlinks
  - Raises ValidationError with security reference

### Engine (agentos/core/extensions/engine.py)

- [x] **Line 1178-1189**: Step type whitelist
  - Only allows 8 whitelisted step types (detect.platform, download.http, extract.zip, exec.shell, exec.powershell, verify.command_exists, verify.http, write.config)
  - Raises InstallError with INVALID_STEP_TYPE code and ADR reference

- [x] **Line 1191-1203**: Permission check before execution
  - Verifies that step's required_permissions are declared in manifest
  - Raises InstallError with PERMISSION_DENIED code and hint to update manifest

- [x] **Line 913-929, 1180-1225**: Audit log for each step
  - Logs to Python logger with structured metadata
  - Attempts to log to task_audits if available
  - Includes extension_id, install_id, step_id, step_type, duration, output, error

### Installer (agentos/core/extensions/installer.py)

- [x] **Line 78-92**: Path traversal prevention
  - Checks for `..` in relative paths
  - Checks for absolute paths
  - Ensures resolved path is within target directory using relative_to()
  - Raises InstallationError with ADR reference if checks fail

- [x] **Line 122-128** (via Validator): SHA256 verification
  - Validator.validate_extension_package() calculates and verifies SHA256
  - Raises ValidationError on hash mismatch
  - Used in both upload and URL installation flows

### API (agentos/webui/api/extensions.py)

- [ ] **Admin token check**: NOT IMPLEMENTED YET
  - POST /api/extensions/install - No auth check (line 408)
  - POST /api/extensions/install-url - No auth check (line 555)
  - DELETE /api/extensions/{id} - No auth check (line 824)
  - PUT /api/extensions/{id}/config - No auth check (line 931)
  - **TODO**: Add auth middleware or decorators when auth system is available

## Test Coverage

### Unit Tests Required

1. **test_validator_rejects_entrypoint.py**
   - Test that validator rejects manifest with entrypoint != null
   - Expected: ValidationError with ADR-EXT-001 message

2. **test_validator_rejects_root_executables.py**
   - Test that validator rejects zip with .py, .js, .sh in root
   - Expected: ValidationError with ADR-EXT-001 message

3. **test_engine_rejects_invalid_step_type.py**
   - Test that engine rejects non-whitelisted step types
   - Expected: InstallError with INVALID_STEP_TYPE code

4. **test_engine_checks_permissions.py**
   - Test that engine rejects steps requiring undeclared permissions
   - Expected: InstallError with PERMISSION_DENIED code

5. **test_installer_path_traversal.py**
   - Test that installer rejects zip with `../` paths
   - Test that installer rejects zip with absolute paths
   - Expected: InstallationError with ADR-EXT-001 message

6. **test_installer_escape_detection.py**
   - Test that installer detects and blocks path escape attempts
   - Expected: InstallationError with escape detection message

### Integration Tests Required

1. **test_e2e_extension_install_with_permissions.py**
   - Create test extension with network permission
   - Verify installation succeeds
   - Verify step with network permission executes

2. **test_e2e_extension_install_without_permissions.py**
   - Create test extension without network permission
   - Add step requiring network permission
   - Verify installation fails with PERMISSION_DENIED

## Verification Commands

```bash
# Run validator tests
pytest tests/unit/core/extensions/test_validator.py -v -k "entrypoint or executable"

# Run engine tests
pytest tests/unit/core/extensions/test_engine.py -v -k "permission or whitelist"

# Run installer tests
pytest tests/unit/core/extensions/test_installer.py -v -k "path_traversal"

# Run all extension tests
pytest tests/unit/core/extensions/ tests/integration/extensions/ -v
```

## Compliance Matrix

| Requirement | Location | Status | Test Coverage |
|-------------|----------|--------|---------------|
| No entrypoint execution | validator.py:135 | ✅ Enforced | ✅ test_validate_manifest_rejects_entrypoint |
| No root executables | validator.py:112 | ✅ Enforced | ✅ test_validate_zip_rejects_root_* (3 tests) |
| Step type whitelist | engine.py:1178 | ✅ Enforced | ✅ test_engine_rejects_invalid_step_type |
| Permission gating | engine.py:1191 | ✅ Enforced | ✅ test_engine_checks_permissions_network (+ 3 more) |
| Path traversal protection | installer.py:78 | ✅ Enforced | ✅ test_path_traversal_protection_in_extract |
| SHA256 verification | validator.py:278 | ✅ Enforced | ✅ Has test |
| Audit logging | engine.py:1180 | ✅ Enforced | ✅ Has test |
| Admin auth | api/extensions.py | ❌ Not implemented | N/A |

## Test Results

All ADR-EXT-001 enforcement tests passing (12 tests):
```bash
# Run all enforcement tests
pytest tests/unit/core/extensions/test_validator.py::TestExtensionValidator::test_validate_manifest_rejects_entrypoint \
      tests/unit/core/extensions/test_validator.py::TestExtensionValidator::test_validate_zip_rejects_root_* \
      tests/unit/core/extensions/test_engine.py::TestADREnforcement \
      tests/unit/core/extensions/test_installer.py::TestADREnforcementInstaller -v

# Result: 12 passed in 1.26s ✅
```

## Next Steps

1. ~~**Write missing tests** (Priority: HIGH)~~ ✅ COMPLETED (2026-01-30)
   - ✅ Created test_validate_manifest_rejects_entrypoint
   - ✅ Created test_validate_zip_rejects_root_* (3 tests)
   - ✅ Created test_engine_* permission tests (6 tests)
   - ✅ Created test_installer path traversal tests (2 tests)
   - ✅ All 12 tests passing

2. **Add admin authentication** (Priority: MEDIUM)
   - When auth system is available, add decorators to API endpoints
   - Test that unauthenticated requests are rejected

3. **Security audit** (Priority: HIGH)
   - Schedule security review of enforcement mechanisms
   - Test with malicious extension packages
   - Verify no bypass vectors exist

4. **Documentation update** (Priority: LOW)
   - Update extension developer guide with ADR-EXT-001 requirements
   - Add examples of compliant extensions
   - Document permission system

## Review Schedule

- **Next Review Date**: 2026-02-15
- **Reviewer**: Security Team + Extension System Maintainers
- **Focus Areas**:
  - Test coverage completeness
  - New bypass vectors discovered
  - Permission system usage patterns
  - Performance impact of checks

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-01-30 | Initial enforcement checklist created | System |
| 2026-01-30 | Added validator entrypoint check | System |
| 2026-01-30 | Added validator root executable check | System |
| 2026-01-30 | Added engine step type whitelist | System |
| 2026-01-30 | Added engine permission gating | System |
| 2026-01-30 | Added installer path traversal protection | System |
