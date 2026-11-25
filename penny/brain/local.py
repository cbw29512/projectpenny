"""Parent wall-clock bound around the single local inference request."""
import json
import logging
import subprocess
import sys

from .request import MAX_WIRE_BYTES, memory_request, render_request

logger = logging.getLogger(__name__)


class LocalBrain:
    def generate(self, prompt: str, timeout: float) -> str:
        return self._invoke(prompt, timeout)

    def generate_with_memory(self, prompt: str, timeout: float, memories) -> str:
        return self._invoke(memory_request(prompt, memories), timeout)

    def _invoke(self, request, timeout: float) -> str:
        try:
            render_request(request)
            if not 0 < timeout <= 90:
                raise ValueError("invalid inference budget")
            wire = json.dumps(request, ensure_ascii=True)
            if len(wire) > MAX_WIRE_BYTES:
                raise ValueError("inference request too large")
        except (ValueError, TypeError):
            logger.warning("Local brain request rejected")
            raise
        try:
            result = subprocess.run(
                [sys.executable, "-m", "penny.brain.transport"],
                input=wire, text=True, encoding="utf-8",
                capture_output=True, timeout=timeout, check=True,
            )
            return json.loads(result.stdout)
        except Exception as exc:
            # Timeout does NOT prove the Ollama server stopped generating.
            logger.error("Local brain request failed (%s)", type(exc).__name__)
            raise RuntimeError("local brain request uncertain") from None
