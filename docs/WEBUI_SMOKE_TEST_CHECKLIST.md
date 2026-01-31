# WebUI Skills 页面 Smoke Test 清单

**日期**: 2026-02-01  
**测试类型**: 手动验证清单（待 Playwright 自动化）  
**状态**: ⚠️ 待部署后验证

---

## 前置条件

1. 安装依赖：`pip install itsdangerous`
2. 设置 Admin Token：`export AGENTOS_ADMIN_TOKEN="your-token"`
3. 导入测试 skill：`agentos skill import tests/fixtures/skills/hello_skill`
4. 启动 server：`python3 -m agentos.webui.app`

---

## Smoke Test 1: 页面加载 ✓

### 步骤
1. 打开浏览器
2. 访问 `http://localhost:5555/#/skills`

### 期望结果
- ✅ 页面正常加载，无 JavaScript 错误
- ✅ 看到 "Skills" 标题
- ✅ 看到导航菜单中的 "Skills" 链接
- ✅ 看到 "Import Skill" 按钮

### 验证截图
```bash
# 如果有 Playwright
npx playwright codegen http://localhost:5555/#/skills
# 手动：截图保存为 docs/evidence/webui-skills-page-load.png
```

---

## Smoke Test 2: Skills 列表展示 ✓

### 步骤
1. 在 Skills 页面
2. 查看列表区域

### 期望结果
- ✅ 看到至少一个 skill 卡片（example.hello）
- ✅ 卡片显示：
  - Skill 名称（Hello Skill）
  - Skill ID（example.hello）
  - 版本（0.1.0）
  - 状态徽章（imported_disabled）
  - 来源（local）
  - 风险等级（Pure）
  - 权限摘要（No special permissions）
  - View 按钮
  - Enable 按钮

### 验证截图
```bash
# 手动：截图保存为 docs/evidence/webui-skills-list.png
```

---

## Smoke Test 3: Import 弹窗 ✓

### 步骤
1. 点击 "Import Skill" 按钮
2. 查看弹窗内容

### 期望结果
- ✅ 弹窗打开
- ✅ 看到两个 Tab：Local 和 GitHub
- ✅ Local Tab 有输入框：Local Path
- ✅ GitHub Tab 有输入框：Owner, Repo, Ref (optional), Subdir (optional)
- ✅ 看到 "Import" 按钮和 "Cancel" 按钮

### 步骤（续）
3. 切换到 GitHub Tab
4. 查看输入框

### 期望结果
- ✅ GitHub Tab 正常显示
- ✅ 所有输入框可用

### 验证截图
```bash
# 手动：截图保存为 docs/evidence/webui-import-dialog.png
```

---

## Smoke Test 4: Enable 操作 + Admin Token 输入 ✓

### 步骤
1. 在 Skills 列表
2. 找到 imported_disabled 状态的 skill
3. 点击 "Enable" 按钮

### 期望结果
- ✅ 弹出 Admin Token 输入对话框
- ✅ 对话框显示：
  - 标题："Admin Token Required"
  - 输入框："Enter Admin Token"
  - 按钮："Submit" 和 "Cancel"

### 步骤（续）
4. 输入错误的 token（如 "wrong-token"）
5. 点击 "Submit"

### 期望结果
- ✅ 显示错误消息："Invalid or missing admin token" 或 "401 Unauthorized"

### 步骤（续）
6. 输入正确的 token（`$AGENTOS_ADMIN_TOKEN`）
7. 点击 "Submit"

### 期望结果
- ✅ 操作成功
- ✅ Skill 状态徽章变为 "enabled"
- ✅ 按钮变为 "Disable"
- ✅ 显示成功消息："Skill enabled successfully"

### 验证截图
```bash
# 手动：截图保存为 docs/evidence/webui-enable-token-prompt.png
# 手动：截图保存为 docs/evidence/webui-enable-success.png
```

---

## Smoke Test 5: Skill 详情页 ✓

### 步骤
1. 在 Skills 列表
2. 点击某个 skill 的 "View" 按钮

### 期望结果
- ✅ 进入详情页
- ✅ 看到：
  - Skill 名称和版本
  - 状态徽章
  - Overview 部分（Skill ID, Version, Source, Risk Class, Hash, Trust Level）
  - Permissions 部分（列出所有权限）
  - Limits 部分（Max Runtime, Max Tokens）
  - Full Manifest 部分（JSON 格式的完整 manifest）
  - Enable/Disable 按钮

### 验证截图
```bash
# 手动：截图保存为 docs/evidence/webui-skill-detail.png
```

---

## Smoke Test 6: Disable 操作 ✓

### 步骤
1. 在已 enabled 的 skill 详情页或列表页
2. 点击 "Disable" 按钮

### 期望结果
- ✅ 弹出 Admin Token 输入对话框
- ✅ 输入正确的 token
- ✅ 操作成功
- ✅ 状态徽章变为 "disabled"
- ✅ 按钮变为 "Enable"

### 验证截图
```bash
# 手动：截图保存为 docs/evidence/webui-disable-success.png
```

---

## Smoke Test 7: 状态过滤 ✓

### 步骤
1. 在 Skills 列表页
2. 使用状态过滤器
3. 选择 "Enabled"

### 期望结果
- ✅ 列表只显示 enabled 状态的 skills

### 步骤（续）
4. 选择 "Disabled"

### 期望结果
- ✅ 列表只显示 disabled 状态的 skills

### 步骤（续）
5. 选择 "Imported (Disabled)"

### 期望结果
- ✅ 列表只显示 imported_disabled 状态的 skills

---

## 自动化 Playwright 脚本（待实现）

```javascript
// tests/e2e/skills.spec.js
import { test, expect } from '@playwright/test';

test.describe('Skills Marketplace', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:5555/#/skills');
  });

  test('should load skills page', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Skills');
    await expect(page.locator('button:has-text("Import Skill")')).toBeVisible();
  });

  test('should display skill cards', async ({ page }) => {
    await expect(page.locator('.skill-card')).toHaveCount(1); // at least 1
    await expect(page.locator('.skill-card')).toContainText('example.hello');
  });

  test('should open import dialog', async ({ page }) => {
    await page.click('button:has-text("Import Skill")');
    await expect(page.locator('.modal')).toBeVisible();
    await expect(page.locator('.tab-btn')).toHaveCount(2); // Local and GitHub
  });

  test('should require admin token for enable', async ({ page }) => {
    await page.click('button:has-text("Enable"):first');
    await expect(page.locator('input[placeholder*="Admin Token"]')).toBeVisible();
  });

  test('should enable skill with valid token', async ({ page }) => {
    await page.click('button:has-text("Enable"):first');
    await page.fill('input[placeholder*="Admin Token"]', process.env.AGENTOS_ADMIN_TOKEN);
    await page.click('button:has-text("Submit")');
    await expect(page.locator('.badge-success')).toContainText('enabled');
  });
});
```

**运行命令**：
```bash
npx playwright test tests/e2e/skills.spec.js
```

---

## 验收标准

### 必须通过的 Smoke Tests

- [ ] Test 1: 页面加载
- [ ] Test 2: Skills 列表展示
- [ ] Test 3: Import 弹窗
- [ ] Test 4: Enable 操作 + Admin Token 输入
- [ ] Test 5: Skill 详情页
- [ ] Test 6: Disable 操作
- [ ] Test 7: 状态过滤

### 守门员裁决标准

**手动验证**（当前）：
- ✅ 完成上述 7 个 Smoke Tests
- ✅ 提供截图证据（至少 5 张）
- ✅ 记录测试时间和环境

**自动化验证**（推荐）：
- ✅ Playwright 脚本通过
- ✅ 测试覆盖所有关键路径
- ✅ 可在 CI 中复现

---

## 当前状态

**实现状态**: ✅ WebUI 代码已实现  
**测试状态**: ⚠️ 待部署后手动验证  
**自动化**: ⚠️ Playwright 脚本待实现

---

## 执行验证

```bash
# 1. 安装依赖
pip install itsdangerous

# 2. 设置环境
export AGENTOS_ADMIN_TOKEN="your-secure-token"

# 3. 导入测试数据
agentos skill import tests/fixtures/skills/hello_skill

# 4. 启动 server
python3 -m agentos.webui.app

# 5. 打开浏览器，执行上述 7 个 Smoke Tests

# 6. 截图并保存到 docs/evidence/

# 7. 更新此清单，标记完成的测试

# 8. (可选) 实现 Playwright 脚本并运行
```

---

**验收负责人**: 待指定  
**验收日期**: 待部署后  
**状态**: ⚠️ PENDING DEPLOYMENT VERIFICATION
