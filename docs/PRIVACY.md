# Privacy: send IDs, never identifiers

Enki's log is append-only and hash-chained: **nothing written to it can be edited or deleted** without breaking the chain. That is the point, and it is also why identifying information must never go in.

## The rule

Events point at things by **your system's internal ID** (a random UUID is ideal). The details stay in your own database, behind your own access controls. If someone needs to know who record `7f3a9c2e…` is, they look it up in your system, and that lookup is itself an event you can log.

**Never put any of these in an event, including in `metadata`:**

- names, initials, signatures
- dates of birth or death, ages over 89
- addresses, postcodes, geographic detail below state level
- phone, fax, email, URLs, IP addresses
- record, account, member, licence, device serial or certificate numbers that a person could be traced by
- photographs, biometrics, free-text notes
- diagnoses, medications, results or any health detail tied to a person

## Do this instead

| Instead of | Send |
|---|---|
| `"patient": "Jane Doe"` | `"target_id": "7f3a9c2e-…", "target_type": "record"` |
| `"changed": {"dob": "1985-03-15"}` | `"metadata": {"changed_fields": ["dob"]}` |
| `"note": "patient called about results"` | `"event_type": "my_clinic.contact.logged"` with only IDs |
| the user's email as `actor_id` | the user's internal ID |

Field **names** ("dob", "address") are fine; field **values** are not.

## Why this works

- Your app stays the system of record. Enki proves *what happened and when*; it never holds the data itself.
- If an event leaks, it reveals only random IDs.
- Access to the real data still goes through your app, so you can log every lookup as an event (`my_clinic.record.accessed`) and audit it in Enki.

## Your responsibilities

Enki gives you tamper-evidence, signed devices and tenant isolation. It does not, by itself, make a system compliant with HIPAA, GDPR or any other law. Encrypt traffic (put Enki behind TLS), restrict who can reach it, protect `enki-data/` and your root password, keep backups, and set retention to what your rules require.
