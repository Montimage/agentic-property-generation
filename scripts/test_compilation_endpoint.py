import argparse
import json
from pathlib import Path

from property_agent.tools import (
    MMTCompilationClient,
    MMTCompilationConfig,
)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Send an MMT XML property to the "
            "remote compilation validator."
        )
    )

    parser.add_argument(
        "property",
        type=Path,
        help="Path to the MMT XML property.",
    )

    parser.add_argument(
        "--endpoint",
        required=True,
        help=(
            "Base URL of the MMT compilation "
            "receiver, e.g. "
            "http://192.168.1.50:8000"
        ),
    )

    args = parser.parse_args()

    xml = args.property.read_text(
        encoding="utf-8"
    )

    client = MMTCompilationClient(
        config=MMTCompilationConfig(
            base_url=args.endpoint
        )
    )

    print(
        "Checking endpoint health..."
    )

    health = client.check_health()

    print(
        json.dumps(
            health,
            indent=2,
        )
    )

    if not health.get(
        "ok",
        False,
    ):
        raise SystemExit(
            "MMT compilation endpoint "
            "is not healthy."
        )

    print()
    print(
        "Sending property for compilation..."
    )

    result = client.compile_xml(
        xml=xml,
        filename=args.property.name,
    )

    print(
        json.dumps(
            result.model_dump(
                mode="json"
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()