# Self-Check Model Matching Optimization

## Problem Statement

The session-based self-check feature needed to filter provider checks based on the current session's model. However, there was a mismatch between how model names are stored in sessions vs. provider registry:

- **Session Storage**: Full model filenames (e.g., `Qwen3-Coder-30B-A3B-Instruct-UD-Q8_K_XL.gguf`)
- **Provider Registry ID**: Simplified names (e.g., `llamacpp:qwen3-coder-30b`)
- **Simple Normalization Failed**: `llamacpp:qwen3-coder-30b-a3b-instruct-ud-q8-k-xl` ≠ `llamacpp:qwen3-coder-30b`

## Solution: Multi-Strategy Intelligent Matching

Implemented a cascading matching strategy in `agentos/selfcheck/runner.py`'s `_get_session_provider()` method:

### Strategy 1: Exact Match
Try to match the fully normalized model name against provider instance IDs.

```python
target_id = f"{provider_type}:{model_normalized}"
if target_id in provider_instances:
    return target_id
```

### Strategy 2a: Prefix Matching
Check if the normalized model name starts with the registry model name.

**Example:**
- Normalized: `qwen3-coder-30b-a3b-instruct-ud-q8-k-xl`
- Registry: `qwen3-coder-30b`
- Match: ✅ (normalized starts with registry)

### Strategy 2b: Dash-less Matching
Handle cases where dash placement differs (e.g., version numbers).

**Example:**
- Normalized: `glm-47-flash-ud-q8-k-xl` → `glm47flashudq8kxl`
- Registry: `glm47flash-q8` → `glm47flashq8`
- Match: Partial (needs Strategy 2c)

### Strategy 2c: Metadata Matching
Check provider configuration metadata for exact model filename match.

**Example:**
- Session model: `GLM-4.7-Flash-UD-Q8_K_XL.gguf`
- Provider config metadata: `{"model": "GLM-4.7-Flash-UD-Q8_K_XL.gguf"}`
- Match: ✅ (exact match in metadata)

### Strategy 3: Fallback to Provider Type
If no specific instance matches, return the provider type to match all instances.

**Example:**
- Session model: `UnknownModel-XYZ.gguf`
- Registry: No matching instance
- Return: `llamacpp` (matches all llamacpp instances)

## Normalization Process

Before matching, model names are normalized:

1. Convert to lowercase
2. Remove `.gguf` extension
3. Replace underscores with dashes
4. Replace version number dots with empty string (e.g., `4.7` → `47`)

```python
model_normalized = (
    model_name.lower()
    .replace(".gguf", "")
    .replace("_", "-")
)
model_normalized = re.sub(r'(\d+)\.(\d+)', r'\1\2', model_normalized)
```

## Provider Filtering Logic

The `_check_providers()` method was also enhanced to support both exact instance matching and provider-type matching:

```python
if target_provider:
    status_id_normalized = status.id.replace("provider.", "")

    if ":" in target_provider:
        # Specific instance requested - exact match
        if status_id_normalized != target_provider:
            continue
    else:
        # Provider type only - match all instances of this type
        provider_type_in_status = status_id_normalized.split(":")[0]
        if provider_type_in_status != target_provider:
            continue
```

## Test Coverage

Created comprehensive test suite in `scripts/tests/test_selfcheck_model_matching.py`:

### Test Cases

1. **Full model filename (Qwen3 30B)** ✅
   - Session: `Qwen3-Coder-30B-A3B-Instruct-UD-Q8_K_XL.gguf`
   - Matched: `llamacpp:qwen3-coder-30b`
   - Strategy: Prefix matching (2a)

2. **Full model filename (GLM 4.7)** ✅
   - Session: `GLM-4.7-Flash-UD-Q8_K_XL.gguf`
   - Matched: `llamacpp:glm47flash-q8`
   - Strategy: Metadata matching (2c)

3. **Short model name (exact match)** ✅
   - Session: `qwen3-coder-30b`
   - Matched: `llamacpp:qwen3-coder-30b`
   - Strategy: Exact match (1)

4. **Only provider type (no model)** ✅
   - Session: No model specified
   - Matched: `llamacpp`
   - Strategy: Direct return (no model)

5. **Unknown model (fallback to type)** ✅
   - Session: `UnknownModel-XYZ.gguf`
   - Matched: `llamacpp`
   - Strategy: Fallback (3)

### Self-Check Filtering Test

Verified that when a session is provided:
- Only the matched provider instance is checked
- Other provider instances are skipped
- Provider check count is 1 (not all instances)

## Benefits

1. **Robust Matching**: Handles various model naming conventions
2. **Backward Compatible**: Falls back to provider type when no exact match
3. **Performance**: Avoids checking unnecessary providers for session-specific self-checks
4. **Extensible**: Easy to add new matching strategies if needed

## Files Modified

- `/Users/pangge/PycharmProjects/AgentOS/agentos/selfcheck/runner.py`
  - Enhanced `_get_session_provider()` with multi-strategy matching
  - Updated `_check_providers()` to support type-only matching

## Files Added

- `/Users/pangge/PycharmProjects/AgentOS/scripts/tests/test_selfcheck_model_matching.py`
  - Comprehensive test suite for matching logic
  - Validates all matching strategies
  - Tests provider filtering behavior

## Example Log Output

```
INFO - Fuzzy match found: llamacpp:qwen3-coder-30b (session model: Qwen3-Coder-30B-A3B-Instruct-UD-Q8_K_XL.gguf)
INFO - Self-check will focus on session provider: llamacpp:qwen3-coder-30b
INFO - Fuzzy match found (metadata): llamacpp:glm47flash-q8 (session model: GLM-4.7-Flash-UD-Q8_K_XL.gguf)
```

## Future Improvements

1. **Caching**: Cache normalization results to improve performance
2. **Fuzzy String Matching**: Use Levenshtein distance for even better matching
3. **Model Aliases**: Allow providers to register model aliases
4. **Pattern Matching**: Support regex patterns in provider configuration

## Conclusion

The intelligent matching system successfully handles the variety of model naming conventions used in AgentOS, ensuring that session-based self-checks accurately target the correct provider instances while maintaining backward compatibility and performance.
