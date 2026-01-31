# 发布检查清单

> 快速参考版本。详细流程请查看 [RELEASE_WORKFLOW.md](./RELEASE_WORKFLOW.md)

---

## 🔍 操作前必检（每次都要做）

### ✅ 确认当前仓库

```bash
# 运行以下命令，确认你在正确的仓库
pwd && git remote -v | head -2 && git branch --show-current
```

**预期输出 - 开发目录（master 分支）**:
```
/Users/pangge/PycharmProjects/AgentOS
origin  git@github.com:seacow-technology/agentos.git (fetch)
master
```

**预期输出 - 发布目录（main 分支）**:
```
/Users/pangge/PycharmProjects/AgentOS/publish
origin  git@github.com:seacow-technology/agentos.git (fetch)
main (或 release/update-*)
```

---

## 📋 完整流程检查清单

### Phase 1: 开发目录 (master 分支) ✅
- [ ] `cd /Users/pangge/PycharmProjects/AgentOS`
- [ ] `pwd && git branch --show-current` → 确认在开发目录 master 分支
- [ ] `git checkout master`
- [ ] `git add <files>` → 暂存改动
- [ ] `git commit -m "..."` → 提交
- [ ] `git push origin master` → 推送

### Phase 2: 导出 ✅
- [ ] `pwd` → 确认在 `/Users/pangge/PycharmProjects/AgentOS`
- [ ] `./scripts/publish/export.sh` → 运行导出
- [ ] 检查输出无错误和警告

### Phase 3: 创建PR ✅
- [ ] `./scripts/publish/push.sh "标题\n\n- 改动1\n- 改动2"` → 创建PR
- [ ] 记录PR URL

### Phase 4: 合并PR ✅
- [ ] `cd publish` → 切换到发布目录
- [ ] `pwd && git branch --show-current` → 确认在 publish 目录
- [ ] `gh pr checks <PR_NUMBER>` → 检查CI
- [ ] 等待CI通过（JavaScript + Python）
- [ ] `gh pr merge <PR_NUMBER> --merge --delete-branch` → 合并

### Phase 5: 验证 ✅
- [ ] `git checkout main`
- [ ] `git pull origin main`
- [ ] `git log --oneline -5` → 查看commit历史
- [ ] 验证关键文件存在

---

## ⚠️ 仓库速查表

| 项目 | 开发目录 | 发布目录 |
|------|---------|---------|
| **仓库名** | agentos | agentos |
| **URL** | `git@github.com:seacow-technology/agentos.git` | `git@github.com:seacow-technology/agentos.git` |
| **分支** | master | main |
| **路径** | `/Users/pangge/PycharmProjects/AgentOS` | `/Users/pangge/PycharmProjects/AgentOS/publish` |
| **推送** | 直接push | 必须通过PR |
| **说明** | 包含所有代码和工具 | 只包含MANIFEST中的文件 |

---

## 🚨 紧急恢复

如果推送到错误的仓库：

```bash
# 1. 确认当前位置
pwd && git remote -v

# 2. 撤销最后一次commit（未push）
git reset --soft HEAD~1

# 3. 撤销最后一次push（已push到远程）
git revert HEAD
git push origin <branch-name>
```

---

## 📞 求助

遇到问题？按顺序检查：
1. ✅ 确认当前仓库（`pwd && git remote -v`）
2. 📖 查看 [RELEASE_WORKFLOW.md](./RELEASE_WORKFLOW.md) 的"常见错误"章节
3. 🔍 搜索错误消息
4. 💬 联系团队

---

**最后更新**: 2026-01-29
