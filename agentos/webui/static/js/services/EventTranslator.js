/**
 * EventTranslator - 将技术事件转换为用户友好的叙事文本
 *
 * PR-V5: Timeline View - 叙事时间线
 *
 * 功能:
 * - 将19种Runner事件类型翻译为人话
 * - 提供图标、文本和级别（info/warning/error/success）
 * - 支持特殊情况和异常解释
 *
 * Usage:
 * ```javascript
 * const friendlyEvent = EventTranslator.translate(rawEvent);
 * // { icon: '🚀', text: '启动任务执行器', level: 'info', ... }
 * ```
 */

// 阶段图标映射
const PHASE_ICONS = {
    'planning': '📋',
    'executing': '⚙️',
    'verifying': '🔍',
    'done': '✅',
    'failed': '❌',
    'blocked': '🚧'
};

// 阶段中文名称映射
const PHASE_NAMES = {
    'planning': '规划',
    'executing': '执行',
    'verifying': '验证',
    'done': '完成',
    'failed': '失败',
    'blocked': '阻塞'
};

// 事件类型模板映射（19种核心事件类型）
const EVENT_TEMPLATES = {
    // ========== Runner 生命周期 ==========
    'runner_spawn': {
        icon: '🚀',
        text: (payload) => {
            const pid = payload?.runner_pid || 'unknown';
            const version = payload?.runner_version || 'v1';
            return `启动任务执行器（PID: ${pid}, Version: ${version}）`;
        },
        level: 'info'
    },

    'runner_exit': {
        icon: '🏁',
        text: (payload) => {
            const exitCode = payload?.exit_code ?? 0;
            const reason = payload?.reason || payload?.explanation || '正常退出';
            return exitCode === 0
                ? `执行器正常退出（${reason}）`
                : `执行器异常退出（退出码: ${exitCode}, ${reason}）`;
        },
        level: (payload) => (payload?.exit_code === 0 ? 'success' : 'error')
    },

    // ========== 阶段转换 ==========
    'phase_enter': {
        icon: (payload) => PHASE_ICONS[payload?.phase] || '📍',
        text: (payload) => {
            const phase = payload?.phase || 'unknown';
            const phaseName = PHASE_NAMES[phase] || phase;
            return `进入 ${phaseName} 阶段`;
        },
        level: 'info'
    },

    'phase_exit': {
        icon: (payload) => {
            const phase = payload?.phase;
            if (phase === 'done') return '✅';
            if (phase === 'failed') return '❌';
            return '➡️';
        },
        text: (payload) => {
            const phase = payload?.phase || 'unknown';
            const phaseName = PHASE_NAMES[phase] || phase;
            return `完成 ${phaseName} 阶段`;
        },
        level: (payload) => {
            const phase = payload?.phase;
            if (phase === 'done') return 'success';
            if (phase === 'failed') return 'error';
            return 'info';
        }
    },

    // ========== Work Items（子任务派发） ==========
    'WORK_ITEMS_EXTRACTED': {
        icon: '📦',
        text: (payload) => {
            const count = payload?.count || payload?.total_items || 0;
            return `提取到 ${count} 个子任务待执行`;
        },
        level: 'info'
    },

    'work_item_dispatched': {
        icon: '📤',
        text: (payload) => {
            const itemId = payload?.work_item_id || payload?.span_id || 'unknown';
            const workType = payload?.work_type || '子任务';
            return `派发子任务 #${itemId}（类型: ${workType}）`;
        },
        level: 'info'
    },

    'work_item_start': {
        icon: '▶️',
        text: (payload) => {
            const itemId = payload?.work_item_id || 'unknown';
            const workType = payload?.work_type || '任务';
            return `开始执行子任务 #${itemId}（${workType}）`;
        },
        level: 'info'
    },

    'WORK_ITEM_STARTED': {
        icon: '▶️',
        text: (payload) => {
            const itemId = payload?.work_item_id || payload?.span_id || 'unknown';
            return `子任务 #${itemId} 已启动`;
        },
        level: 'info'
    },

    'work_item_done': {
        icon: '✅',
        text: (payload) => {
            const itemId = payload?.work_item_id || 'unknown';
            const workType = payload?.work_type || '任务';
            return `子任务 #${itemId} 完成（${workType}）`;
        },
        level: 'success'
    },

    'work_item_complete': {
        icon: '✅',
        text: (payload) => {
            const itemId = payload?.work_item_id || 'unknown';
            return `子任务 #${itemId} 执行成功`;
        },
        level: 'success'
    },

    'WORK_ITEM_COMPLETED': {
        icon: '✅',
        text: (payload) => {
            const itemId = payload?.work_item_id || payload?.span_id || 'unknown';
            return `子任务 #${itemId} 已完成`;
        },
        level: 'success'
    },

    'work_item_failed': {
        icon: '❌',
        text: (payload) => {
            const itemId = payload?.work_item_id || 'unknown';
            const reason = payload?.reason || payload?.error || '执行失败';
            return `子任务 #${itemId} 失败（${reason}）`;
        },
        level: 'error'
    },

    'WORK_ITEM_FAILED': {
        icon: '❌',
        text: (payload) => {
            const itemId = payload?.work_item_id || payload?.span_id || 'unknown';
            const error = payload?.error || '未知错误';
            return `子任务 #${itemId} 执行失败（${error}）`;
        },
        level: 'error'
    },

    // ========== Checkpoints（进度点） ==========
    'checkpoint_begin': {
        icon: '💾',
        text: (payload) => {
            const checkpointType = payload?.checkpoint_type || 'checkpoint';
            return `开始创建进度点（${checkpointType}）`;
        },
        level: 'info'
    },

    'checkpoint_commit': {
        icon: '💾',
        text: (payload) => {
            const checkpointId = payload?.checkpoint_id || 'unknown';
            const evidenceCount = payload?.evidence_refs
                ? Object.keys(payload.evidence_refs).length
                : 0;
            return evidenceCount > 0
                ? `保存进度点 ${checkpointId}（已验证 ${evidenceCount} 项证据）`
                : `保存进度点 ${checkpointId}`;
        },
        level: 'success'
    },

    'checkpoint_verified': {
        icon: '✅',
        text: (payload) => {
            const checkpointId = payload?.checkpoint_id || 'unknown';
            return `进度点 ${checkpointId} 验证通过`;
        },
        level: 'success'
    },

    'checkpoint_invalid': {
        icon: '⚠️',
        text: (payload) => {
            const checkpointId = payload?.checkpoint_id || 'unknown';
            const reason = payload?.reason || '数据不一致';
            return `进度点 ${checkpointId} 验证失败（${reason}）`;
        },
        level: 'warning'
    },

    // ========== Evidence（证据收集） ==========
    'evidence_collected': {
        icon: '📎',
        text: (payload) => {
            const evidenceType = payload?.evidence_type || 'evidence';
            const evidenceId = payload?.evidence_id || 'unknown';
            return `收集证据：${evidenceType} (ID: ${evidenceId})`;
        },
        level: 'info'
    },

    // ========== Gates（检查点） ==========
    'gate_start': {
        icon: '🚦',
        text: (payload) => {
            const gateType = payload?.gate_type || 'gate';
            return `开始运行检查点：${gateType}`;
        },
        level: 'info'
    },

    'gate_result': {
        icon: (payload) => payload?.passed ? '✅' : '❌',
        text: (payload) => {
            const gateType = payload?.gate_type || 'gate';
            const passed = payload?.passed;

            if (passed) {
                return `检查点通过：${gateType}`;
            } else {
                const reasonCode = payload?.reason_code || '未知原因';
                const hint = payload?.hint || '';
                return hint
                    ? `检查点失败：${gateType}（${reasonCode} - ${hint}）`
                    : `检查点失败：${gateType}（${reasonCode}）`;
            }
        },
        level: (payload) => payload?.passed ? 'success' : 'error'
    },

    'GATE_VERIFICATION_RESULT': {
        icon: (payload) => payload?.passed || payload?.success ? '✅' : '❌',
        text: (payload) => {
            const gateType = payload?.gate_type || payload?.type || 'gate';
            const passed = payload?.passed || payload?.success;

            if (passed) {
                return `检查点验证通过：${gateType}`;
            } else {
                const reason = payload?.reason || payload?.error || '验证失败';
                return `检查点验证失败：${gateType}（${reason}）`;
            }
        },
        level: (payload) => (payload?.passed || payload?.success) ? 'success' : 'error'
    },

    // ========== Recovery（恢复） ==========
    'recovery_detected': {
        icon: '🔄',
        text: (payload) => {
            const taskId = payload?.task_id || 'unknown';
            const reason = payload?.reason || '检测到中断';
            return `检测到任务中断（${reason}）`;
        },
        level: 'warning'
    },

    'recovery_resumed_from_checkpoint': {
        icon: '🔄',
        text: (payload) => {
            const checkpointId = payload?.checkpoint_id || 'unknown';
            const phase = payload?.phase || 'unknown';
            return `从进度点 ${checkpointId} 恢复继续（阶段: ${PHASE_NAMES[phase] || phase}）`;
        },
        level: 'info'
    },

    'recovery_requeued': {
        icon: '🔄',
        text: (payload) => {
            const taskId = payload?.task_id || 'unknown';
            return `任务 ${taskId} 已重新加入队列`;
        },
        level: 'info'
    }
};

export class EventTranslator {
    /**
     * 将原始事件转换为用户友好的叙事事件
     *
     * @param {Object} event - 原始事件对象
     * @param {string} event.event_type - 事件类型
     * @param {Object} event.payload - 事件载荷
     * @param {string} event.created_at - 创建时间
     * @param {number} event.seq - 事件序列号
     * @returns {Object} 友好事件对象
     */
    static translate(event) {
        const template = EVENT_TEMPLATES[event.event_type];

        if (!template) {
            // 未知事件类型，返回默认格式
            return {
                icon: '📋',
                text: `事件: ${event.event_type}`,
                level: 'info',
                timestamp: event.created_at,
                seq: event.seq,
                rawEvent: event,
                explanation: event.payload?.explanation || event.payload?.hint || null
            };
        }

        // 解析图标（可能是函数）
        const icon = typeof template.icon === 'function'
            ? template.icon(event.payload)
            : template.icon;

        // 解析文本（必须是函数）
        const text = template.text(event.payload);

        // 解析级别（可能是函数）
        const level = typeof template.level === 'function'
            ? template.level(event.payload)
            : template.level;

        // 提取解释/提示
        const explanation = event.payload?.explanation
            || event.payload?.hint
            || event.payload?.reason
            || null;

        return {
            icon,
            text,
            level,
            timestamp: event.created_at,
            seq: event.seq,
            span_id: event.span_id,
            phase: event.phase,
            rawEvent: event,
            explanation
        };
    }

    /**
     * 批量翻译事件
     *
     * @param {Array} events - 事件数组
     * @returns {Array} 友好事件数组
     */
    static translateBatch(events) {
        return events.map(event => this.translate(event));
    }

    /**
     * 检查事件是否应该节流（用于聚合）
     *
     * @param {string} eventType - 事件类型
     * @returns {boolean} 是否应该节流
     */
    static shouldThrottle(eventType) {
        // Progress 类事件需要节流
        const throttlePatterns = [
            /progress$/i,
            /heartbeat$/i,
            /lease_renewed$/i
        ];

        return throttlePatterns.some(pattern => pattern.test(eventType));
    }

    /**
     * 获取事件的显示优先级（用于排序）
     *
     * @param {Object} event - 友好事件对象
     * @returns {number} 优先级（数字越大优先级越高）
     */
    static getPriority(event) {
        const priorityMap = {
            'error': 100,
            'warning': 80,
            'success': 60,
            'info': 40
        };

        return priorityMap[event.level] || 0;
    }

    /**
     * 判断是否为关键事件（不应被过滤）
     *
     * @param {Object} event - 友好事件对象
     * @returns {boolean} 是否为关键事件
     */
    static isCritical(event) {
        const criticalLevels = ['error', 'warning'];
        return criticalLevels.includes(event.level);
    }
}

// 导出常量供外部使用
export { PHASE_ICONS, PHASE_NAMES, EVENT_TEMPLATES };

// 默认导出
export default EventTranslator;
