"""
Local voice processing module for Family Hub.
This module handles wake word detection and local speech-to-text processing
to maintain privacy by keeping voice processing on the device.
"""

import logging
import threading
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class LocalVoiceProcessor:
    """
    A local voice processor that maintains privacy by processing
    voice commands locally without sending audio to external services.
    """

    def __init__(self, wake_word: str = "kitchen", sensitivity: float = 0.5):
        self.wake_word = wake_word.lower()
        self.sensitivity = sensitivity
        self.is_listening_for_wake_word = True
        self.is_processing_command = False
        self._stop_event = threading.Event()
        self.command_callback: Optional[Callable[[str], None]] = None
        self.wake_word_detected_callback: Optional[Callable[[], None]] = None
        self.audio_buffer = []

    def set_command_callback(self, callback: Callable[[str], None]):
        """Set the callback function to handle recognized commands."""
        self.command_callback = callback

    def set_wake_word_callback(self, callback: Callable[[], None]):
        """Set the callback function when wake word is detected."""
        self.wake_word_detected_callback = callback

    def start_listening(self):
        """Start listening for the wake word."""
        if self.is_listening_for_wake_word:
            logger.info(f"Already listening for wake word: {self.wake_word}")
            return

        self.is_listening_for_wake_word = True
        self._stop_event.clear()

        # Start the listening loop in a separate thread
        listen_thread = threading.Thread(target=self._listening_loop, daemon=True)
        listen_thread.start()

        logger.info(f"Started listening for wake word: {self.wake_word}")

    def stop_listening(self):
        """Stop listening for the wake word."""
        self.is_listening_for_wake_word = False
        self.is_processing_command = False
        self._stop_event.set()
        logger.info("Stopped listening for wake word")

    def _listening_loop(self):
        """Simulated listening loop."""
        while not self._stop_event.is_set() and self.is_listening_for_wake_word:
            # In a real implementation, this would interface with actual audio processing
            # For now we just sleep and the actual processing happens in the frontend
            if not self._stop_event.wait(0.5):
                pass  # Continue waiting

    def process_audio_for_wake_word(self, audio_data: bytes) -> bool:
        """
        Process audio data to detect the wake word.
        In a real implementation, this would interface with Porcupine or similar.
        For now, this would be handled by frontend code.
        """
        # This method exists to maintain the interface for future Porcupine integration
        return False

    def process_audio_for_command(self, audio_data: bytes) -> Optional[str]:
        """
        Process audio data to convert speech to text.
        In a real implementation, this would use Vosk or Whisper locally.
        """
        # This method exists to maintain the interface for future STT integration
        return None

    def simulate_wake_word_detection(self, text_input: str) -> bool:
        """
        Simulate wake word detection from text input for testing purposes.
        """
        return self.wake_word in text_input.lower()


class PrivacyFocusedVoiceProcessor:
    """
    A privacy-focused voice processor that handles local wake word detection
    and command processing without sending audio to external services.
    """

    def __init__(self, wake_word: str = "kitchen"):
        self.wake_word = wake_word
        self.local_processor = LocalVoiceProcessor(wake_word)
        self.is_active = False

    def start_processing(self, command_callback: Callable[[str], None]):
        """Start the local voice processing system."""
        self.local_processor.set_command_callback(command_callback)
        self.local_processor.start_listening()
        self.is_active = True
        logger.info(f"Privacy-focused voice processing started with wake word: {self.wake_word}")

    def stop_processing(self):
        """Stop the local voice processing system."""
        self.local_processor.stop_listening()
        self.is_active = False
        logger.info("Privacy-focused voice processing stopped")

    def process_text_command(self, text: str) -> Dict[str, Any]:
        """
        Process a text command as if it came from local STT processing.
        """
        text_lower = text.lower()
        wake_word_lower = self.wake_word.lower()

        # Check if the wake word is in the text
        if self.local_processor.simulate_wake_word_detection(text):
            # Find the position of the wake word and extract everything after it
            pos = text_lower.find(wake_word_lower)
            if pos != -1:
                # Extract the actual command after the wake word
                command = text[pos + len(self.wake_word) :].strip()
                if command.startswith(","):
                    command = command[1:].strip()  # Remove leading comma and space if present
                return {"status": "command_detected", "command": command, "wake_word_detected": True}
            else:
                # Fallback if find fails for some reason
                command = text_lower.replace(wake_word_lower, "").strip()
                if command.startswith(","):
                    command = command[1:].strip()
                return {"status": "command_detected", "command": command, "wake_word_detected": True}
        else:
            return {"status": "wake_word_not_detected", "command": text, "wake_word_detected": False}

    def is_processing_active(self) -> bool:
        """Check if the local voice processing is active."""
        return self.is_active


# Global instance for the application
local_voice_processor = None


def init_local_processor(wake_word: str = "kitchen") -> PrivacyFocusedVoiceProcessor:
    """Initialize the local voice processor."""
    global local_voice_processor
    local_voice_processor = PrivacyFocusedVoiceProcessor(wake_word)
    return local_voice_processor


def get_local_processor() -> Optional[PrivacyFocusedVoiceProcessor]:
    """Get the global local voice processor instance."""
    return local_voice_processor
