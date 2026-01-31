# AgentOS 打包验证指南

## 📋 更新内容总结

### 已完成的修改

#### 1. **MANIFEST.txt** (`scripts/publish/MANIFEST.txt`)
更新项目清单，新增以下目录：

**P0（必须）- 核心功能模块：**
- `agentos/core/brain/` - 分类器版本管理、改进提案、信息需求模式学习
- `agentos/core/communication/` - SEARCH→FETCH→BRIEF Pipeline
- `agentos/webui/middleware/` - 安全中间件（CSRF、速率限制、会话安全）
- `agentos/webui/websocket/` - WebSocket 实时通知
- `agentos/webui/static/` - 前端静态资源（包含 cytoscape、vis-network、prism 主题）
- `agentos/webui/templates/` - HTML 模板

**P1（功能完整性）：**
- `agentos/metrics/` - 信息需求度量系统
- `agentos/core/maintenance/` - 系统维护和清理

**P2（质量保障）：**
- `examples/` - 示例代码和演示
- `scripts/gates/` - 质量门系统
- `scripts/demos/` - 演示脚本

#### 2. **MANIFEST.in** (新创建)
Python 打包标准文件，使用 `graft` 和 `recursive-include` 确保：
- ✅ 所有 Python 模块被包含
- ✅ 静态资源（.css、.js、.html、.svg 等）被包含
- ✅ 配置文件（.yaml、.yml、.json）被包含
- ✅ 数据库迁移文件（.sql）被包含
- ✅ 排除测试、缓存等不必要文件

#### 3. **pyproject.toml** (更新)
新增 Hatchling 构建配置：

```toml
[tool.hatch.build]
include = [
    "agentos/**/*.yaml",
    "agentos/**/*.yml",
    "agentos/**/*.json",
    "agentos/**/*.sql",
    "agentos/**/*.html",
    "agentos/**/*.css",
    "agentos/**/*.js",
    # ... 其他静态资源类型
]

[tool.hatch.build.targets.wheel]
packages = ["agentos", "memoryos"]
force-include = { "rules" = "rules" }

[tool.hatch.build.targets.sdist]
include = [
    "/agentos",
    "/memoryos",
    "/rules",
    "/examples",
    "/scripts/gates",
    "/scripts/demos",
    # ...
]
```

**关键点：**
- Hatchling 默认只打包 `.py` 文件
- `[tool.hatch.build] include` 配置确保非 `.py` 文件也被打包进 **wheel**
- 没有此配置，`pip install` 后会缺失静态资源、模板等文件

---

## 🧪 验证步骤

### 方法 A：使用自动化脚本（推荐）

```bash
# 一键完成所有验证
./scripts/verify_packaging.sh
```

这个脚本会自动：
1. 清理旧构建产物
2. 构建 sdist 和 wheel
3. 验证 sdist 内容
4. 验证 wheel 内容（最关键）
5. 在临时虚拟环境中测试安装
6. 生成验证报告

**期望输出：**
```
==========================================
🎉 所有验证通过！可以安全发布
==========================================
```

### 方法 B：手动验证（详细）

#### 步骤 1：构建包

```bash
# 安装构建工具（如果还没有）
pip install build

# 清理旧构建
rm -rf dist/ build/ *.egg-info

# 构建
python3 -m build
```

应该生成：
- `dist/agentos-0.3.1.tar.gz` (sdist)
- `dist/agentos-0.3.1-py3-none-any.whl` (wheel)

#### 步骤 2：检查 sdist 内容

```bash
# 查看 sdist 中的关键目录
tar -tzf dist/*.tar.gz | grep -E "agentos/(webui/static|core/brain|webui/middleware)" | head -20

# 检查静态资源
tar -tzf dist/*.tar.gz | grep -E "(cytoscape|vis-network|prism.*\.css)"

# 检查示例和门禁
tar -tzf dist/*.tar.gz | grep -E "(examples/|scripts/gates/)"
```

#### 步骤 3：检查 wheel 内容（最关键）

```bash
python3 << 'EOF'
import zipfile, glob
wheel = glob.glob('dist/*.whl')[0]
z = zipfile.ZipFile(wheel)

# 检查关键路径
paths = [x for x in z.namelist() if any(
    pat in x for pat in [
        'agentos/webui/static',
        'agentos/webui/templates',
        'agentos/core/brain',
        'agentos/webui/middleware',
        'agentos/core/communication'
    ]
)]

print(f'Wheel 中找到 {len(paths)} 个相关文件')
print('\n前 40 个文件:')
print('\n'.join(paths[:40]))
EOF
```

**期望结果：**
- 能看到 `agentos/webui/static/` 下的文件
- 能看到 `agentos/webui/templates/` 下的 HTML 文件
- 能看到 `agentos/core/brain/` 的 Python 文件
- 能看到 `agentos/webui/middleware/` 的 Python 文件

**⚠️ 如果 wheel 里没有静态资源，用户 pip install 后会出现：**
- WebUI 页面加载失败（404 错误）
- 缺少 CSS/JS 文件
- 模板文件找不到

#### 步骤 4：干净环境安装测试

```bash
# 创建临时虚拟环境
python3 -m venv /tmp/test-agentos
source /tmp/test-agentos/bin/activate

# 安装 wheel
pip install dist/*.whl

# 验证安装
python3 << 'EOF'
import agentos
from pathlib import Path

base = Path(agentos.__file__).parent
checks = {
    'static': base / 'webui' / 'static',
    'templates': base / 'webui' / 'templates',
    'brain': base / 'core' / 'brain',
    'middleware': base / 'webui' / 'middleware',
    'communication': base / 'core' / 'communication',
}

print("安装验证:")
for name, path in checks.items():
    status = '✓' if path.exists() else '✗ MISSING'
    print(f'{status} {name}: {path.relative_to(base)}')
EOF

# 测试启动（可选）
# agentos webui --help

# 清理
deactivate
rm -rf /tmp/test-agentos
```

---

## 🚨 常见问题排查

### 问题 1：wheel 中缺少静态资源

**症状：**
- sdist 中有静态文件，但 wheel 中没有
- `pip install` 后 WebUI 无法加载 CSS/JS

**原因：**
- `MANIFEST.in` 只影响 sdist
- Hatchling 默认只打包 `.py` 文件

**解决方案：**
✅ 已在 `pyproject.toml` 中添加 `[tool.hatch.build] include` 配置

### 问题 2：某些模块导入失败

**症状：**
```python
ModuleNotFoundError: No module named 'agentos.core.brain'
```

**可能原因：**
1. 目录缺少 `__init__.py`
2. `pyproject.toml` 中 `packages` 配置错误

**验证：**
```bash
# 检查所有 __init__.py
find agentos/core/brain agentos/webui/middleware agentos/metrics -name "__init__.py"
```

✅ 已验证：所有关键目录都有 `__init__.py`

### 问题 3：配置文件或迁移脚本缺失

**症状：**
- 运行时找不到 `.yaml` 配置文件
- 数据库迁移失败（`.sql` 文件缺失）

**解决方案：**
✅ 已在 `[tool.hatch.build] include` 中添加：
- `agentos/**/*.yaml`
- `agentos/**/*.yml`
- `agentos/**/*.json`
- `agentos/**/*.sql`

---

## 📊 验证检查清单

发布前确保以下所有项目都通过：

### sdist 验证
- [ ] 包含 `agentos/core/brain/`
- [ ] 包含 `agentos/core/communication/`
- [ ] 包含 `agentos/webui/middleware/`
- [ ] 包含 `agentos/webui/static/vendor/cytoscape/`
- [ ] 包含 `agentos/webui/static/vendor/vis-network/`
- [ ] 包含 `agentos/webui/templates/`
- [ ] 包含 `examples/`
- [ ] 包含 `scripts/gates/`

### wheel 验证（更关键）
- [ ] 包含 `agentos/webui/static/` 下的所有文件
- [ ] 包含 `agentos/webui/templates/` 下的 HTML 文件
- [ ] 包含 `agentos/core/brain/` 的所有 Python 文件
- [ ] 包含 `agentos/webui/middleware/` 的所有 Python 文件
- [ ] 包含 `agentos/core/communication/` 的所有 Python 文件
- [ ] 包含 `agentos/metrics/` 的所有 Python 文件
- [ ] 包含配置文件（.yaml/.yml/.json）
- [ ] 包含迁移脚本（.sql）

### 安装测试
- [ ] 在干净虚拟环境中 `pip install dist/*.whl` 成功
- [ ] 能够 `import agentos` 无错误
- [ ] 所有关键目录在安装位置存在
- [ ] WebUI 能够启动（如果手动测试）

---

## 🎯 下一步操作

1. **立即验证（必做）：**
   ```bash
   ./scripts/verify_packaging.sh
   ```

2. **如果验证失败：**
   - 查看脚本输出的错误信息
   - 检查 `pyproject.toml` 配置
   - 检查 `MANIFEST.in` 配置
   - 确认所有目录有 `__init__.py`
   - 重新运行验证

3. **验证通过后：**
   - 可以安全发布到 PyPI（或私有仓库）
   - 建议在测试环境先安装验证
   - 监控用户反馈，特别是静态资源相关问题

---

## 📚 参考资料

- [Hatchling 官方文档](https://hatch.pypa.io/latest/config/build/)
- [Python Packaging 指南](https://packaging.python.org/)
- [MANIFEST.in 语法](https://packaging.python.org/en/latest/guides/using-manifest-in/)

---

**最后更新：** 2026-01-31
**验证脚本：** `scripts/verify_packaging.sh`
**相关文件：**
- `scripts/publish/MANIFEST.txt`
- `MANIFEST.in`
- `pyproject.toml`
