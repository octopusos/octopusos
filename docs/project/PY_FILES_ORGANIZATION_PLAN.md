# Python 文件整理计划

## 📊 现状统计

**根目录 Python 文件总数**：75 个

## 📁 分类整理方案

### 1. 测试文件 → tests/

#### 1.1 集成测试（tests/integration/）
- test_api_integration.py
- test_projects_api_integration.py
- test_recovery_integration.py
- test_recovery_migration.py
- test_mode_monitor_integration.py
- test_mode_monitoring_api.py
- test_pipeline_view_integration.py
- test_timeout_integration.py
- test_timeout_methods.py
- test_task4_integration.py
- test_task9_e2e.py
- test_writer_monitoring.py
- test_writer_monitoring_advanced.py

#### 1.2 E2E 测试（tests/e2e/）
- test_projects_e2e.py
- test_v04_minimal_e2e.py

#### 1.3 单元测试（tests/unit/）
- test_audit_middleware.py
- test_cancel_handler_demo.py
- test_cancel_running_method_exists.py
- test_cancel_running_simple.py
- test_cancel_running_task.py
- test_diagnostics_api.py
- test_error_builders.py
- test_error_builders_simple.py
- test_error_codes_simple.py
- test_executable_api.py
- test_executable_api_simple.py
- test_hash_debug.py
- test_lmstudio_cross_platform.py
- test_logging_system.py
- test_mode_alerts.py
- test_mode_alerts_standalone.py
- test_mode_monitor_runtime.py
- test_mode_policy_verification.py
- test_path_security.py
- test_path_security_simple.py
- test_process_manager_refactor.py
- test_process_manager_structure.py
- test_projects_crud.py
- test_projects_quick.py
- test_providers_config_phase2.py
- test_providers_config_phase2_simple.py
- test_providers_error_handling.py
- test_refresh_endpoint.py
- test_refresh_simple.py
- test_retry_enforcement.py
- test_retry_logic_simple.py
- test_runner_recovery_simple.py
- test_startup_simulation.py
- test_task13_validation.py
- test_task15_executable_detection.py
- test_task4_exit_reason.py
- test_task8_alert_trigger.py
- test_task8_api.py
- test_task8_basic.py
- test_task8_standalone.py

#### 1.4 压力测试（tests/stress/）
- test_audit_concurrent_stress.py

#### 1.5 手动测试（tests/manual/）
- test_sse_manual.py
- test_pr_v1_implementation.py

### 2. 验证脚本 → scripts/validation/

- verify_implementation.py
- verify_schema_v31.py
- verify_task10.py
- verify_task3_mode_integration.py
- verify_task3_simple.py
- verify_task5_tests.py
- verify_task6_completion.py
- verify_task8_alert_integration.py
- verify_timeout_e2e_tests.py
- verify_timeout_manager.py

### 3. 演示脚本 → examples/demos/

- demo_chat_auto_trigger.py
- demo_providers_config_phase2.py
- demo_work_items_serial.py

### 4. 工具脚本 → scripts/tools/

- add_encoding_batch.py
- add_utf8_encoding.py
- compute_hash.py

### 5. 需要删除的文件

- main.py（PyCharm 默认示例文件，无实际用途）

## 🎯 执行步骤

1. 创建目录（如果不存在）
2. 移动测试文件到 tests/ 子目录
3. 移动验证脚本到 scripts/validation/
4. 移动演示脚本到 examples/demos/
5. 移动工具脚本到 scripts/tools/
6. 删除无用的 main.py

## ✅ 预期结果

- 根目录 Python 文件数：0 个
- 所有文件按用途分类归档
- 项目结构更加清晰
