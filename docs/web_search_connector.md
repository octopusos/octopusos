# Web Search Connector

## Overview

The Web Search Connector provides web search capabilities using various search engines. It supports DuckDuckGo out-of-the-box (free, no API key required), with extensible support for Google and Bing search APIs.

## Features

- **DuckDuckGo Search**: Fully implemented, free, no API key required
- **Multi-Provider Support**: Extensible architecture for Google and Bing APIs
- **Standardized Results**: All providers return uniform format
- **Result Deduplication**: Automatically removes duplicate URLs
- **Comprehensive Error Handling**: Handles API, network, and rate limit errors
- **Async Support**: Non-blocking async/await interface

## Installation

The DuckDuckGo search dependency is included in the main dependencies:

```bash
pip install duckduckgo-search
```

Or install the newer package name:

```bash
pip install ddgs
```

## Usage

### Basic Usage

```python
from agentos.core.communication.connectors.web_search import WebSearchConnector

# Create connector (uses DuckDuckGo by default)
connector = WebSearchConnector({
    "engine": "duckduckgo",
    "max_results": 10,
    "timeout": 30,
    "deduplicate": True,
})

# Perform search
result = await connector.execute("search", {
    "query": "Python programming language",
    "max_results": 5,
    "language": "en",
})

# Access results
print(f"Found {result['total_results']} results")
for item in result['results']:
    print(f"Title: {item['title']}")
    print(f"URL: {item['url']}")
    print(f"Snippet: {item['snippet']}")
```

### Configuration Options

```python
config = {
    # Search engine to use: "duckduckgo", "google", or "bing"
    "engine": "duckduckgo",

    # Maximum number of results to return (default: 10)
    "max_results": 10,

    # Request timeout in seconds (default: 30)
    "timeout": 30,

    # Enable/disable URL deduplication (default: True)
    "deduplicate": True,

    # API key for Google/Bing (not required for DuckDuckGo)
    "api_key": None,
}
```

## Search Parameters

```python
params = {
    # Required: Search query string
    "query": "artificial intelligence",

    # Optional: Maximum results (overrides config)
    "max_results": 5,

    # Optional: Language code (e.g., "en", "zh", "es")
    "language": "en",
}
```

## Response Format

All search providers return standardized results:

```python
{
    "query": "Python programming language",
    "engine": "duckduckgo",
    "total_results": 5,
    "results": [
        {
            "title": "Welcome to Python.org",
            "url": "https://www.python.org/",
            "snippet": "The official home of the Python programming language...",
        },
        # ... more results
    ]
}
```

## Supported Search Engines

### DuckDuckGo (Fully Implemented)

**Status**: ✅ Production Ready

**Features**:
- Free, no API key required
- No rate limiting (reasonable use)
- Privacy-focused
- Good quality results

**Configuration**:
```python
connector = WebSearchConnector({
    "engine": "duckduckgo",
    "max_results": 10,
})
```

### Google Custom Search (Skeleton)

**Status**: ⚠️ Implementation Required

**Requirements**:
1. Sign up for [Google Custom Search API](https://developers.google.com/custom-search)
2. Create a Custom Search Engine at [Google CSE](https://cse.google.com/)
3. Get API key and Search Engine ID

**Configuration**:
```python
connector = WebSearchConnector({
    "engine": "google",
    "api_key": "your_google_api_key",
    "search_engine_id": "your_search_engine_id",
    "max_results": 10,
})
```

### Bing Web Search (Skeleton)

**Status**: ⚠️ Implementation Required

**Requirements**:
1. Sign up for [Bing Search API](https://www.microsoft.com/en-us/bing/apis/bing-web-search-api)
2. Get your subscription key

**Configuration**:
```python
connector = WebSearchConnector({
    "engine": "bing",
    "api_key": "your_bing_subscription_key",
    "max_results": 10,
})
```

## Error Handling

The connector provides specific exception types for different error scenarios:

```python
from agentos.core.communication.connectors.web_search import (
    WebSearchError,
    APIError,
    NetworkError,
    RateLimitError,
)

try:
    result = await connector.execute("search", {"query": "test"})
except RateLimitError as e:
    print(f"Rate limited: {e}")
except NetworkError as e:
    print(f"Network error: {e}")
except APIError as e:
    print(f"API error: {e}")
except WebSearchError as e:
    print(f"General search error: {e}")
```

## Features

### Result Standardization

All search providers return results in a unified format:
- `title`: Result title
- `url`: Result URL
- `snippet`: Result description/snippet

The connector automatically maps provider-specific field names to this standard format.

### URL Deduplication

When enabled (default), the connector:
1. Normalizes URLs (removes trailing slashes, lowercases)
2. Compares URLs by scheme, host, and path
3. Keeps only the first occurrence of each URL

### Validation

The connector validates:
- Query is non-empty string
- Supported search engine
- Required API keys for commercial providers
- URL format in results

## Testing

Run the included test script:

```bash
python test_web_search.py
```

The test script includes:
- Basic search functionality
- Error handling
- Result deduplication
- Multiple queries

## Implementation Notes

### DuckDuckGo Implementation

The DuckDuckGo implementation:
- Uses the `duckduckgo-search` package (or newer `ddgs` package)
- Runs synchronous API calls in thread pool to maintain async interface
- Supports region/language selection
- Includes moderate SafeSearch filter
- Handles rate limiting gracefully

### Adding New Providers

To add a new search provider:

1. Implement `_search_<provider>()` method
2. Handle provider-specific errors
3. Return raw results in provider format
4. Let `_standardize_results()` handle format conversion

Example:
```python
async def _search_custom(
    self, query: str, max_results: int, language: str
) -> List[Dict[str, Any]]:
    """Implement custom search provider."""
    # Your implementation here
    return raw_results
```

## Performance Considerations

- DuckDuckGo searches typically complete in 0.5-2 seconds
- Results are not cached (consider implementing caching if needed)
- Async interface prevents blocking on network I/O
- Thread pool execution for synchronous API clients

## Limitations

### DuckDuckGo

- No official API (uses web scraping)
- May return 0 results for some queries
- Rate limiting on excessive use
- Results may vary by region

### Google & Bing

- Require API keys and billing
- Rate limits apply
- Not yet implemented (skeleton code provided)

## Future Enhancements

Potential improvements:

1. **Result Caching**: Cache search results to reduce API calls
2. **More Providers**: Add support for:
   - Brave Search
   - Ecosia
   - Yahoo Search
3. **Advanced Filtering**: Support date ranges, file types, domains
4. **Result Ranking**: Implement custom ranking/scoring
5. **Pagination**: Support fetching more results
6. **Search Suggestions**: Provide query suggestions

## Troubleshooting

### No Results Returned

DuckDuckGo may return 0 results for some queries due to:
- Query too specific
- Recent content not indexed
- Regional restrictions

**Solution**: Try different query phrasing or use more general terms.

### Package Warnings

If you see warnings about `duckduckgo_search` being renamed to `ddgs`:

```bash
pip uninstall duckduckgo-search
pip install ddgs
```

### Rate Limiting

If you encounter rate limit errors:
- Reduce request frequency
- Implement exponential backoff
- Consider caching results

### Import Errors

If you get import errors:

```bash
pip install duckduckgo-search
# or
pip install ddgs
```

## References

- [DuckDuckGo Search on GitHub](https://github.com/deedy5/duckduckgo_search)
- [Google Custom Search API](https://developers.google.com/custom-search)
- [Bing Web Search API](https://www.microsoft.com/en-us/bing/apis/bing-web-search-api)

## License

This connector is part of AgentOS and is licensed under the MIT License.
