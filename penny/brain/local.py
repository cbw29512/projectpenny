"""Parent wall-clock bound around the single local inference request."""
import json
import logging
import subprocess
import sys

logger = logging.getLogger(__name__)


class LocalBrain:
    def generate(self, prompt: str, timeout: float) -> str:
        if not isinstance(prompt, str) or not 1 <= len(prompt) <= 2000:
            raise ValueError("invalid prompt")
        if not 0 < timeout <= 90:
            raise ValueError("invalid inference budget")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "penny.brain.transport"],
                input=json.dumps(prompt), text=True, encoding="utf-8",
                capture_output=True, timeout=timeout, check=True,
            )
            return json.loads(result.stdout)
        except Exception as exc:
            # Timeout does NOT prove the Ollama server stopped generating.
            logger.error("Local brain request failed (%s)", type(exc).__name__)
            raise RuntimeError("local brain request uncertain") from None
