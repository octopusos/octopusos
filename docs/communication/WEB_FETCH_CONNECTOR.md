# Web Fetch Connector - Implementation Documentation

## Overview

The Web Fetch Connector provides secure HTTP/HTTPS content fetching capabilities for AgentOS CommunicationOS. It implements real HTTP client functionality with comprehensive error handling, security controls, and HTML content extraction.

**File Location**: `agentos/core/communication/connectors/web_fetch.py`

## Features

### 1. HTTP Operations
- **Async HTTP Requests**: Uses `httpx` for high-performance async HTTP operations
- **Multiple HTTP Methods**: Supports GET, POST, PUT, DELETE, etc.
- **Custom Headers**: Allows custom request headers
- **Redirect Handling**: Configurable redirect following
- **Timeout Control**: Per-request timeout configuration

### 2. Content Fetching
- **Text Content**: Fetches and decodes HTML, JSON, XML, and other text formats
- **Binary Content**: Supports downloading binary files
- **Size Limits**: Enforces maximum content size limits
- **Streaming Downloads**: Memory-efficient chunked downloads for large files

### 3. HTML Content Extraction
- **Title Extraction**: Extracts page title from `<title>` or OpenGraph tags
- **Description Extraction**: Extracts meta descriptions
- **Main Content Extraction**: Identifies and extracts main content area
- **Boilerplate Removal**: Removes navigation, ads, footers, scripts, etc.
- **Link Extraction**: Extracts all links with text
- **Image Extraction**: Extracts image URLs and alt text
- **Plain Text Conversion**: Converts HTML to clean plain text

### 4. Error Handling
- **Network Errors**: Handles connection failures, DNS errors, etc.
- **Timeout Errors**: Detects and reports timeout errors
- **HTTP Errors**: Handles 4xx and 5xx status codes
- **Size Limit Errors**: Prevents fetching content exceeding max size
- **Invalid URL Errors**: Validates URL format

### 5. Security Integration
- **SSRF Protection**: Integrates with PolicyEngine SSRF checks
- **Domain Filtering**: Supports allowed/blocked domain lists
- **Rate Limiting**: Works with CommunicationService rate limiter
- **Audit Logging**: All operations logged via EvidenceLogger
- **Input Sanitization**: Integrates with InputSanitizer

## Configuration

### Connector Configuration

```python
config = {
    "timeout": 30,                    # Request timeout in seconds
    "max_size": 10 * 1024 * 1024,    # Max content size (10MB)
    "user_agent": "AgentOS/1.0",     # User agent string
    "follow_redirects": True,         # Follow HTTP redirects
}

connector = WebFetchConnector(config=config)
```

### Policy Configuration

Default policy (from PolicyEngine):
```python
{
    "name": "default_web_fetch",
    "enabled": True,
    "allowed_operations": ["fetch", "download"],
    "blocked_domains": ["localhost", "127.0.0.1", "0.0.0.0"],
    "rate_limit_per_minute": 20,
    "max_response_size_mb": 10,
    "timeout_seconds": 60,
    "sanitize_inputs": True,
    "sanitize_outputs": True,
}
```

## Usage

### Basic Usage

```python
from agentos.core.communication.service import CommunicationService
from agentos.core.communication.connectors.web_fetch import WebFetchConnector
from agentos.core.communication.models import ConnectorType

# Initialize service and connector
service = CommunicationService()
connector = WebFetchConnector()
service.register_connector(ConnectorType.WEB_FETCH, connector)

# Fetch a URL
response = await service.execute(
    connector_type=ConnectorType.WEB_FETCH,
    operation="fetch",
    params={
        "url": "https://example.com",
        "extract_content": True,
    }
)

print(f"Status: {response.status}")
print(f"Content: {response.data['content']}")
if response.data.get('extracted'):
    print(f"Title: {response.data['extracted']['title']}")
```

### Fetch with Custom Headers

```python
response = await service.execute(
    connector_type=ConnectorType.WEB_FETCH,
    operation="fetch",
    params={
        "url": "https://api.example.com/data",
        "method": "POST",
        "headers": {
            "Authorization": "Bearer token",
            "Content-Type": "application/json",
        },
        "body": '{"key": "value"}',
    }
)
```

### Download File

```python
response = await service.execute(
    connector_type=ConnectorType.WEB_FETCH,
    operation="download",
    params={
        "url": "https://example.com/file.pdf",
        "destination": "/path/to/save/file.pdf",  # Optional
        "chunk_size": 8192,                        # Optional
    }
)

print(f"Downloaded to: {response.data['destination']}")
print(f"Size: {response.data['size']} bytes")
```

### Direct Connector Usage (without service)

```python
connector = WebFetchConnector()

# Fetch
result = await connector._fetch({
    "url": "https://example.com",
    "extract_content": True,
})

# Download
result = await connector._download({
    "url": "https://example.com/file.zip",
})
```

## API Reference

### `WebFetchConnector`

#### Methods

##### `__init__(config: Optional[Dict[str, Any]] = None)`
Initialize the connector with optional configuration.

##### `async execute(operation: str, params: Dict[str, Any]) -> Any`
Execute a web fetch operation (fetch or download).

##### `async _fetch(params: Dict[str, Any]) -> Dict[str, Any]`
Fetch content from a URL.

**Parameters:**
- `url` (str, required): URL to fetch
- `method` (str, optional): HTTP method (default: "GET")
- `headers` (dict, optional): Custom headers
- `timeout` (int, optional): Request timeout in seconds
- `body` (str, optional): Request body for POST/PUT
- `extract_content` (bool, optional): Extract HTML content (default: True)

**Returns:**
```python
{
    "url": str,              # Original URL
    "final_url": str,        # Final URL after redirects
    "status_code": int,      # HTTP status code
    "content": str,          # Response content
    "headers": dict,         # Response headers
    "content_type": str,     # Content type
    "content_length": int,   # Content length in bytes
    "extracted": {           # Only if extract_content=True and HTML
        "title": str,
        "description": str,
        "content": str,      # HTML content (limited)
        "text": str,         # Plain text (limited)
        "links": list,       # List of links
        "images": list,      # List of images
        "url": str,
    }
}
```

##### `async _download(params: Dict[str, Any]) -> Dict[str, Any]`
Download a file from a URL.

**Parameters:**
- `url` (str, required): URL to download
- `destination` (str, optional): Local file path (uses temp file if not provided)
- `chunk_size` (int, optional): Download chunk size (default: 8192)

**Returns:**
```python
{
    "url": str,              # Original URL
    "final_url": str,        # Final URL after redirects
    "destination": str,      # Local file path
    "size": int,             # Downloaded file size in bytes
    "content_type": str,     # Content type
    "headers": dict,         # Response headers
}
```

##### `get_supported_operations() -> List[str]`
Returns list of supported operations: `["fetch", "download"]`

##### `validate_config() -> bool`
Validates connector configuration.

## HTML Content Extraction

The connector uses BeautifulSoup to extract meaningful content from HTML pages:

### Extraction Process

1. **Title Extraction**
   - Tries `<title>` tag
   - Falls back to OpenGraph `og:title`

2. **Description Extraction**
   - Tries `<meta name="description">`
   - Falls back to OpenGraph `og:description`

3. **Content Cleaning**
   - Removes: scripts, styles, nav, footer, header, aside, iframe
   - Removes elements with ad-related class/ID patterns
   - Removes common boilerplate sections

4. **Main Content Identification**
   - Looks for: `<main>`, `<article>`, `<div class="content">`, `<div id="content">`
   - Falls back to `<body>` if no main content found

5. **Text Extraction**
   - Converts HTML to plain text
   - Removes multiple newlines
   - Strips whitespace

6. **Link & Image Extraction**
   - Extracts all links with href and text
   - Extracts all images with src and alt
   - Filters fragment-only links (#)

### Limits

To prevent excessive memory usage:
- HTML content: Limited to 5,000 characters
- Plain text: Limited to 10,000 characters
- Links: Limited to 50 links
- Images: Limited to 20 images

## Error Handling

### Exception Types

| Exception Type | Description | Response Status |
|---------------|-------------|-----------------|
| `ValueError` | Invalid URL or missing required params | `DENIED` |
| `httpx.TimeoutException` | Request timeout | `FAILED` |
| `httpx.HTTPStatusError` | HTTP error status (4xx, 5xx) | `FAILED` |
| `httpx.RequestError` | Network error (DNS, connection, etc.) | `FAILED` |
| `Exception` (size limit) | Content exceeds max size | `FAILED` |

### Error Response Format

```python
{
    "status": RequestStatus.FAILED,
    "error": "Error message",
    "request_id": "comm-xxx",
}
```

## Security Features

### SSRF Protection

The connector integrates with PolicyEngine SSRF checks:
- Blocks localhost access (localhost, 127.0.0.1, ::1)
- Blocks private IP ranges (10.x, 172.16-31.x, 192.168.x)
- Blocks link-local addresses
- Validates URL scheme (only http, https, ftp, ftps)

### Domain Filtering

Supports:
- **Blocked Domains**: Deny list of domains
- **Allowed Domains**: Allow list (if set, only these are allowed)

### Rate Limiting

Enforced by CommunicationService:
- Default: 20 requests per minute
- Configurable per policy
- Returns `RATE_LIMITED` status when exceeded

### Audit Logging

All operations logged with:
- Request ID
- Evidence ID (audit trail)
- Operation parameters
- Response data
- Timestamp
- Context (task_id, session_id, etc.)

## Testing

### Unit Tests

Located in: `tests/test_web_fetch_connector.py`

Run tests:
```bash
# All tests
pytest tests/test_web_fetch_connector.py -v

# Network tests only
pytest tests/test_web_fetch_connector.py -v -m network

# Non-network tests
pytest tests/test_web_fetch_connector.py -v -k "not network"
```

### Test Coverage

- Basic URL fetching
- Custom headers and methods
- File downloads
- HTML content extraction
- Error handling (invalid URL, timeout, size limit)
- Configuration validation
- Integration with CommunicationService
- Security policy enforcement

### Demo

Run comprehensive demo:
```bash
python examples/communication_web_fetch_demo.py
```

Demos include:
1. Basic web fetch
2. File download
3. Error handling & security policies
4. Custom headers and methods
5. Rate limiting
6. HTML content extraction

## Dependencies

Added to `pyproject.toml`:
- `httpx>=0.27.0` (already present)
- `beautifulsoup4>=4.12.0` (added)
- `lxml>=5.0.0` (added)

Install dependencies:
```bash
pip install beautifulsoup4 lxml
```

## Performance Considerations

### Memory Efficiency
- Streaming downloads for large files
- Content size limits prevent memory exhaustion
- Chunked reading/writing

### Connection Management
- Async HTTP client with connection pooling
- Configurable connection limits
- Automatic connection cleanup

### Timeout Management
- Configurable per-request timeouts
- Prevents hanging requests
- Default: 30 seconds

## Future Enhancements

Potential improvements:
1. **Caching**: Cache responses for repeated URLs
2. **Compression**: Support brotli compression
3. **Authentication**: Built-in OAuth, API key support
4. **Retry Logic**: Automatic retry with exponential backoff
5. **Content Type Handlers**: Specialized handlers for JSON, XML, RSS
6. **Robots.txt**: Respect robots.txt rules
7. **User Agent Rotation**: Randomize user agents
8. **Proxy Support**: HTTP/SOCKS proxy configuration
9. **Cookie Handling**: Persistent cookie jar
10. **Advanced Extraction**: Use trafilatura or readability for better extraction

## Integration with Other Components

### CommunicationService
- Registers as `ConnectorType.WEB_FETCH`
- Enforces policies via PolicyEngine
- Logs operations via EvidenceLogger
- Enforces rate limits via RateLimiter
- Sanitizes inputs/outputs via Sanitizers

### PolicyEngine
- Domain filtering
- SSRF protection
- Operation validation
- Risk assessment

### EvidenceLogger
- Audit trail for all operations
- Evidence IDs for traceability
- Compliance and debugging support

## Example Use Cases

1. **Web Scraping**: Extract content from web pages for analysis
2. **API Integration**: Fetch data from REST APIs
3. **Document Download**: Download PDFs, images, files
4. **Content Monitoring**: Monitor web pages for changes
5. **Data Collection**: Collect data from multiple sources
6. **Research**: Fetch academic papers, articles, etc.
7. **Testing**: Verify web service availability
8. **Integration Testing**: Test API endpoints

## Acceptance Criteria

All requirements met:
- ✅ Uses httpx for async HTTP requests
- ✅ Implements `_fetch()` method with GET/POST/etc. support
- ✅ Supports custom headers
- ✅ Supports timeout control
- ✅ Supports max content size limits
- ✅ Returns status_code, content, headers
- ✅ Implements `_download()` method with streaming
- ✅ Downloads to file or temp file
- ✅ Integrates HTML content extraction (BeautifulSoup)
- ✅ Extracts title, description, main content
- ✅ Removes boilerplate (navigation, ads, etc.)
- ✅ Comprehensive error handling
- ✅ Network, timeout, size, HTTP error handling
- ✅ Dependencies added to pyproject.toml
- ✅ Can fetch HTTPS URLs successfully
- ✅ Can extract HTML content
- ✅ Integrates with PolicyEngine (SSRF checks in service layer)

## Conclusion

The Web Fetch Connector provides a robust, secure, and feature-rich implementation for fetching web content. It integrates seamlessly with the CommunicationOS security framework while providing powerful HTML extraction capabilities.

For questions or issues, please refer to the test suite and demo for comprehensive usage examples.
