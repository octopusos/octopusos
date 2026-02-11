from octopusos.core.chat.tool_dispatch.aws_mcp_dispatch import (
    _build_request_server_config,
    _extract_region,
)
from octopusos.core.mcp.config import MCPServerConfig


def _server_config() -> MCPServerConfig:
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


def test_extract_region_from_region_code() -> None:
    assert _extract_region("列出 ap-southeast-2 的 ec2 实例") == "ap-southeast-2"


def test_extract_region_from_city_alias() -> None:
    assert _extract_region("查询我在悉尼有哪些 EC2 实例") == "ap-southeast-2"


def test_extract_region_from_multiple_nl_aliases() -> None:
    assert _extract_region("show me ec2 in tokyo") == "ap-northeast-1"
    assert _extract_region("列出新加坡 region 的实例") == "ap-southeast-1"
    assert _extract_region("frankfurt ec2 instances") == "eu-central-1"
    assert _extract_region("查美国俄亥俄的 ec2") == "us-east-2"
    assert _extract_region("mumbai ec2") == "ap-south-1"


def test_extract_region_handles_spacing_and_punctuation() -> None:
    assert _extract_region("list ec2 in ap southeast 2") == "ap-southeast-2"
    assert _extract_region("list ec2 in us east 1") == "us-east-1"
    assert _extract_region("查看（Sydney）EC2") == "ap-southeast-2"


def test_build_request_server_config_overrides_region_per_request() -> None:
    base = _server_config()
    request_config, inferred_region = _build_request_server_config(base, "show ec2 instances in sydney")

    assert inferred_region == "ap-southeast-2"
    assert request_config.env.get("AWS_REGION") == "ap-southeast-2"
    assert base.env.get("AWS_REGION") == "us-east-1"
