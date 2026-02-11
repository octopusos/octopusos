"""
Speech-to-Text (STT) providers for OctopusOS voice communication.
"""

from octopusos.core.communication.voice.stt.base import ISTTProvider
from octopusos.core.communication.voice.stt.whisper_local import WhisperLocalSTT
from octopusos.core.communication.voice.stt.vad import VADDetector

__all__ = ["ISTTProvider", "WhisperLocalSTT", "VADDetector"]
