# P1-A UI Manual Testing Guide
## Cognitive Completeness Layer - 前端验证手册

---

## 测试目的

虽然后端和 API 已经 100% 通过自动化测试，但前端 UI 组件需要人工验证以确保：
1. Dashboard 卡片正确渲染
2. Coverage Badge 在 Explain Drawer 中正确显示
3. Blind Spot Warning 在适当时机显示
4. 用户交互流畅且直观

---

## 前置条件

### 1. 启动 WebUI
```bash
# 方法 1: 使用 uvicorn (推荐)
python3 -m uvicorn agentos.webui.app:app --host 127.0.0.1 --port 9090 --log-level warning

# 方法 2: 如果已有进程在运行
ps aux | grep uvicorn | grep 9090
# 如果没有，执行方法 1
```

### 2. 验证 BrainOS 索引存在
```bash
ls -la .brainos/v0.1_mvp.db
# 应该显示: -rw-r--r-- ~30MB
```

### 3. 打开浏览器
```
访问: http://localhost:9090
或: http://127.0.0.1:9090
```

---

## 测试清单

### ✅ Test 1: BrainOS Dashboard (Overview)

**步骤**:
1. 点击左侧导航栏 "Brain" 或访问 `http://localhost:9090/#/brain`
2. 等待页面加载（应该 <1 秒）

**预期结果**:
- [ ] 页面标题显示 "BrainOS Dashboard"
- [ ] 看到 2 个主要卡片：
  - Cognitive Coverage Card (左侧)
  - Top Blind Spots Card (右侧)

**截图**: 保存为 `P1_A_UI_Test_1_Dashboard.png`

---

### ✅ Test 2: Cognitive Coverage Card

**位置**: Dashboard 左侧卡片

**检查项**:
- [ ] 卡片标题: "Cognitive Coverage"
- [ ] 副标题: "How much does BrainOS know about your codebase?"
- [ ] 显示 3 个进度条：
  - [ ] **Code Coverage**: ~71.9% (绿色条)
    - 标签: "Code Coverage"
    - 数值: "71.9%"
    - 说明: "2258 / 3140 files covered"
  - [ ] **Doc Coverage**: ~68.2% (黄色条)
    - 标签: "Doc Coverage"
    - 数值: "68.2%"
    - 说明: "2143 / 3140 files documented"
  - [ ] **Dependency Coverage**: ~6.8% (红色条)
    - 标签: "Dependency Coverage"
    - 数值: "6.8%"
    - 说明: "213 / 3140 files in dep graph"

**颜色验证**:
- [ ] 绿色: ≥70% (Code Coverage)
- [ ] 黄色: 50-69% (Doc Coverage)
- [ ] 红色: <50% (Dependency Coverage)

**交互**:
- [ ] 鼠标悬停在进度条上，应该显示 tooltip（可选功能）

**截图**: 保存为 `P1_A_UI_Test_2_Coverage_Card.png`

---

### ✅ Test 3: Top Blind Spots Card

**位置**: Dashboard 右侧卡片

**检查项**:
- [ ] 卡片标题: "Top Blind Spots"
- [ ] 副标题: "Critical areas where BrainOS lacks understanding"
- [ ] 显示严重程度统计：
  - [ ] "High: 14" (红色徽章)
  - [ ] "Medium: 1" (黄色徽章)
  - [ ] "Low: 2" (蓝色徽章)

**盲区列表**:
- [ ] 显示 Top 5 盲区（或所有盲区如果 <5 个）
- [ ] 每个盲区条目显示：
  - [ ] 严重程度图标（🔴 高 / 🟡 中 / 🔵 低）
  - [ ] 实体名称（如 "governance"）
  - [ ] 盲区类型（如 "Capability No Implementation"）
  - [ ] 原因描述（如 "Declared capability with no implementation files"）

**示例盲区**:
1. 🔴 **governance** (Capability No Implementation)
   - "Declared capability with no implementation files"
2. 🔴 **execution gate** (Capability No Implementation)
   - "Declared capability with no implementation files"
3. 🔴 **planning guard** (Capability No Implementation)
   - "Declared capability with no implementation files"

**空数据测试** (如果数据库为空):
- [ ] 显示: "No blind spots detected! 🎉"

**截图**: 保存为 `P1_A_UI_Test_3_Blind_Spots_Card.png`

---

### ✅ Test 4: Explain Drawer - Coverage Badge (Why Query)

**步骤**:
1. 访问 Tasks 视图: `http://localhost:9090/#/tasks`
2. 找到任意一个任务（或创建一个测试任务）
3. 点击任务卡片右上角的 🧠 按钮（"Explain" 按钮）
4. 确保 "Why" 标签页是激活状态

**预期结果**:
- [ ] Explain Drawer 从右侧滑出
- [ ] 顶部显示 "Why Query" 标题
- [ ] 看到 **Coverage Badge** 组件（在查询结果上方）：
  - [ ] 标签显示: "Coverage:"
  - [ ] 证据来源标签（如 [Git] [Doc] 或 [Git] [Doc] [Code]）
  - [ ] 颜色编码:
    - 绿色: 3/3 证据来源
    - 黄色: 2/3 证据来源
    - 红色: 1/3 证据来源
  - [ ] 解释文本（如 "Based on Git + Doc. Missing: Code."）

**测试用例**:
- **Full Coverage** (如果存在):
  - 标签: [Git] [Doc] [Code] (绿色)
  - 文本: "This explanation is based on all sources (Git + Doc + Code)."
- **Partial Coverage**:
  - 标签: [Git] [Doc] (黄色)
  - 文本: "This explanation is based on git/doc. Missing: code."
- **Limited Coverage**:
  - 标签: [Git] (红色)
  - 文本: "This explanation is based only on git. Limited coverage."

**截图**: 保存为 `P1_A_UI_Test_4_Coverage_Badge_Why.png`

---

### ✅ Test 5: Explain Drawer - Coverage Badge (Impact Query)

**步骤**:
1. 在已打开的 Explain Drawer 中，点击 "Impact" 标签页
2. 等待查询完成

**预期结果**:
- [ ] "Impact Query" 标签激活
- [ ] Coverage Badge 显示（与 Why Query 相同格式）
- [ ] 证据来源标签和颜色正确

**截图**: 保存为 `P1_A_UI_Test_5_Coverage_Badge_Impact.png`

---

### ✅ Test 6: Explain Drawer - Coverage Badge (Trace Query)

**步骤**:
1. 点击 "Trace" 标签页

**预期结果**:
- [ ] "Trace Query" 标签激活
- [ ] Coverage Badge 显示

**截图**: 保存为 `P1_A_UI_Test_6_Coverage_Badge_Trace.png`

---

### ✅ Test 7: Explain Drawer - Coverage Badge (Map Query)

**步骤**:
1. 点击 "Map" 标签页（或 "Subgraph" 标签页，取决于实现）

**预期结果**:
- [ ] "Map Query" 标签激活
- [ ] Coverage Badge 显示

**截图**: 保存为 `P1_A_UI_Test_7_Coverage_Badge_Map.png`

---

### ✅ Test 8: Blind Spot Warning (High Severity)

**步骤**:
1. 访问 Extensions 视图: `http://localhost:9090/#/extensions`
2. 找到 "governance" 能力（这是一个已知的盲区）
3. 点击 🧠 按钮打开 Explain Drawer
4. 选择任意查询类型（Why/Impact/Trace/Map）

**预期结果**:
- [ ] 在查询结果区域看到 **Blind Spot Warning** 横幅（红色背景）：
  - [ ] 标题: "⚠️ Cognitive Blind Spot: High Severity"
  - [ ] 盲区类型: "Capability No Implementation"
  - [ ] 原因: "Declared capability with no implementation files"
  - [ ] 建议: "Add implementation file or remove orphaned capability"
  - [ ] 严重程度: "Severity: 0.8 (High)"

**截图**: 保存为 `P1_A_UI_Test_8_Blind_Spot_Warning_High.png`

---

### ✅ Test 9: Blind Spot Warning (Medium/Low Severity)

**步骤**:
1. 查找一个中等或低严重度的盲区（如果存在）
2. 点击该实体的 🧠 按钮

**预期结果**:
- [ ] Blind Spot Warning 显示，但颜色不同：
  - 中等: 黄色背景
  - 低: 蓝色背景

**截图**: 保存为 `P1_A_UI_Test_9_Blind_Spot_Warning_Medium_Low.png` (如果适用)

---

### ✅ Test 10: 无盲区实体 (Normal Entity)

**步骤**:
1. 找到一个不是盲区的实体（如一个正常的 Python 文件）
2. 点击 🧠 按钮打开 Explain Drawer

**预期结果**:
- [ ] **不显示** Blind Spot Warning
- [ ] 只显示 Coverage Badge
- [ ] 查询结果正常显示

**截图**: 保存为 `P1_A_UI_Test_10_Normal_Entity.png`

---

## 性能测试

### ✅ Test 11: Dashboard 加载性能

**步骤**:
1. 打开浏览器开发者工具 (F12)
2. 切换到 Network 标签
3. 刷新 BrainOS Dashboard 页面
4. 记录以下指标：

**预期性能**:
- [ ] Dashboard 页面加载: <500ms
- [ ] `/api/brain/coverage` API 调用: <200ms
- [ ] `/api/brain/blind-spots` API 调用: <100ms
- [ ] 总渲染时间 (DOMContentLoaded): <1000ms

**记录结果**:
```
Dashboard Load Time: ______ ms
/api/brain/coverage: ______ ms
/api/brain/blind-spots: ______ ms
DOMContentLoaded: ______ ms
```

---

### ✅ Test 12: Explain Drawer 查询性能

**步骤**:
1. 打开 Explain Drawer (任意实体)
2. 记录每个查询类型的响应时间

**预期性能**:
- [ ] Why Query: <1000ms
- [ ] Impact Query: <1000ms
- [ ] Trace Query: <1000ms
- [ ] Map Query: <1000ms

**记录结果**:
```
Why Query: ______ ms
Impact Query: ______ ms
Trace Query: ______ ms
Map Query: ______ ms
```

---

## 响应式设计测试

### ✅ Test 13: 移动端适配 (可选)

**步骤**:
1. 打开浏览器开发者工具 (F12)
2. 切换到设备模拟模式（Device Toolbar）
3. 选择移动设备（如 iPhone 12）
4. 访问 BrainOS Dashboard

**预期结果**:
- [ ] Dashboard 卡片在移动端正确堆叠（上下排列）
- [ ] 进度条在小屏幕上正常显示
- [ ] Explain Drawer 占据全屏或大部分屏幕

**截图**: 保存为 `P1_A_UI_Test_13_Mobile_Responsive.png`

---

## 错误场景测试

### ✅ Test 14: 数据库不存在 (Error Handling)

**步骤**:
1. 临时重命名数据库文件:
   ```bash
   mv .brainos/v0.1_mvp.db .brainos/v0.1_mvp.db.bak
   ```
2. 刷新 BrainOS Dashboard

**预期结果**:
- [ ] 显示友好的错误消息（而不是崩溃）
- [ ] 提示用户: "BrainOS index not found. Build index first."
- [ ] Coverage Card 显示空状态
- [ ] Blind Spots Card 显示空状态

**恢复**:
```bash
mv .brainos/v0.1_mvp.db.bak .brainos/v0.1_mvp.db
```

**截图**: 保存为 `P1_A_UI_Test_14_Error_Handling.png`

---

### ✅ Test 15: 空数据库 (Empty State)

**步骤**:
1. 创建一个空的数据库（或使用测试数据库）
2. 刷新 Dashboard

**预期结果**:
- [ ] Coverage Card 显示: "0 / 0 files covered"
- [ ] Blind Spots Card 显示: "No blind spots detected! 🎉"

**截图**: 保存为 `P1_A_UI_Test_15_Empty_State.png`

---

## 用户体验测试

### ✅ Test 16: 颜色编码直观性

**检查项**:
- [ ] 绿色用于高覆盖率 (≥70%)
- [ ] 黄色用于中等覆盖率 (50-69%)
- [ ] 红色用于低覆盖率 (<50%)
- [ ] 高严重度盲区用红色图标 🔴
- [ ] 中等严重度用黄色图标 🟡
- [ ] 低严重度用蓝色图标 🔵

**主观评价**:
- [ ] 颜色对比度足够（易于区分）
- [ ] 颜色语义清晰（直观理解）

---

### ✅ Test 17: 文本可读性

**检查项**:
- [ ] 所有文本清晰可读（字体大小合适）
- [ ] 专业术语有解释（或易于理解）
- [ ] 错误消息友好（非技术用户可理解）

**主观评价**:
- [ ] Dashboard 文案简洁明了
- [ ] Coverage Badge 解释清晰
- [ ] Blind Spot Warning 建议可操作

---

### ✅ Test 18: 交互流畅性

**检查项**:
- [ ] 页面切换流畅（无明显卡顿）
- [ ] Explain Drawer 滑出/收起动画流畅
- [ ] 按钮点击响应及时（<100ms）
- [ ] 加载状态有反馈（Spinner/Progress Bar）

**主观评价**:
- [ ] 整体交互感觉流畅
- [ ] 无明显 Bug 或异常

---

## 测试结果汇总

### 功能测试
```
Test 1:  Dashboard Overview              [ ] PASS [ ] FAIL
Test 2:  Cognitive Coverage Card         [ ] PASS [ ] FAIL
Test 3:  Top Blind Spots Card            [ ] PASS [ ] FAIL
Test 4:  Coverage Badge (Why)            [ ] PASS [ ] FAIL
Test 5:  Coverage Badge (Impact)         [ ] PASS [ ] FAIL
Test 6:  Coverage Badge (Trace)          [ ] PASS [ ] FAIL
Test 7:  Coverage Badge (Map)            [ ] PASS [ ] FAIL
Test 8:  Blind Spot Warning (High)       [ ] PASS [ ] FAIL
Test 9:  Blind Spot Warning (Med/Low)    [ ] PASS [ ] FAIL
Test 10: Normal Entity (No Warning)      [ ] PASS [ ] FAIL
```

### 性能测试
```
Test 11: Dashboard Load Performance      [ ] PASS [ ] FAIL
Test 12: Query Performance               [ ] PASS [ ] FAIL
```

### 响应式设计
```
Test 13: Mobile Responsive               [ ] PASS [ ] FAIL
```

### 错误处理
```
Test 14: Database Not Found              [ ] PASS [ ] FAIL
Test 15: Empty State                     [ ] PASS [ ] FAIL
```

### 用户体验
```
Test 16: Color Coding Intuitiveness      [ ] PASS [ ] FAIL
Test 17: Text Readability                [ ] PASS [ ] FAIL
Test 18: Interaction Smoothness          [ ] PASS [ ] FAIL
```

---

## 最终评分

**Total Tests**: 18
**Passed**: ______
**Failed**: ______
**Pass Rate**: ______%

**Overall Grade**: [ ] A [ ] B [ ] C [ ] D

---

## 问题记录

如果发现任何问题，请记录如下：

### Issue 1:
- **Test**: Test #___
- **Description**: _______________________
- **Severity**: [ ] Critical [ ] High [ ] Medium [ ] Low
- **Screenshot**: ___________________

### Issue 2:
- **Test**: Test #___
- **Description**: _______________________
- **Severity**: [ ] Critical [ ] High [ ] Medium [ ] Low
- **Screenshot**: ___________________

---

## 签名

**测试人员**: _______________________
**测试日期**: 2026-01-30
**完成时间**: _______________________

---

*本手册由 P1-A Task 6 验收流程生成*
