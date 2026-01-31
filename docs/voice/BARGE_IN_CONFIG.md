# Barge-In Configuration Guide

**AgentOS Voice v0.2 Wave 2 - Interruption Detection**

This guide explains how to configure and tune barge-in detection for voice conversations.

---

## Table of Contents

- [Overview](#overview)
- [How Barge-In Works](#how-barge-in-works)
- [Configuration Parameters](#configuration-parameters)
- [Detection Modes](#detection-modes)
- [Tuning Guidelines](#tuning-guidelines)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Overview

**Barge-in** allows users to interrupt TTS playback by speaking, creating a natural conversational experience. When the system detects user speech during TTS playback, it:

1. **Cancels** ongoing TTS synthesis
2. **Stops** audio playback on client
3. **Resumes** listening for user input

### Key Benefits

✅ **Natural conversation flow**: Users don't have to wait for TTS to finish
✅ **Reduced latency**: Faster turn-taking in dialogue
✅ **Better UX**: More responsive and human-like interaction

---

## How Barge-In Works

### Detection Pipeline

```
┌─────────────┐
│ User speaks │
│ during TTS  │
└──────┬──────┘
       │
       v
┌──────────────────┐
│ Audio captured   │
│ (microphone)     │
└──────┬───────────┘
       │
       v
┌──────────────────┐
│ Energy/VAD       │
│ detection        │
└──────┬───────────┘
       │
       v
   ┌───┴────┐
   │ Speech?│──No──> Continue TTS
   └───┬────┘
       │Yes
       v
┌──────────────────┐
│ Min duration     │
│ check            │
└──────┬───────────┘
       │
       v
   ┌───┴─────────┐
   │ Trigger     │
   │ barge-in    │
   └──────┬──────┘
          │
          v
┌─────────────────┐
│ Cancel TTS      │
│ Stop playback   │
│ Resume listening│
└─────────────────┘
```

### Detection Methods

1. **RMS Energy Threshold**: Detects speech based on audio volume
2. **VAD (Voice Activity Detection)**: Uses WebRTC VAD for more accurate detection
3. **Hybrid (RMS + VAD)**: Triggers if either method detects speech

---

## Configuration Parameters

### BargeInConfig Class

```python
from agentos.core.communication.voice.barge_in import BargeInConfig

config = BargeInConfig(
    enabled=True,
    vad_energy_threshold=0.03,
    detection_mode="rms_or_vad",
    cancel_delay_ms=100,
    min_speech_duration_ms=200
)
```

### Parameter Reference

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `enabled` | bool | `True` | - | Master switch for barge-in |
| `vad_energy_threshold` | float | `0.03` | 0.0 - 1.0 | RMS energy threshold (normalized) |
| `detection_mode` | str | `"rms_or_vad"` | See below | Detection algorithm |
| `cancel_delay_ms` | int | `100` | 0 - 1000 | Delay before cancelling TTS (ms) |
| `min_speech_duration_ms` | int | `200` | 50 - 1000 | Minimum speech duration to trigger (ms) |

### Environment Variables

```bash
# Enable/disable barge-in globally
VOICE_BARGE_IN_ENABLED=true

# Detection mode
VOICE_BARGE_IN_MODE=rms_or_vad

# RMS threshold (0.0 - 1.0)
VOICE_BARGE_IN_THRESHOLD=0.03

# Minimum speech duration (ms)
VOICE_BARGE_IN_MIN_DURATION=200
```

---

## Detection Modes

### 1. RMS-Only Mode (`"rms"`)

**How it works**: Calculates RMS (Root Mean Square) energy of audio and compares to threshold.

**Advantages**:
- Simple, fast, low CPU
- No dependencies (pure Python + NumPy)
- Works with any audio chunk size

**Disadvantages**:
- Sensitive to background noise
- May trigger on non-speech sounds (door slams, keyboard clicks)

**Configuration**:
```python
config = BargeInConfig(
    detection_mode="rms",
    vad_energy_threshold=0.03  # Adjust based on environment
)
```

**Tuning**:
- Quiet environment: `0.01 - 0.02`
- Normal environment: `0.03 - 0.05`
- Noisy environment: `0.05 - 0.1`

### 2. VAD-Only Mode (`"vad"`)

**How it works**: Uses WebRTC VAD (Voice Activity Detection) to distinguish speech from noise.

**Advantages**:
- More accurate than RMS
- Robust to background noise
- Distinguishes speech from non-speech audio

**Disadvantages**:
- Requires `webrtcvad` library
- Only works with specific chunk sizes (10/20/30ms)
- Slightly higher CPU usage

**Configuration**:
```python
config = BargeInConfig(
    detection_mode="vad"
)
```

**Requirements**:
```bash
pip install webrtcvad
```

### 3. Hybrid Mode (`"rms_or_vad"`) - **Recommended**

**How it works**: Triggers if either RMS or VAD detects speech (OR logic).

**Advantages**:
- Best of both worlds
- Lower false negative rate
- Robust to various environments

**Disadvantages**:
- Slightly higher false positive rate
- Falls back to RMS if webrtcvad unavailable

**Configuration**:
```python
config = BargeInConfig(
    detection_mode="rms_or_vad",
    vad_energy_threshold=0.03
)
```

---

## Tuning Guidelines

### Step 1: Determine Your Environment

| Environment | Noise Level | Recommended Threshold |
|-------------|-------------|----------------------|
| Studio/Quiet room | Very low | 0.01 - 0.02 |
| Office | Low | 0.03 - 0.04 |
| Home (typical) | Medium | 0.04 - 0.06 |
| Coffee shop | High | 0.06 - 0.1 |
| Outdoor | Very high | 0.1+ (or disable) |

### Step 2: Test with Sample Audio

```python
import numpy as np
from agentos.core.communication.voice.barge_in import BargeInDetector, BargeInConfig

# Create detector
config = BargeInConfig(
    detection_mode="rms",
    vad_energy_threshold=0.03
)
detector = BargeInDetector(config)

# Simulate TTS playback
detector.start_tts_playback()

# Test with sample audio
audio_chunk = np.random.randint(-5000, 5000, size=1600, dtype=np.int16).tobytes()

result = detector.detect(audio_chunk)
print(f"Barge-in triggered: {result}")
```

### Step 3: Adjust Minimum Duration

**Goal**: Avoid false triggers from brief sounds (coughs, clicks)

| Scenario | Recommended Duration |
|----------|---------------------|
| Very responsive (risky) | 100ms |
| Balanced (default) | 200ms |
| Conservative | 300-500ms |

### Step 4: Monitor False Positives/Negatives

**Metrics to track**:
- False positive rate (trigger without speech)
- False negative rate (miss actual speech)
- User satisfaction (perceived responsiveness)

```python
# Example logging
logger.info(
    f"Barge-in metrics: "
    f"total_triggers={handler.barge_in_count}, "
    f"false_positives={fp_count}, "
    f"false_negatives={fn_count}"
)
```

---

## Troubleshooting

### Issue: Too Many False Triggers

**Symptoms**: Barge-in activates on background noise, typing, etc.

**Solutions**:
1. **Increase threshold**:
   ```python
   config.vad_energy_threshold = 0.05  # was 0.03
   ```

2. **Increase minimum duration**:
   ```python
   config.min_speech_duration_ms = 300  # was 200
   ```

3. **Switch to VAD-only mode**:
   ```python
   config.detection_mode = "vad"
   ```

4. **Add noise gate**: Filter out low-energy audio before detection

### Issue: Misses User Speech

**Symptoms**: User speaks but barge-in doesn't trigger

**Solutions**:
1. **Decrease threshold**:
   ```python
   config.vad_energy_threshold = 0.02  # was 0.03
   ```

2. **Decrease minimum duration**:
   ```python
   config.min_speech_duration_ms = 150  # was 200
   ```

3. **Switch to hybrid mode**:
   ```python
   config.detection_mode = "rms_or_vad"
   ```

4. **Check microphone gain**: Ensure audio levels are adequate

### Issue: Inconsistent Detection

**Symptoms**: Sometimes works, sometimes doesn't

**Solutions**:
1. **Check audio chunk size**: VAD requires 10/20/30ms chunks
2. **Verify TTS state**: Detection only works when `is_playing_tts = True`
3. **Monitor audio levels**: Log RMS values to diagnose

```python
# Debug logging
def detect_with_logging(detector, audio_chunk):
    # Calculate RMS
    audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
    rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2)) / 32768.0

    logger.debug(
        f"Barge-in detection: "
        f"rms={rms:.4f}, "
        f"threshold={detector.config.vad_energy_threshold}, "
        f"is_playing_tts={detector.is_playing_tts}"
    )

    return detector.detect(audio_chunk)
```

---

## Best Practices

### 1. User Preferences

Allow users to customize barge-in behavior:

```python
# Store per-user settings
user_config = {
    "barge_in_enabled": True,
    "sensitivity": "medium"  # low/medium/high
}

# Map to threshold
sensitivity_map = {
    "low": 0.06,     # Less sensitive
    "medium": 0.03,  # Default
    "high": 0.02     # More sensitive
}

config.vad_energy_threshold = sensitivity_map[user_config["sensitivity"]]
```

### 2. Adaptive Thresholds

Adjust thresholds based on detected noise floor:

```python
class AdaptiveBargeInDetector:
    def __init__(self, config):
        self.detector = BargeInDetector(config)
        self.noise_samples = []
        self.noise_floor = 0.01

    def calibrate(self, audio_chunk):
        """Calibrate noise floor during silence."""
        audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
        rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2)) / 32768.0

        self.noise_samples.append(rms)
        if len(self.noise_samples) > 10:
            self.noise_floor = np.percentile(self.noise_samples, 90)
            self.noise_samples = []

            # Update threshold (noise floor + margin)
            self.detector.config.vad_energy_threshold = self.noise_floor + 0.02
```

### 3. Context-Aware Detection

Disable barge-in for critical messages:

```python
async def synthesize_with_context(tts_provider, text, priority):
    if priority == "critical":
        # Disable barge-in for critical messages
        detector.config.enabled = False

    async for chunk in tts_provider.synthesize(text, "alloy"):
        yield chunk

    # Re-enable after critical message
    detector.config.enabled = True
```

### 4. Visual Feedback

Provide visual cues for barge-in state:

```javascript
// Frontend: Show barge-in indicator
function updateBargeInState(isListening) {
  const indicator = document.getElementById('barge-in-indicator');

  if (isListening) {
    indicator.classList.add('active');
    indicator.textContent = 'Listening... (speak to interrupt)';
  } else {
    indicator.classList.remove('active');
    indicator.textContent = '';
  }
}
```

### 5. A/B Testing

Test different configurations with user groups:

```python
# Assign users to test groups
def get_barge_in_config(user_id):
    group = hash(user_id) % 3

    if group == 0:
        # Control group
        return BargeInConfig(vad_energy_threshold=0.03)
    elif group == 1:
        # Test group A (more sensitive)
        return BargeInConfig(vad_energy_threshold=0.02)
    else:
        # Test group B (less sensitive)
        return BargeInConfig(vad_energy_threshold=0.04)
```

---

## Advanced Configuration

### Custom Detection Logic

Implement custom detection by subclassing:

```python
from agentos.core.communication.voice.barge_in import BargeInDetector

class CustomBargeInDetector(BargeInDetector):
    def _detect_custom(self, audio_chunk: bytes) -> bool:
        """Custom detection logic."""
        # Example: Detect specific keyword
        # (requires speech recognition)
        return self.detect_keyword(audio_chunk, "stop")

    def detect(self, audio_chunk: bytes, sample_rate: int = 16000) -> bool:
        # Use custom logic in addition to RMS/VAD
        custom_result = self._detect_custom(audio_chunk)

        if custom_result:
            return True

        # Fall back to standard detection
        return super().detect(audio_chunk, sample_rate)
```

---

## Related Documentation

- [TTS User Guide](./TTS_USER_GUIDE.md)
- [Voice API Documentation](/docs/VOICE_API_DOCUMENTATION.md)
- [ADR-016: TTS Audio Chunking Strategy](/docs/adr/ADR-016-voice-tts-chunking.md)

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/agentos/agentos/issues
- Voice Channel: `#voice` in Discord
- Email: voice-support@agentos.org
