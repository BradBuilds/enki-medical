"""
Make, check and admit your own Enki library.

A library is a folder under libraries/ with a pack.json and a definitions/ folder. Enki only
loads libraries that are admitted in an active set with a matching content hash, so a library
that is changed after admission is refused until you admit it again.

    python scripts/library.py new my_clinic                 # create libraries/my_clinic
    python scripts/library.py check my_clinic               # validate it and show its content hash
    python scripts/library.py admit my_clinic               # pin it in active_set.local.json

Then set, in your .env:

    ENKI_ACTIVE_SET=active_set.local.json
    ENKI_EVENT_LIBRARIES=my_clinic

and restart. Events whose event_type your library declares are now accepted at /ingest/events.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

LIBRARIES = ROOT / "libraries"
BASE_ACTIVE_SET = ROOT / "active_set_v3.json"
NAME = re.compile(r"^[a-z][a-z0-9_]{1,40}$")


def _example_event_types(ns: str) -> list[dict]:
    return [
        {
            "event_type_id": f"{ns}.record.created",
            "label": "Record created",
            "category": "records",
            "description": "A record was created in the connected system. Reference it by its internal ID only.",
            "typical_fields": ["actor_id", "target_id", "target_type", "timestamp", "scope"],
            "notes": ["Never put a name, date of birth, address or other identifier in metadata"],
        },
        {
            "event_type_id": f"{ns}.record.updated",
            "label": "Record updated",
            "category": "records",
            "description": "A record changed. List which fields changed, not their values.",
            "typical_fields": ["actor_id", "target_id", "target_type", "timestamp", "scope"],
            "notes": ["metadata.changed_fields lists field names only"],
        },
        {
            "event_type_id": f"{ns}.record.accessed",
            "label": "Record accessed",
            "category": "access",
            "description": "Someone or something read a record. This is your access audit trail.",
            "typical_fields": ["actor_id", "target_id", "target_type", "timestamp", "scope"],
            "notes": ["metadata.fields_accessed lists field names only"],
        },
    ]


def cmd_new(args: argparse.Namespace) -> int:
    name = args.name
    if not NAME.fullmatch(name):
        print("Library names use lowercase letters, digits and underscores, starting with a letter (e.g. my_clinic).")
        return 1
    ns = args.namespace or name
    folder = LIBRARIES / name
    if folder.exists():
        print(f"libraries/{name} already exists; nothing changed.")
        return 1
    (folder / "definitions").mkdir(parents=True)
    definition = {
        "id": f"{ns}.event_types",
        "type": "custom",
        "version": "0.1.0",
        "description": f"Event types for the {name} library",
        "content": {
            "category": "event_types",
            "purpose": "Event types this library adds to Enki. Every id must start with this library's namespace.",
            "event_types": _example_event_types(ns),
        },
    }
    manifest = {
        "pack_id": name,
        "version": "0.1.0",
        "name": f"{name} library",
        "description": f"Event types for {name}",
        "definitions": [{"id": f"{ns}.event_types", "path": f"definitions/{ns}.event_types.json", "type": "custom"}],
        "dependencies": [],
        "namespaces_owned": [ns],
        "metadata": {"license": "choose one"},
    }
    (folder / "definitions" / f"{ns}.event_types.json").write_text(json.dumps(definition, indent=2) + "\n", encoding="utf-8")
    (folder / "pack.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Created libraries/{name}")
    print(f"  pack.json                          namespace '{ns}'")
    print(f"  definitions/{ns}.event_types.json  3 example event types to edit")
    print(f"Next: edit the event types, then  python scripts/library.py check {name}")
    return 0


def _check(name: str) -> tuple[bool, str]:
    from core.packs.loader import load_pack
    from core.spine.content_hash import compute_pack_hash

    folder = LIBRARIES / name
    if not (folder / "pack.json").is_file():
        print(f"libraries/{name}/pack.json not found.")
        return False, ""
    result = load_pack(folder)
    if not result.ok:
        print(f"libraries/{name} is not valid:")
        for e in result.errors:
            print(f"  {getattr(e, 'code', '')}: {getattr(e, 'message', e)}")
        return False, ""
    manifest = json.loads((folder / "pack.json").read_text(encoding="utf-8"))
    owned = tuple(f"{ns}." for ns in manifest.get("namespaces_owned", []))
    bad = [evt.get("event_type_id") for d in result.definitions for evt in d.content.get("event_types", []) or []
           if not str(evt.get("event_type_id", "")).startswith(owned or ("\0",))]
    if bad:
        print(f"These event types are outside the library's namespaces {manifest.get('namespaces_owned')}: {bad}")
        return False, ""
    digest = compute_pack_hash(str(folder))
    return True, digest


def cmd_check(args: argparse.Namespace) -> int:
    ok, digest = _check(args.name)
    if not ok:
        return 1
    print(f"libraries/{args.name} is valid.")
    print(f"content hash: {digest}")
    return 0


def cmd_admit(args: argparse.Namespace) -> int:
    ok, digest = _check(args.name)
    if not ok:
        return 1
    from core.spine.active_set import load_active_set_strict

    target = ROOT / args.active_set
    data = json.loads((target if target.exists() else BASE_ACTIVE_SET).read_text(encoding="utf-8"))
    manifest = json.loads((LIBRARIES / args.name / "pack.json").read_text(encoding="utf-8"))
    entry = {"pack_id": args.name, "version": manifest["version"], "content_hash": digest}
    data["packs"] = [p for p in data["packs"] if p.get("pack_id") != args.name] + [entry]
    data.setdefault("metadata", {})["name"] = "Local active set"
    data["metadata"]["description"] = "Shipped packs plus your own admitted libraries"
    target.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    load_active_set_strict(target)  # proves every pinned pack still matches its hash
    print(f"Admitted {args.name} {manifest['version']} into {args.active_set}")
    print("Set in .env:")
    print(f"  ENKI_ACTIVE_SET={args.active_set}")
    print(f"  ENKI_EVENT_LIBRARIES={args.name}")
    print("then restart Enki.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Make, check and admit your own Enki library.")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("new", help="create a new library with example event types")
    p.add_argument("name")
    p.add_argument("--namespace", help="event type prefix (default: the library name)")
    p.set_defaults(func=cmd_new)
    p = sub.add_parser("check", help="validate a library and show its content hash")
    p.add_argument("name")
    p.set_defaults(func=cmd_check)
    p = sub.add_parser("admit", help="pin a library in your local active set")
    p.add_argument("name")
    p.add_argument("--active-set", default="active_set.local.json")
    p.set_defaults(func=cmd_admit)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
