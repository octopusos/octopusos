# Extension Multi-Platform Support - Implementation Summary

## Overview

已完成对 AgentOS 扩展系统的多平台支持改进，使扩展能够在 Linux、macOS 和 Windows 上安装和运行。

## 实现的改进

### 1. 条件评估器增强

**文件**: `agentos/core/extensions/engine.py`

**改进内容**:
- 支持更复杂的条件表达式
- 支持 Python 运算符: `in`, `==`, `!=`, `and`, `or`, `not`
- 支持布尔字面量: `true`, `false`

**示例**:
```yaml
when: "platform_os in ['linux', 'darwin']"  # Unix 系统
when: "platform_os == 'win32'"               # Windows
when: "platform_arch == 'x64'"               # x64 架构
when: "platform_os == 'darwin' and platform_arch == 'arm64'"  # Apple Silicon
```

### 2. Postman 扩展多平台安装

**文件**: `store/extensions/tools.postman/install/plan.yaml`

**支持的平台**:
- ✅ Linux (x64, arm64)
- ✅ macOS (x64, arm64)
- ✅ Windows (x64)

**安装策略**:

#### Unix (Linux/macOS)
```bash
# 使用官方安装脚本
curl -o- "https://dl-cli.pstmn.io/install/unix.sh" | sh

# 查找并链接已安装的二进制文件
if command -v postman >/dev/null 2>&1; then
  ln -sf $(command -v postman) bin/postman
elif [ -f "$HOME/.postman/postman-cli" ]; then
  ln -sf "$HOME/.postman/postman-cli" bin/postman
fi
```

#### Windows
```powershell
# 使用官方 PowerShell 安装脚本
[System.Net.ServicePointManager]::SecurityProtocol = 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://dl-cli.pstmn.io/install/win64.ps1'))

# 创建批处理包装器
$wrapperContent = "@echo off`r`n`"C:\path\to\postman.exe`" %*"
Set-Content -Path "bin\postman.bat" -Value $wrapperContent
```

### 3. Manifest 声明

**文件**: `store/extensions/tools.postman/manifest.json`

```json
{
  "platforms": [
    "linux",
    "darwin",
    "win32"
  ],
  "architectures": [
    "x64",
    "arm64"
  ]
}
```

### 4. Handler 跨平台支持

**文件**: `store/extensions/tools.postman/handlers.py`

**改进**:
- 自动检测平台（Windows vs Unix）
- 使用正确的二进制文件扩展名（`.bat` vs 无扩展名）
- 提供详细的错误信息包括平台信息

```python
import platform

system = platform.system()
if system == 'Windows':
    postman_bin = os.path.join(work_dir, 'bin', 'postman.bat')
else:
    postman_bin = os.path.join(work_dir, 'bin', 'postman')
```

## 使用方法

### 创建多平台扩展

1. **在 manifest.json 中声明平台**:
```json
{
  "platforms": ["linux", "darwin", "win32"],
  "architectures": ["x64", "arm64"]
}
```

2. **在 plan.yaml 中使用条件**:
```yaml
steps:
  # Unix 安装
  - id: install_unix
    type: exec.shell
    when: "platform_os in ['linux', 'darwin']"
    command: |
      # Unix 安装命令

  # Windows 安装
  - id: install_windows
    type: exec.powershell
    when: "platform_os == 'win32'"
    command: |
      # PowerShell 安装命令
```

3. **在 handlers.py 中处理平台差异**:
```python
import platform

system = platform.system()
if system == 'Windows':
    # Windows 逻辑
    binary_path = 'bin/tool.bat'
else:
    # Unix 逻辑
    binary_path = 'bin/tool'
```

## 安装目录策略

### 推荐方案：扩展 bin 目录

所有平台统一使用扩展目录下的 `bin/` 子目录：

```
store/extensions/tools.example/
├── bin/
│   ├── tool         # Unix: 二进制文件或符号链接
│   └── tool.bat     # Windows: 批处理包装器
├── handlers.py
├── manifest.json
└── install/
    └── plan.yaml
```

### Unix 系统
- 官方安装器通常安装到：`~/.tool/`, `~/.local/bin/`, `/usr/local/bin/`
- 扩展策略：创建符号链接到 `bin/tool`

### Windows 系统
- 官方安装器通常安装到：`%LOCALAPPDATA%\Tool\`, `%ProgramFiles%\Tool\`
- 扩展策略：创建批处理包装器到 `bin\tool.bat`

## 条件表达式参考

### 支持的变量
- `platform_os`: 操作系统
  - `'linux'` - Linux
  - `'darwin'` - macOS
  - `'win32'` - Windows
- `platform_arch`: 架构
  - `'x64'` - 64位 Intel/AMD
  - `'arm64'` - 64位 ARM
  - `'x86'` - 32位（遗留）

### 支持的运算符
- 比较: `==`, `!=`
- 成员: `in`, `not in`
- 逻辑: `and`, `or`, `not`
- 字面量: `true`, `false`

### 常用模式

```yaml
# 所有平台
when: "true"

# 特定平台
when: "platform_os == 'linux'"
when: "platform_os == 'darwin'"
when: "platform_os == 'win32'"

# 多个平台
when: "platform_os in ['linux', 'darwin']"

# 特定架构
when: "platform_arch == 'x64'"
when: "platform_arch == 'arm64'"

# 组合条件
when: "platform_os == 'darwin' and platform_arch == 'arm64'"
when: "platform_os in ['linux', 'darwin'] and platform_arch == 'x64'"
```

## 测试

### 当前平台测试
```bash
# 安装扩展
python -m agentos.cli.extensions install extension.zip

# 测试命令
/tool-command args
```

### 模拟其他平台（开发时）
```python
# 在 engine.py 中修改平台检测逻辑进行测试
context = StepContext(
    platform_os='win32',  # 模拟 Windows
    platform_arch='x64',
    work_dir=Path('.'),
    extension_id='test',
    variables={}
)
```

## 文档

- **多平台支持指南**: `docs/extensions/MULTI_PLATFORM_SUPPORT.md`
- **完整文档**: 包含示例、最佳实践和故障排除

## 示例扩展

查看 `tools.postman` 扩展作为参考：
- `store/extensions/tools.postman/install/plan.yaml` - 多平台安装计划
- `store/extensions/tools.postman/handlers.py` - 跨平台处理器
- `store/extensions/tools.postman/manifest.json` - 平台声明

## 下一步

1. **测试 Windows**: 在 Windows 系统上测试 Postman 扩展安装
2. **创建更多示例**: 为其他工具创建多平台扩展（k6, Newman, etc.）
3. **改进验证**: 添加架构检测和验证逻辑
4. **文档完善**: 添加更多平台特定的故障排除指南

## 技术细节

### 安全性
- 条件评估使用受限的 `eval()`，禁用内置函数
- 只允许安全的运算符和表达式
- 不允许函数调用或导入

### 性能
- 条件在安装时评估一次
- 不匹配的步骤被跳过，不执行
- 平台检测使用 Python 标准库 `platform` 模块

### 兼容性
- 向后兼容旧的简单条件语法
- 支持布尔字面量 `true`/`false`
- 自动处理字符串引号（单引号或双引号）
