# Extension 安装 404 根本原因分析

## 问题现象

前端上传扩展后，立即收到 404 错误（只出现一次）：
```
GET http://127.0.0.1:9090/api/extensions/install/inst_XXX 404 (Not Found)
```

## 根本原因

**ZIP 文件结构不正确** - 缺少必需的顶层目录！

### 验证器要求

`agentos/core/extensions/validator.py` 第 69 行:
```python
if len(top_dirs) != 1:
    raise ValidationError(
        f"Zip must contain exactly one top-level directory, found: {top_dirs}"
    )
```

**要求**: ZIP 必须包含**恰好一个**顶层目录。

### 错误的 ZIP 结构

```bash
cd postman
zip -r ../postman-extension.zip .  # ❌ 错误打包方式
```

产生的结构：
```
postman-extension.zip
  ├── manifest.json     ← 多个顶层项
  ├── install/
  ├── docs/
  └── commands/
```

验证失败：`found: {'install', 'docs', 'commands', 'manifest.json'}`

### 正确的 ZIP 结构

```bash
zip -r postman-extension.zip postman  # ✅ 正确打包方式
```

产生的结构：
```
postman-extension.zip
  └── postman/          ← 唯一的顶层目录
      ├── manifest.json
      ├── install/
      ├── docs/
      └── commands/
```

验证通过！

## 失败流程分析

### 错误的 ZIP 导致的流程

```
1. 前端上传 ZIP
   ↓
2. 后端返回 {"install_id": "inst_xxx", "status": "INSTALLING"}
   ↓
3. 前端开始轮询 /api/extensions/install/inst_xxx
   ↓
4. 后台线程启动
   ↓
5. 步骤 1: 验证 ZIP 结构
   → ValidationError: Zip must contain exactly one top-level directory ❌
   ↓
6. 异常被捕获，但 install record 从未被创建
   ↓
7. 前端轮询 → 404 (记录不存在)
   ↓
8. 我们的修复代码检测到 404，删除 installId，停止轮询 ✅
```

### 正确的 ZIP 的流程

```
1. 前端上传 ZIP
   ↓
2. 后端返回 {"install_id": "inst_xxx", "status": "INSTALLING"}
   ↓
3. 前端开始轮询
   ↓
4. 后台线程启动
   ↓
5. 步骤 1: 验证 ZIP 结构 ✅
   ↓
6. 步骤 2-4: 检查、注册、设置状态 ✅
   ↓
7. 步骤 5: 创建 install record ✅
   ↓
8. 前端轮询 → 200 (可获取进度) ✅
   ↓
9. 步骤 6-8: 更新进度、执行安装、完成 ✅
```

## 测试验证

### 错误的 ZIP
```bash
$ cd postman && zip -r ../test.zip .
$ python3 test_install.py

✗ ValidationError: Zip must contain exactly one top-level directory
✗ Install record 不存在 → 404
```

### 正确的 ZIP
```bash
$ zip -r postman-extension.zip postman
$ python3 test_install.py

✓ ZIP 结构验证通过
✓ 注册扩展成功
✓ 创建 install record 成功
✓ 可以正常轮询进度
✓ 记录存在，不再 404
```

## 其他发现

### 1. icon.png 是空文件
- 已删除空的 `postman/icon.png` (0 字节)
- manifest 中未声明 icon，所以不影响

### 2. 前端 404 处理生效
我们的修复代码工作正常：
```javascript
if (response.status === 404) {
    this.activeInstalls.delete(installId);  // 删除无效 ID
    // 移除 UI，刷新列表
}
```
这就是为什么 404 "只出现一次" - 第一次请求 404 后就停止轮询了。

### 3. 安装计划会失败（预期）
`verify_postman` 步骤会失败，因为 postman CLI 未安装：
```bash
Command failed with exit code 127: /bin/bash: postman: command not found
```
但这是正常的，记录会被标记为 FAILED，不会 404。

## 解决方案总结

### 立即修复
✅ 重新打包 ZIP，确保包含顶层目录：
```bash
zip -r postman-extension.zip postman
```

### 已有的修复（仍然有效）
✅ 前端 404 处理 - 防止无限轮询
✅ Schema 验证兼容性 - 支持旧格式
✅ 智能清理旧安装 - 允许重试

### 建议的改进

#### 1. 更早创建 install record
```python
def install_extension_upload():
    install_id = generate_install_id()

    # 立即创建 install record (status: PENDING)
    registry.create_install_record(
        install_id=install_id,
        extension_id="unknown",  # 稍后更新
        status=InstallStatus.PENDING
    )

    # 然后启动后台线程
    thread = Thread(target=run_installation)
    thread.start()

    return {"install_id": install_id}
```

但这需要修改外键约束处理。

#### 2. 前端显示更友好的错误
```javascript
if (data.status === 'FAILED') {
    // 显示具体错误信息
    this.showNotification(
        `Installation failed: ${data.error}`,
        'error'
    );
}
```

#### 3. 提供 ZIP 结构检查工具
```python
# 添加到 CLI
agentos extension validate postman-extension.zip
```

## 文件清单

已修复的文件：
- ✅ `postman-extension.zip` - 重新打包，包含顶层目录
- ✅ `postman/` - 删除了空的 icon.png

不需要修改的代码：
- ✅ 前端 404 处理已经正确
- ✅ Schema 验证已经兼容
- ✅ 后端清理逻辑已经完善

## 总结

**404 错误的真正原因**：
- 🔴 ZIP 结构不正确
- 🔴 验证在第一步就失败
- 🔴 install record 从未被创建
- 🔴 前端轮询时记录不存在 → 404

**修复后**：
- ✅ ZIP 结构正确
- ✅ 验证通过
- ✅ install record 成功创建
- ✅ 前端可以正常轮询进度
- ✅ 即使安装失败，也会返回 FAILED 状态，不是 404

**下一步**：
1. 使用新的 `postman-extension.zip` 重新上传
2. 应该能看到正常的安装进度
3. 最终会显示 FAILED (因为 postman CLI 未安装)
4. 这是正常的，用户可以手动安装 postman CLI 后重试
