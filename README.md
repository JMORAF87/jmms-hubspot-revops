# HubSpot RevOps Control System

A HubSpot-centered Revenue Operations system that connects opportunity intelligence, deterministic CRM synchronization, workflow orchestration, and Revenue Leak monitoring.

Built as a working JM Multiservices engineering project and sanitized here as a standalone technical portfolio implementation.

## What It Solves

CRM automation becomes risky when multiple systems can modify the same commercial state without clear ownership.

This project separates those responsibilities:

~~~text
Opportunity Intelligence
        ↓
Human Approval
        ↓
Deterministic Integration
        ↓
HubSpot CRM
        ↓
Revenue Leak Monitoring
~~~

The result is a system designed to:

- synchronize approved opportunities into HubSpot
- avoid duplicate Deals
- preserve human-owned CRM state
- maintain Contact / Company / Deal relationships
- identify operational Revenue Leak conditions
- orchestrate workflows through n8n
- execute and validate automation through GitHub Actions
- keep consequential CRM logic deterministic

---

## Architecture

~~~mermaid
flowchart LR

    A[Opportunity Sources]
    B[Opportunity Intelligence]
    C{Human Approval}
    D[Python Integration]
    E[HubSpot CRM]
    F[Revenue Leak Monitor]
    G[CRM Health Status]

    H[n8n]
    I[GitHub Actions]
    J[AI Assistance]

    A --> B
    B --> C
    C -->|Approved| D
    D --> E
    E --> F
    F --> G

    H --> I
    I --> D
    I --> F

    J -. Research / enrichment .-> B
~~~

### Responsibility Model

| Layer | Responsibility |
|---|---|
| Opportunity intelligence | Discovery, qualification, pursuit decisions |
| Human approval | Controls entry into the CRM execution path |
| Python | Identity, mapping, idempotency, validation, business rules |
| HubSpot | Contacts, Companies, Deals, pipeline state, commercial history |
| Revenue Leak Monitor | Deterministic CRM health classification |
| n8n | Operator-facing orchestration |
| GitHub Actions | CI, remote execution pattern, tests, validation |
| AI | Research, enrichment, recommendations — not CRM source of truth |

---

## Core Capabilities

### Stable Cross-System Identity

Each source opportunity has a stable external ID:

~~~text
opportunity_id
        ↓
jmms_external_opportunity_id
~~~

The HubSpot property is configured as unique and acts as the reconciliation key.

---

### Idempotent Deal Synchronization

~~~text
external ID absent
        ↓
CREATE Deal

external ID present
        ↓
UPDATE existing Deal
~~~

Repeated executions reconcile against the same CRM record rather than creating duplicates.

---

### CRM Ownership Boundaries

The integration deliberately separates source-owned data from human-owned CRM state.

Opportunity synchronization can manage fields such as:

- acquisition source
- qualification score
- known opportunity value
- external identity

HubSpot retains ownership of:

- Deal stage
- Deal owner
- activities
- tasks
- Next step
- commercial progression

This prevents background synchronization from reversing human CRM work.

---

### Contact / Company / Deal Associations

The implementation validates the relationship graph:

~~~text
Contact
    ↓
Primary Company

Deal
    ↓
Primary Company

Deal
    ↓
Contact
~~~

Repeated runs reconcile deterministic records and associations.

---

## Revenue Leak Monitor

The Revenue Leak Monitor evaluates open Deals using deterministic business rules.

Current states:

- `Healthy`
- `Data Incomplete`
- `Missing Next Step`
- `Follow-up Overdue`
- `Stale Opportunity`
- `Close Date Overdue`

Rule precedence:

~~~text
Data Incomplete
        ↓
Close Date Overdue
        ↓
Follow-up Overdue
        ↓
Missing Next Step
        ↓
Stale Opportunity
        ↓
Healthy
~~~

The monitor owns only the dedicated Revenue Leak Status property.

It does **not** autonomously:

- move Deal stages
- change Deal owners
- create consequential tasks
- invent Deal values
- approve opportunities

---

## Tested Control Loop

The Lab implementation validated this progression:

~~~text
Data Incomplete
        ↓
CRM relationship / ownership repaired

Missing Next Step
        ↓
Next action added

Healthy
~~~

Re-evaluating an unchanged Healthy Deal produces:

~~~text
current_status = Healthy
proposed_status = Healthy
changed = false
write = NO_CHANGE
~~~

This avoids unnecessary CRM writes.

---

## Automated Tests

Revenue Leak logic is covered by seven deterministic tests:

1. Data Incomplete
2. Close Date Overdue
3. Follow-up Overdue
4. Missing Next Step
5. Stale Opportunity
6. Healthy
7. New Opportunity next-step exception

Run them with:

~~~bash
python3 -m unittest tests/test_revenue_leak_monitor.py -v
~~~

Expected result:

~~~text
Ran 7 tests

OK
~~~

---

## Synthetic Opportunity Dataset

The public repository contains only synthetic demonstration data.

`data/opportunity-log.csv`

No client or production opportunity data is included.

Validate the dataset with:

~~~bash
python3 scripts/validate_opportunity_log.py
~~~

The sample dataset demonstrates:

- stable opportunity identity
- qualification scores
- pursuit decisions
- approval state
- acquisition sources
- engagement-model differences

---

## n8n Orchestration

A sanitized n8n workflow export is included at:

`n8n/hubspot-revops-orchestrator.json`

Architecture:

~~~text
n8n
    ↓
GitHub Actions
    ↓
Python integration
    ↓
HubSpot
~~~

n8n orchestrates execution rather than duplicating Python business logic.

The public workflow contains configuration placeholders rather than private credentials or repository secrets.

---

## Continuous Integration

Public CI is intentionally non-mutating.

`.github/workflows/ci.yml`

It validates:

- Python syntax
- synthetic opportunity data
- Revenue Leak unit tests
- n8n workflow JSON

The public CI workflow does not contain HubSpot credentials and does not perform CRM writes.

---

## Repository Structure

~~~text
.
├── .github/
│   └── workflows/
│       └── ci.yml
├── data/
│   └── opportunity-log.csv
├── docs/
│   ├── architecture.md
│   ├── architecture-visual.md
│   ├── case-study.md
│   └── demo-script.md
├── n8n/
│   └── hubspot-revops-orchestrator.json
├── schema/
│   ├── mappings.md
│   ├── pipeline.md
│   └── properties.md
├── scripts/
│   ├── ensure_opportunity_ids.py
│   └── validate_opportunity_log.py
├── src/
│   ├── read_deals.py
│   ├── revenue_leak_monitor.py
│   ├── sync_growth_os.py
│   ├── update_test_deal.py
│   ├── upsert_deal.py
│   └── upsert_relationships.py
├── tests/
│   └── test_revenue_leak_monitor.py
├── .env.example
├── .gitignore
└── README.md
~~~

---

## Local Validation

Python 3.12+ is recommended.

The core implementation uses Python standard-library modules and does not require a third-party package installation for the included validation suite.

Compile the project:

~~~bash
python3 -m py_compile \
  src/read_deals.py \
  src/update_test_deal.py \
  src/upsert_deal.py \
  src/upsert_relationships.py \
  src/sync_growth_os.py \
  src/revenue_leak_monitor.py \
  scripts/ensure_opportunity_ids.py \
  scripts/validate_opportunity_log.py
~~~

Run tests:

~~~bash
python3 -m unittest tests/test_revenue_leak_monitor.py -v
~~~

Validate sample data:

~~~bash
python3 scripts/validate_opportunity_log.py
~~~

Validate the n8n export:

~~~bash
python3 -m json.tool \
  n8n/hubspot-revops-orchestrator.json \
  >/dev/null
~~~

---

## HubSpot Configuration

The implementation uses a dedicated HubSpot development/test environment.

Expected object access includes:

- Deals read/write
- Contacts read/write
- Companies read/write

A local credential can be supplied through:

~~~bash
HUBSPOT_SERVICE_KEY=...
~~~

See:

`.env.example`

Never commit a real credential.

The public CI workflow deliberately does not require one.

---

## Safety Design

The implementation uses several explicit safety boundaries:

- separate development/test CRM environment
- stable unique external identity
- dry-run-first integration behavior
- explicit approval gate
- explicit write flags
- read-after-write verification
- human ownership of CRM progression
- dedicated Revenue Leak property ownership
- non-mutating public CI
- credentials excluded from Git
- AI excluded from consequential CRM state

---

## Documentation

More detail is available in:

- [`docs/architecture.md`](docs/architecture.md) — complete system design
- [`docs/architecture-visual.md`](docs/architecture-visual.md) — architecture diagrams
- [`docs/case-study.md`](docs/case-study.md) — engineering and RevOps case study
- [`schema/mappings.md`](schema/mappings.md) — synchronization contract
- [`schema/pipeline.md`](schema/pipeline.md) — CRM pipeline design
- [`schema/properties.md`](schema/properties.md) — HubSpot custom property schema

---

## What This Project Demonstrates

### CRM / RevOps

- HubSpot architecture
- pipeline modeling
- custom property governance
- CRM relationship design
- Revenue Leak controls
- operational ownership boundaries

### Integration Engineering

- REST API integration
- stable external identity
- idempotent synchronization
- field normalization
- deterministic reconciliation
- safe mutation patterns

### Automation

- Python
- n8n
- GitHub Actions
- scheduling patterns
- automated validation
- execution observability

### Applied AI Architecture

AI is treated as an intelligence layer for research, enrichment, and recommendations.

Identity, synchronization, CRM health rules, and consequential state changes remain deterministic.

---

## Scope

This repository is a sanitized technical portfolio version of an internal JM Multiservices implementation.

It intentionally excludes:

- client data
- production opportunity records
- credentials
- private repository history
- production account identifiers
- autonomous scheduled CRM writes

No revenue or conversion uplift is claimed from the Lab implementation. V1 was designed to validate system behavior, integration architecture, safety controls, and operational reliability.

---

## V1 Status

Implemented and validated:

- HubSpot CRM architecture
- custom Deal schema
- API read/write
- stable external identity
- idempotent Deal reconciliation
- CRM associations
- approval gating
- deterministic field mapping
- Deal-stage preservation
- Revenue Leak monitoring
- seven automated rule tests
- n8n orchestration
- GitHub Actions validation
- synthetic public dataset
- architecture and case-study documentation

**V1 engineering is complete.**
