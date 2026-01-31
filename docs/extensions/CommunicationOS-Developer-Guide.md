# CommunicationOS Developer Guide

**Version**: 1.0.0
**Audience**: Extension developers, contributors
**Prerequisites**: Python 3.11+, familiarity with async/await

---

## Table of Contents

1. [Overview](#overview)
2. [Creating a Custom Connector](#creating-a-custom-connector)
3. [Connector Interface Reference](#connector-interface-reference)
4. [Registering Connectors](#registering-connectors)
5. [Testing Your Connector](#testing-your-connector)
6. [Best Practices](#best-practices)
7. [Examples](#examples)
8. [Troubleshooting](#troubleshooting)

---

## Overview

CommunicationOS is designed to be **extensible**. You can create custom connectors to integrate with any external service:

- REST APIs
- GraphQL endpoints
- Message queues (RabbitMQ, Kafka)
- Cloud storage (S3, GCS, Azure Blob)
- Monitoring services (Datadog, New Relic)
- Custom enterprise systems

This guide will show you how to:
1. Implement a connector that follows the `BaseConnector` interface
2. Register your connector with CommunicationService
3. Test and deploy your connector
4. Follow security and performance best practices

---

## Creating a Custom Connector

### Step 1: Create Connector File

Create a new file in `agentos/core/communication/connectors/`:

```bash
touch agentos/core/communication/connectors/my_custom_connector.py
```

### Step 2: Import Base Classes

```python
"""My Custom Connector - Integration with CustomService API.

This connector provides secure access to CustomService operations,
including data retrieval, updates, and notifications.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from agentos.core.communication.connectors.base import BaseConnector

logger = logging.getLogger(__name__)
```

### Step 3: Implement Connector Class

```python
class MyCustomConnector(BaseConnector):
    """Connector for CustomService API integration.

    This connector supports the following operations:
    - get_data: Retrieve data from CustomService
    - send_notification: Send notifications via CustomService
    - update_resource: Update a resource in CustomService

    Configuration:
        api_key: API key for authentication
        base_url: Base URL for CustomService API (default: https://api.customservice.com)
        timeout: Request timeout in seconds (default: 30)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the custom connector.

        Args:
            config: Configuration dictionary with:
                - api_key: Required API key
                - base_url: Optional base URL
                - timeout: Optional timeout in seconds
        """
        super().__init__(config)
        self.api_key = config.get("api_key") if config else None
        self.base_url = config.get("base_url", "https://api.customservice.com")
        self.timeout = config.get("timeout", 30)

    async def execute(self, operation: str, params: Dict[str, Any]) -> Any:
        """Execute a CustomService operation.

        Args:
            operation: Operation name (get_data, send_notification, update_resource)
            params: Operation-specific parameters

        Returns:
            Operation result

        Raises:
            NotImplementedError: If operation is not supported
            ValueError: If required parameters are missing
            Exception: If operation fails
        """
        if not self.enabled:
            raise Exception(f"{self.name} is disabled")

        # Dispatch to operation handler
        if operation == "get_data":
            return await self._get_data(params)
        elif operation == "send_notification":
            return await self._send_notification(params)
        elif operation == "update_resource":
            return await self._update_resource(params)
        else:
            raise NotImplementedError(f"Operation '{operation}' not supported")

    async def _get_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve data from CustomService.

        Args:
            params: Must contain:
                - resource_id: ID of resource to retrieve

        Returns:
            Dict with resource data
        """
        resource_id = params.get("resource_id")
        if not resource_id:
            raise ValueError("'resource_id' parameter is required")

        # Make API call (example using aiohttp)
        import aiohttp

        url = f"{self.base_url}/api/v1/resources/{resource_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                response.raise_for_status()
                data = await response.json()

        logger.info(f"Retrieved data for resource {resource_id}")
        return {
            "resource_id": resource_id,
            "data": data,
            "status": "success",
        }

    async def _send_notification(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send notification via CustomService.

        Args:
            params: Must contain:
                - message: Notification message
                - recipient: Recipient identifier

        Returns:
            Dict with notification result
        """
        message = params.get("message")
        recipient = params.get("recipient")

        if not message or not recipient:
            raise ValueError("'message' and 'recipient' parameters are required")

        # Implement notification logic here
        logger.info(f"Sent notification to {recipient}")

        return {
            "status": "sent",
            "recipient": recipient,
            "message_id": "notif-12345",
        }

    async def _update_resource(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update a resource in CustomService.

        Args:
            params: Must contain:
                - resource_id: ID of resource to update
                - data: Update data

        Returns:
            Dict with update result
        """
        resource_id = params.get("resource_id")
        data = params.get("data")

        if not resource_id or not data:
            raise ValueError("'resource_id' and 'data' parameters are required")

        # Implement update logic here
        logger.info(f"Updated resource {resource_id}")

        return {
            "resource_id": resource_id,
            "status": "updated",
        }

    def get_supported_operations(self) -> List[str]:
        """Get list of supported operations.

        Returns:
            List of operation names
        """
        return ["get_data", "send_notification", "update_resource"]

    def validate_config(self) -> bool:
        """Validate connector configuration.

        Returns:
            True if configuration is valid, False otherwise
        """
        if not self.api_key:
            logger.error("API key is required but not configured")
            return False

        if not self.base_url:
            logger.error("Base URL is required but not configured")
            return False

        return True

    async def health_check(self) -> bool:
        """Perform health check.

        Returns:
            True if service is reachable and healthy, False otherwise
        """
        if not self.enabled:
            return False

        if not self.validate_config():
            return False

        try:
            # Ping the service
            import aiohttp

            url = f"{self.base_url}/api/v1/health"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False
```

---

## Connector Interface Reference

### Required Methods

#### 1. `execute(operation: str, params: Dict[str, Any]) -> Any`

**Purpose**: Execute a connector operation.

**Parameters**:
- `operation` (str): Name of operation to perform
- `params` (Dict): Operation-specific parameters

**Returns**: Operation result (any type, usually Dict)

**Raises**:
- `NotImplementedError`: Operation not supported
- `ValueError`: Invalid parameters
- `Exception`: Operation failed

**Example**:
```python
async def execute(self, operation: str, params: Dict[str, Any]) -> Any:
    if operation == "my_operation":
        return await self._my_operation(params)
    else:
        raise NotImplementedError(f"Operation '{operation}' not supported")
```

#### 2. `get_supported_operations() -> List[str]`

**Purpose**: Return list of operations this connector supports.

**Returns**: List of operation names

**Example**:
```python
def get_supported_operations(self) -> List[str]:
    return ["get_data", "send_notification", "update_resource"]
```

### Optional Methods (with defaults)

#### 3. `validate_config() -> bool`

**Purpose**: Validate connector configuration.

**Returns**: True if valid, False otherwise

**Example**:
```python
def validate_config(self) -> bool:
    if not self.config.get("api_key"):
        logger.error("Missing required config: api_key")
        return False
    return True
```

#### 4. `health_check() -> bool`

**Purpose**: Check if external service is reachable.

**Returns**: True if healthy, False otherwise

**Example**:
```python
async def health_check(self) -> bool:
    try:
        # Ping service endpoint
        response = await self._ping_service()
        return response.status == 200
    except Exception:
        return False
```

#### 5. `get_status() -> Dict[str, Any]`

**Purpose**: Get connector status information.

**Returns**: Status dictionary

**Default implementation** (from BaseConnector):
```python
def get_status(self) -> Dict[str, Any]:
    return {
        "name": self.name,
        "enabled": self.enabled,
        "supported_operations": self.get_supported_operations(),
        "config_valid": self.validate_config(),
    }
```

---

## Registering Connectors

### 1. Add ConnectorType Enum

Edit `agentos/core/communication/models.py`:

```python
class ConnectorType(str, Enum):
    """Types of external communication connectors."""

    WEB_SEARCH = "web_search"
    WEB_FETCH = "web_fetch"
    RSS = "rss"
    EMAIL_SMTP = "email_smtp"
    SLACK = "slack"
    MY_CUSTOM = "my_custom"  # Add your type
    CUSTOM = "custom"
```

### 2. Create Default Policy

Edit `agentos/core/communication/policy.py` in `_load_default_policies()`:

```python
def _load_default_policies(self) -> None:
    # ... existing policies ...

    # Default policy for your custom connector
    self.policies[ConnectorType.MY_CUSTOM] = CommunicationPolicy(
        name="default_my_custom",
        connector_type=ConnectorType.MY_CUSTOM,
        allowed_operations=["get_data", "send_notification", "update_resource"],
        blocked_domains=["localhost", "127.0.0.1"],
        require_approval=False,  # Set to True for sensitive operations
        rate_limit_per_minute=20,
        max_response_size_mb=5,
        timeout_seconds=30,
        sanitize_inputs=True,
        sanitize_outputs=True,
    )
```

### 3. Register with Service

Register your connector when initializing CommunicationService:

**Option A: In WebUI API** (`agentos/webui/api/communication.py`):

```python
from agentos.core.communication.connectors.my_custom_connector import MyCustomConnector

def get_service() -> CommunicationService:
    global _service
    if _service is None:
        # ... existing initialization ...

        # Register your connector
        _service.register_connector(
            ConnectorType.MY_CUSTOM,
            MyCustomConnector(config={
                "api_key": os.getenv("MY_CUSTOM_API_KEY"),
                "base_url": os.getenv("MY_CUSTOM_BASE_URL"),
            })
        )

    return _service
```

**Option B: Programmatically**:

```python
from agentos.core.communication import CommunicationService, ConnectorType
from agentos.core.communication.connectors.my_custom_connector import MyCustomConnector

service = CommunicationService()

# Register connector
my_connector = MyCustomConnector(config={
    "api_key": "your-api-key",
    "base_url": "https://api.customservice.com",
})
service.register_connector(ConnectorType.MY_CUSTOM, my_connector)

# Use connector
response = await service.execute(
    connector_type=ConnectorType.MY_CUSTOM,
    operation="get_data",
    params={"resource_id": "123"},
)
```

---

## Testing Your Connector

### 1. Unit Tests

Create test file `agentos/core/communication/tests/test_my_custom_connector.py`:

```python
"""Unit tests for MyCustomConnector."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agentos.core.communication.connectors.my_custom_connector import MyCustomConnector


@pytest.fixture
def connector():
    """Create connector instance with test config."""
    return MyCustomConnector(config={
        "api_key": "test-api-key",
        "base_url": "https://test.api.com",
    })


@pytest.mark.asyncio
async def test_get_data_success(connector):
    """Test successful data retrieval."""
    # Mock HTTP response
    with patch("aiohttp.ClientSession") as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"id": "123", "data": "test"})
        mock_response.raise_for_status = MagicMock()

        mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response

        # Execute operation
        result = await connector.execute("get_data", {"resource_id": "123"})

        # Verify result
        assert result["status"] == "success"
        assert result["resource_id"] == "123"
        assert "data" in result


@pytest.mark.asyncio
async def test_get_data_missing_param(connector):
    """Test error when required parameter is missing."""
    with pytest.raises(ValueError, match="'resource_id' parameter is required"):
        await connector.execute("get_data", {})


@pytest.mark.asyncio
async def test_unsupported_operation(connector):
    """Test error for unsupported operation."""
    with pytest.raises(NotImplementedError, match="not supported"):
        await connector.execute("unsupported_op", {})


def test_get_supported_operations(connector):
    """Test listing supported operations."""
    ops = connector.get_supported_operations()
    assert "get_data" in ops
    assert "send_notification" in ops
    assert "update_resource" in ops


def test_validate_config_success(connector):
    """Test config validation with valid config."""
    assert connector.validate_config() is True


def test_validate_config_missing_api_key():
    """Test config validation with missing API key."""
    connector = MyCustomConnector(config={})
    assert connector.validate_config() is False
```

### 2. Integration Tests

Test with CommunicationService:

```python
"""Integration tests for MyCustomConnector with CommunicationService."""

import pytest

from agentos.core.communication import CommunicationService, ConnectorType
from agentos.core.communication.policy import PolicyEngine
from agentos.core.communication.models import RequestStatus
from agentos.core.communication.connectors.my_custom_connector import MyCustomConnector


@pytest.mark.asyncio
async def test_execute_through_service():
    """Test executing connector through CommunicationService."""
    # Setup service
    service = CommunicationService()

    # Register connector
    connector = MyCustomConnector(config={
        "api_key": "test-api-key",
        "base_url": "https://test.api.com",
    })
    service.register_connector(ConnectorType.MY_CUSTOM, connector)

    # Execute operation
    response = await service.execute(
        connector_type=ConnectorType.MY_CUSTOM,
        operation="get_data",
        params={"resource_id": "123"},
    )

    # Verify response
    assert response.status == RequestStatus.SUCCESS
    assert response.evidence_id is not None  # Audit trail generated
```

### 3. Run Tests

```bash
# Run specific test file
pytest agentos/core/communication/tests/test_my_custom_connector.py -v

# Run all communication tests
pytest agentos/core/communication/tests/ -v

# Run with coverage
pytest agentos/core/communication/tests/ --cov=agentos.core.communication
```

---

## Best Practices

### 1. Error Handling

**DO**:
```python
async def execute(self, operation: str, params: Dict[str, Any]) -> Any:
    try:
        result = await self._make_api_call(params)
        return result
    except aiohttp.ClientError as e:
        logger.error(f"API call failed: {str(e)}")
        raise Exception(f"CustomService API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise
```

**DON'T**:
```python
async def execute(self, operation: str, params: Dict[str, Any]) -> Any:
    # Don't swallow exceptions silently
    try:
        return await self._make_api_call(params)
    except:
        return {"status": "error"}  # ❌ Loss of error context
```

### 2. Logging

**DO**:
```python
logger.info(f"Executing {operation} with params: {self._sanitize_params(params)}")
logger.debug(f"API response: {response[:100]}")  # Truncate sensitive data
logger.error(f"Operation failed: {str(e)}", exc_info=True)
```

**DON'T**:
```python
logger.info(f"API key: {self.api_key}")  # ❌ Leaks credentials
print(response)  # ❌ Use logger instead
```

### 3. Parameter Validation

**DO**:
```python
def _validate_params(self, params: Dict[str, Any], required: List[str]) -> None:
    """Validate required parameters are present."""
    missing = [p for p in required if p not in params]
    if missing:
        raise ValueError(f"Missing required parameters: {', '.join(missing)}")
```

**DON'T**:
```python
# Don't assume parameters exist
resource_id = params["resource_id"]  # ❌ KeyError if missing
# Use: params.get("resource_id") or validate first
```

### 4. Timeouts

**DO**:
```python
async with aiohttp.ClientSession() as session:
    async with session.get(
        url,
        timeout=aiohttp.ClientTimeout(total=self.timeout)  # ✅ Configurable timeout
    ) as response:
        return await response.json()
```

**DON'T**:
```python
async with session.get(url) as response:  # ❌ No timeout = hang forever
    return await response.json()
```

### 5. Async Best Practices

**DO**:
```python
async def execute(self, operation: str, params: Dict[str, Any]) -> Any:
    # Use async/await consistently
    result = await self._make_api_call(params)
    return result
```

**DON'T**:
```python
def execute(self, operation: str, params: Dict[str, Any]) -> Any:
    # ❌ Blocking call in async function
    import requests
    response = requests.get(url)
    return response.json()
```

### 6. Configuration Management

**DO**:
```python
def __init__(self, config: Optional[Dict[str, Any]] = None):
    super().__init__(config)
    # Support env vars as fallback
    self.api_key = config.get("api_key") or os.getenv("MY_CUSTOM_API_KEY")
    self.base_url = config.get("base_url", "https://default.api.com")
```

**DON'T**:
```python
def __init__(self, config: Optional[Dict[str, Any]] = None):
    # ❌ Hardcoded credentials
    self.api_key = "my-secret-key-123"
```

---

## Examples

### Example 1: Simple HTTP Connector

```python
"""GitHub API Connector - minimal example."""

import aiohttp
from agentos.core.communication.connectors.base import BaseConnector


class GitHubConnector(BaseConnector):
    """Connector for GitHub API."""

    async def execute(self, operation: str, params: Dict[str, Any]) -> Any:
        if operation == "get_repo":
            owner = params.get("owner")
            repo = params.get("repo")

            url = f"https://api.github.com/repos/{owner}/{repo}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    return await response.json()

        raise NotImplementedError(f"Operation '{operation}' not supported")

    def get_supported_operations(self) -> List[str]:
        return ["get_repo"]
```

### Example 2: Connector with Authentication

```python
"""Authenticated API Connector - shows auth handling."""

class AuthenticatedConnector(BaseConnector):
    """Connector with Bearer token authentication."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api_key = config.get("api_key")

    async def execute(self, operation: str, params: Dict[str, Any]) -> Any:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            # All requests include auth headers
            async with session.get(url) as response:
                return await response.json()

    def validate_config(self) -> bool:
        return bool(self.api_key)
```

### Example 3: Connector with Retry Logic

```python
"""Connector with retry logic - shows resilience."""

import asyncio
from typing import Any, Dict

class ResilientConnector(BaseConnector):
    """Connector with automatic retry on failure."""

    async def execute(self, operation: str, params: Dict[str, Any]) -> Any:
        max_retries = 3
        retry_delay = 1  # seconds

        for attempt in range(max_retries):
            try:
                return await self._execute_with_retry(operation, params)
            except aiohttp.ClientError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1} failed, retrying...")
                    await asyncio.sleep(retry_delay * (attempt + 1))
                else:
                    raise Exception(f"Failed after {max_retries} attempts: {str(e)}")

    async def _execute_with_retry(self, operation: str, params: Dict[str, Any]) -> Any:
        # Actual implementation
        pass
```

---

## Troubleshooting

### Problem: Connector not found

**Error**: `No connector registered for my_custom`

**Solution**:
1. Check ConnectorType enum includes your type
2. Verify you called `service.register_connector()`
3. Check spelling of connector type

### Problem: Config validation fails

**Error**: `API key is required but not configured`

**Solution**:
1. Pass config when creating connector
2. Set environment variables
3. Check `validate_config()` implementation

### Problem: Operations fail silently

**Error**: No error, but nothing happens

**Solution**:
1. Check logs for exceptions
2. Verify operation name matches `get_supported_operations()`
3. Ensure `execute()` doesn't swallow exceptions

### Problem: Rate limiting too aggressive

**Error**: `429 Too Many Requests`

**Solution**:
1. Increase rate limit in policy configuration
2. Implement backoff/retry logic
3. Use batch operations when possible

### Problem: SSRF protection blocks legitimate URLs

**Error**: `SSRF protection: Domain blocked`

**Solution**:
1. Add domain to `allowed_domains` in policy
2. Remove from `blocked_domains` if mistakenly added
3. Use fully qualified domain names (not IPs)

---

## Next Steps

- **Architecture**: See [CommunicationOS Architecture](../communication/CommunicationOS-Architecture.md)
- **User Manual**: See [User Manual](../user/CommunicationOS-User-Manual.md)
- **Security**: See [Security Guide](../security/CommunicationOS-Security-Guide.md)
- **API Reference**: See [Communication API](../communication_api.md)

---

## Support

- Issues: GitHub Issues
- Discussions: GitHub Discussions
- Documentation: `/docs/communication/`
