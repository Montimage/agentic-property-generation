import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
KNOWLEDGE_ROOT = PROJECT_ROOT / "knowledge"

def load_protocol_attributes(protocol: str) -> dict[str, Any]:
    """Load MMT attribute knowledge for a protocol."""

    path = (
        KNOWLEDGE_ROOT
        / "protocols"
        / protocol.lower()
        / "attributes.json"
    )

    if not path.exists():
        raise FileNotFoundError(
            f"No protocol knowledge found for '{protocol}'."
        )

    return json.loads(path.read_text(encoding="utf-8"))


def load_example_index() -> list[dict[str, Any]]:
    """Load metadata for validated property examples."""

    path = KNOWLEDGE_ROOT / "examples" / "index.json"

    if not path.exists():
        raise FileNotFoundError(
            "Property example index was not found."
        )

    return json.loads(path.read_text(encoding="utf-8"))


def load_property_example(relative_path: str) -> str:
    """Load a validated XML property example."""

    path = KNOWLEDGE_ROOT / "examples" / relative_path

    if not path.exists():
        raise FileNotFoundError(
            f"Property example '{relative_path}' was not found."
        )

    return path.read_text(encoding="utf-8")

def has_protocol_knowledge(protocol: str) -> bool:
    """
    Return True when local MMT attribute knowledge
    exists for the requested protocol.
    """

    path = (
        KNOWLEDGE_ROOT
        / "protocols"
        / protocol.lower()
        / "attributes.json"
    )

    return path.exists()

def has_protocol_semantics(
    protocol: str,
) -> bool:
    """
    Return True when verified semantic knowledge exists
    for the requested protocol.
    """

    path = (
        KNOWLEDGE_ROOT
        / "protocols"
        / protocol.lower()
        / "semantics.json"
    )

    return path.exists()

def load_protocol_semantics(
    protocol: str,
) -> dict[str, Any]:
    """
    Load verified semantic knowledge for a protocol.

    Semantic knowledge may describe procedure codes,
    message identifiers, enumerated values, states, or
    other protocol-specific meanings.
    """

    path = (
        KNOWLEDGE_ROOT
        / "protocols"
        / protocol.lower()
        / "semantics.json"
    )

    if not path.exists():
        raise FileNotFoundError(
            "No protocol semantic knowledge found "
            f"for '{protocol}'."
        )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

def list_protocols_with_attribute_knowledge(
) -> list[str]:
    """
    Return protocol names for which local MMT attribute
    knowledge is available.

    A protocol is considered available when its
    knowledge directory contains attributes.json.
    """

    protocols_root = (
        KNOWLEDGE_ROOT
        / "protocols"
    )

    if not protocols_root.exists():
        return []

    protocols = [
        path.parent.name
        for path in protocols_root.glob(
            "*/attributes.json"
        )
    ]

    return sorted(
        set(protocols)
    )