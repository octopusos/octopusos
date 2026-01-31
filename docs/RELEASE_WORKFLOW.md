# AgentOS 发布工作流程

> **重要**: 本文档定义了私有仓库与公共仓库之间的标准发布流程。必须严格遵守，避免仓库混淆。

---

## 📁 仓库架构

### 双仓库模式
- **架构说明**: 使用两个独立的 GitHub 仓库，分别用于开发和公开发布

### 私有仓库（主开发仓库）
- **名称**: `agentos-origin`
- **URL**: `git@github.com:seacow-technology/agentos-origin.git`
- **分支**: `master`
- **用途**: 主要开发仓库，包含所有功能和内部代码
- **本地路径**: `/Users/pangge/PycharmProjects/AgentOS`
- **特点**:
  - 私有仓库，不对外公开
  - 可以直接 push
  - 包含完整代码和内部工具

### 公共仓库（发布仓库）
- **名称**: `agentos`
- **URL**: `git@github.com:seacow-technology/agentos.git`
- **分支**: `main`
- **用途**: 公开发布仓库，通过MANIFEST过滤内容
- **本地路径**: `/Users/pangge/PycharmProjects/AgentOS/publish`
- **特点**:
  - 公开仓库，任何人可访问
  - 独立的git工作区（位于publish/目录）
  - 受分支保护策略保护
  - 不允许直接push到main，必须通过PR
  - 只包含MANIFEST中列出的文件

---

## ⚠️ 工作目录验证（关键步骤）

**在执行任何git操作前，必须先验证当前仓库：**

```bash
# 方法1: 检查远程URL
git remote -v

# 预期输出 - 私有仓库:
# origin  git@github.com:seacow-technology/agentos-origin.git (fetch)
# origin  git@github.com:seacow-technology/agentos-origin.git (push)

# 预期输出 - 公共仓库:
# origin  git@github.com:seacow-technology/agentos.git (fetch)
# origin  git@github.com:seacow-technology/agentos.git (push)

# 方法2: 检查当前路径和分支
pwd && git branch --show-current

# 预期输出 - 私有仓库:
# /Users/pangge/PycharmProjects/AgentOS
# master

# 预期输出 - 公共仓库:
# /Users/pangge/PycharmProjects/AgentOS/publish
# main (或 release/update-*)
```

---

## 🔄 标准发布流程

### Phase 1: 私有仓库开发与提交

#### 1.1 确认在开发目录（master 分支）
```bash
cd /Users/pangge/PycharmProjects/AgentOS
pwd                                    # 必须是主目录，不是 publish/
git branch --show-current              # 应该在 master 或功能分支
```

#### 1.2 开发与提交代码
```bash
# 查看改动
git status

# 提交改动
git add <files>
git commit -m "feat: 描述改动

详细说明...

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

#### 1.3 合并分支到master（如有功能分支）
```bash
# 切换到master
git checkout master

# 合并功能分支
git merge <feature-branch> --no-ff -m "Merge branch '<feature-branch>' into master

描述合并内容...

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

#### 1.4 推送到私有远程
```bash
# 确认在master分支
git branch --show-current  # 必须是 master

# 推送
git push origin master
```

---

### Phase 2: 打包验证与版本标记

#### 2.1 运行打包验证
```bash
# 确认在私有仓库根目录
pwd  # 应该是 /Users/pangge/PycharmProjects/AgentOS

# 运行打包验证（会构建sdist和wheel并验证内容）
./scripts/verify_packaging.sh
```

**打包验证做什么？**
- 清理旧构建产物
- 构建sdist和wheel
- 验证sdist内容（关键目录和静态资源）
- **验证wheel内容（最关键）** - 确保静态资源被包含
- 在干净环境中测试安装
- 验证所有关键模块可导入

**必须通过的检查：**
- ✅ sdist 包含所有MANIFEST文件
- ✅ wheel 包含静态资源（.css/.js/.html等）
- ✅ wheel 包含模板文件
- ✅ wheel 包含配置文件（.yaml/.json）
- ✅ 干净环境安装成功
- ✅ 所有关键目录存在

#### 2.2 标记版本（私有仓库）
```bash
# 从pyproject.toml提取版本号
VERSION=$(grep "^version" pyproject.toml | sed 's/version = "\(.*\)"/\1/')
echo "Version: ${VERSION}"

# 创建带注释的tag
git tag -a "v${VERSION}" -m "Release version ${VERSION}

$(git log -1 --pretty=%B)

🤖 Tagged by AgentOS Release Pipeline"

# 推送tag到私有仓库
git push origin "v${VERSION}"
```

**为什么要标记？**
- 在私有仓库中标记发布点
- 便于回溯和审计
- 与公共仓库发布对应

#### 2.3 生成Release Notes
```bash
# 从模板生成Release Notes
./scripts/publish/create_release_notes.sh "${VERSION}"

# 编辑生成的文件，填写[TODO]部分
vim RELEASE_NOTES.md
```

**Release Notes包含什么？**
- 版本号和发布类型
- 功能亮点（Highlights）
- 新功能列表
- Bug修复列表
- 打包验证证据
- 升级指南

---

### Phase 3: 导出到公共仓库

#### 3.1 运行导出脚本
```bash
# 确认在私有仓库根目录
pwd  # 应该是 /Users/pangge/PycharmProjects/AgentOS

# 运行导出脚本（会自动复制MANIFEST中的文件到publish/）
./scripts/publish/export.sh
```

**导出脚本做什么？**
- 清理publish/目录（保留.git）
- 根据MANIFEST.txt复制允许的文件
- 生成.env.example和run.sh
- 移除敏感文件（.env, *.key等）
- 扫描secrets（使用ripgrep）
- 验证目录结构

#### 3.2 验证导出结果
```bash
# 进入publish目录
cd publish

# 验证分支（应该是 main）
git branch --show-current  # 应该显示 main

# 查看改动
git status --short | head -20

# 验证关键文件
ls -lh agentos/webui/static/vendor/  # 检查vendor
ls -la agentos/store/migrations/     # 检查migrations
```

---

### Phase 4: 创建Pull Request

#### 3.1 确认在发布目录（main 分支）
```bash
# 必须在publish目录
pwd  # 应该是 /Users/pangge/PycharmProjects/AgentOS/publish

# 验证分支
git branch --show-current  # 应该是 main 或即将切换到 main
```

#### 3.2 使用脚本创建PR
```bash
# 在私有仓库根目录执行
cd /Users/pangge/PycharmProjects/AgentOS

# 创建PR（脚本会自动切换到publish目录）
./scripts/publish/push.sh "PR标题

- 改动说明1
- 改动说明2
- 改动说明3"
```

**push.sh脚本做什么？**
1. 检查publish/.git存在
2. 检查gh CLI已安装且已认证
3. 从main分支创建新的feature分支 `release/update-YYYYMMDD-HHMMSS`
4. 暂存所有改动
5. 创建commit
6. 推送到远程
7. 使用gh CLI创建PR

#### 3.3 记录PR URL
脚本执行成功后会输出PR URL：
```
✅ PR URL: https://github.com/seacow-technology/agentos/pull/X
```

---

### Phase 5: 审查与合并PR

#### 4.1 查看PR状态
```bash
# 在publish目录
cd /Users/pangge/PycharmProjects/AgentOS/publish

# 查看PR列表
gh pr list

# 查看特定PR
gh pr view <PR_NUMBER>

# 查看CI检查状态
gh pr checks <PR_NUMBER>
```

#### 4.2 等待CI通过
CI检查包括：
- CodeQL Analysis (JavaScript/TypeScript)
- CodeQL Analysis (Python)

**等待CI完成的命令：**
```bash
# 持续检查CI状态
watch -n 10 "gh pr checks <PR_NUMBER>"

# 或手动检查
gh pr checks <PR_NUMBER>
```

#### 4.3 合并PR
```bash
# 方法1: 自动合并（CI通过后自动merge）
gh pr merge <PR_NUMBER> --auto --squash --delete-branch

# 方法2: 手动合并（立即merge）
gh pr merge <PR_NUMBER> --merge --delete-branch

# 方法3: 通过Web界面
# 访问 PR URL，点击 "Merge pull request"
```

---

### Phase 6: 验证发布与PyPI发布（可选）

#### 5.1 更新本地公共仓库
```bash
# 确认在publish目录
cd /Users/pangge/PycharmProjects/AgentOS/publish

# 切换到main分支
git checkout main

# 拉取最新改动
git pull origin main
```

#### 6.2 验证改动已发布
```bash
# 查看最新commit
git log --oneline -5

# 验证关键文件
ls -lh agentos/webui/static/vendor/        # vendor应该存在
find agentos/webui/static/vendor/ -type f | wc -l  # 应该有文件
du -sh agentos/webui/static/vendor/        # 检查大小

# 验证数据库迁移
ls -la agentos/store/migrations/            # 应该存在迁移文件
```

#### 6.3 发布到PyPI（可选）
```bash
# 安装twine（如果还没有）
pip install twine

# 先发布到TestPyPI测试
python3 -m twine upload --repository testpypi dist/*

# 测试安装
pip install -i https://test.pypi.org/simple/ agentos

# 测试通过后，发布到正式PyPI
python3 -m twine upload dist/*
```

#### 6.4 创建GitHub Release（可选）
```bash
# 在publish目录
cd publish

# 使用gh CLI创建Release
gh release create v${VERSION} \
  --title "AgentOS v${VERSION}" \
  --notes-file ../RELEASE_NOTES.md \
  dist/*.whl dist/*.tar.gz
```

---

## 📋 发布检查清单

### 准备阶段
- [ ] 所有功能开发完成并测试通过
- [ ] 在私有仓库master分支
- [ ] 所有改动已提交并推送到远程
- [ ] 检查MANIFEST.txt是否包含需要发布的目录
- [ ] pyproject.toml中版本号已更新

### 打包验证阶段（新增）
- [ ] 运行`./scripts/verify_packaging.sh`成功
- [ ] sdist验证通过
- [ ] **wheel验证通过（最关键）**
- [ ] wheel包含静态资源（173+文件）
- [ ] wheel包含模板文件
- [ ] 干净环境安装测试通过

### 版本标记阶段（新增）
- [ ] 从pyproject.toml提取版本号
- [ ] 创建annotated tag `v${VERSION}`
- [ ] 推送tag到私有仓库
- [ ] 生成Release Notes
- [ ] 编辑Release Notes填写[TODO]部分

### 导出阶段
- [ ] 运行`./scripts/publish/export.sh`成功
- [ ] 无secrets检测警告
- [ ] publish/目录结构正确
- [ ] vendor文件完整（如有）

### PR阶段
- [ ] 确认在publish目录（公共仓库）
- [ ] 运行`./scripts/publish/push.sh`成功
- [ ] PR已创建并记录URL
- [ ] PR描述清晰完整

### 合并阶段
- [ ] CI检查全部通过
- [ ] 代码审查完成（如需要）
- [ ] PR已成功合并
- [ ] Feature分支已删除

### 验证阶段
- [ ] 本地main分支已更新
- [ ] 关键文件存在且完整
- [ ] commit历史正确
- [ ] 远程仓库状态正确

### 发布阶段（可选）
- [ ] 发布到TestPyPI测试
- [ ] 从TestPyPI安装测试通过
- [ ] 发布到正式PyPI
- [ ] 创建GitHub Release
- [ ] Release Notes已附加到GitHub Release

---

## 🚨 常见错误与解决

### 错误1: 在错误的分支执行操作
**症状**: git push失败或推送到错误的分支

**解决**:
```bash
# 检查当前分支
pwd && git branch --show-current

# 如果在错误的目录，切换到正确位置
cd /Users/pangge/PycharmProjects/AgentOS         # 开发分支 (master)
cd /Users/pangge/PycharmProjects/AgentOS/publish # 发布分支 (main)
```

### 错误2: 尝试直接push到main分支
**症状**: `protected branch` 错误

**解决**: main分支受保护，必须通过PR。使用：
```bash
./scripts/publish/push.sh "PR标题"
```

### 错误3: publish/目录不是独立git仓库
**症状**: `publish/.git not found`

**解决**: 初始化publish为独立仓库：
```bash
cd publish
git init
git branch -M main
git remote add origin git@github.com:seacow-technology/agentos.git
```

### 错误4: gh CLI未认证
**症状**: `GitHub CLI not authenticated`

**解决**:
```bash
gh auth login
# 选择 GitHub.com
# 选择 SSH
# 按提示完成认证
```

### 错误5: 导出的文件缺失
**症状**: publish/目录缺少某些文件

**解决**: 检查并更新MANIFEST.txt：
```bash
# 编辑MANIFEST
vim scripts/publish/MANIFEST.txt

# 添加需要发布的目录或文件
# 例如: agentos/webui/

# 重新导出
./scripts/publish/export.sh
```

### 错误6: vendor文件未包含在PR中
**症状**: PR中缺少vendor目录

**原因**: vendor目录可能未被git追踪

**解决**:
```bash
# 在开发目录（master分支）检查vendor状态
cd /Users/pangge/PycharmProjects/AgentOS
git status agentos/webui/static/vendor/

# 如果是untracked，添加并提交
git add agentos/webui/static/vendor/
git commit -m "feat(webui): add vendor directory with CDN resources"
git push origin master

# 重新导出
./scripts/publish/export.sh
```

---

## 🔧 关键工具与依赖

### 必需工具
1. **Git** - 版本控制
2. **GitHub CLI (gh)** - 创建PR
   ```bash
   brew install gh
   gh auth login
   ```
3. **ripgrep (rg)** - 密码扫描
   ```bash
   brew install ripgrep
   ```

### 验证工具安装
```bash
# 检查所有必需工具
command -v git && echo "✓ Git installed"
command -v gh && echo "✓ GitHub CLI installed"
command -v rg && echo "✓ ripgrep installed"

# 检查gh认证状态
gh auth status
```

---

## 📝 发布脚本参考

### scripts/publish/export.sh
**功能**: 将私有仓库内容按MANIFEST过滤导出到publish/

**关键步骤**:
1. 清理publish/（保留.git）
2. 按MANIFEST.txt复制文件
3. 添加公共仓库声明到README
4. 生成.env.example
5. 生成run.sh
6. 移除敏感文件
7. 扫描secrets
8. 验证目录结构

### scripts/publish/push.sh
**功能**: 创建PR到公共仓库

**关键步骤**:
1. 预检查（publish/.git、gh CLI）
2. 检查是否有改动
3. 创建feature分支 `release/update-YYYYMMDD-HHMMSS`
4. 暂存并提交改动
5. 推送到远程
6. 使用gh CLI创建PR

### scripts/publish/MANIFEST.txt
**功能**: 定义哪些文件/目录可以发布到公共仓库

**示例**:
```
# 核心模块
agentos/__init__.py
agentos/cli/
agentos/webui/
agentos/core/
agentos/store/

# 文档
README.md
LICENSE
SECURITY.md
```

---

## 🎯 最佳实践

### 1. 提交消息规范
使用Conventional Commits格式：
```
<type>(<scope>): <subject>

<body>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

类型：
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建/工具

### 2. PR标题规范
```
<type>(<scope>): <subject>

- 改动点1
- 改动点2
- 改动点3
```

### 3. 分支命名规范
- 功能分支: `feat/<feature-name>`
- 修复分支: `fix/<bug-name>`
- 发布分支: `release/update-YYYYMMDD-HHMMSS`（自动生成）

### 4. 发布频率建议
- **热修复**: 立即发布
- **功能更新**: 每周或每两周
- **大版本**: 按规划发布

### 5. 回滚策略
如果发布出现问题：
```bash
# 在发布目录（main分支）
cd /Users/pangge/PycharmProjects/AgentOS/publish
git checkout main
git revert <commit-hash>
gh pr create --title "revert: 回滚 <原PR标题>" --body "原因..."
```

---

## 📊 发布流程图

```
┌─────────────────────────────────────────────────────────┐
│          开发目录 (本地 master 分支)                      │
│         /Users/pangge/PycharmProjects/AgentOS            │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ 1. 开发、提交、合并
                     │
                     ▼
            ┌────────────────────┐
            │   git push origin  │
            │       master       │
            └────────┬───────────┘
                     │
                     │ 2. 运行导出脚本
                     │
                     ▼
       ┌──────────────────────────────────┐
       │  ./scripts/publish/export.sh     │
       │  (复制MANIFEST文件到publish/)     │
       └──────────┬───────────────────────┘
                  │
                  │ 3. 创建PR
                  │
                  ▼
     ┌────────────────────────────────────┐
     │  ./scripts/publish/push.sh         │
     │  (创建feature分支并创建PR)         │
     └──────────┬─────────────────────────┘
                │
                │ 4. 推送并创建PR
                │
                ▼
┌───────────────────────────────────────────────────┐
│    远程仓库 main 分支 (受分支保护)                   │
│    git@github.com:seacow-technology/agentos.git   │
│                                                   │
│   ┌──────────────────────────────────┐          │
│   │  PR #X: release/update-*         │          │
│   │  - 等待CI检查                     │          │
│   │  - 代码审查（可选）               │          │
│   └──────────┬───────────────────────┘          │
│              │                                   │
│              │ 5. 合并PR                         │
│              │                                   │
│              ▼                                   │
│   ┌──────────────────────────────────┐          │
│   │     main branch (已发布)          │          │
│   └──────────────────────────────────┘          │
└───────────────────────────────────────────────────┘
                │
                │ 6. 验证
                │
                ▼
       ┌─────────────────┐
       │   git pull      │
       │   验证改动       │
       └─────────────────┘
```

---

## ⚡ 快速参考命令

### 使用自动化脚本（推荐）
```bash
# 一键完成整个发布流程
cd /Users/pangge/PycharmProjects/AgentOS
./scripts/publish/release.sh "feat: 版本标题

- 改动1
- 改动2
- 改动3"

# 脚本会自动完成：
# - 验证仓库状态
# - 提取版本号
# - 运行打包验证
# - 创建并推送版本tag
# - 生成Release Notes
# - 导出到publish/
# - 创建PR到公共仓库
```

### 手动发布流程（复制粘贴版）
```bash
# ===== 1. 在开发目录（master分支）提交改动 =====
cd /Users/pangge/PycharmProjects/AgentOS
pwd && git branch --show-current  # 验证目录和分支
git status
git add <files>
git commit -m "feat: 描述

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
git push origin master

# ===== 2. 运行打包验证 =====
./scripts/verify_packaging.sh

# ===== 3. 标记版本并推送tag =====
VERSION=$(grep "^version" pyproject.toml | sed 's/version = "\(.*\)"/\1/')
echo "Version: ${VERSION}"
git tag -a "v${VERSION}" -m "Release version ${VERSION}"
git push origin "v${VERSION}"

# ===== 4. 生成Release Notes =====
./scripts/publish/create_release_notes.sh "${VERSION}"
vim RELEASE_NOTES.md  # 编辑填写[TODO]部分

# ===== 5. 导出到发布目录 =====
./scripts/publish/export.sh

# ===== 6. 创建PR =====
./scripts/publish/push.sh "feat: v${VERSION}

- 改动1
- 改动2"

# ===== 7. 等待并合并PR（在publish目录）=====
cd publish
gh pr list
gh pr checks <PR_NUMBER>
gh pr merge <PR_NUMBER> --merge --delete-branch

# ===== 8. 验证发布 =====
git checkout main
git pull origin main
git log --oneline -5

# ===== 9. 发布到PyPI（可选）=====
python3 -m twine upload --repository testpypi dist/*  # 测试
python3 -m twine upload dist/*                        # 正式

# ===== 10. 创建GitHub Release（可选）=====
gh release create v${VERSION} \
  --title "AgentOS v${VERSION}" \
  --notes-file ../RELEASE_NOTES.md \
  dist/*.whl dist/*.tar.gz
```

---

## 📖 相关文档

- [MANIFEST.txt](../scripts/publish/MANIFEST.txt) - 发布文件清单
- [export.sh](../scripts/publish/export.sh) - 导出脚本
- [push.sh](../scripts/publish/push.sh) - PR创建脚本
- [README.md](../scripts/publish/README.md) - 发布脚本说明
- [CONTRIBUTING.md](../CONTRIBUTING.md) - 贡献指南

---

## 📞 支持

如有问题，请查看：
1. 本文档的"常见错误与解决"章节
2. GitHub Issues: https://github.com/seacow-technology/agentos/issues
3. 内部文档: [Notion发布手册]

---

**文档版本**: v2.0
**最后更新**: 2026-01-31
**维护者**: AgentOS Team
**重大更新**: 添加打包验证、版本标记、Release Notes 生成流程

**注意**: 本文档是关键发布流程文档，任何修改都必须经过团队审查。
