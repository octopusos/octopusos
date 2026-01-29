/**
 * NextStepPredictor - 预测任务执行的下一步
 *
 * PR-V5: Timeline View - 叙事时间线
 *
 * 功能:
 * - 根据当前阶段预测下一步操作
 * - 根据最后事件调整预测
 * - 提供异常情况的下一步说明
 *
 * Usage:
 * ```javascript
 * const nextStep = NextStepPredictor.predict('executing', lastEvent);
 * // "下一步：验证执行结果"
 * ```
 */

import { PHASE_NAMES } from './EventTranslator.js';

export class NextStepPredictor {
    /**
     * 预测下一步操作
     *
     * @param {string} currentPhase - 当前阶段 (planning/executing/verifying/done)
     * @param {Object} lastEvent - 最后一个事件（友好格式）
     * @returns {string} 下一步描述
     */
    static predict(currentPhase, lastEvent = null) {
        // 基于最后事件的特殊情况
        if (lastEvent) {
            const specialCase = this._checkSpecialCase(lastEvent);
            if (specialCase) {
                return specialCase;
            }
        }

        // 基于当前阶段的默认预测
        return this._predictByPhase(currentPhase);
    }

    /**
     * 检查特殊情况
     *
     * @param {Object} lastEvent - 最后事件
     * @returns {string|null} 特殊情况的下一步，或 null
     */
    static _checkSpecialCase(lastEvent) {
        const eventType = lastEvent.rawEvent?.event_type;

        // Gate 失败 → 重试
        if (eventType === 'gate_result' && !lastEvent.rawEvent.payload?.passed) {
            return '下一步：重新规划并重试（检查点未通过）';
        }

        if (eventType === 'GATE_VERIFICATION_RESULT' && !lastEvent.rawEvent.payload?.passed) {
            return '下一步：重新规划并重试（验证失败）';
        }

        // Work items 派发 → 等待完成
        if (eventType === 'work_item_dispatched' || eventType === 'WORK_ITEMS_EXTRACTED') {
            const count = lastEvent.rawEvent.payload?.count || lastEvent.rawEvent.payload?.total_items;
            return count
                ? `下一步：等待 ${count} 个子任务完成`
                : '下一步：等待所有子任务完成';
        }

        if (eventType === 'work_item_start' || eventType === 'WORK_ITEM_STARTED') {
            return '下一步：执行子任务内容';
        }

        // Work item 失败 → 重试或跳过
        if (eventType === 'work_item_failed' || eventType === 'WORK_ITEM_FAILED') {
            return '下一步：重试失败的子任务或跳过';
        }

        // Checkpoint 提交 → 继续下一阶段
        if (eventType === 'checkpoint_commit') {
            return '下一步：继续执行下一阶段';
        }

        // Recovery 恢复 → 从断点继续
        if (eventType === 'recovery_resumed_from_checkpoint') {
            const phase = lastEvent.rawEvent.payload?.phase;
            const phaseName = PHASE_NAMES[phase] || phase;
            return `下一步：从 ${phaseName} 阶段继续执行`;
        }

        if (eventType === 'recovery_detected') {
            return '下一步：扫描恢复点并重启任务';
        }

        // Runner 退出 → 结束
        if (eventType === 'runner_exit') {
            const exitCode = lastEvent.rawEvent.payload?.exit_code ?? 0;
            return exitCode === 0
                ? '任务执行完成'
                : '下一步：分析错误日志并重试';
        }

        return null;
    }

    /**
     * 基于阶段的默认预测
     *
     * @param {string} phase - 当前阶段
     * @returns {string} 下一步描述
     */
    static _predictByPhase(phase) {
        const predictions = {
            'planning': '下一步：开始执行任务',
            'executing': '下一步：验证执行结果',
            'verifying': '下一步：运行检查点（Gates）',
            'done': '任务已完成',
            'failed': '任务已失败（查看日志分析原因）',
            'blocked': '任务被阻塞（等待依赖解除）'
        };

        return predictions[phase] || '下一步：继续处理...';
    }

    /**
     * 预测完整的流程进度
     *
     * @param {string} currentPhase - 当前阶段
     * @returns {Object} 进度信息
     */
    static predictProgress(currentPhase) {
        const phases = ['planning', 'executing', 'verifying', 'done'];
        const currentIndex = phases.indexOf(currentPhase);

        if (currentIndex === -1) {
            return {
                current: currentPhase,
                percentage: 0,
                completed: 0,
                total: 4,
                remaining: phases
            };
        }

        const completed = currentIndex;
        const total = phases.length;
        const percentage = Math.round((completed / total) * 100);
        const remaining = phases.slice(currentIndex + 1);

        return {
            current: currentPhase,
            percentage,
            completed,
            total,
            remaining
        };
    }

    /**
     * 预测剩余时间（基于历史数据）
     *
     * @param {string} currentPhase - 当前阶段
     * @param {Array} events - 事件历史
     * @returns {Object} 时间估算
     */
    static estimateRemainingTime(currentPhase, events) {
        if (!events || events.length === 0) {
            return {
                estimated_seconds: null,
                confidence: 'unknown',
                message: '数据不足，无法估算'
            };
        }

        // 查找阶段转换事件
        const phaseEnterEvents = events.filter(e =>
            e.rawEvent?.event_type === 'phase_enter'
        );

        if (phaseEnterEvents.length < 2) {
            return {
                estimated_seconds: null,
                confidence: 'low',
                message: '历史数据不足'
            };
        }

        // 计算平均阶段时长（简化版）
        const avgPhaseTime = this._calculateAveragePhaseTime(phaseEnterEvents);

        const phases = ['planning', 'executing', 'verifying', 'done'];
        const currentIndex = phases.indexOf(currentPhase);
        const remainingPhases = phases.length - currentIndex - 1;

        const estimatedSeconds = avgPhaseTime * remainingPhases;

        return {
            estimated_seconds: Math.round(estimatedSeconds),
            confidence: phaseEnterEvents.length >= 4 ? 'high' : 'medium',
            message: this._formatDuration(estimatedSeconds)
        };
    }

    /**
     * 计算平均阶段时长
     *
     * @param {Array} phaseEnterEvents - phase_enter 事件
     * @returns {number} 平均时长（秒）
     */
    static _calculateAveragePhaseTime(phaseEnterEvents) {
        if (phaseEnterEvents.length < 2) return 60; // 默认 60 秒

        let totalDuration = 0;
        let count = 0;

        for (let i = 1; i < phaseEnterEvents.length; i++) {
            const prev = new Date(phaseEnterEvents[i - 1].timestamp);
            const curr = new Date(phaseEnterEvents[i].timestamp);
            const duration = (curr - prev) / 1000; // 转为秒

            if (duration > 0 && duration < 3600) { // 过滤异常值（> 1小时）
                totalDuration += duration;
                count++;
            }
        }

        return count > 0 ? totalDuration / count : 60;
    }

    /**
     * 格式化时长
     *
     * @param {number} seconds - 秒数
     * @returns {string} 格式化后的时长
     */
    static _formatDuration(seconds) {
        if (seconds < 60) {
            return `约 ${Math.round(seconds)} 秒`;
        } else if (seconds < 3600) {
            const minutes = Math.round(seconds / 60);
            return `约 ${minutes} 分钟`;
        } else {
            const hours = Math.round(seconds / 3600);
            return `约 ${hours} 小时`;
        }
    }

    /**
     * 生成当前活动描述
     *
     * @param {Object} lastEvent - 最后事件
     * @returns {string} 当前活动描述
     */
    static describeCurrentActivity(lastEvent) {
        if (!lastEvent) {
            return '等待任务启动...';
        }

        const eventType = lastEvent.rawEvent?.event_type;

        // 正在执行的活动
        if (eventType === 'phase_enter') {
            const phase = lastEvent.rawEvent.payload?.phase;
            const phaseName = PHASE_NAMES[phase] || phase;
            return `正在 ${phaseName} 阶段`;
        }

        if (eventType === 'work_item_start' || eventType === 'WORK_ITEM_STARTED') {
            const itemId = lastEvent.rawEvent.payload?.work_item_id || 'unknown';
            return `正在执行子任务 #${itemId}`;
        }

        if (eventType === 'gate_start') {
            const gateType = lastEvent.rawEvent.payload?.gate_type || 'gate';
            return `正在运行检查点：${gateType}`;
        }

        if (eventType === 'checkpoint_begin') {
            return '正在创建进度点...';
        }

        // 完成的活动
        if (eventType === 'work_item_done' || eventType === 'work_item_complete') {
            return '子任务已完成';
        }

        if (eventType === 'gate_result') {
            const passed = lastEvent.rawEvent.payload?.passed;
            return passed ? '检查点通过' : '检查点失败';
        }

        if (eventType === 'runner_exit') {
            const exitCode = lastEvent.rawEvent.payload?.exit_code ?? 0;
            return exitCode === 0 ? '任务执行完成' : '任务执行失败';
        }

        // 默认：显示最后事件的文本
        return lastEvent.text;
    }
}

export default NextStepPredictor;
