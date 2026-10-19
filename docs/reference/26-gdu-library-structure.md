# GDU Library Structure — Expanded Definition Architecture

**Status:** Authoritative Specification  
**Governance:** Definition Taxonomy & Composition  
**Audience:** Core developers, definition authors, architects  
**Created:** 2026-01-09  
**Depends On:** 25-gdu-core-master-plan.md  
**Authority:** This document defines the structural organization of definitions within the GDU

---

## Purpose

This document establishes the **expanded library structure** for the Governed Definition Universe (GDU). It defines how definitions are organized by type, how depth is managed without combinatorial explosion, and how illegal semantic combinations are prevented structurally.

---

## Core Principle

> **Definitions are organized by semantic role, not by domain.  
> Composition is explicit, constrained, and auditable.**

This enables:
- **Controlled depth:** Complex meanings built from simple primitives
- **Structural validation:** Invalid combinations rejected at composition time
- **Semantic clarity:** Each definition has a single, well-defined purpose

---

## Library Taxonomy (Logical Organization)

The **library structure** describes the **logical organization of definitions**, not the physical filesystem layout.

### Important Distinction

- **Logical taxonomy:** How definitions are conceptually organized (entities, attributes, values, etc.)
- **Physical storage:** Definitions installed in `gdu/registry/packs/{PACK_DIGEST}/definitions/`
- **Relationship:** Packs may contain definitions from multiple logical categories

### Example: base60 Pack (Single Pack, Multiple Logical Categories)

```
gdu/registry/packs/e742a368cf1f.../
├── pack.json
└── definitions/
    ├── base60.system.json      (entities category)
    ├── base60.rules.json       (operators category)
    ├── base60.glyphs.json      (language/senses category)
    └── base60.digits.json      (values category)
```

These definitions logically belong to different categories, but are physically packaged together for installation.

### LDU Authoring Example (Mutable Workspace)

Before admission, definitions are authored and organized in the LDU:

```
ldu/
├── entities/
│   └── myentity.json
├── attributes/
│   └── myattr.json
└── compositions/
    └── mycomposition.json
```

This is the authoring workspace only. **Runtime never reads from LDU.**

### Library Taxonomy Levels

Definitions, regardless of how they are packaged, logically belong to these categories:

```
libraries/ (logical organization, NOT filesystem)
  entities/          # Base objects and concepts
  attributes/        # Properties that entities can have
  values/            # Concrete instances of attribute values
  constraints/       # Rules governing valid combinations
  compositions/      # Explicit combinations of entities + attributes + values
  operators/         # Transformation and computation primitives
  language/          # Natural language mapping system
    tokens/
    lexemes/
    senses/
    phrases/
    sentences/
    mappings/
  policy/            # Governance rules and permissions
  network/           # Network topology and structure definitions
  units/             # Measurement units and conversions
  logic/             # Logical operators and expressions
  time/              # Temporal concepts and relationships
  identity/          # Identity types and schemas (existing)
```

---

## About This Taxonomy

The sections below describe what types of definitions belong in each logical category. When you author definitions in the LDU workspace, you will organize them according to this taxonomy. When definitions are admitted into the GDU (via admission ceremony), they are installed into immutable packs, but their **logical category** remains constant according to this classification.

### Physical → Logical Mapping

When reading this document:
- Treat each major heading (entities, attributes, etc.) as a **semantic category**
- Not all categories are separate packs
- Some packs contain definitions from multiple categories
- The taxonomy ensures definitions are semantically grouped, not necessarily physically separated

---

## Library Folder Structure

```
gdu/
  libraries/
    entities/          # Base objects and concepts
    attributes/        # Properties that entities can have
    values/            # Concrete instances of attribute values
    constraints/       # Rules governing valid combinations
    compositions/      # Explicit combinations of entities + attributes + values
    operators/         # Transformation and computation primitives
    language/          # Natural language mapping system
      tokens/          # Atomic language units
      lexemes/         # Word forms and variants
      senses/          # Meaning distinctions
      phrases/         # Multi-word units
      sentences/       # Structured statements
      mappings/        # Language → definition links
    policy/            # Governance rules and permissions
    network/           # Network topology and structure definitions
    units/             # Measurement units and conversions
    logic/             # Logical operators and expressions
    time/              # Temporal concepts and relationships
    identity/          # Identity types and schemas (existing)
```

### entities/

**Purpose:** Define base objects and concepts that exist independently.

**What lives here:**
- Fundamental objects: `car`, `house`, `person`, `document`
- Abstract concepts: `transaction`, `session`, `event`
- Categories: `vehicle`, `building`, `organization`

**What does NOT live here:**
- Properties (those go in `attributes/`)
- Specific instances (those go in `values/` or external data stores)
- Combinations (those go in `compositions/`)

**Example entities:**
```
car
bicycle
mansion
apartment
server
database
account
user
```

**Key constraint:**  
Entities are **self-contained** — they do not reference attributes or values in their base definition.

---

### attributes/

**Purpose:** Define properties that can be applied to entities.

**What lives here:**
- Physical properties: `color`, `size`, `weight`, `temperature`
- Structural properties: `capacity`, `dimensions`, `topology`
- State properties: `status`, `mode`, `phase`
- Relational properties: `owner`, `parent`, `member_of`

**What does NOT live here:**
- The entities themselves
- Specific values (those go in `values/`)
- Combination rules (those go in `constraints/`)

**Example attributes:**
```
color
size
weight
owner
status
capacity
temperature
location
```

**Key constraint:**  
Attributes define the **schema** of a property without specifying concrete values.

**Attribute Definition Structure:**
```json
{
  "id": "attribute.color",
  "type": "attribute",
  "version": "1.0.0",
  "content": {
    "name": "color",
    "value_type": "enumeration",
    "applicable_to": ["physical_entity"],
    "cardinality": "single"
  }
}
```

---

### values/

**Purpose:** Define concrete instances of attribute values.

**What lives here:**
- Color values: `red`, `blue`, `green`, `#FF0000`
- Size values: `small`, `medium`, `large`, `10cm`
- Status values: `active`, `inactive`, `pending`
- Unit values: `meter`, `kilogram`, `second`

**What does NOT live here:**
- Entities or attributes
- Combinations (those go in `compositions/`)
- Transformation rules (those go in `operators/`)

**Example values:**
```
red
blue
small
large
active
inactive
metric_ton
```

**Key constraint:**  
Values are **atomic** — they represent a single, indivisible semantic unit.

**Value Definition Structure:**
```json
{
  "id": "value.color.red",
  "type": "value",
  "version": "1.0.0",
  "content": {
    "attribute": "attribute.color",
    "name": "red",
    "representation": "#FF0000",
    "constraints": []
  }
}
```

---

### constraints/

**Purpose:** Define rules that govern valid combinations and relationships.

**What lives here:**
- Mutual exclusivity: `color values are mutually exclusive`
- Cardinality: `entity can have at most one size`
- Type compatibility: `color only applies to physical entities`
- Value ranges: `temperature must be between -273.15°C and infinity`
- Dependency rules: `if status=active then owner must be set`

**What does NOT live here:**
- Entities, attributes, or values
- Specific combinations (those go in `compositions/`)
- Business logic (that lives in application code)

**Example constraints:**
```
color_mutual_exclusivity
size_cardinality_one
temperature_physical_lower_bound
owner_required_when_active
```

**Key constraint:**  
Constraints are **declarative** — they describe rules without implementing enforcement logic.

**Constraint Definition Structure:**
```json
{
  "id": "constraint.color_mutual_exclusivity",
  "type": "constraint",
  "version": "1.0.0",
  "content": {
    "name": "color_mutual_exclusivity",
    "rule_type": "mutual_exclusion",
    "scope": {
      "attribute": "attribute.color"
    },
    "description": "An entity can have only one color value at a time",
    "enforcement": "composition_time"
  }
}
```

---

### compositions/

**Purpose:** Explicitly define valid combinations of entities, attributes, and values.

**What lives here:**
- Attributed entities: `red_car`, `small_house`, `active_user`
- Multi-attribute combinations: `small_red_car`, `large_blue_mansion`
- Complex compositions: `fast_red_sports_car_with_leather_interior`

**What does NOT live here:**
- Base definitions (entities, attributes, values)
- Constraints (those are referenced, not defined here)
- Instance data (specific car #12345)

**Example compositions:**
```
red_car
small_house
active_user
small_red_car
large_blue_mansion
high_capacity_server
```

**Key constraint:**  
Compositions are **validated** against all applicable constraints before admission.

**Composition Definition Structure:**
```json
{
  "id": "composition.small_red_car",
  "type": "composition",
  "version": "1.0.0",
  "content": {
    "name": "small_red_car",
    "base_entity": "entity.car",
    "attributes": [
      {
        "attribute": "attribute.size",
        "value": "value.size.small"
      },
      {
        "attribute": "attribute.color",
        "value": "value.color.red"
      }
    ],
    "constraints_satisfied": [
      "constraint.color_mutual_exclusivity",
      "constraint.size_cardinality_one"
    ]
  }
}
```

---

### operators/

**Purpose:** Define transformation, computation, and query primitives.

**What lives here:**
- Arithmetic: `add`, `subtract`, `multiply`, `divide`
- Comparison: `equals`, `greater_than`, `less_than`
- Logical: `and`, `or`, `not`, `implies`
- Set operations: `union`, `intersection`, `difference`
- Transformations: `convert_units`, `normalize`, `aggregate`
- Filters: `where`, `select`, `project`

**What does NOT live here:**
- Data values
- Business logic implementations
- Specific computation instances

**Example operators:**
```
add
equals
greater_than
union
convert_temperature
normalize_string
filter_by_attribute
```

**Key constraint:**  
Operators are **pure** — they have well-defined inputs, outputs, and no side effects.

**Operator Definition Structure:**
```json
{
  "id": "operator.equals",
  "type": "operator",
  "version": "1.0.0",
  "content": {
    "name": "equals",
    "operator_type": "comparison",
    "signature": {
      "inputs": [
        {"name": "left", "type": "any"},
        {"name": "right", "type": "any"}
      ],
      "output": {"type": "boolean"}
    },
    "properties": ["reflexive", "symmetric", "transitive"],
    "description": "Tests if two values are equal"
  }
}
```

---

### language/

**Purpose:** Map natural language to formal definitions.

This is the **most complex** library, with six sub-levels:

#### language/tokens/

**Purpose:** Atomic language units (characters, symbols, punctuation).

**Examples:**
```
token.letter.a
token.digit.5
token.punctuation.comma
token.symbol.dollar
```

#### language/lexemes/

**Purpose:** Word forms and their variants (lemma, inflections).

**Examples:**
```
lexeme.car (singular)
lexeme.cars (plural)
lexeme.run (base form)
lexeme.running (gerund)
lexeme.ran (past tense)
```

#### language/senses/

**Purpose:** Distinct meanings of a word.

**Examples:**
```
sense.bank.financial_institution
sense.bank.river_edge
sense.run.move_quickly
sense.run.operate_software
sense.run.manage_business
```

**Why this exists:**  
Prevents ambiguity by forcing explicit sense selection during mapping.

#### language/phrases/

**Purpose:** Multi-word units with specific meanings.

**Examples:**
```
phrase.red_car
phrase.small_house
phrase.high_performance_server
phrase.active_user_session
```

#### language/sentences/

**Purpose:** Structured statements and assertions.

**Examples:**
```
sentence.the_car_is_red
sentence.user_status_is_active
sentence.server_capacity_exceeds_threshold
```

#### language/mappings/

**Purpose:** Explicit links between language and formal definitions.

**Examples:**
```
mapping.red_car → composition.red_car
mapping.the_car_is_red → assertion(entity.car, attribute.color, value.red)
mapping.small_house → composition.small_house
```

**Key constraint:**  
Mappings are **bidirectional** — they enable both natural language → definition and definition → natural language.

**Mapping Definition Structure:**
```json
{
  "id": "mapping.red_car",
  "type": "language_mapping",
  "version": "1.0.0",
  "content": {
    "phrase": "phrase.red_car",
    "target": "composition.red_car",
    "language": "en-US",
    "confidence": 1.0,
    "context": ["automotive", "description"]
  }
}
```

---

### policy/

**Purpose:** Governance rules, permissions, and access control.

**What lives here:**
- Access policies: `admin_full_access`, `read_only_user`
- Governance rules: `requires_two_approvals`, `minimum_review_period`
- Audit requirements: `log_all_writes`, `retain_for_7_years`
- Compliance rules: `gdpr_right_to_deletion`, `hipaa_phi_protection`

**Example policies:**
```
admin_full_access
read_only_user
requires_two_approvals
log_all_writes
gdpr_compliant_retention
```

---

### network/

**Purpose:** Network topology and structure definitions (protocol-independent).

**What lives here:**
- Node types: `peer`, `relay`, `gateway`, `edge_node`
- Topology patterns: `mesh`, `star`, `tree`, `hybrid`
- Connection types: `persistent`, `transient`, `broadcast`
- Network roles: `coordinator`, `participant`, `observer`

**What does NOT live here (yet):**
- Protocol specifications (future work)
- Message formats (future work)
- Routing algorithms (future work)

**Example definitions:**
```
node.peer
node.relay
topology.mesh
connection.persistent
role.coordinator
```

**Key constraint:**  
Network definitions are **structural placeholders** only — no protocol semantics yet.

---

### units/

**Purpose:** Measurement units and conversion rules.

**What lives here:**
- Base units: `meter`, `kilogram`, `second`, `ampere`
- Derived units: `newton`, `joule`, `watt`, `volt`
- Conversions: `inch_to_meter`, `fahrenheit_to_celsius`
- Dimensions: `length`, `mass`, `time`, `temperature`

**Example definitions:**
```
unit.meter
unit.kilogram
unit.second
unit.newton
conversion.inch_to_meter
dimension.length
```

---

### logic/

**Purpose:** Logical operators and expressions.

**What lives here:**
- Boolean operators: `and`, `or`, `not`, `xor`, `implies`
- Quantifiers: `forall`, `exists`, `unique`
- Predicates: `is_valid`, `is_member`, `satisfies`

**Example definitions:**
```
logic.and
logic.or
logic.not
logic.implies
logic.forall
logic.exists
```

---

### time/

**Purpose:** Temporal concepts and relationships.

**What lives here:**
- Time units: `second`, `minute`, `hour`, `day`, `year`
- Temporal relations: `before`, `after`, `during`, `overlaps`
- Time points: `instant`, `interval`, `duration`
- Calendars: `gregorian`, `julian`, `iso8601`

**Example definitions:**
```
time.second
time.minute
time.hour
temporal.before
temporal.after
temporal.during
calendar.gregorian
```

---

### identity/

**Purpose:** Identity types and schemas (existing library).

**What lives here:**
- Identity types: `user`, `service`, `device`, `organization`
- Credential types: `password`, `api_key`, `certificate`, `token`
- Identity attributes: `email`, `username`, `public_key`

**Example definitions:**
```
identity.user
identity.service
identity.device
credential.api_key
```

**Note:** This library already exists — it is included here for completeness.

---

## Depth Management Without Explosion

### The Depth Problem

If we naively allow all combinations:
- 100 entities × 50 attributes × 200 values = **1,000,000** compositions
- Adding constraints, operators, language mappings → **exponential explosion**

### The Solution: Explicit Composition

**Rule:** Only explicitly defined compositions are valid.

#### Level 1: Base Entity

```
entity.car
```

**Definition:**
- A vehicle with four wheels
- No attributes specified
- No values attached

#### Level 2: Single Attribute

```
composition.red_car
  = entity.car + attribute.color = value.red
```

**Definition:**
- Base entity: `car`
- One attribute: `color`
- One value: `red`

#### Level 3: Multiple Attributes

```
composition.small_red_car
  = entity.car
    + attribute.size = value.small
    + attribute.color = value.red
```

**Definition:**
- Base entity: `car`
- Two attributes: `size`, `color`
- Two values: `small`, `red`

#### Level 4: Complex Composition

```
composition.fast_small_red_sports_car
  = entity.car
    + attribute.size = value.small
    + attribute.color = value.red
    + attribute.performance = value.fast
    + attribute.category = value.sports
```

**Definition:**
- Base entity: `car`
- Four attributes
- Four values

### Depth Control Mechanisms

1. **Explicit admission:** Each composition must pass admission ceremony
2. **Constraint validation:** All constraints checked before admission
3. **Use-based creation:** Compositions created only when needed
4. **Reference counting:** Track which compositions are actually used

**Result:**  
Instead of 1 million potential combinations, we admit only the ~1000 that are actually needed.

---

## Language Depth Linking

Language mapping works through **progressive refinement**:

### Example: "The small red car is fast"

#### Step 1: Sentence Structure

```
sentence.the_small_red_car_is_fast
  → subject: "the small red car"
  → predicate: "is fast"
```

#### Step 2: Phrase Decomposition

```
phrase.the_small_red_car
  → determiner: "the"
  → adjective: "small"
  → adjective: "red"
  → noun: "car"
```

#### Step 3: Lexeme Extraction

```
lexeme.the (determiner)
lexeme.small (adjective)
lexeme.red (adjective)
lexeme.car (noun, singular)
```

#### Step 4: Sense Disambiguation

```
sense.small.physical_dimension (not "insignificant")
sense.red.color (not "communist" or "angry")
sense.car.vehicle (not "railroad_car")
```

#### Step 5: Mapping to Definitions

```
mapping.small → value.size.small
mapping.red → value.color.red
mapping.car → entity.car
mapping.fast → value.performance.fast
```

#### Step 6: Composition Resolution

```
composition.small_red_car
  = entity.car
    + attribute.size = value.small
    + attribute.color = value.red
```

#### Step 7: Operator Application

```
operator.assign(
  subject = composition.small_red_car,
  attribute = attribute.performance,
  value = value.fast
)
```

### Why This Prevents Explosion

- Each layer is **explicitly defined**
- Mappings are **manually validated**
- Compositions are **constraint-checked**
- Only **used paths** are created

**Result:**  
Natural language processing becomes a **graph traversal** problem, not a generation problem.

---

## Preventing Illegal Meanings Structurally

### Type System

Each definition has a **type** that constrains what it can combine with:

```
entity → can have attributes
attribute → can have values
value → cannot have further attributes
```

### Example 1: "bike car"

**Attempt:**
```
composition.bike_car
  = entity.bike + entity.car
```

**Structural rejection:**
```
ERROR: Cannot compose two entities
RULE: Compositions must be entity + attribute + value
SUGGESTION: Did you mean "bike_and_car_collection"?
```

### Example 2: "big small mansion"

**Attempt:**
```
composition.big_small_mansion
  = entity.mansion
    + attribute.size = value.big
    + attribute.size = value.small
```

**Constraint rejection:**
```
ERROR: Constraint violation
CONSTRAINT: size_cardinality_one
RULE: Entity can have at most one size value
CONFLICTING VALUES: value.big, value.small
```

### Example 3: "red temperature"

**Attempt:**
```
composition.red_temperature
  = entity.temperature
    + attribute.color = value.red
```

**Type rejection:**
```
ERROR: Attribute not applicable to entity
ENTITY: temperature (abstract measurement)
ATTRIBUTE: color (physical property)
RULE: color only applies to physical entities
SUGGESTION: Did you mean "high temperature" or "red object"?
```

### Structural Prevention Mechanisms

1. **Type checking:** Enforce entity/attribute/value hierarchy
2. **Applicability rules:** Attributes declare which entities they can apply to
3. **Cardinality constraints:** Enforce single/multiple value limits
4. **Mutual exclusivity:** Prevent contradictory values
5. **Domain constraints:** Group-related definitions and prevent cross-domain mixing

---

## Example Definition Templates

### Entity Definition Template

```json
{
  "id": "entity.car",
  "type": "entity",
  "version": "1.0.0",
  "content": {
    "name": "car",
    "category": "vehicle",
    "description": "A four-wheeled motor vehicle",
    "base_attributes": [],
    "supertypes": ["entity.vehicle"],
    "subtypes": ["entity.sedan", "entity.suv"]
  }
}
```

### Attribute Definition Template

```json
{
  "id": "attribute.color",
  "type": "attribute",
  "version": "1.0.0",
  "content": {
    "name": "color",
    "value_type": "enumeration",
    "applicable_to": ["entity.physical_object"],
    "cardinality": "single",
    "required": false,
    "default": null,
    "constraints": ["constraint.color_mutual_exclusivity"]
  }
}
```

### Value Definition Template

```json
{
  "id": "value.color.red",
  "type": "value",
  "version": "1.0.0",
  "content": {
    "attribute": "attribute.color",
    "name": "red",
    "representation": {
      "hex": "#FF0000",
      "rgb": [255, 0, 0],
      "name": "red"
    },
    "constraints": [],
    "aliases": ["crimson", "scarlet"]
  }
}
```

### Constraint Definition Template

```json
{
  "id": "constraint.color_mutual_exclusivity",
  "type": "constraint",
  "version": "1.0.0",
  "content": {
    "name": "color_mutual_exclusivity",
    "rule_type": "mutual_exclusion",
    "scope": {
      "attribute": "attribute.color"
    },
    "description": "An entity can have only one color value at a time",
    "enforcement": "composition_time",
    "severity": "error",
    "message": "Cannot assign multiple color values to a single entity"
  }
}
```

### Composition Definition Template

```json
{
  "id": "composition.small_red_car",
  "type": "composition",
  "version": "1.0.0",
  "content": {
    "name": "small_red_car",
    "base_entity": "entity.car",
    "attributes": [
      {
        "attribute": "attribute.size",
        "value": "value.size.small"
      },
      {
        "attribute": "attribute.color",
        "value": "value.color.red"
      }
    ],
    "constraints_satisfied": [
      "constraint.color_mutual_exclusivity",
      "constraint.size_cardinality_one"
    ],
    "created": "2026-01-09T00:00:00Z",
    "creator": "identity.user.definition_author",
    "usage_count": 42
  }
}
```

### Language Mapping Definition Template

```json
{
  "id": "mapping.red_car",
  "type": "language_mapping",
  "version": "1.0.0",
  "content": {
    "phrase": "phrase.red_car",
    "target": "composition.red_car",
    "language": "en-US",
    "confidence": 1.0,
    "context": ["automotive", "description"],
    "alternatives": [
      "composition.car_that_is_red",
      "composition.red_colored_car"
    ],
    "disambiguation_hints": [
      "If 'red' could mean 'communist', choose different sense",
      "If 'car' could mean 'railroad_car', check context"
    ]
  }
}
```

---

## Composition Validation Process

When a new composition is proposed:

### Step 1: Type Check

```
✓ Base is an entity
✓ All attributes are valid attribute definitions
✓ All values are valid value definitions
```

### Step 2: Applicability Check

```
✓ attribute.color applies to entity.car (car is physical_object)
✓ attribute.size applies to entity.car (car has dimensions)
```

### Step 3: Cardinality Check

```
✓ Only one size value assigned
✓ Only one color value assigned
```

### Step 4: Constraint Check

```
✓ color_mutual_exclusivity: only one color assigned
✓ size_cardinality_one: only one size assigned
```

### Step 5: Domain Check

```
✓ All definitions from compatible domains
✓ No cross-domain conflicts
```

### Step 6: Admission

```
✓ All checks pass
✓ Composition admitted to GDU
✓ Activation record created
```

---

## Anti-Patterns (Prohibited)

### ❌ Domain-Based Organization

**Wrong:**
```
gdu/
  libraries/
    automotive/        # NO - organized by domain
    healthcare/        # NO - organized by domain
    finance/           # NO - organized by domain
```

**Why wrong:**  
Domains cross-cut semantic roles. A "patient" is an entity, "blood_pressure" is an attribute, "high" is a value.

### ❌ Implicit Composition

**Wrong:**
```python
# Allowing runtime composition without admission
car = Entity("car")
car.color = "red"  # Implicit composition - NOT ALLOWED
```

**Why wrong:**  
Bypasses constraint validation and admission ceremony.

### ❌ Value-Carrying Entities

**Wrong:**
```json
{
  "id": "entity.red_car",
  "type": "entity",
  "content": {
    "name": "red_car",
    "color": "red"  // NO - entities don't carry values
  }
}
```

**Why wrong:**  
Conflates entity definition with composition. "Red car" is a composition, not an entity.

### ❌ Unscoped Attributes

**Wrong:**
```json
{
  "id": "attribute.color",
  "type": "attribute",
  "content": {
    "name": "color",
    "applicable_to": "everything"  // NO - too broad
  }
}
```

**Why wrong:**  
Abstract concepts don't have colors. Must specify physical_object or similar scope.

---

## Implementation Notes

### Phase 1: Core Libraries

**Priority:** Critical  
**Deliverables:**
1. Create folder structure
2. Define base entities (10-20 common entities)
3. Define base attributes (10-15 common attributes)
4. Define base values (50-100 common values)
5. Define base constraints (5-10 critical constraints)

### Phase 2: Composition System

**Priority:** High  
**Dependencies:** Phase 1  
**Deliverables:**
1. Implement composition validator
2. Implement constraint checker
3. Create 20-30 example compositions
4. Add composition tests

### Phase 3: Language Mapping

**Priority:** Medium  
**Dependencies:** Phase 1, 2  
**Deliverables:**
1. Define token/lexeme/sense hierarchy
2. Create 50-100 common mappings
3. Implement disambiguation logic
4. Add language mapping tests

### Phase 4: Advanced Libraries

**Priority:** Low  
**Dependencies:** Phase 1, 2  
**Deliverables:**
1. Expand operators library
2. Expand units library
3. Expand time library
4. Expand logic library

---

## Explicitly Out of Scope

This specification does NOT cover:

- **Update security:** How definitions are modified (future doc)
- **Network protocol:** How nodes communicate (future doc)
- **Replication:** How GDU is synchronized (future doc)
- **Query language:** How to search/filter definitions (future doc)
- **Version migration:** How definitions evolve (future doc)
- **Performance optimization:** Caching, indexing strategies (future doc)

---

## Integration with GDU Core

This library structure extends 25-gdu-core-master-plan.md:

- **GDU boundary:** All libraries are within GDU (admitted via ceremony)
- **LDU workflow:** Draft definitions in LDU, admit to GDU libraries
- **Resolution:** Loader resolves from library structure by canonical ID
- **Digest:** `ACTIVE_GDU_DIGEST` includes all library definitions
- **Fail-closed:** Missing definitions in any library trigger fatal error

---

## Appendix A: Complete Folder Tree

```
gdu/
  libraries/
    entities/
      pack.json
      defs/
        car__1.0.0.json
        bicycle__1.0.0.json
        mansion__1.0.0.json
        server__1.0.0.json
        user__1.0.0.json
        transaction__1.0.0.json
    
    attributes/
      pack.json
      defs/
        color__1.0.0.json
        size__1.0.0.json
        weight__1.0.0.json
        status__1.0.0.json
        capacity__1.0.0.json
        owner__1.0.0.json
    
    values/
      pack.json
      defs/
        color.red__1.0.0.json
        color.blue__1.0.0.json
        size.small__1.0.0.json
        size.large__1.0.0.json
        status.active__1.0.0.json
        status.inactive__1.0.0.json
    
    constraints/
      pack.json
      defs/
        color_mutual_exclusivity__1.0.0.json
        size_cardinality_one__1.0.0.json
        temperature_lower_bound__1.0.0.json
        owner_required_when_active__1.0.0.json
    
    compositions/
      pack.json
      defs/
        red_car__1.0.0.json
        small_house__1.0.0.json
        active_user__1.0.0.json
        small_red_car__1.0.0.json
        large_blue_mansion__1.0.0.json
    
    operators/
      pack.json
      defs/
        add__1.0.0.json
        equals__1.0.0.json
        greater_than__1.0.0.json
        union__1.0.0.json
        filter__1.0.0.json
    
    language/
      tokens/
        pack.json
        defs/
          letter.a__1.0.0.json
          digit.5__1.0.0.json
          punctuation.comma__1.0.0.json
      
      lexemes/
        pack.json
        defs/
          car__1.0.0.json
          cars__1.0.0.json
          run__1.0.0.json
          running__1.0.0.json
      
      senses/
        pack.json
        defs/
          bank.financial__1.0.0.json
          bank.river__1.0.0.json
          run.move__1.0.0.json
          run.operate__1.0.0.json
      
      phrases/
        pack.json
        defs/
          red_car__1.0.0.json
          small_house__1.0.0.json
          high_performance_server__1.0.0.json
      
      sentences/
        pack.json
        defs/
          the_car_is_red__1.0.0.json
          user_status_is_active__1.0.0.json
      
      mappings/
        pack.json
        defs/
          red_car__1.0.0.json
          small_house__1.0.0.json
          the_car_is_red__1.0.0.json
    
    policy/
      pack.json
      defs/
        admin_full_access__1.0.0.json
        read_only_user__1.0.0.json
        requires_two_approvals__1.0.0.json
    
    network/
      pack.json
      defs/
        node.peer__1.0.0.json
        node.relay__1.0.0.json
        topology.mesh__1.0.0.json
        connection.persistent__1.0.0.json
    
    units/
      pack.json
      defs/
        meter__1.0.0.json
        kilogram__1.0.0.json
        newton__1.0.0.json
        inch_to_meter__1.0.0.json
    
    logic/
      pack.json
      defs/
        and__1.0.0.json
        or__1.0.0.json
        not__1.0.0.json
        implies__1.0.0.json
        forall__1.0.0.json
    
    time/
      pack.json
      defs/
        second__1.0.0.json
        minute__1.0.0.json
        before__1.0.0.json
        after__1.0.0.json
        gregorian__1.0.0.json
    
    identity/
      pack.json
      defs/
        user__1.0.0.json
        service__1.0.0.json
        device__1.0.0.json
        api_key__1.0.0.json
```

---

## Appendix B: Depth vs Breadth Trade-offs

| Approach | Depth | Breadth | Explosion Risk | Maintenance |
|----------|-------|---------|----------------|-------------|
| **Implicit Composition** | Infinite | Infinite | **EXTREME** | Impossible |
| **Domain Silos** | Shallow | Wide | Medium | Hard |
| **Explicit Composition (ENKI)** | Controlled | Managed | **LOW** | Tractable |

**ENKI's approach:**
- Depth is controlled through explicit composition admission
- Breadth is managed through constraint validation
- Explosion is prevented through use-based creation
- Maintenance is tractable through structural organization

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-09 | 1.0.0 | Initial specification |

---

**End of GDU Library Structure Specification**
