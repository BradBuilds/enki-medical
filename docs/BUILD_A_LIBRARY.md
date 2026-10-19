# Build a library

A **library** defines the event types your apps may send, in your own namespace. Enki accepts an event only if its `event_type` is built in or declared by a library you have **admitted**. Admission pins the library's exact content by hash, so if anyone changes the library afterwards, Enki refuses to load it until it is admitted again. That is what makes your vocabulary governed rather than just configured.

## The whole flow

```bash
python scripts/library.py new my_clinic        # 1. create libraries/my_clinic with example event types
# 2. edit libraries/my_clinic/definitions/my_clinic.event_types.json
python scripts/library.py check my_clinic      # 3. validate and show the content hash
python scripts/library.py admit my_clinic      # 4. pin it in active_set.local.json
```

Then in `.env`:

```
ENKI_ACTIVE_SET=active_set.local.json
ENKI_EVENT_LIBRARIES=my_clinic
```

and restart (`docker compose up -d`). Events of type `my_clinic.record.accessed` (and the others you declared) are now accepted. Try it:

```bash
python examples/connect_app.py --event-type my_clinic.record.accessed
```

Before admission the same event comes back `FULL_REJECT` with `INVALID_EVENT_TYPE`; after, `FULL_ACCEPT`.

## What a library looks like

```
libraries/my_clinic/
  pack.json
  definitions/
    my_clinic.event_types.json
```

`pack.json` names the library, its version, its files and the namespaces it owns:

```json
{
  "pack_id": "my_clinic",
  "version": "0.1.0",
  "name": "my_clinic library",
  "description": "Event types for my_clinic",
  "definitions": [
    {"id": "my_clinic.event_types", "path": "definitions/my_clinic.event_types.json", "type": "custom"}
  ],
  "dependencies": [],
  "namespaces_owned": ["my_clinic"]
}
```

The definition file lists the event types:

```json
{
  "id": "my_clinic.event_types",
  "type": "custom",
  "version": "0.1.0",
  "description": "Event types for the my_clinic library",
  "content": {
    "category": "event_types",
    "event_types": [
      {
        "event_type_id": "my_clinic.record.accessed",
        "label": "Record accessed",
        "category": "access",
        "description": "Someone or something read a record.",
        "typical_fields": ["actor_id", "target_id", "target_type", "timestamp", "scope"]
      }
    ]
  }
}
```

## Rules Enki enforces

- **Namespace.** Every `event_type_id` must start with a namespace in `namespaces_owned` (e.g. `my_clinic.`). A library cannot add or override built-in types such as `assertion.*`.
- **Admission.** A library listed in `ENKI_EVENT_LIBRARIES` must be in the active set with a matching `content_hash`. Edit it, and Enki refuses it (`PACK_HASH_MISMATCH`) until you run `admit` again.
- **Versions.** Bump `version` in `pack.json` when you change event types, then admit again. Old events keep their old types; the chain is never rewritten.
- **Writers cannot assert.** Tier W devices may send your event types but never `assertion.*`.

## Several libraries

List them comma-separated: `ENKI_EVENT_LIBRARIES=my_clinic,lab_results`. Admit each one into the same active set.

## Sharing a library

A library is just a folder. Publish it as its own repository; others copy it into `libraries/`, run `check` to see the same content hash you published, and `admit` it. If the hash differs, the files differ.

## The bundled libraries

| Library | Provides |
|---|---|
| `auditvocab` | built-in event types (`node.*`, `pack.*`, `validation.*`, `assertion.*`, `usage.*`), severities, fields |
| `identity` | actors, entities and scopes (`local`, `shared`, `global`) |
| `assertionvocab` | the assertion lifecycle vocabulary |
| `base60` | base-60 identifiers used for receipt ids |
| `numeric`, `language` | number and language definitions |

The pack format in full: [docs/reference/20-definition-pack-format.md](reference/20-definition-pack-format.md).
