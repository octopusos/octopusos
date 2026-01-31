# Preview API - Three.js WebGL UMD Preset

## Overview

The Preview API has been extended to support automatic dependency injection for Three.js applications. This solves the common problem of "FontLoader is not a constructor" and similar errors when using Three.js extensions.

## Problem Statement

When using Three.js, the core library (`three.min.js`) does not include all features. Extensions like `FontLoader`, `TextGeometry`, and `OrbitControls` must be loaded separately in the correct order:

```html
<!-- CORRECT order -->
<script src="three.min.js"></script>                    <!-- Core first -->
<script src="loaders/FontLoader.js"></script>           <!-- Extensions second -->
<script src="geometries/TextGeometry.js"></script>
```

If you load only the core, you get:
```
TypeError: FontLoader is not a constructor
```

## Solution

The `three-webgl-umd` preset automatically:
1. Detects which Three.js extensions your code uses
2. Injects the required script tags in the correct order
3. Uses CDN URLs (jsDelivr) for fast loading

## API Reference

### POST /api/preview

Create a preview session with optional preset.

**Request:**
```json
{
  "html": "<!DOCTYPE html>...",
  "preset": "three-webgl-umd",
  "snippet_id": "optional-tracking-id"
}
```

**Response:**
```json
{
  "session_id": "uuid-here",
  "url": "/api/preview/uuid-here",
  "preset": "three-webgl-umd",
  "deps_injected": [
    "three-core",
    "three-fontloader",
    "three-text-geometry",
    "three-orbit-controls"
  ],
  "expires_at": 1706484000
}
```

### GET /api/preview/{session_id}

Retrieve the HTML content with injected dependencies.

**Response:** HTML content with proper headers
- Status 200: Success
- Status 404: Session not found
- Status 410: Session expired (TTL: 1 hour)

### GET /api/preview/{session_id}/meta

Get session metadata without retrieving HTML.

**Response:**
```json
{
  "session_id": "uuid-here",
  "preset": "three-webgl-umd",
  "deps_injected": ["three-core", "three-fontloader"],
  "snippet_id": "optional-tracking-id",
  "created_at": 1706480400,
  "expires_at": 1706484000,
  "ttl_remaining": 3600
}
```

### DELETE /api/preview/{session_id}

Delete a preview session (cleanup).

## Supported Presets

### `html-basic` (default)
No processing. HTML is served as-is.

### `three-webgl-umd`
Automatic Three.js dependency detection and injection.

**Detected Dependencies:**

| Dependency | Trigger | CDN URL |
|------------|---------|---------|
| `three-core` | Always | `three@0.169.0/build/three.min.js` |
| `three-fontloader` | `FontLoader` in code | `three@0.169.0/examples/js/loaders/FontLoader.js` |
| `three-text-geometry` | `TextGeometry` in code | `three@0.169.0/examples/js/geometries/TextGeometry.js` |
| `three-orbit-controls` | `OrbitControls` in code | `three@0.169.0/examples/js/controls/OrbitControls.js` |
| `three-transform-controls` | `TransformControls` in code | `three@0.169.0/examples/js/controls/TransformControls.js` |
| `three-gltf-loader` | `GLTFLoader` in code | `three@0.169.0/examples/js/loaders/GLTFLoader.js` |
| `three-obj-loader` | `OBJLoader` in code | `three@0.169.0/examples/js/loaders/OBJLoader.js` |
| `three-effect-composer` | `EffectComposer` in code | `three@0.169.0/examples/js/postprocessing/EffectComposer.js` |
| `three-render-pass` | `RenderPass` in code | `three@0.169.0/examples/js/postprocessing/RenderPass.js` |

## Usage Example

### Python (requests)

```python
import requests

html = """
<!DOCTYPE html>
<html>
<body>
    <script>
        const loader = new THREE.FontLoader();
        loader.load('font.json', function(font) {
            const geometry = new THREE.TextGeometry('Hello', { font });
            console.log('Success!');
        });
    </script>
</body>
</html>
"""

# Create preview with preset
response = requests.post('http://localhost:8000/api/preview', json={
    'html': html,
    'preset': 'three-webgl-umd'
})

data = response.json()
print(f"Preview URL: {data['url']}")
print(f"Dependencies: {data['deps_injected']}")

# Result:
# Preview URL: /api/preview/abc-123-def
# Dependencies: ['three-core', 'three-fontloader', 'three-text-geometry']
```

### JavaScript (fetch)

```javascript
const html = `
<!DOCTYPE html>
<html>
<body>
    <script>
        const controls = new THREE.OrbitControls(camera, renderer.domElement);
    </script>
</body>
</html>
`;

const response = await fetch('/api/preview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        html: html,
        preset: 'three-webgl-umd',
        snippet_id: 'my-snippet-123'
    })
});

const data = await response.json();
console.log('Preview created:', data);

// Load in iframe
const iframe = document.createElement('iframe');
iframe.src = data.url;
document.body.appendChild(iframe);
```

## Testing

Run the test suite:

```bash
# Start the server
python -m agentos.webui.app

# In another terminal, run tests
python test_preview_api.py
```

Test cases:
1. Basic HTML preview (no processing)
2. Three.js with FontLoader (auto-detection)
3. Dependency detection accuracy
4. Meta endpoint functionality
5. 404 for nonexistent sessions

## Architecture

### Dependency Detection

Uses regex pattern matching to detect Three.js class usage:

```python
if re.search(r'\bFontLoader\b', code):
    deps.append("three-fontloader")
```

### Injection Strategy

Script tags are injected before `</head>` (preferred) or `<body>`:

```python
head_close = html.find('</head>')
if head_close != -1:
    return html[:head_close] + scripts + '\n' + html[head_close:]
```

### Session Management

Sessions are stored in-memory with TTL:

```python
@dataclass
class PreviewSession:
    session_id: str
    html: str
    preset: str
    deps_injected: List[str]
    snippet_id: Optional[str]
    created_at: int
    expires_at: int  # created_at + 3600 (1 hour)
```

## Audit Events

All preview operations are logged for debugging and analytics:

| Event Type | Trigger | Metadata |
|------------|---------|----------|
| `preview_session_created` | POST /api/preview | `preset`, `deps_count` |
| `preview_runtime_selected` | Preset applied | `preset` |
| `preview_dep_injected` | Dependencies injected | `deps` (list) |
| `preview_session_opened` | GET /api/preview/{id} | None |
| `preview_session_expired` | TTL exceeded | None |

Example log:
```
INFO:agentos.webui.api.preview:Preview audit: {
  "timestamp": "2026-01-28T10:30:00Z",
  "event_type": "preview_session_created",
  "preview_id": "abc-123-def",
  "snippet_id": "my-snippet",
  "metadata": {"preset": "three-webgl-umd", "deps_count": 3}
}
```

## Future Enhancements

1. Add more Three.js extensions (postprocessing, shaders)
2. Support other presets (React, Vue, D3.js)
3. Persistent storage (database) for longer TTL
4. Background TTL cleanup task
5. Rate limiting and size limits
6. Custom CDN URL configuration

## Troubleshooting

### "Preview session not found" (404)

Session may have expired (TTL: 1 hour) or never existed.

**Solution:** Create a new preview session.

### "Preview session expired" (410)

Session TTL exceeded.

**Solution:** Create a new preview session. Consider increasing TTL if needed.

### Dependencies not detected

The detection uses regex pattern matching on class names.

**Check:**
- Is the class name spelled correctly? (`FontLoader` not `fontLoader`)
- Is the code in the HTML? (Not loaded externally)

**Workaround:** Manually add script tags to your HTML before preview.

### Wrong dependency order

Core should always load before extensions. This is handled automatically.

**Verify:** Check `deps_injected` in response - `three-core` should be first.

## Security Considerations

1. **Same-Origin Only:** `X-Frame-Options: SAMEORIGIN` prevents embedding from other domains
2. **TTL:** Sessions expire after 1 hour to prevent storage bloat
3. **No Execution:** Server never executes user code (HTML served as-is)
4. **CDN URLs:** Uses trusted CDN (jsDelivr) for dependencies

## Changelog

### 2026-01-28 - Initial Release

- Added `three-webgl-umd` preset
- Automatic dependency detection (9 extensions supported)
- Smart injection (before `</head>` or `<body>`)
- Session TTL (1 hour)
- Meta endpoint for session info
- Audit logging for all operations
- Comprehensive test suite

## License

MIT License (same as AgentOS)
