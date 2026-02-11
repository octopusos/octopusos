from octopusos.core.chat.tool_dispatch import aws_mcp_dispatch
from octopusos.core.mcp.config import MCPServerConfig


class _FakeManager:
    def __init__(self, servers):
        self._servers = servers

    def get_enabled_servers(self):
        return self._servers


def _aws_server() -> MCPServerConfig:
    return MCPServerConfig(
        id="mcp_aws_default",
        enabled=True,
        transport="stdio",
        command=["aws-mcp"],
        env={
            "OCTOPUSOS_MCP_PACKAGE_ID": "aws.mcp",
            "AWS_PROFILE": "default",
            "AWS_REGION": "us-east-1",
        },
    )


def test_requires_region_before_any_aws_operation(monkeypatch) -> None:
    monkeypatch.setattr(aws_mcp_dispatch, "MCPConfigManager", lambda: _FakeManager([_aws_server()]))

    called = {"value": False}

    def _never_call(_):
        called["value"] = True
        return {"ok": True}

    monkeypatch.setattr(aws_mcp_dispatch, "_run_async", _never_call)

    result = aws_mcp_dispatch.try_handle_aws_via_mcp("列出我的 EC2 实例")
    assert result is not None
    assert result.get("handled") is True
    assert result.get("blocked") is True
    assert result.get("needs_region") is True
    assert called["value"] is False
