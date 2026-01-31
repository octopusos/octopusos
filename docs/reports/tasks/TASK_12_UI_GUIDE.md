# Task #12 UI 使用指南：Project Settings 配置

## 🎨 界面预览

### 1. 项目创建/编辑模态框 - 标签页布局

```
┌─────────────────────────────────────────────────────────────┐
│  Create Project / Edit Project                         ✕    │
├─────────────────────────────────────────────────────────────┤
│  ┌───────────────┬───────────────┐                          │
│  │ Basic Info    │   Settings    │  ← 标签页导航            │
│  └───────────────┴───────────────┘                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [标签页内容区域]                                              │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                          [Cancel]  [Save]    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Basic Info 标签页

### 界面布局

```
┌──────────────────────────────────────────────────────────────┐
│  Name *                                                       │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Enter project name                                     │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  Description                                                  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Optional project description                           │  │
│  │                                                        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  Tags                                                         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ python, web, api (comma-separated)                     │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  Default Working Directory                                   │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ /path/to/workspace                                     │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| Name | ✅ | 项目名称，唯一标识符 |
| Description | ❌ | 项目描述，支持多行文本 |
| Tags | ❌ | 逗号分隔的标签列表 |
| Default Working Directory | ❌ | 项目默认工作目录 |

---

## ⚙️ Settings 标签页

### 界面布局

```
┌──────────────────────────────────────────────────────────────┐
│  ━━━ Execution Settings ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                               │
│  Default Runner                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ -- System Default --            ▼                      │  │
│  └────────────────────────────────────────────────────────┘  │
│  Default AI provider for tasks in this project               │
│                                                               │
│  Provider Policy                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ -- None --                      ▼                      │  │
│  └────────────────────────────────────────────────────────┘  │
│  Control which providers are allowed                         │
│                                                               │
│  ━━━ Environment Variables ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                               │
│  Environment Overrides                                        │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ ┌──────────────┬──────────────────────────┬─────────┐ │  │
│  │ │ DEBUG        │ true                     │  🗑️    │ │  │
│  │ └──────────────┴──────────────────────────┴─────────┘ │  │
│  │ ┌──────────────┬──────────────────────────┬─────────┐ │  │
│  │ │ LOG_LEVEL    │ info                     │  🗑️    │ │  │
│  │ └──────────────┴──────────────────────────┴─────────┘ │  │
│  └────────────────────────────────────────────────────────┘  │
│  [+ Add Variable]                                             │
│  Environment variables to inject (whitelist only)            │
│                                                               │
│  ━━━ Risk Profile ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                               │
│  ☑ Allow shell write operations                              │
│  Permit tasks to write files via shell commands              │
│                                                               │
│  ☐ Require admin token for high-risk operations              │
│  Enforce token validation for dangerous actions              │
│                                                               │
│  Writable Paths (one per line)                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ /tmp                                                   │  │
│  │ ./output                                               │  │
│  │ /var/project/data                                      │  │
│  └────────────────────────────────────────────────────────┘  │
│  Paths where write operations are allowed                    │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔧 Settings 字段详解

### 1. Execution Settings（执行设置）

#### Default Runner
**下拉选项**:
- `-- System Default --` (空值，使用系统默认)
- `Llama.cpp (Local)` - 本地 Llama.cpp 引擎
- `OpenAI` - OpenAI API
- `Anthropic` - Anthropic Claude API

**作用**: 指定项目任务默认使用的 AI 模型提供者

**示例**:
```json
{
  "settings": {
    "default_runner": "llama.cpp"
  }
}
```

#### Provider Policy
**下拉选项**:
- `-- None --` (无策略限制)
- `Prefer Local` - 优先使用本地模型
- `Cloud Only` - 仅允许云端 API
- `Local Only` - 仅允许本地模型

**作用**: 控制项目可以使用的 AI 提供者范围

**示例**:
```json
{
  "settings": {
    "provider_policy": "prefer-local"
  }
}
```

---

### 2. Environment Variables（环境变量）

#### 动态键值对编辑器

**特性**:
- ✅ 动态添加/删除变量
- ✅ 键名使用等宽字体（易于识别）
- ✅ 支持任意数量的变量
- ✅ 自动滚动（超过 200px 高度）

**操作流程**:
1. 点击 **[+ Add Variable]** 按钮
2. 在 KEY 输入框输入变量名（如 `DEBUG`）
3. 在 value 输入框输入变量值（如 `true`）
4. 点击 🗑️ 图标删除不需要的变量

**数据格式**:
```json
{
  "settings": {
    "env_overrides": {
      "DEBUG": "true",
      "LOG_LEVEL": "info",
      "PYTHONPATH": "/custom/modules"
    }
  }
}
```

**白名单机制**:
> ⚠️ 注意：环境变量仅影响任务执行环境，应遵循最小权限原则

---

### 3. Risk Profile（风险配置）

#### Allow shell write operations
**类型**: 复选框

**作用**: 允许任务通过 shell 命令写入文件

**默认值**: `false` (不允许)

**用途**:
- 控制任务是否可以创建/修改文件
- 适用于需要生成输出文件的项目

**示例**:
```json
{
  "settings": {
    "risk_profile": {
      "allow_shell_write": true
    }
  }
}
```

#### Require admin token for high-risk operations
**类型**: 复选框

**作用**: 强制要求管理员令牌才能执行高风险操作

**默认值**: `false` (不要求)

**用途**:
- 增强敏感项目的安全性
- 防止未授权的危险操作

**示例**:
```json
{
  "settings": {
    "risk_profile": {
      "require_admin_token": true
    }
  }
}
```

#### Writable Paths
**类型**: 多行文本框

**格式**: 每行一个路径

**作用**: 指定任务可以写入文件的路径白名单

**支持路径类型**:
- 绝对路径: `/tmp`, `/var/project`
- 相对路径: `./output`, `../shared`

**数据处理**:
```javascript
// 自动过滤空行和空白字符
const paths = textarea.value
    .split('\n')
    .map(p => p.trim())
    .filter(p => p.length > 0);
```

**示例**:
```json
{
  "settings": {
    "risk_profile": {
      "writable_paths": [
        "/tmp",
        "./output",
        "/var/project/data"
      ]
    }
  }
}
```

---

## 🎯 使用场景示例

### 场景 1: 本地 AI 开发项目

**需求**:
- 使用本地 Llama.cpp 模型
- 优先本地推理
- 允许生成文件到 `./output` 目录
- 启用调试模式

**配置**:
```json
{
  "name": "Local AI Dev",
  "settings": {
    "default_runner": "llama.cpp",
    "provider_policy": "local-only",
    "env_overrides": {
      "DEBUG": "true",
      "MODEL_PATH": "/models/llama-2-7b"
    },
    "risk_profile": {
      "allow_shell_write": true,
      "require_admin_token": false,
      "writable_paths": ["./output", "/tmp"]
    }
  }
}
```

### 场景 2: 生产环境项目

**需求**:
- 使用 OpenAI API
- 仅云端 API（稳定性优先）
- 严格的写入权限控制
- 需要管理员令牌

**配置**:
```json
{
  "name": "Production System",
  "settings": {
    "default_runner": "openai",
    "provider_policy": "cloud-only",
    "env_overrides": {
      "OPENAI_API_KEY": "sk-...",
      "LOG_LEVEL": "warning"
    },
    "risk_profile": {
      "allow_shell_write": true,
      "require_admin_token": true,
      "writable_paths": ["/var/project/logs"]
    }
  }
}
```

### 场景 3: 测试/实验项目

**需求**:
- 优先本地，回退云端
- 宽松的写入权限
- 丰富的环境变量

**配置**:
```json
{
  "name": "Experiment Lab",
  "settings": {
    "default_runner": "llama.cpp",
    "provider_policy": "prefer-local",
    "env_overrides": {
      "DEBUG": "true",
      "EXPERIMENT_MODE": "true",
      "LOG_LEVEL": "debug",
      "CACHE_DIR": "/tmp/cache"
    },
    "risk_profile": {
      "allow_shell_write": true,
      "require_admin_token": false,
      "writable_paths": ["/tmp", "./experiments", "./results"]
    }
  }
}
```

---

## 🖱️ 用户操作流程

### 创建新项目

```
1. 点击 [New Project] 按钮
   ↓
2. 在 "Basic Info" 标签页填写项目基本信息
   - 输入项目名称 (必填)
   - 输入描述 (可选)
   - 输入标签 (可选)
   - 输入默认工作目录 (可选)
   ↓
3. 点击 "Settings" 标签页
   ↓
4. 配置执行设置
   - 选择 Default Runner
   - 选择 Provider Policy
   ↓
5. 添加环境变量 (可选)
   - 点击 [+ Add Variable]
   - 输入 KEY 和 value
   - 可添加多个
   ↓
6. 配置风险配置
   - 勾选/取消勾选权限选项
   - 填写可写路径 (每行一个)
   ↓
7. 点击 [Save] 保存项目
   ↓
8. 看到成功提示: "Project created successfully"
```

### 编辑已有项目

```
1. 在项目卡片上点击 ✏️ (Edit) 按钮
   ↓
2. 模态框打开，显示 "Edit Project"
   ↓
3. 所有字段已预填充当前值
   - Basic Info 标签页: 基础信息
   - Settings 标签页: 所有设置项
   ↓
4. 修改需要更改的字段
   ↓
5. 切换标签页查看/修改其他配置
   ↓
6. 点击 [Save] 保存修改
   ↓
7. 看到成功提示: "Project updated successfully"
```

---

## 🎨 视觉设计特点

### 标签页设计

```
┌───────────────┬───────────────┐
│ Basic Info    │   Settings    │  ← 未选中状态: 灰色文字
└───────────────┴───────────────┘

┌───────────────┬───────────────┐
│ Basic Info    │   Settings    │  ← 选中状态: 蓝色文字 + 底部蓝线
└───────────────┴═══════════════┘
```

### 环境变量编辑器

```
┌──────────────┬──────────────────────────┬─────────┐
│ DEBUG        │ true                     │  🗑️    │  ← 鼠标悬停: 删除按钮变红
└──────────────┴──────────────────────────┴─────────┘
  ↑ 等宽字体      ↑ 普通文本                ↑ 图标按钮
  灰色背景
```

### 区域分隔

```
━━━ Execution Settings ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ↑ 标题样式: 加粗 + 底部边框线
```

---

## 📱 响应式适配

### 桌面端 (>768px)
- 标签页横向排列
- 环境变量行横向布局
- 充分利用宽度

### 移动端 (<768px)
- 标签页可能换行或滚动
- 环境变量行保持横向（自适应缩小）
- 表单控件全宽

---

## ⌨️ 键盘快捷键

| 快捷键 | 功能 |
|--------|------|
| Tab | 在表单字段间切换 |
| Shift + Tab | 反向切换 |
| Enter | 提交表单（在文本框中） |
| Esc | 关闭模态框 |

---

## 🔍 数据验证

### 前端验证

| 字段 | 验证规则 |
|------|---------|
| Name | 必填，非空 |
| Tags | 可选，逗号分隔 |
| Default Runner | 可选，下拉选择 |
| Provider Policy | 可选，下拉选择 |
| 环境变量 KEY | 非空才保存 |
| 环境变量 value | 允许空值 |
| Writable Paths | 每行一个，自动过滤空行 |

### 后端验证

```python
# ProjectSettings Schema 验证
class ProjectSettings(BaseModel):
    default_runner: Optional[str] = None
    provider_policy: Optional[str] = None
    env_overrides: Dict[str, str] = {}
    risk_profile: Optional[RiskProfile] = None
```

---

## 💡 最佳实践

### 1. 环境变量管理
- ✅ 只添加必要的环境变量
- ✅ 避免硬编码敏感信息（如 API 密钥）
- ✅ 使用描述性的键名（如 `LOG_LEVEL` 而非 `L`）

### 2. 风险配置
- ✅ 默认禁用 shell 写入（除非必要）
- ✅ 明确指定可写路径（避免使用 `/`）
- ✅ 生产环境启用 admin token 要求

### 3. Provider 策略
- ✅ 开发环境使用 `prefer-local`
- ✅ 生产环境使用 `cloud-only`
- ✅ 离线环境使用 `local-only`

---

## 🐛 常见问题

### Q1: 为什么我的环境变量没有保存？
**A**: 确保 KEY 字段不为空。空键的环境变量会被自动过滤。

### Q2: 如何删除所有环境变量？
**A**: 逐个点击 🗑️ 图标删除，或者切换标签页后回来（会保留已填写的）。

### Q3: Writable Paths 支持通配符吗？
**A**: 当前版本不支持通配符，需要明确指定每个路径。

### Q4: 可以为不同仓库设置不同的 Settings 吗？
**A**: 当前 Settings 是项目级别的，所有仓库共享。未来版本可能支持仓库级别配置。

---

## 📊 字段映射表

| UI 字段 | JSON 路径 | 类型 | 默认值 |
|---------|-----------|------|--------|
| Default Runner | `settings.default_runner` | string | null |
| Provider Policy | `settings.provider_policy` | string | null |
| 环境变量 | `settings.env_overrides` | object | {} |
| Allow shell write | `settings.risk_profile.allow_shell_write` | boolean | false |
| Require admin token | `settings.risk_profile.require_admin_token` | boolean | false |
| Writable Paths | `settings.risk_profile.writable_paths` | array | [] |

---

**文档版本**: 1.0
**最后更新**: 2026-01-29
**适用版本**: AgentOS v1.0+
