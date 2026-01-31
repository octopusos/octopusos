# Voice TTS User Guide

**AgentOS Voice v0.2 Wave 2 - Text-to-Speech**

This guide covers how to use Text-to-Speech (TTS) capabilities in AgentOS Voice communication.

---

## Table of Contents

- [Overview](#overview)
- [Supported TTS Providers](#supported-tts-providers)
- [Available Voices](#available-voices)
- [Configuration](#configuration)
- [API Usage](#api-usage)
- [Speed Control](#speed-control)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)

---

## Overview

AgentOS Voice TTS enables the system to convert text responses into natural-sounding speech. Key features:

- **Streaming synthesis**: Low latency, progressive audio delivery
- **Multiple voices**: Choose from various voice profiles
- **Speed control**: Adjust playback speed (0.25x - 4.0x)
- **Cancellation support**: Barge-in friendly (user can interrupt)
- **Provider abstraction**: Easily switch between TTS engines

---

## Supported TTS Providers

### 1. OpenAI TTS (Recommended for Production)

**Features**:
- High-quality neural voices (tts-1, tts-1-hd models)
- 6 distinct voice profiles
- Streaming synthesis support
- Multilingual (50+ languages)

**Requirements**:
- OpenAI API key
- Internet connection

**Configuration**:
```bash
# Environment variables
VOICE_TTS_PROVIDER=openai
OPENAI_API_KEY=sk-...
VOICE_TTS_MODEL=tts-1           # or tts-1-hd for higher quality
VOICE_TTS_CHUNK_SIZE=4096       # Audio chunk size in bytes
```

**Pricing** (as of 2026-01):
- tts-1: $15 per 1M characters
- tts-1-hd: $30 per 1M characters

### 2. Mock TTS (Testing Only)

**Features**:
- Generates silence or simple tones
- No external dependencies
- Useful for testing and development

**Configuration**:
```bash
VOICE_TTS_PROVIDER=mock
VOICE_TTS_MOCK_GENERATE_TONE=false   # true for tone, false for silence
```

---

## Available Voices

### OpenAI Voices

| Voice ID | Name | Gender | Characteristics | Best For |
|----------|------|--------|-----------------|----------|
| `alloy` | Alloy | Neutral | Balanced, versatile | General purpose |
| `echo` | Echo | Male | Clear, professional | News, announcements |
| `fable` | Fable | Male | British accent, expressive | Storytelling |
| `onyx` | Onyx | Male | Deep, authoritative | Narration |
| `nova` | Nova | Female | Friendly, warm | Customer service |
| `shimmer` | Shimmer | Female | Soft, soothing | Meditation, reading |

### Mock Voices

| Voice ID | Name | Characteristics |
|----------|------|-----------------|
| `test-voice-1` | Test Voice 1 | Mock silence/tone |
| `test-voice-2` | Test Voice 2 | Mock silence/tone |

---

## Configuration

### Session Creation with TTS

When creating a voice session, specify TTS configuration:

```python
from agentos.core.communication.voice.service import VoiceService

voice_service = VoiceService()

session = await voice_service.create_session(
    user_id="user-123",
    provider="local",
    tts_config={
        "provider": "openai",
        "voice_id": "alloy",
        "speed": 1.0,
        "model": "tts-1"
    }
)
```

### WebUI Configuration

In AgentOS WebUI, configure TTS in Voice settings:

```json
{
  "tts": {
    "provider": "openai",
    "default_voice": "alloy",
    "default_speed": 1.0,
    "chunk_size": 4096,
    "format": "opus"
  }
}
```

---

## API Usage

### Basic Text Synthesis

```python
from agentos.core.communication.voice.tts.openai_provider import OpenAITTSProvider

# Initialize provider
tts_provider = OpenAITTSProvider(
    api_key="sk-...",
    model="tts-1",
    chunk_size=4096
)

# Synthesize text
text = "Hello, this is AgentOS speaking."
voice_id = "alloy"

async for audio_chunk in tts_provider.synthesize(text, voice_id, speed=1.0):
    # Send audio_chunk to WebSocket client
    await websocket.send_bytes(audio_chunk)
```

### Get Available Voices

```python
voices = tts_provider.get_voices()

for voice in voices:
    print(f"{voice['id']}: {voice['name']} ({voice['language']})")
    print(f"  {voice['description']}")
```

### Cancel Ongoing Synthesis (Barge-In)

```python
# Start synthesis
synthesis = tts_provider.synthesize("Long text...", "alloy")
request_id = None

async for chunk in synthesis:
    # Track request ID
    if not request_id and tts_provider.active_requests:
        request_id = list(tts_provider.active_requests.keys())[0]

    # User interrupts (barge-in detected)
    if user_interrupted:
        cancelled = await tts_provider.cancel(request_id)
        break
```

---

## Speed Control

### Speed Parameter

Control playback speed using the `speed` parameter (0.25 - 4.0):

```python
# Slow (0.5x)
async for chunk in tts_provider.synthesize(text, "alloy", speed=0.5):
    await send_audio(chunk)

# Normal (1.0x)
async for chunk in tts_provider.synthesize(text, "alloy", speed=1.0):
    await send_audio(chunk)

# Fast (2.0x)
async for chunk in tts_provider.synthesize(text, "alloy", speed=2.0):
    await send_audio(chunk)
```

### Speed Clamping

- Values < 0.25 are clamped to 0.25
- Values > 4.0 are clamped to 4.0

### Use Cases

| Speed | Use Case |
|-------|----------|
| 0.5x | Language learning, accessibility |
| 0.75x | Careful listening, complex content |
| 1.0x | Normal speech (default) |
| 1.25x | Efficient listening |
| 1.5x | Fast review |
| 2.0x+ | Rapid skimming |

---

## Error Handling

### Common Errors

#### 1. Invalid API Key

```python
try:
    async for chunk in tts_provider.synthesize(text, voice_id):
        await send_audio(chunk)
except Exception as e:
    if "authentication" in str(e).lower():
        logger.error("OpenAI API key is invalid")
        # Fallback to mock TTS or error message
```

#### 2. Rate Limiting

```python
from openai import RateLimitError

try:
    async for chunk in tts_provider.synthesize(text, voice_id):
        await send_audio(chunk)
except RateLimitError:
    logger.warning("Rate limit exceeded, retrying...")
    await asyncio.sleep(5)
    # Retry synthesis
```

#### 3. Invalid Voice ID

```python
# Voice ID validation is automatic - falls back to "alloy"
async for chunk in tts_provider.synthesize(text, "invalid-voice"):
    # Will use "alloy" instead
    await send_audio(chunk)
```

---

## Best Practices

### 1. Chunk Size Optimization

**Recommended**: 4096 bytes (default)

- Larger chunks: Lower overhead, higher latency
- Smaller chunks: Lower latency, higher overhead

```python
# Low latency (real-time)
tts_provider = OpenAITTSProvider(chunk_size=2048)

# Balanced (default)
tts_provider = OpenAITTSProvider(chunk_size=4096)

# Low overhead (batch)
tts_provider = OpenAITTSProvider(chunk_size=8192)
```

### 2. Voice Selection

**Guidelines**:
- Use consistent voice per session for user familiarity
- Match voice to content type (e.g., "echo" for news)
- Consider user preferences (store in profile)

### 3. Text Preprocessing

**Optimize for TTS**:
- Remove markdown formatting (`**bold**` → `bold`)
- Expand abbreviations (`Dr.` → `Doctor`)
- Add pronunciation hints (use IPA if needed)
- Split very long texts into sentences

```python
def preprocess_for_tts(text):
    # Remove markdown
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)

    # Expand common abbreviations
    text = text.replace("Dr.", "Doctor")
    text = text.replace("Mr.", "Mister")
    text = text.replace("Ms.", "Miss")

    return text
```

### 4. Caching (Optional)

For frequently used phrases, consider caching synthesized audio:

```python
import hashlib

class TTSCache:
    def __init__(self):
        self.cache = {}

    def get_cache_key(self, text, voice_id, speed):
        return hashlib.md5(f"{text}:{voice_id}:{speed}".encode()).hexdigest()

    async def get_or_synthesize(self, tts_provider, text, voice_id, speed):
        key = self.get_cache_key(text, voice_id, speed)

        if key in self.cache:
            return self.cache[key]

        # Synthesize and cache
        chunks = []
        async for chunk in tts_provider.synthesize(text, voice_id, speed):
            chunks.append(chunk)

        audio = b"".join(chunks)
        self.cache[key] = audio
        return audio
```

### 5. Monitoring and Logging

**Track key metrics**:
- Synthesis duration
- TTFB (Time To First Byte)
- Chunk count
- Cancellation rate (barge-in)

```python
import time
import logging

logger = logging.getLogger(__name__)

async def synthesize_with_metrics(tts_provider, text, voice_id):
    start_time = time.time()
    first_byte_time = None
    chunk_count = 0

    async for chunk in tts_provider.synthesize(text, voice_id):
        if chunk_count == 0:
            first_byte_time = time.time() - start_time

        chunk_count += 1
        yield chunk

    total_time = time.time() - start_time

    logger.info(
        f"TTS synthesis completed: "
        f"TTFB={first_byte_time:.2f}s, "
        f"total={total_time:.2f}s, "
        f"chunks={chunk_count}"
    )
```

---

## Troubleshooting

### Issue: High Latency (TTFB > 2s)

**Possible causes**:
- Network latency to OpenAI API
- Large chunk size
- Model selection (tts-1-hd is slower than tts-1)

**Solutions**:
- Reduce chunk_size to 2048
- Switch to tts-1 model
- Use local TTS provider (if available)

### Issue: Audio Cutoff (Incomplete Synthesis)

**Possible causes**:
- Premature cancellation
- Network interruption
- Request timeout

**Solutions**:
- Check barge-in detection threshold
- Increase timeout settings
- Verify WebSocket connection stability

### Issue: Voice Quality Issues

**Possible causes**:
- Text preprocessing problems
- Speed too fast/slow
- Audio codec issues

**Solutions**:
- Improve text preprocessing
- Adjust speed to 0.75-1.25 range
- Use tts-1-hd for better quality

---

## Related Documentation

- [Barge-In Configuration Guide](./BARGE_IN_CONFIG.md)
- [Voice API Documentation](/docs/VOICE_API_DOCUMENTATION.md)
- [ADR-016: TTS Audio Chunking Strategy](/docs/adr/ADR-016-voice-tts-chunking.md)

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/agentos/agentos/issues
- Voice Channel: `#voice` in Discord
- Email: voice-support@agentos.org
