# AgentOS Runtime 打包指南

## 概述

本指南介绍如何使用 Nuitka 将 AgentOS 打包为单可执行文件。

## 前置条件

### macOS

```bash
# 安装 Xcode Command Line Tools
xcode-select --install

# 安装 Python 3.13+
brew install python@3.13

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -e .
pip install nuitka ordered-set zstandard
```

### Windows

```bash
# 安装 Visual Studio Build Tools
# 下载: https://visualstudio.microsoft.com/downloads/
# 选择 "C++ 生成工具"

# 安装 Python 3.13+
# 下载: https://www.python.org/downloads/

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 安装依赖
pip install -e .
pip install nuitka ordered-set zstandard
```

### Linux

```bash
# 安装依赖（Ubuntu/Debian）
sudo apt-get update
sudo apt-get install -y python3-dev gcc g++ ccache

# 安装 Python 3.13+
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get install python3.13 python3.13-venv

# 创建虚拟环境
python3.13 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -e .
pip install nuitka ordered-set zstandard
```

---

## 快速开始

### 构建当前平台

```bash
# 激活虚拟环境
source .venv/bin/activate  # macOS/Linux
# 或
.venv\Scripts\activate     # Windows

# 运行构建脚本
python3 scripts/build_runtime.py

# 检查输出
ls -lh dist/
```

### 预期输出

**macOS ARM64**:
```
dist/agentos-runtime-macos-arm64  (约 41 MB)
```

**macOS Intel**:
```
dist/agentos-runtime-macos-x64  (约 42 MB)
```

**Windows x64**:
```
dist/agentos-runtime-windows-x64.exe  (约 45 MB)
```

---

## 构建脚本详解

### 脚本参数

`build_runtime.py` 自动检测平台，无需手动指定参数。

### 自定义构建

如需自定义构建选项，编辑 `scripts/build_runtime.py`:

```python
# 添加更多包
"--include-package=your_package",

# 排除特定模块
"--nofollow-import-to=unwanted_module",

# 启用 UPX 压缩（需安装 UPX）
"--compress-binary",

# 禁用 LTO（如果编译出错）
# 删除或注释: "--lto=yes",
```

---

## 测试构建

### 自动测试

```bash
# 运行完整测试套件
./scripts/test_runtime.sh
```

### 手动测试

```bash
# 测试版本
dist/agentos-runtime-macos-arm64 --version

# 测试帮助
dist/agentos-runtime-macos-arm64 --help

# 初始化数据库
DATABASE_PATH=/tmp/test.db dist/agentos-runtime-macos-arm64 init

# 启动服务器
DATABASE_PATH=/tmp/test.db dist/agentos-runtime-macos-arm64 web --port 8000
```

---

## macOS 特定问题

### Gatekeeper 限制

首次运行时，macOS 可能阻止未签名的二进制文件。

**方法 1: 移除隔离属性**

```bash
xattr -d com.apple.quarantine dist/agentos-runtime-macos-arm64
```

**方法 2: 系统设置**

1. 尝试运行可执行文件
2. 系统会弹出警告
3. 打开 "系统偏好设置" > "安全性与隐私" > "通用"
4. 点击 "仍要打开"

**方法 3: 代码签名**（推荐用于分发）

```bash
# 需要 Apple Developer 账号
codesign --sign "Developer ID Application: Your Name" \
         --force \
         --deep \
         dist/agentos-runtime-macos-arm64
```

---

## Windows 特定问题

### 防病毒软件

Windows Defender 可能误报 Nuitka 生成的可执行文件。

**解决方案**:
1. 添加排除项到 Windows Defender
2. 使用代码签名证书（EV Code Signing）

### Visual Studio Build Tools

如果编译失败，确保安装了完整的 C++ 工具链：

```bash
# 下载 Visual Studio Installer
# 选择 "使用 C++ 的桌面开发"
# 包含组件:
# - MSVC v143
# - Windows 10/11 SDK
# - CMake
```

---

## 性能优化

### 减小体积

1. **排除更多包**:
   ```python
   "--nofollow-import-to=module_name",
   ```

2. **启用 UPX 压缩**:
   ```bash
   # 安装 UPX
   brew install upx  # macOS
   choco install upx  # Windows

   # 在 build_runtime.py 中添加
   "--compress-binary",
   ```

3. **按需加载**:
   在代码中延迟导入大型模块

### 加快启动

1. **延迟导入**:
   ```python
   def heavy_function():
       import heavy_module  # 仅在需要时导入
       return heavy_module.do_work()
   ```

2. **缓存配置**:
   使用 `@lru_cache` 缓存配置加载

3. **预编译正则**:
   在模块级别编译正则表达式

---

## CI/CD 集成

### GitHub Actions

工作流已配置在 `.github/workflows/build-runtime.yml`

**触发构建**:
```bash
# Push 到主分支
git push origin master

# 创建标签
git tag v0.3.0
git push origin v0.3.0

# 手动触发
# 在 GitHub 仓库页面 > Actions > Build Runtime > Run workflow
```

**下载构件**:
1. 打开 Actions 页面
2. 选择最近的构建
3. 下载 Artifacts 部分的构件

### 本地多平台构建

使用 Docker 构建其他平台（高级）:

```bash
# 构建 Linux 版本（在 macOS/Windows 上）
docker run --rm -v $(pwd):/app -w /app python:3.13 \
  bash -c "pip install -e . && pip install nuitka && python scripts/build_runtime.py"
```

---

## 故障排除

### 问题: 编译错误 "cannot find -lpython3.13"

**原因**: Python 开发头文件缺失

**解决**:
```bash
# macOS
brew reinstall python@3.13

# Ubuntu/Debian
sudo apt-get install python3.13-dev

# Windows
# 重新安装 Python，确保勾选 "Include development headers"
```

### 问题: 链接错误 "too many files"

**原因**: 文件描述符限制

**解决**:
```bash
# macOS/Linux
ulimit -n 4096

# 永久设置（macOS）
echo "ulimit -n 4096" >> ~/.zshrc
```

### 问题: 运行时错误 "module not found"

**原因**: 模块未包含在打包中

**解决**:
```python
# 在 build_runtime.py 中添加
"--include-module=missing_module",
```

### 问题: 体积过大 (> 100 MB)

**原因**: 包含了不必要的依赖

**解决**:
```python
# 检查哪些包被包含
nuitka --show-modules agentos/cli/main.py

# 排除大型包
"--nofollow-import-to=large_package",
```

### 问题: 启动很慢 (> 10 秒)

**原因**: onefile 模式需要解压

**解决方案 1**: 使用 standalone 模式
```python
# 移除 "--onefile" 参数
# 输出将是一个目录而不是单文件
```

**解决方案 2**: 优化导入
```python
# 延迟导入非关键模块
def command_that_needs_module():
    import heavy_module
    # ...
```

---

## 高级配置

### 自定义输出名称

```python
# 修改 build_runtime.py
output_name = f"custom-name-{platform_name}"
```

### 包含额外数据文件

```python
# 添加更多数据目录
"--include-data-dir=path/to/data=target/path",
"--include-data-file=single_file.txt=target/file.txt",
```

### 调试模式

```python
# 添加调试标志
"--debug",
"--show-progress",
"--show-memory",
```

---

## 发布检查清单

发布前确保：

- [ ] 所有平台构建成功
- [ ] 运行测试套件通过
- [ ] 文件大小合理（< 50 MB）
- [ ] 启动时间可接受（< 3 秒）
- [ ] 代码签名完成（生产环境）
- [ ] 版本号正确
- [ ] CHANGELOG 更新

---

## 参考资源

- [Nuitka 官方文档](https://nuitka.net/doc/user-manual.html)
- [Nuitka 性能优化指南](https://nuitka.net/pages/performance.html)
- [Tauri Sidecar 集成](https://tauri.app/v1/guides/building/sidecar)
- [Python 打包最佳实践](https://packaging.python.org/)

---

**文档版本**: 1.0
**最后更新**: 2026-01-30
