# Mode Bug 修复工作流程图

**版本**: 1.0.0
**生效日期**: 2026-01-30
**适用范围**: Mode 系统 Bug 修复全流程
**状态**: Active

---

## 目录

1. [完整工作流程](#1-完整工作流程)
2. [Bug 报告阶段](#2-bug-报告阶段)
3. [Bug 分类阶段](#3-bug-分类阶段)
4. [Bug 修复阶段](#4-bug-修复阶段)
5. [Code Review 阶段](#5-code-review-阶段)
6. [测试验证阶段](#6-测试验证阶段)
7. [发布上线阶段](#7-发布上线阶段)
8. [关键决策点](#8-关键决策点)
9. [角色和职责](#9-角色和职责)

---

## 1. 完整工作流程

### 1.1 端到端流程图

```mermaid
graph TB
    Start([Bug 发现]) --> Report[Bug 报告]
    Report --> Triage{Bug 分类}

    Triage --> P0[P0: Critical]
    Triage --> P1[P1: High]
    Triage --> P2[P2: Medium]
    Triage --> P3[P3: Low]

    P0 --> EmergencyResponse[紧急响应<br/>1小时内]
    P1 --> PriorityFix[优先修复<br/>4小时内]
    P2 --> Defer[推迟到冻结期后]
    P3 --> Backlog[加入Backlog]

    EmergencyResponse --> Analyze[根因分析]
    PriorityFix --> Analyze

    Analyze --> Solution{是否需要<br/>破坏性变更?}

    Solution -->|是| Exception[申请例外]
    Solution -->|否| Implement[实施修复]

    Exception --> ExceptionApproval{例外审批}
    ExceptionApproval -->|拒绝| Defer
    ExceptionApproval -->|批准| Implement

    Implement --> Tests[编写测试]
    Tests --> AllTestsPass{所有测试<br/>通过?}

    AllTestsPass -->|否| Implement
    AllTestsPass -->|是| CodeReview[代码审查]

    CodeReview --> ReviewPass{审查通过?}
    ReviewPass -->|否| Implement
    ReviewPass -->|是| Merge[合并到主分支]

    Merge --> NeedRelease{需要立即<br/>发布?}

    NeedRelease -->|P0/P1| CreateRelease[创建Patch版本]
    NeedRelease -->|其他| WaitRelease[等待下次发布]

    CreateRelease --> Deploy[部署到生产]
    WaitRelease --> Deploy

    Deploy --> Monitor[监控验证]
    Monitor --> Success{修复成功?}

    Success -->|是| Close[关闭Issue]
    Success -->|否| Rollback[回滚]

    Rollback --> Analyze

    Close --> End([完成])
    Defer --> End
    Backlog --> End
```

### 1.2 时间线视图

```mermaid
gantt
    title Bug 修复时间线（P0 Critical Bug）
    dateFormat HH:mm
    axisFormat %H:%M

    section 报告
    Bug发现并报告          :report, 00:00, 15m

    section 分类
    自动分类              :triage1, after report, 15m
    技术负责人确认        :triage2, after triage1, 30m

    section 修复
    根因分析              :analyze, after triage2, 2h
    实施修复              :fix, after analyze, 4h
    编写测试              :test, after fix, 2h

    section 审查
    代码审查              :review, after test, 2h
    修改和调整            :adjust, after review, 1h

    section 发布
    合并到主分支          :merge, after adjust, 30m
    创建Patch版本         :release, after merge, 30m
    部署到生产            :deploy, after release, 1h

    section 验证
    监控验证              :monitor, after deploy, 24h
```

---

## 2. Bug 报告阶段

### 2.1 Bug 报告流程

```mermaid
graph LR
    A[用户/开发者<br/>发现Bug] --> B{选择报告<br/>方式}

    B -->|P0紧急| C[直接联系<br/>紧急热线]
    B -->|P1-P3| D[GitHub Issues]
    B -->|内部| E[内部Bug系统]

    C --> F[填写Bug报告]
    D --> F
    E --> F

    F --> G[自动标签分类]
    G --> H[通知技术负责人]
    H --> I[分配初始优先级]
    I --> J[进入分类队列]
```

### 2.2 Bug 报告输入输出

**输入**:
- Bug 现象描述
- 重现步骤
- 环境信息
- 日志和截图
- 影响范围估计

**输出**:
- Bug Issue 编号
- 初始优先级标签
- 分配的技术负责人
- SLA 时限

**工具**:
- GitHub Issues
- 内部 Bug 追踪系统
- 邮件（紧急情况）

**人员**:
- 报告人：任何用户或开发者
- 接收人：技术支持/On-call 工程师

---

## 3. Bug 分类阶段

### 3.1 Bug 分类决策树

```mermaid
graph TD
    Start([收到Bug报告]) --> Q1{系统是否<br/>完全不可用?}

    Q1 -->|是| Q1_1{是否数据<br/>丢失?}
    Q1 -->|否| Q2{核心功能<br/>是否受影响?}

    Q1_1 -->|是| P0_Data[P0: 数据丢失]
    Q1_1 -->|否| P0_System[P0: 系统崩溃]

    Q2 -->|是| Q2_1{影响多少<br/>用户?}
    Q2 -->|否| Q3{性能是否<br/>严重下降?}

    Q2_1 -->|>80%| P0_Users[P0: 大规模影响]
    Q2_1 -->|30-80%| P1_Users[P1: 核心功能不可用]
    Q2_1 -->|<30%| P2_Partial[P2: 部分用户受影响]

    Q3 -->|是<br/>>50%退化| P1_Perf[P1: 性能严重退化]
    Q3 -->|否| Q4{是否有<br/>安全漏洞?}

    Q4 -->|是| Q4_1{CVE评分?}
    Q4 -->|否| Q5{是否影响<br/>次要功能?}

    Q4_1 -->|>=9.0| P0_Security[P0: 严重安全漏洞]
    Q4_1 -->|7.0-8.9| P1_Security[P1: 中等安全漏洞]
    Q4_1 -->|4.0-6.9| P2_Security[P2: 低风险漏洞]
    Q4_1 -->|<4.0| P3_Security[P3: 信息泄露]

    Q5 -->|是| P2_Minor[P2: 次要功能问题]
    Q5 -->|否| Q6{是否UI/文档<br/>问题?}

    Q6 -->|是| P3_UI[P3: UI/文档问题]
    Q6 -->|否| P3_Other[P3: 其他小问题]

    P0_Data --> Action_P0[立即响应<br/>1小时SLA]
    P0_System --> Action_P0
    P0_Users --> Action_P0
    P0_Security --> Action_P0

    P1_Users --> Action_P1[优先处理<br/>4小时SLA]
    P1_Perf --> Action_P1
    P1_Security --> Action_P1

    P2_Partial --> Action_P2[推迟处理<br/>1周SLA]
    P2_Minor --> Action_P2
    P2_Security --> Action_P2

    P3_UI --> Action_P3[Backlog<br/>2周SLA]
    P3_Other --> Action_P3
    P3_Security --> Action_P3
```

### 3.2 分类输出

**对于 P0 (Critical)**:
- ✅ 立即通知 On-call 工程师
- ✅ 创建紧急响应小组
- ✅ 启动紧急修复流程
- ✅ 每小时更新进度

**对于 P1 (High)**:
- ✅ 4小时内分配给负责人
- ✅ 插入当前 Sprint
- ✅ 每日更新进度
- ✅ 优先级标记

**对于 P2/P3 (Medium/Low)**:
- ✅ 标记为 "mode-freeze-deferred"
- ✅ 加入待修复队列
- ✅ 等待冻结期结束

---

## 4. Bug 修复阶段

### 4.1 修复流程详细图

```mermaid
graph TB
    Start([分配给负责人]) --> CreateBranch[创建修复分支<br/>fix/mode-XXX-desc]

    CreateBranch --> RootCause[根因分析]

    RootCause --> Q1{是否理解<br/>根本原因?}
    Q1 -->|否| Investigation[深入调查<br/>添加调试日志]
    Investigation --> RootCause
    Q1 -->|是| Solution[设计解决方案]

    Solution --> Q2{是否需要<br/>API变更?}

    Q2 -->|是| ApplyException[申请例外审批]
    Q2 -->|否| MinimalFix[实施最小化修复]

    ApplyException --> Q3{例外获批?}
    Q3 -->|否| RethinkSolution[重新设计<br/>非侵入式方案]
    Q3 -->|是| MinimalFix

    RethinkSolution --> Solution

    MinimalFix --> AddComments[添加代码注释<br/>说明修复原因]

    AddComments --> WriteTests[编写回归测试]

    WriteTests --> RunUnitTests[运行单元测试]
    RunUnitTests --> Q4{单元测试<br/>通过?}
    Q4 -->|否| FixTests[修复测试或代码]
    FixTests --> RunUnitTests
    Q4 -->|是| RunIntegrationTests[运行集成测试]

    RunIntegrationTests --> Q5{集成测试<br/>通过?}
    Q5 -->|否| FixIntegration[修复集成问题]
    FixIntegration --> RunIntegrationTests
    Q5 -->|是| RunFullSuite[运行完整测试套件]

    RunFullSuite --> Q6{全部测试<br/>通过?}
    Q6 -->|否| DebugFailure[调试失败原因]
    DebugFailure --> MinimalFix
    Q6 -->|是| CheckStyle[代码风格检查]

    CheckStyle --> Q7{风格检查<br/>通过?}
    Q7 -->|否| FixStyle[修复风格问题]
    FixStyle --> CheckStyle
    Q7 -->|是| UpdateDocs[更新文档]

    UpdateDocs --> UpdateChangelog[更新CHANGELOG]
    UpdateChangelog --> PushBranch[推送分支]
    PushBranch --> CreatePR[创建Pull Request]

    CreatePR --> End([进入审查阶段])
```

### 4.2 修复阶段关键输出

**代码层面**:
- [ ] 修复代码（最小化变更）
- [ ] 回归测试
- [ ] 代码注释
- [ ] 通过所有测试
- [ ] 通过代码风格检查

**文档层面**:
- [ ] CHANGELOG 更新
- [ ] API 文档更新（如需要）
- [ ] 内联注释说明修复原因

**流程层面**:
- [ ] Git 分支（命名规范）
- [ ] Commit message（规范格式）
- [ ] Pull Request（链接 Issue）

---

## 5. Code Review 阶段

### 5.1 Code Review 流程

```mermaid
graph TB
    Start([收到PR]) --> AssignReviewers[分配审查者<br/>至少2人]

    AssignReviewers --> CheckCI[等待CI检查]
    CheckCI --> Q1{CI通过?}

    Q1 -->|否| NotifyAuthor[通知作者<br/>修复CI问题]
    NotifyAuthor --> AuthorFix[作者修复]
    AuthorFix --> CheckCI

    Q1 -->|是| Review1[审查者1审查]
    Q1 -->|是| Review2[审查者2审查]

    Review1 --> CheckFunctional1[功能审查]
    Review2 --> CheckFunctional2[功能审查]

    CheckFunctional1 --> CheckFreeze1[冻结规范审查]
    CheckFunctional2 --> CheckFreeze2[冻结规范审查]

    CheckFreeze1 --> CheckQuality1[代码质量审查]
    CheckFreeze2 --> CheckQuality2[代码质量审查]

    CheckQuality1 --> Decision1{审查者1<br/>决定}
    CheckQuality2 --> Decision2{审查者2<br/>决定}

    Decision1 -->|批准| Approve1[Approve]
    Decision1 -->|需修改| RequestChanges1[Request Changes]
    Decision1 -->|评论| Comment1[Comment]

    Decision2 -->|批准| Approve2[Approve]
    Decision2 -->|需修改| RequestChanges2[Request Changes]
    Decision2 -->|评论| Comment2[Comment]

    RequestChanges1 --> AuthorAddress[作者响应反馈]
    RequestChanges2 --> AuthorAddress
    Comment1 --> AuthorConsider[作者考虑建议]
    Comment2 --> AuthorConsider

    AuthorAddress --> UpdatePR[更新PR]
    AuthorConsider --> Q2{是否需要<br/>更新?}
    Q2 -->|是| UpdatePR
    Q2 -->|否| WaitForApproval

    UpdatePR --> Review1

    Approve1 --> BothApproved{两位审查者<br/>都批准?}
    Approve2 --> BothApproved

    BothApproved -->|是| MaintainerCheck[Maintainer最终检查]
    BothApproved -->|否| WaitForApproval[等待另一位批准]

    WaitForApproval --> BothApproved

    MaintainerCheck --> Q3{Maintainer<br/>批准?}
    Q3 -->|否| MaintainerFeedback[提出额外反馈]
    MaintainerFeedback --> AuthorAddress
    Q3 -->|是| ReadyMerge[标记为Ready to Merge]

    ReadyMerge --> End([进入合并阶段])
```

### 5.2 Code Review 检查清单

#### 功能审查
```mermaid
graph LR
    A[功能审查] --> B[Bug是否修复?]
    A --> C[是否添加回归测试?]
    A --> D[测试是否覆盖边界条件?]
    A --> E[是否有副作用?]

    B --> Pass1{✓}
    C --> Pass2{✓}
    D --> Pass3{✓}
    E --> Pass4{✓}

    Pass1 --> Result[功能审查通过]
    Pass2 --> Result
    Pass3 --> Result
    Pass4 --> Result
```

#### 冻结规范审查
```mermaid
graph LR
    A[冻结规范审查] --> B[是否只修复Bug?]
    A --> C[是否改变API?]
    A --> D[是否向后兼容?]
    A --> E[是否有例外批准?]

    B --> Check1{是}
    C --> Check2{否}
    D --> Check3{是}
    E --> Check4{是/N/A}

    Check1 --> Result[冻结规范通过]
    Check2 --> Result
    Check3 --> Result
    Check4 --> Result
```

#### 代码质量审查
```mermaid
graph LR
    A[代码质量审查] --> B[代码清晰?]
    A --> C[注释充分?]
    A --> D[遵循规范?]
    A --> E[无安全问题?]

    B --> Quality1{✓}
    C --> Quality2{✓}
    D --> Quality3{✓}
    E --> Quality4{✓}

    Quality1 --> Result[质量审查通过]
    Quality2 --> Result
    Quality3 --> Result
    Quality4 --> Result
```

---

## 6. 测试验证阶段

### 6.1 测试金字塔

```mermaid
graph TB
    subgraph "测试金字塔"
        E2E[端到端测试<br/>E2E Tests<br/>数量: 少]
        Integration[集成测试<br/>Integration Tests<br/>数量: 中]
        Unit[单元测试<br/>Unit Tests<br/>数量: 多]
    end

    E2E -.->|依赖| Integration
    Integration -.->|依赖| Unit

    Unit --> Quick[快速反馈<br/>< 1秒]
    Integration --> Medium[中等反馈<br/>< 10秒]
    E2E --> Slow[较慢反馈<br/>< 1分钟]
```

### 6.2 测试执行流程

```mermaid
graph TB
    Start([修复完成]) --> RunUnit[运行单元测试<br/>pytest tests/unit/mode/]

    RunUnit --> Q1{单元测试<br/>通过?}
    Q1 -->|否| FixUnit[修复单元测试失败]
    FixUnit --> RunUnit
    Q1 -->|是| CheckCoverage[检查代码覆盖率]

    CheckCoverage --> Q2{覆盖率<br/>>80%?}
    Q2 -->|否| AddTests[添加更多测试]
    AddTests --> RunUnit
    Q2 -->|是| RunIntegration[运行集成测试<br/>pytest tests/integration/mode/]

    RunIntegration --> Q3{集成测试<br/>通过?}
    Q3 -->|否| FixIntegration[修复集成问题]
    FixIntegration --> RunIntegration
    Q3 -->|是| RunE2E[运行端到端测试<br/>pytest tests/e2e/]

    RunE2E --> Q4{E2E测试<br/>通过?}
    Q4 -->|否| FixE2E[修复E2E问题]
    FixE2E --> RunE2E
    Q4 -->|是| RunPerf{Bug级别<br/>P0/P1?}

    RunPerf -->|是| PerfTest[运行性能测试]
    RunPerf -->|否| SecurityScan

    PerfTest --> Q5{性能<br/>无退化?}
    Q5 -->|否| OptimizeFix[优化修复代码]
    OptimizeFix --> RunUnit
    Q5 -->|是| SecurityScan[安全扫描]

    SecurityScan --> Q6{安全扫描<br/>通过?}
    Q6 -->|否| FixSecurity[修复安全问题]
    FixSecurity --> SecurityScan
    Q6 -->|是| ManualTest[人工验证测试]

    ManualTest --> Q7{人工测试<br/>通过?}
    Q7 -->|否| BackToFix[返回修复阶段]
    BackToFix --> Start
    Q7 -->|是| AllTestsPass[所有测试通过]

    AllTestsPass --> End([进入发布阶段])
```

---

## 7. 发布上线阶段

### 7.1 发布决策流程

```mermaid
graph TB
    Start([审查通过]) --> Merge[合并到主分支]

    Merge --> Q1{Bug级别?}

    Q1 -->|P0| ImmediateRelease[立即发布]
    Q1 -->|P1| Q2{影响<br/>>50%用户?}
    Q1 -->|P2/P3| WaitRelease[等待下次发布]

    Q2 -->|是| ImmediateRelease
    Q2 -->|否| ScheduleRelease[安排在下次发布]

    ImmediateRelease --> BumpVersion[更新版本号<br/>Patch版本]
    ScheduleRelease --> BatchRelease[批量发布准备]

    BumpVersion --> UpdateChangelog[更新CHANGELOG]
    BatchRelease --> UpdateChangelog

    UpdateChangelog --> CreateTag[创建Git Tag]
    CreateTag --> BuildRelease[构建发布包]

    BuildRelease --> Q3{构建<br/>成功?}
    Q3 -->|否| DebugBuild[调试构建问题]
    DebugBuild --> BuildRelease
    Q3 -->|是| RunSmokeTests[运行冒烟测试]

    RunSmokeTests --> Q4{冒烟测试<br/>通过?}
    Q4 -->|否| RollbackBuild[回滚构建]
    RollbackBuild --> DebugBuild
    Q4 -->|是| PrepareRollback[准备回滚方案]

    PrepareRollback --> DeployStaging[部署到预发布环境]

    DeployStaging --> Q5{预发布<br/>验证通过?}
    Q5 -->|否| DebugStaging[调试预发布问题]
    DebugStaging --> DeployStaging
    Q5 -->|是| DeployProduction[部署到生产环境]

    DeployProduction --> MonitorMetrics[监控关键指标]

    MonitorMetrics --> Q6{1小时内<br/>异常?}
    Q6 -->|是| Q7{是否严重?}
    Q6 -->|否| ContinueMonitor[继续监控24小时]

    Q7 -->|是| ExecuteRollback[执行回滚]
    Q7 -->|否| InvestigateIssue[调查问题]

    ExecuteRollback --> PostMortem[事后分析]
    PostMortem --> Start

    InvestigateIssue --> Q8{可以<br/>修复?}
    Q8 -->|是| HotFix[热修复]
    Q8 -->|否| ExecuteRollback

    HotFix --> MonitorMetrics

    ContinueMonitor --> Q9{24小时内<br/>稳定?}
    Q9 -->|否| InvestigateLongTerm[调查长期问题]
    Q9 -->|是| CloseIssue[关闭Issue]

    InvestigateLongTerm --> Q10{需要<br/>回滚?}
    Q10 -->|是| ExecuteRollback
    Q10 -->|否| CreateFollowup[创建后续Issue]

    CloseIssue --> UpdateMetrics[更新修复指标]
    CreateFollowup --> UpdateMetrics

    UpdateMetrics --> End([发布完成])

    WaitRelease --> End
```

### 7.2 部署监控指标

```mermaid
graph LR
    subgraph "监控指标"
        A[错误率]
        B[响应时间]
        C[吞吐量]
        D[CPU使用率]
        E[内存使用率]
        F[用户反馈]
    end

    A --> Threshold1[< 0.1%]
    B --> Threshold2[< 200ms P95]
    C --> Threshold3[无下降]
    D --> Threshold4[< 80%]
    E --> Threshold5[< 80%]
    F --> Threshold6[无投诉]

    Threshold1 --> Decision{全部<br/>达标?}
    Threshold2 --> Decision
    Threshold3 --> Decision
    Threshold4 --> Decision
    Threshold5 --> Decision
    Threshold6 --> Decision

    Decision -->|是| Success[发布成功]
    Decision -->|否| Alert[触发告警]
```

---

## 8. 关键决策点

### 8.1 严重级别判定

```mermaid
graph LR
    Input[Bug报告] --> Criteria[评估标准]

    Criteria --> Impact[影响范围]
    Criteria --> Scope[影响用户数]
    Criteria --> Data[数据影响]
    Criteria --> Security[安全性]

    Impact --> Score1[得分1]
    Scope --> Score2[得分2]
    Data --> Score3[得分3]
    Security --> Score4[得分4]

    Score1 --> Total[总分]
    Score2 --> Total
    Score3 --> Total
    Score4 --> Total

    Total --> Decision{总分?}

    Decision -->|>90| P0[P0: Critical]
    Decision -->|60-90| P1[P1: High]
    Decision -->|30-60| P2[P2: Medium]
    Decision -->|<30| P3[P3: Low]
```

### 8.2 是否需要例外批准

```mermaid
graph TB
    Start([开始修复]) --> Q1{是否改变<br/>公共API?}

    Q1 -->|是| NeedException[需要例外批准]
    Q1 -->|否| Q2{是否改变<br/>配置格式?}

    Q2 -->|是| NeedException
    Q2 -->|否| Q3{是否破坏<br/>向后兼容?}

    Q3 -->|是| NeedException
    Q3 -->|否| Q4{是否重构<br/>架构?}

    Q4 -->|是| NeedException
    Q4 -->|否| Q5{是否添加<br/>新功能?}

    Q5 -->|是| NeedException
    Q5 -->|否| NoException[不需要例外]

    NeedException --> Apply[申请例外审批]
    NoException --> Proceed[继续修复流程]
```

### 8.3 是否立即发布

```mermaid
graph TB
    Start([修复完成]) --> Q1{Bug级别?}

    Q1 -->|P0| Immediate[立即发布]
    Q1 -->|P1| Q2{用户影响?}
    Q1 -->|P2/P3| Wait[等待下次发布]

    Q2 -->|>50%| Immediate
    Q2 -->|30-50%| Q3{有缓解<br/>措施?}
    Q2 -->|<30%| Schedule[安排下次发布]

    Q3 -->|是| Schedule
    Q3 -->|否| Immediate

    Immediate --> CreatePatch[创建Patch版本]
    Schedule --> AddToBatch[加入发布批次]
    Wait --> Backlog[加入Backlog]
```

---

## 9. 角色和职责

### 9.1 角色矩阵

```mermaid
graph TB
    subgraph "Bug修复角色"
        Reporter[报告人<br/>Reporter]
        Triage[分类人<br/>Triager]
        Owner[负责人<br/>Owner]
        Reviewer[审查者<br/>Reviewer]
        Maintainer[维护者<br/>Maintainer]
        ReleaseManager[发布经理<br/>Release Manager]
    end

    Reporter --> |提交| BugReport[Bug报告]
    BugReport --> |分类| Triage
    Triage --> |分配| Owner
    Owner --> |修复| Fix[修复代码]
    Fix --> |审查| Reviewer
    Reviewer --> |批准| Maintainer
    Maintainer --> |最终审批| ReleaseManager
    ReleaseManager --> |发布| Release[发布上线]
```

### 9.2 职责说明

#### 报告人 (Reporter)
- **职责**:
  - 发现并报告 Bug
  - 提供详细的重现步骤
  - 协助验证修复
- **工具**: GitHub Issues, 邮件, 内部系统

#### 分类人 (Triager)
- **职责**:
  - 验证 Bug 可重现性
  - 评估严重级别
  - 分配给合适的负责人
- **时限**: P0 1小时, P1 4小时
- **工具**: Issue 系统, 测试环境

#### 负责人 (Owner)
- **职责**:
  - 根因分析
  - 实施修复
  - 编写测试
  - 更新文档
- **时限**: 按 SLA 执行
- **工具**: IDE, Git, 测试工具

#### 审查者 (Reviewer)
- **职责**:
  - 代码审查
  - 功能验证
  - 冻结规范检查
- **要求**: 至少 2 人
- **工具**: GitHub PR, 代码审查工具

#### 维护者 (Maintainer)
- **职责**:
  - 最终审批
  - 合并代码
  - 确保质量
- **要求**: Mode 系统专家
- **工具**: Git, CI/CD

#### 发布经理 (Release Manager)
- **职责**:
  - 决定发布时机
  - 协调发布流程
  - 监控发布后状态
- **工具**: 发布脚本, 监控系统

---

## 10. 相关文档

- [MODE_BUG_FIX_PROCESS.md](./MODE_BUG_FIX_PROCESS.md) - Bug 修复流程详细说明
- [MODE_FREEZE_SPECIFICATION.md](./MODE_FREEZE_SPECIFICATION.md) - Mode 冻结规范
- [MODE_BUG_FIX_QUICK_REFERENCE.md](./MODE_BUG_FIX_QUICK_REFERENCE.md) - 快速参考
- [MODE_BUG_FIX_TESTING_GUIDE.md](./MODE_BUG_FIX_TESTING_GUIDE.md) - 测试指南
- [templates/BUG_FIX_TEMPLATE.md](./templates/BUG_FIX_TEMPLATE.md) - Bug 修复模板
- [examples/MODE_BUG_FIX_EXAMPLES.md](./examples/MODE_BUG_FIX_EXAMPLES.md) - Bug 修复示例

---

**文档状态**: ✅ Active
**最后更新**: 2026-01-30
**维护者**: Architecture Committee
**反馈渠道**: architecture-committee@company.com
