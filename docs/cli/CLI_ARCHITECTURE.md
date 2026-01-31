# CLI Task Control Plane - 架构图

## 系统架构概览

```mermaid
graph TB
    subgraph "CLI Layer - 用户交互"
        CLI[Interactive CLI]
        Menu[Main Menu]
        Settings[Settings Manager]
    end
    
    subgraph "Control Layer - 任务控制"
        TaskMgr[Task Manager]
        TaskDB[(SQLite DB)]
        Config[CLI Settings]
    end
    
    subgraph "Execution Layer - 后台执行"
        Runner[Task Runner<br/>subprocess]
        Pipeline[Pipeline<br/>待集成]
    end
    
    User((User)) -->|交互| CLI
    CLI -->|显示| Menu
    CLI -->|操作| TaskMgr
    CLI -->|配置| Settings
    Settings -->|持久化| Config
    
    TaskMgr -->|读写| TaskDB
    TaskMgr -->|创建| Runner
    Runner -->|更新状态| TaskDB
    Runner -->|执行| Pipeline
    
    CLI -.->|查询状态| TaskDB
    
    style CLI fill:#e1f5ff
    style TaskMgr fill:#fff4e1
    style Runner fill:#ffe1f5
    style TaskDB fill:#e1ffe1
```

## 数据流图

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant TaskManager
    participant DB
    participant Runner
    participant Pipeline
    
    User->>CLI: 1) 创建任务<br/>(自然语言)
    CLI->>TaskManager: create_task()
    TaskManager->>DB: INSERT task
    DB-->>TaskManager: task_id
    TaskManager-->>CLI: Task
    
    CLI->>Runner: 2) 启动 subprocess
    activate Runner
    
    Runner->>DB: 3) 查询 task
    DB-->>Runner: status: created
    Runner->>DB: 更新 status: planning
    
    Runner->>Pipeline: 4) 执行 planning
    Pipeline-->>Runner: plan 生成
    
    Runner->>DB: 5) 更新 status: awaiting_approval
    deactivate Runner
    
    User->>CLI: 6) 查询状态
    CLI->>DB: SELECT task
    DB-->>CLI: status: awaiting_approval
    CLI-->>User: 显示暂停状态
    
    User->>CLI: 7) 批准
    CLI->>DB: UPDATE status: executing
    
    CLI->>Runner: 8) 重启 subprocess
    activate Runner
    Runner->>Pipeline: 9) 执行 plan
    Pipeline-->>Runner: 完成
    Runner->>DB: 10) UPDATE status: succeeded
    deactivate Runner
    
    User->>CLI: 11) 查询最终状态
    CLI->>DB: SELECT task
    DB-->>CLI: status: succeeded
    CLI-->>User: 显示完成
```

## 三层模型架构

```mermaid
graph LR
    subgraph "1. Run Mode - 人机关系"
        RM1[Interactive<br/>每步确认]
        RM2[Assisted<br/>关键点暂停]
        RM3[Autonomous<br/>全自动]
    end
    
    subgraph "2. Mode - 系统阶段"
        M1[Implementation]
        M2[Planning]
        M3[Design]
        M4[其他...]
    end
    
    subgraph "3. Model Policy - 算力选择"
        MP1[Intent: mini]
        MP2[Planning: 4.1]
        MP3[Impl: 4.1]
    end
    
    Task[Task] --> RM2
    Task --> M2
    Task --> MP2
    
    style RM2 fill:#e1f5ff
    style M2 fill:#fff4e1
    style MP2 fill:#ffe1f5
    style Task fill:#e1ffe1
```

## 状态机转换图

```mermaid
stateDiagram-v2
    [*] --> created: New Task
    
    created --> intent_processing: Runner Start
    intent_processing --> planning: Intent Done
    
    planning --> awaiting_approval: Run Mode = assisted/interactive
    planning --> executing: Run Mode = autonomous
    
    awaiting_approval --> executing: User Approve
    awaiting_approval --> canceled: User Abort
    
    executing --> succeeded: Success
    executing --> failed: Error
    
    succeeded --> [*]
    failed --> [*]
    canceled --> [*]
    
    note right of awaiting_approval
        关键暂停点：
        - Run Mode 决定是否暂停
        - 人工审批后继续
    end note
```

## 文件组织结构

```
agentos/
├── cli/
│   ├── main.py              # 入口，集成交互模式
│   └── interactive.py       # 交互式主循环 [NEW]
│
├── config/
│   ├── __init__.py          # [NEW]
│   └── cli_settings.py      # CLI 配置管理 [NEW]
│
├── core/
│   ├── task/
│   │   ├── models.py        # Task 模型（扩展）
│   │   ├── manager.py       # TaskManager（不变）
│   │   ├── run_mode.py      # RunMode/ModelPolicy [NEW]
│   │   └── __init__.py      # 导出新类型
│   │
│   └── runner/
│       ├── __init__.py      # [NEW]
│       └── task_runner.py   # 后台 Runner [NEW]
│
tests/
└── test_cli_e2e.py          # 端到端测试 [NEW]

docs/
└── cli/
    ├── CLI_TASK_CONTROL_PLANE.md      # 使用文档 [NEW]
    ├── CLI_IMPLEMENTATION_SUMMARY.md  # 实现总结 [NEW]
    └── CLI_ARCHITECTURE.md             # 架构图（本文档）[NEW]
```

## 核心类关系图

```mermaid
classDiagram
    class Task {
        +task_id: str
        +status: str
        +metadata: dict
        +get_run_mode(): str
        +get_model_policy(): dict
    }
    
    class RunMode {
        <<enumeration>>
        INTERACTIVE
        ASSISTED
        AUTONOMOUS
        +requires_approval_at(stage): bool
    }
    
    class ModelPolicy {
        +default: str
        +intent: str
        +planning: str
        +implementation: str
        +get_model_for_stage(stage): str
    }
    
    class TaskMetadata {
        +run_mode: RunMode
        +model_policy: ModelPolicy
        +nl_request: str
        +to_dict(): dict
        +from_dict(dict): TaskMetadata
    }
    
    class TaskManager {
        +create_task(title, metadata): Task
        +get_task(task_id): Task
        +update_task_status(task_id, status)
        +add_lineage()
        +add_audit()
    }
    
    class TaskRunner {
        +task_manager: TaskManager
        +run_task(task_id)
        -_execute_stage(task): str
        -_log_audit()
    }
    
    class InteractiveCLI {
        +task_manager: TaskManager
        +settings: CLISettings
        +run()
        +handle_new_task()
        +handle_resume_task()
        +start_task_runner(task_id)
    }
    
    class CLISettings {
        +default_run_mode: str
        +default_model_policy: dict
        +get_run_mode(): RunMode
        +get_model_policy(): ModelPolicy
    }
    
    Task --> TaskMetadata: uses
    TaskMetadata --> RunMode: contains
    TaskMetadata --> ModelPolicy: contains
    TaskManager --> Task: manages
    TaskRunner --> TaskManager: uses
    TaskRunner --> Task: executes
    InteractiveCLI --> TaskManager: uses
    InteractiveCLI --> CLISettings: uses
    InteractiveCLI --> TaskRunner: starts
```

## 部署视图

```mermaid
graph TB
    subgraph "User Terminal"
        CLI_Process[agentos interactive<br/>主进程]
    end
    
    subgraph "Background Processes"
        Runner1[Task Runner 1<br/>subprocess]
        Runner2[Task Runner 2<br/>subprocess]
        RunnerN[Task Runner N<br/>subprocess]
    end
    
    subgraph "Persistent Storage"
        DB[(store/registry.sqlite)]
        Config[~/.agentos/settings.json]
    end
    
    CLI_Process -->|fork| Runner1
    CLI_Process -->|fork| Runner2
    CLI_Process -->|fork| RunnerN
    
    CLI_Process -.->|read| DB
    CLI_Process -->|read/write| Config
    
    Runner1 -->|write| DB
    Runner2 -->|write| DB
    RunnerN -->|write| DB
    
    style CLI_Process fill:#e1f5ff
    style Runner1 fill:#ffe1f5
    style Runner2 fill:#ffe1f5
    style RunnerN fill:#ffe1f5
    style DB fill:#e1ffe1
    style Config fill:#fff4e1
```

## 技术栈

```mermaid
graph LR
    subgraph "Frontend"
        A[Click CLI Framework]
        B[Python Input/Output]
    end
    
    subgraph "Core"
        C[Task Manager]
        D[Task Runner]
        E[State Machine]
    end
    
    subgraph "Storage"
        F[SQLite]
        G[JSON Config]
    end
    
    subgraph "Execution"
        H[subprocess]
        I[Pipeline待集成]
    end
    
    A --> C
    C --> F
    C --> D
    D --> H
    D --> I
    B --> G
    
    style A fill:#e1f5ff
    style C fill:#fff4e1
    style D fill:#ffe1f5
    style F fill:#e1ffe1
```

## 与现有系统集成点

```mermaid
graph TB
    subgraph "新增 CLI Layer"
        CLI[Interactive CLI]
        Runner[Task Runner]
    end
    
    subgraph "现有 Core Layer"
        TaskMgr[Task Manager<br/>已有]
        Executor[Executor Engine<br/>已有]
        Coordinator[Coordinator<br/>已有]
    end
    
    subgraph "现有 Storage Layer"
        DB[(SQLite<br/>schema_v06)]
    end
    
    CLI -->|调用| TaskMgr
    CLI -->|启动| Runner
    Runner -->|调用| TaskMgr
    Runner -.->|待集成| Coordinator
    Runner -.->|待集成| Executor
    
    TaskMgr -->|读写| DB
    
    style CLI fill:#e1f5ff,stroke:#0066cc,stroke-width:3px
    style Runner fill:#ffe1f5,stroke:#cc0066,stroke-width:3px
    style TaskMgr fill:#fff4e1
    style DB fill:#e1ffe1
```

## 设计原则

### 1. 最小侵入 (Minimal Intrusion)
- 不修改现有 TaskManager 核心逻辑
- 不修改现有 Executor/Coordinator
- 纯增量添加新模块

### 2. 渐进式演进 (Progressive Evolution)
- 当前：subprocess 模式（简单可靠）
- 未来：daemon 模式（高性能）
- 接口保持兼容

### 3. 关注点分离 (Separation of Concerns)
- CLI Layer：用户交互
- Control Layer：任务管理
- Execution Layer：实际执行

### 4. 通过数据库通信 (DB as IPC)
- 最简单的进程间通信
- 天然支持持久化
- 易于调试和追溯

## 核心创新点

### 1. Task-Centric 架构
不同于 opencode 的 session-centric，我们以 task 为中心，提供：
- 完整的 task lineage
- 原生 audit 支持
- 任意时刻可恢复

### 2. 三层模型
清晰分离三个概念：
- Run Mode（人机关系）
- Mode（系统阶段）
- Model Policy（算力选择）

### 3. 智能暂停
根据 Run Mode 自动在关键点暂停：
- Interactive：每步都停
- Assisted：planning 停
- Autonomous：不停

### 4. 可治理性
不只是"让 AI 跑"，而是"让人随时能接管"：
- 任务可暂停
- 任务可恢复
- 任务可追溯
- 任务可审计

---

**文档版本**: v1.0.0  
**创建日期**: 2026-01-26  
**维护者**: AgentOS Team
