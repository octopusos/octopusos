# PR-0201-2026-4: Enable/Disable API + Admin Token Guard - 实施状态报告

**日期**: 2026-02-01
**状态**: ⚠️ **阻塞中 - 等待依赖完成**
**依赖**: PR-0201-2026-1（Manifest + Registry）必须先完成

---

## 执行摘要

PR-0201-2026-4 旨在实现 Skill 启用/禁用的 Server API 和 CLI 命令，以及 Admin Token 守卫机制。经过环境检查，发现：

### 关键发现

1. ✅ **Admin Token 机制已存在且完善**
   - `/Users/pangge/PycharmProjects/AgentOS/agentos/core/capabilities/admin_token.py`
   - `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/auth/simple_token.py`
   - `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/static/js/components/AdminTokenGate.js`

2. ⚠️ **依赖 PR-0201-2026-1 尚未完成**
   - Skills 目录不存在：`agentos/skills/`
   - Registry 实现不存在：`agentos/skills/registry.py`
   - Manifest 实现不存在：`agentos/skills/manifest.py`
   - Importer 实现不存在：`agentos/skills/importer/`

3. ℹ️ **现有 skills.py 是占位符**
   - `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/api/skills.py` 存在
   - 但只包含 FastAPI 占位代码，不依赖 Registry

---

## 依赖分析

### PR-0201-2026-1 必须提供的组件

```
agentos/skills/
├── __init__.py
├── manifest.py          # Skill 元数据模型
├── registry.py          # SkillRegistry 类
└── importer/
    ├── __init__.py
    ├── local_importer.py    # LocalImporter
    └── github_importer.py   # GitHubImporter
```

**关键 API 需求**：
```python
# SkillRegistry 必须提供的接口
class SkillRegistry:
    def list_skills(self, status: Optional[str] = None) -> List[Dict]: ...
    def get_skill(self, skill_id: str) -> Optional[Dict]: ...
    def set_status(self, skill_id: str, status: str): ...

# LocalImporter 必须提供的接口
class LocalImporter:
    def __init__(self, registry: SkillRegistry): ...
    def import_from_path(self, path: str) -> str: ...

# GitHubImporter 必须提供的接口
class GitHubImporter:
    def __init__(self, registry: SkillRegistry): ...
    def import_from_github(self, owner: str, repo: str, ref: Optional[str], subdir: Optional[str]) -> str: ...
```

---

## 现有 Admin Token 机制分析

### 1. Backend Token Manager

**文件**: `/Users/pangge/PycharmProjects/AgentOS/agentos/core/capabilities/admin_token.py`

**功能**：
- 环境变量验证：`AGENTOS_ADMIN_TOKEN`
- 常数时间字符串比较（防御时序攻击）
- 单例模式：`get_admin_token_manager()`
- 便捷验证函数：`validate_admin_token(token)`

**使用示例**：
```python
from agentos.core.capabilities.admin_token import validate_admin_token

if not validate_admin_token(token):
    return {"error": "Unauthorized"}, 403
```

### 2. FastAPI Token Guard

**文件**: `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/auth/simple_token.py`

**功能**：
- FastAPI 依赖注入：`require_admin()`
- Bearer Token 提取：`extract_bearer_token(request)`
- 开发模式支持（token 未配置时允许访问）

**使用示例**：
```python
from fastapi import Depends
from agentos.webui.auth.simple_token import require_admin

@router.post("/skills/import", dependencies=[Depends(require_admin)])
async def import_skill():
    ...
```

### 3. Frontend Token Gate

**文件**: `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/static/js/components/AdminTokenGate.js`

**功能**：
- 会话存储管理
- 用户交互式 Token 提示对话框
- 自动注入 `X-Admin-Token` 请求头
- Token 状态 UI 组件

**使用示例**：
```javascript
// 执行受保护操作
await window.adminTokenGate.executeProtected(
    async (token) => {
        const response = await fetch('/api/skills/import', {
            method: 'POST',
            headers: {
                'X-Admin-Token': token,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        return response.json();
    },
    { requireToken: true }
);
```

---

## 实施计划（待 PR-1 完成后）

### Phase 1: API 路由实现

**文件**: `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/api/skills.py`（替换现有占位符）

**端点设计**：
```python
from fastapi import APIRouter, HTTPException, Depends
from agentos.webui.auth.simple_token import require_admin
from agentos.skills.registry import SkillRegistry
from agentos.skills.importer.local_importer import LocalImporter
from agentos.skills.importer.github_importer import GitHubImporter

router = APIRouter()

# 公开端点（无需 Token）
@router.get("")
async def list_skills(status: Optional[str] = None):
    """列出所有 skills（支持状态过滤）"""
    registry = SkillRegistry()
    skills = registry.list_skills(status=status if status != 'all' else None)
    return {"ok": True, "data": skills}

@router.get("/{skill_id}")
async def get_skill(skill_id: str):
    """获取 skill 详情（包含 manifest）"""
    registry = SkillRegistry()
    skill = registry.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"ok": True, "data": skill}

# 受保护端点（需要 Admin Token）
@router.post("/import", dependencies=[Depends(require_admin)])
async def import_skill(data: ImportRequest):
    """导入 skill（需要 Admin Token）"""
    registry = SkillRegistry()

    if data.type == 'local':
        if not data.path:
            raise HTTPException(status_code=400, detail="Missing path")
        importer = LocalImporter(registry)
        try:
            skill_id = importer.import_from_path(data.path)
            return {"ok": True, "data": {"skill_id": skill_id, "status": "imported_disabled"}}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    elif data.type == 'github':
        if not data.owner or not data.repo:
            raise HTTPException(status_code=400, detail="Missing owner or repo")
        importer = GitHubImporter(registry)
        try:
            skill_id = importer.import_from_github(data.owner, data.repo, data.ref, data.subdir)
            return {"ok": True, "data": {"skill_id": skill_id, "status": "imported_disabled"}}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        raise HTTPException(status_code=400, detail="Invalid type")

@router.post("/{skill_id}/enable", dependencies=[Depends(require_admin)])
async def enable_skill(skill_id: str):
    """启用 skill（需要 Admin Token）"""
    registry = SkillRegistry()
    skill = registry.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    registry.set_status(skill_id, 'enabled')
    return {"ok": True, "data": {"skill_id": skill_id, "status": "enabled"}}

@router.post("/{skill_id}/disable", dependencies=[Depends(require_admin)])
async def disable_skill(skill_id: str):
    """禁用 skill（需要 Admin Token）"""
    registry = SkillRegistry()
    skill = registry.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    registry.set_status(skill_id, 'disabled')
    return {"ok": True, "data": {"skill_id": skill_id, "status": "disabled"}}
```

### Phase 2: CLI 命令扩展

**文件**: `/Users/pangge/PycharmProjects/AgentOS/agentos/cli/commands/skill.py`（新建或扩展）

**命令设计**：
```python
import click
from agentos.skills.registry import SkillRegistry

@click.group()
def skill():
    """Skill management commands"""
    pass

@skill.command()
@click.option('--status', type=click.Choice(['enabled', 'disabled', 'imported_disabled', 'all']),
              default='all', help='Filter by status')
def list(status):
    """List all skills"""
    registry = SkillRegistry()
    skills = registry.list_skills(status=None if status == 'all' else status)

    if not skills:
        click.echo("No skills found")
        return

    for s in skills:
        status_icon = "✓" if s['status'] == 'enabled' else "○"
        click.echo(f"{status_icon} {s['id']} - {s.get('description', 'No description')}")

@skill.command()
@click.argument('skill_id')
def info(skill_id):
    """Get skill details"""
    registry = SkillRegistry()
    skill = registry.get_skill(skill_id)
    if not skill:
        click.echo(f"❌ Skill not found: {skill_id}", err=True)
        return

    click.echo(f"Skill: {skill['id']}")
    click.echo(f"Status: {skill['status']}")
    click.echo(f"Description: {skill.get('description', 'N/A')}")

@skill.command()
@click.argument('skill_id')
@click.option('--token', envvar='AGENTOS_ADMIN_TOKEN', required=True,
              help='Admin token (or set AGENTOS_ADMIN_TOKEN env var)')
def enable(skill_id, token):
    """Enable a skill (requires admin token)"""
    from agentos.core.capabilities.admin_token import validate_admin_token

    if not validate_admin_token(token):
        click.echo("❌ Invalid admin token", err=True)
        return

    registry = SkillRegistry()
    skill = registry.get_skill(skill_id)
    if not skill:
        click.echo(f"❌ Skill not found: {skill_id}", err=True)
        return

    registry.set_status(skill_id, 'enabled')
    click.echo(f"✅ Skill enabled: {skill_id}")

@skill.command()
@click.argument('skill_id')
@click.option('--token', envvar='AGENTOS_ADMIN_TOKEN', required=True,
              help='Admin token (or set AGENTOS_ADMIN_TOKEN env var)')
def disable(skill_id, token):
    """Disable a skill (requires admin token)"""
    from agentos.core.capabilities.admin_token import validate_admin_token

    if not validate_admin_token(token):
        click.echo("❌ Invalid admin token", err=True)
        return

    registry = SkillRegistry()
    skill = registry.get_skill(skill_id)
    if not skill:
        click.echo(f"❌ Skill not found: {skill_id}", err=True)
        return

    registry.set_status(skill_id, 'disabled')
    click.echo(f"✅ Skill disabled: {skill_id}")
```

### Phase 3: 测试实现

#### 单元测试

**文件**: `/Users/pangge/PycharmProjects/AgentOS/tests/unit/webui/api/test_skills_api.py`

```python
import pytest
from fastapi.testclient import TestClient
from agentos.webui.app import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

@pytest.fixture
def admin_token():
    return "test-admin-token"

@pytest.fixture(autouse=True)
def set_admin_token(monkeypatch, admin_token):
    monkeypatch.setenv("AGENTOS_ADMIN_TOKEN", admin_token)

class TestSkillsAPI:
    """Skill API 单元测试"""

    def test_list_skills_no_auth_required(self, client):
        """测试：列出 skills 不需要认证"""
        response = client.get("/api/skills")
        assert response.status_code == 200
        assert "ok" in response.json()

    def test_get_skill_no_auth_required(self, client):
        """测试：获取 skill 详情不需要认证"""
        # 假设有 test.skill 存在
        response = client.get("/api/skills/test.skill")
        # 404 也是成功（说明不需要认证）
        assert response.status_code in [200, 404]

    def test_enable_without_token_returns_401(self, client):
        """测试：启用 skill 没有 token 返回 401"""
        response = client.post("/api/skills/test.skill/enable")
        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]

    def test_enable_with_invalid_token_returns_401(self, client, admin_token):
        """测试：启用 skill 错误 token 返回 401"""
        response = client.post(
            "/api/skills/test.skill/enable",
            headers={"Authorization": "Bearer wrong-token"}
        )
        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"]

    def test_enable_with_valid_token_succeeds(self, client, admin_token):
        """测试：启用 skill 正确 token 成功"""
        # 先导入一个 skill（需要 PR-1 完成后才能测试）
        # 这里假设 test.skill 已存在
        response = client.post(
            "/api/skills/test.skill/enable",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # 可能返回 200 或 404（skill 不存在）
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            assert response.json()["data"]["status"] == "enabled"

    def test_disable_requires_token(self, client):
        """测试：禁用 skill 需要 token"""
        response = client.post("/api/skills/test.skill/disable")
        assert response.status_code == 401

    def test_import_local_without_token_returns_401(self, client):
        """测试：导入 local skill 没有 token 返回 401"""
        response = client.post("/api/skills/import", json={
            "type": "local",
            "path": "/tmp/test-skill"
        })
        assert response.status_code == 401

    def test_import_github_without_token_returns_401(self, client):
        """测试：导入 GitHub skill 没有 token 返回 401"""
        response = client.post("/api/skills/import", json={
            "type": "github",
            "owner": "test",
            "repo": "skill"
        })
        assert response.status_code == 401

    def test_import_local_with_valid_token(self, client, admin_token):
        """测试：导入 local skill 正确 token（集成测试）"""
        response = client.post(
            "/api/skills/import",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"type": "local", "path": "/tmp/test-skill"}
        )
        # 可能返回 200 或 400（路径不存在）
        assert response.status_code in [200, 400]
```

#### 集成测试

**文件**: `/Users/pangge/PycharmProjects/AgentOS/tests/integration/test_skill_enable_disable.py`

```python
import pytest
import os
import tempfile
from pathlib import Path
from agentos.skills.registry import SkillRegistry
from agentos.skills.importer.local_importer import LocalImporter

@pytest.fixture
def registry():
    """创建临时 registry"""
    return SkillRegistry()

@pytest.fixture
def admin_token():
    return "test-admin-token"

@pytest.fixture(autouse=True)
def set_admin_token(monkeypatch, admin_token):
    monkeypatch.setenv("AGENTOS_ADMIN_TOKEN", admin_token)

@pytest.fixture
def test_skill_path(tmp_path):
    """创建测试 skill"""
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()

    # 创建 manifest.yaml
    manifest = skill_dir / "manifest.yaml"
    manifest.write_text("""
skill_id: test.skill
version: 1.0.0
description: Test skill
""")

    return str(skill_dir)

class TestSkillLifecycle:
    """测试完整的 skill 生命周期：import → enable → disable"""

    def test_import_enable_disable_workflow(self, registry, test_skill_path):
        """测试：导入 → 启用 → 禁用 完整流程"""
        # Step 1: Import skill
        importer = LocalImporter(registry)
        skill_id = importer.import_from_path(test_skill_path)

        assert skill_id == "test.skill"

        # Verify initial status is 'imported_disabled'
        skill = registry.get_skill(skill_id)
        assert skill is not None
        assert skill['status'] == 'imported_disabled'

        # Step 2: Enable skill
        registry.set_status(skill_id, 'enabled')

        skill = registry.get_skill(skill_id)
        assert skill['status'] == 'enabled'

        # Step 3: Disable skill
        registry.set_status(skill_id, 'disabled')

        skill = registry.get_skill(skill_id)
        assert skill['status'] == 'disabled'

    def test_list_skills_with_status_filter(self, registry, test_skill_path):
        """测试：按状态过滤 skills"""
        importer = LocalImporter(registry)
        skill_id = importer.import_from_path(test_skill_path)

        # List all skills
        all_skills = registry.list_skills()
        assert len(all_skills) >= 1

        # List only imported_disabled skills
        disabled_skills = registry.list_skills(status='imported_disabled')
        assert any(s['id'] == skill_id for s in disabled_skills)

        # Enable and list only enabled skills
        registry.set_status(skill_id, 'enabled')
        enabled_skills = registry.list_skills(status='enabled')
        assert any(s['id'] == skill_id for s in enabled_skills)
```

#### CLI 测试

**文件**: `/Users/pangge/PycharmProjects/AgentOS/tests/cli/test_skill_commands.py`

```python
import pytest
from click.testing import CliRunner
from agentos.cli.commands.skill import skill

@pytest.fixture
def cli_runner():
    return CliRunner()

@pytest.fixture
def admin_token():
    return "test-admin-token"

class TestSkillCLI:
    """测试 Skill CLI 命令"""

    def test_list_skills(self, cli_runner):
        """测试：agentos skill list"""
        result = cli_runner.invoke(skill, ['list'])
        assert result.exit_code == 0

    def test_enable_without_token_fails(self, cli_runner):
        """测试：没有 token 时 enable 失败"""
        result = cli_runner.invoke(skill, ['enable', 'test.skill'])
        assert result.exit_code != 0
        assert "Invalid admin token" in result.output

    def test_enable_with_token_succeeds(self, cli_runner, admin_token, monkeypatch):
        """测试：有 token 时 enable 成功"""
        monkeypatch.setenv("AGENTOS_ADMIN_TOKEN", admin_token)
        result = cli_runner.invoke(skill, ['enable', 'test.skill', '--token', admin_token])
        # 可能返回 0（成功）或 1（skill 不存在）
        assert "Invalid admin token" not in result.output
```

### Phase 4: 配置和文档

#### 配置

**文件**: `/Users/pangge/PycharmProjects/AgentOS/agentos/core/config.py`（已存在）

确保支持：
```python
# Environment variable: AGENTOS_ADMIN_TOKEN
# 或在配置文件中添加：
{
  "admin_token": "your-secure-token-here"
}
```

#### 用户文档

**文件**: `/Users/pangge/PycharmProjects/AgentOS/docs/SKILLS_ADMIN_GUIDE.md`（新建）

```markdown
# Skills 管理指南

## 配置 Admin Token

Skills 的 import/enable/disable 操作需要 Admin Token 保护。

### 设置 Token

**方法 1：环境变量**
```bash
export AGENTOS_ADMIN_TOKEN="your-secure-token-here"
```

**方法 2：配置文件**
```yaml
# ~/.agentos/config.yaml
admin_token: your-secure-token-here
```

### 生成安全 Token

```bash
# 生成随机 token
openssl rand -hex 32

# 或使用 Python
python -c "import secrets; print(secrets.token_hex(32))"
```

## CLI 使用

### 列出所有 Skills

```bash
agentos skill list
agentos skill list --status enabled
```

### 查看 Skill 详情

```bash
agentos skill info my.skill
```

### 启用 Skill

```bash
export AGENTOS_ADMIN_TOKEN="your-token"
agentos skill enable my.skill
```

### 禁用 Skill

```bash
agentos skill disable my.skill --token your-token
```

## API 使用

### 列出 Skills（无需认证）

```bash
curl http://localhost:8000/api/skills
```

### 启用 Skill（需要认证）

```bash
curl -X POST http://localhost:8000/api/skills/my.skill/enable \
  -H "Authorization: Bearer your-token"
```

### 禁用 Skill（需要认证）

```bash
curl -X POST http://localhost:8000/api/skills/my.skill/disable \
  -H "Authorization: Bearer your-token"
```

## 安全最佳实践

1. 使用强随机 token（至少 32 字节）
2. 不要在代码或日志中硬编码 token
3. 使用环境变量或安全配置文件
4. 定期轮换 token
5. 限制 token 访问权限（仅管理员）
```

---

## 验收标准

### 必须通过的测试

- [ ] `tests/unit/webui/api/test_skills_api.py::test_enable_without_token_returns_401`
- [ ] `tests/unit/webui/api/test_skills_api.py::test_enable_with_invalid_token_returns_401`
- [ ] `tests/unit/webui/api/test_skills_api.py::test_enable_with_valid_token_succeeds`
- [ ] `tests/unit/webui/api/test_skills_api.py::test_disable_requires_token`
- [ ] `tests/unit/webui/api/test_skills_api.py::test_import_local_without_token_returns_401`
- [ ] `tests/unit/webui/api/test_skills_api.py::test_import_github_without_token_returns_401`
- [ ] `tests/integration/test_skill_enable_disable.py::test_import_enable_disable_workflow`
- [ ] `tests/cli/test_skill_commands.py::test_enable_without_token_fails`
- [ ] `tests/cli/test_skill_commands.py::test_enable_with_token_succeeds`

### 功能验收

- [ ] GET `/api/skills` - 公开访问（无需 token）
- [ ] GET `/api/skills/{id}` - 公开访问（无需 token）
- [ ] POST `/api/skills/import` - 需要 Admin Token
  - [ ] 无 token → 401
  - [ ] 错误 token → 401
  - [ ] 正确 token → 200
- [ ] POST `/api/skills/{id}/enable` - 需要 Admin Token
  - [ ] 无 token → 401
  - [ ] 错误 token → 401
  - [ ] 正确 token → 200
- [ ] POST `/api/skills/{id}/disable` - 需要 Admin Token
  - [ ] 无 token → 401
  - [ ] 错误 token → 401
  - [ ] 正确 token → 200

### CLI 验收

- [ ] `agentos skill list` - 工作正常
- [ ] `agentos skill info <id>` - 工作正常
- [ ] `agentos skill enable <id>` - 需要 `--token` 或 `AGENTOS_ADMIN_TOKEN`
- [ ] `agentos skill disable <id>` - 需要 `--token` 或 `AGENTOS_ADMIN_TOKEN`

---

## 风险和缓解措施

### 风险 1: PR-0201-2026-1 延迟

**影响**: 无法开始实施
**缓解**:
- 提前准备完整实施计划（本文档）
- 与 PR-1 团队协调 API 契约
- 准备 Mock Registry 用于独立测试

### 风险 2: Admin Token 机制不兼容

**影响**: 需要调整 Token 验证逻辑
**缓解**:
- 已确认现有机制完善（✅ 已验证）
- 提供 FastAPI 和 Flask 两种集成方式
- 支持开发模式（token 未配置时允许访问）

### 风险 3: 测试覆盖不足

**影响**: 安全漏洞未被发现
**缓解**:
- 编写全面的单元测试（401/403 场景）
- 编写集成测试（完整生命周期）
- 手动渗透测试（绕过 token 验证）

---

## 时间估算（待 PR-1 完成后）

| 任务 | 预估时间 | 优先级 |
|------|---------|--------|
| API 路由实现 | 2 小时 | P0 |
| CLI 命令扩展 | 1.5 小时 | P0 |
| 单元测试 | 2 小时 | P0 |
| 集成测试 | 1.5 小时 | P0 |
| CLI 测试 | 1 小时 | P1 |
| 文档编写 | 1 小时 | P1 |
| **总计** | **9 小时** | - |

---

## 下一步行动

### 立即行动

1. ✅ **生成本实施报告**
2. ⏳ **等待 PR-0201-2026-1 完成通知**
3. ✅ **准备测试用例模板**

### PR-1 完成后立即行动

1. 验证 Registry API 契约
2. 实施 API 路由（2 小时）
3. 实施 CLI 命令（1.5 小时）
4. 编写和运行测试（4.5 小时）
5. 编写文档（1 小时）
6. 提交 PR

---

## 附录：现有 Admin Token 机制使用示例

### Backend 使用（FastAPI）

```python
from fastapi import APIRouter, Depends
from agentos.webui.auth.simple_token import require_admin

router = APIRouter()

@router.post("/protected-endpoint", dependencies=[Depends(require_admin)])
async def protected_operation():
    return {"ok": True}
```

### Backend 使用（手动验证）

```python
from agentos.core.capabilities.admin_token import validate_admin_token
from flask import request, jsonify

@app.route('/api/protected', methods=['POST'])
def protected_operation():
    token = request.headers.get('X-Admin-Token')
    if not validate_admin_token(token):
        return jsonify({'error': 'Unauthorized'}), 403
    return jsonify({'ok': True})
```

### Frontend 使用

```javascript
// 执行受保护操作
await window.adminTokenGate.executeProtected(
    async (token) => {
        const response = await fetch('/api/skills/import', {
            method: 'POST',
            headers: {
                'X-Admin-Token': token,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({type: 'local', path: '/tmp/skill'})
        });
        return response.json();
    },
    {
        requireToken: true,
        title: 'Import Skill',
        message: 'Admin token required to import skills'
    }
);
```

---

## 联系方式

如有问题或需要协调，请联系：
- PR-4 负责人：[您的姓名]
- PR-1 负责人：[待确定]
- 项目协调：[待确定]

---

**文档版本**: 1.0
**最后更新**: 2026-02-01
**状态**: 阻塞中 - 等待依赖
