from __future__ import annotations

import argparse

from common import load_project_env

BOOT_ENV_PATH = load_project_env()

from core.settings import DEFAULT_COLLECTION_KEY
from services import collection_service, index_service


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build runtime indexes for the core default collection and optional compatibility routes.")
    parser.add_argument("--collection-key", type=str, help="Optional collection key to rebuild.")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument(
        "--include-compatibility-bundle",
        action="store_true",
        help="When rebuilding the default collection, also refresh the sample-pack compatibility routes.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if BOOT_ENV_PATH:
        print(f"Loaded env: {BOOT_ENV_PATH}")

    if args.collection_key:
        resolved_key = collection_service.resolve_collection_key(args.collection_key)
        if resolved_key is None:
            resolved_key = DEFAULT_COLLECTION_KEY
        target_keys = index_service.expand_reindex_collection_keys(
            resolved_key,
            include_compatibility_bundle=args.include_compatibility_bundle,
        )
    else:
        resolved_key = DEFAULT_COLLECTION_KEY
        target_keys = index_service.expand_reindex_collection_keys(
            DEFAULT_COLLECTION_KEY,
            include_compatibility_bundle=args.include_compatibility_bundle,
        )

    print(f"Reindex target keys: {', '.join(target_keys)}")
    for key in target_keys:
        result = index_service.reindex_single_collection(reset=args.reset, collection_key=key)
        print(
            f"[{key}] docs={result['docs']}/{result['docs_total']} "
            f"chunks={result['chunks']} vectors={result['vectors']}"
        )
        print(f"[{key}] validation={result['validation']['summary_text']}")

    if resolved_key == DEFAULT_COLLECTION_KEY:
        if args.include_compatibility_bundle:
            print("Default build_index run refreshed the core collection and the sample-pack compatibility bundle.")
        else:
            print("Default build_index run refreshed only the core default collection.")
    else:
        print("Selected collection rebuild also refreshed the default all collection.")


if __name__ == "__main__":
    main()
