# VoiceAudioPlayer 快速参考

## 📦 安装

```html
<!-- 在 HTML 中加载 -->
<script src="/static/js/voice/audio_player.js"></script>
```

## 🚀 快速开始

```javascript
// 1. 初始化
const player = new VoiceAudioPlayer();

// 2. 恢复音频上下文（在用户交互后）
await player.resumeContext();

// 3. 播放 TTS 音频
await player.enqueueChunk(base64Audio, {
    codec: 'pcm_s16le',
    sample_rate: 16000,
    channels: 1
});
```

## 📖 API 参考

### 构造函数

```javascript
new VoiceAudioPlayer()
```

### 核心方法

#### `enqueueChunk(base64Audio, format)`
播放 TTS 音频块

```javascript
await player.enqueueChunk(base64Audio, {
    codec: 'pcm_s16le' | 'opus',  // 编解码器
    sample_rate: 16000,            // 采样率
    channels: 1                    // 声道数
});
```

#### `stopPlayback()`
立即停止播放（Barge-in）

```javascript
player.stopPlayback();
```

#### `resumeContext()`
恢复音频上下文（处理 autoplay 策略）

```javascript
await player.resumeContext();
```

### 音量控制

```javascript
player.setVolume(0.5);  // 0.0 - 1.0
player.mute();
player.unmute();
```

### 统计信息

```javascript
const stats = player.getStats();
// {
//     chunksReceived: 10,
//     chunksPlayed: 8,
//     totalBytesReceived: 160000,
//     queueLength: 2,
//     isPlaying: true,
//     isBuffering: false,
//     audioContextState: 'running'
// }
```

### 资源管理

```javascript
player.reset();    // 重置状态
player.destroy();  // 销毁并清理资源
```

## 🔧 配置

### 缓冲阈值

```javascript
player.bufferThreshold = 3;  // 缓冲 3 个音频块后开始播放
```

### 默认采样率

```javascript
player.sampleRate = 16000;  // 默认 16kHz
```

## 🎯 使用场景

### 场景 1: 流式 TTS 播放

```javascript
const player = new VoiceAudioPlayer();
await player.resumeContext();

// 接收多个音频块
for (const chunk of ttsChunks) {
    await player.enqueueChunk(chunk.audio, chunk.format);
}
```

### 场景 2: Barge-in 停止

```javascript
// 用户说话时停止播放
micCapture.on('speech_start', () => {
    player.stopPlayback();
});
```

### 场景 3: 音量渐变

```javascript
// 淡入
for (let v = 0; v <= 1; v += 0.1) {
    player.setVolume(v);
    await sleep(100);
}

// 淡出
for (let v = 1; v >= 0; v -= 0.1) {
    player.setVolume(v);
    await sleep(100);
}
```

## ⚠️ 注意事项

### 1. Autoplay 策略
必须在用户交互后恢复音频上下文：

```javascript
button.addEventListener('click', async () => {
    await player.resumeContext();
    // 开始播放...
});
```

### 2. 内存管理
长时间运行需要定期清理：

```javascript
// 每 5 分钟重置
setInterval(() => {
    if (!player.isPlaying) {
        player.reset();
    }
}, 5 * 60 * 1000);
```

### 3. 错误处理

```javascript
try {
    await player.enqueueChunk(base64Audio, format);
} catch (error) {
    console.error('播放失败:', error.message);
    // 回退策略...
}
```

## 🌐 浏览器支持

| 浏览器 | 最低版本 | 状态 |
|--------|---------|------|
| Chrome | 90+ | ✅ |
| Edge | 90+ | ✅ |
| Firefox | 90+ | ✅ |
| Safari | 14+ | ✅ |

## 🔍 调试

### 启用日志

```javascript
// 音频播放器会自动输出日志
// 在浏览器控制台查看 [VoiceAudioPlayer] 前缀的日志
```

### 监控统计

```javascript
setInterval(() => {
    console.log(player.getStats());
}, 1000);
```

## 📚 相关文档

- [完整实施报告](./TASK_10_AUDIO_PLAYER_IMPLEMENTATION_REPORT.md)
- [Voice API 文档](./VOICE_API_DOCUMENTATION.md)
- [测试指南](../../tests/frontend/test_audio_player.html)

## 🐛 常见问题

### Q: 音频播放卡顿？
A: 增加缓冲阈值 `player.bufferThreshold = 3`

### Q: AudioContext suspended？
A: 在用户交互后调用 `await player.resumeContext()`

### Q: Opus 解码失败？
A: 回退到 PCM 格式或检查浏览器支持

### Q: 内存占用过高？
A: 定期调用 `player.reset()` 清理队列

---

**最后更新**: 2026-02-01
