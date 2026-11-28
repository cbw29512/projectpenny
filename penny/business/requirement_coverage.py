"""Advisory literal requirement coverage; not a semantic quality verdict."""
import logging
import re
import unicodedata
from dataclasses import dataclass
from hashlib import sha256

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Requirement:
    """Maker-defined identifier and alternative literal phrases."""
    key: str
    phrases: tuple[str, ...]


def _tokens(text):
    return tuple(re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", text).casefold()))


def inspect_coverage(content, requirements):
    """Identify literal evidence or gaps without granting approval.

    A match may be negated, misleading, or irrelevant. A missing phrase
    may have a valid paraphrase. Both require independent review.
    """
    try:
        if type(content) is not str or not 1 <= len(content) <= 6000:
            raise ValueError("invalid checklist content")
        if type(requirements) is not tuple or not 1 <= len(requirements) <= 20:
            raise ValueError("invalid requirement count")
        keys = set()
        findings = []
        words = _tokens(content)
        for requirement in requirements:
            if type(requirement) is not Requirement:
                raise ValueError("invalid requirement")
            key, phrases = requirement.key, requirement.phrases
            if (type(key) is not str or not re.fullmatch(r"[a-z][a-z0-9_-]{0,39}", key)
                    or key in keys or type(phrases) is not tuple
                    or not 1 <= len(phrases) <= 5):
                raise ValueError("invalid requirement definition")
            keys.add(key)
            alternatives = []
            for phrase in phrases:
                if type(phrase) is not str or not 1 <= len(phrase) <= 100:
                    raise ValueError("invalid requirement phrase")
                tokens = _tokens(phrase)
                if not tokens:
                    raise ValueError("empty requirement phrase")
                alternatives.append(tokens)
            matched = any(
                words[i:i+len(term)] == term
                for term in alternatives
                for i in range(len(words)-len(term)+1)
            )
            findings.append({"key": key, "status": "literal_match" if matched else "not_detected"})
        return {
            "content_sha256": sha256(content.encode("utf-8")).hexdigest(),
            "findings": findings,
            "semantic_quality_verified": False,
            "commercial_release_authorized": False,
        }
    except Exception as exc:
        logger.error("Requirement coverage refused (%s)", type(exc).__name__)
        raise
