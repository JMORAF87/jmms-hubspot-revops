# JMMS HubSpot RevOps Architecture

## Purpose

JMMS HubSpot RevOps V1 is a HubSpot-centered commercial operations system that connects opportunity intelligence, deterministic CRM synchronization, workflow orchestration, and Revenue Leak monitoring.

The architecture deliberately separates responsibilities between systems rather than treating one tool as the entire platform.

Core principle:

~~~text
HubSpot
= operational CRM / commercial system of record

JMMS Growth OS
= opportunity intelligence and approval layer

Python
= deterministic integration and business logic

n8n
= operator-facing workflow orchestration

GitHub Actions
= remote execution, scheduling, validation, and observability

AI
= research / enrichment / recommendations where useful
~~~

Consequential CRM state is not delegated to autonomous AI behavior.

---

## System Roles

### HubSpot CRM

HubSpot is the operational CRM and system of record for:

- Contacts
- Companies
- Deals
- Deal stages
- CRM ownership
- activities
- tasks
- Next step
- commercial history
- Revenue Leak Status

HubSpot does not act as the opportunity discovery engine.

---

### JMMS Growth OS

Growth OS is responsible for:

- opportunity discovery
- opportunity identity
- qualification intelligence
- pursuit decisions
- approval state
- acquisition-source metadata
- known opportunity value
- orchestration context

Growth OS does not replace HubSpot as the operational CRM.

---

### Python Integration Layer

Python contains deterministic integration logic.

Primary modules:

- `read_deals.py`
- `update_test_deal.py`
- `upsert_deal.py`
- `upsert_relationships.py`
- `sync_growth_os.py`
- `revenue_leak_monitor.py`

Responsibilities include:

- HubSpot API access
- field normalization
- stable identity
- idempotent create/update behavior
- CRM relationship synchronization
- approval gating
- Revenue Leak classification
- write safety
- read-after-write verification

Business rules live here rather than being duplicated across n8n nodes.

---

### n8n

n8n is the operator-facing orchestration layer.

Runtime:

Hugging Face-hosted self-managed n8n.

Version-controlled workflow:

`n8n/jmms-hubspot-revops-hubspot-orchestrator.json`

n8n is used to:

- trigger Growth OS / HubSpot operations
- select controlled execution modes
- dispatch GitHub Actions
- wait for the exact downstream execution
- route success or failure

n8n does not duplicate the deterministic Python synchronization logic.

---

### GitHub Actions

GitHub Actions provides the remote execution environment for the integration.

Responsibilities include:

- manual workflow dispatch
- scheduled Revenue Leak monitoring
- Python syntax validation
- Growth OS data validation
- automated unit tests
- controlled execution modes
- execution logs
- run summaries
- downloadable run artifacts

This makes execution independent of the user's local computer.

---

### AI

AI is intentionally outside the CRM source-of-truth boundary.

Appropriate AI use includes:

- opportunity research
- enrichment
- classification assistance
- recommendation generation
- summarization
- analytical support

AI does not directly own:

- Deal stage
- CRM identity
- commercial amount
- final approval state
- Revenue Leak rules
- consequential CRM mutations

---

## Production Architecture

~~~text
                    ┌───────────────────────┐
                    │   Opportunity Sources │
                    │ LinkedIn / Referral / │
                    │ Inbound / Marketplaces│
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │    JMMS Growth OS     │
                    │                       │
                    │ Discovery             │
                    │ Qualification         │
                    │ Pursuit decision      │
                    │ Approval gate         │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │ Deterministic Python  │
                    │ Integration Layer     │
                    │                       │
                    │ Identity              │
                    │ Mapping               │
                    │ Idempotency           │
                    │ Safety controls       │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │      HubSpot CRM      │
                    │                       │
                    │ Contacts              │
                    │ Companies             │
                    │ Deals                 │
                    │ Pipeline              │
                    │ Activities            │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │ Revenue Leak Monitor  │
                    │                       │
                    │ Deterministic rules   │
                    │ CRM health diagnosis  │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │ JMMS Revenue Leak     │
                    │ Status in HubSpot     │
                    └───────────────────────┘
~~~

Execution and orchestration surround this core flow:

~~~text
Hugging Face n8n
        │
        │ workflow dispatch
        ▼
GitHub Actions
        │
        │ validated execution
        ▼
Python integration
        │
        ▼
HubSpot
~~~

---

## Environment Model

Two HubSpot environments are intentionally separated.

### Production

Portal:

`JM Multiservices`

Purpose:

- real JMMS commercial records
- real Contacts
- real Companies
- real Deals
- production RevOps operation

Production data is not used for destructive integration testing.

---

### Lab

Portal:

`JMMS RevOps Lab`

Purpose:

- API development
- mutation testing
- idempotency testing
- association testing
- orchestration testing
- Revenue Leak testing
- scheduled dry-run validation

Lab records use explicit test identities.

---

## HubSpot Object Model

### Contact

Represents an individual person.

Example responsibilities:

- identity
- email
- relationship to Company
- relationship to Deal
- lifecycle participation

---

### Company

Represents the commercial organization.

Example responsibilities:

- business identity
- domain
- industry
- lifecycle state
- associated Contacts
- associated Deals

---

### Deal

Represents the commercial opportunity.

The Deal is the primary integration target between Growth OS and HubSpot.

Important JMMS properties include:

- `jmms_service_line`
- `jmms_acquisition_source`
- `jmms_qualification_score`
- `jmms_revenue_leak_status`
- `jmms_external_opportunity_id`

HubSpot also retains native properties such as:

- Deal stage
- amount
- Deal owner
- Close date
- Next step
- activities
- Record ID

---

## Association Model

Validated relationship graph:

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

Association synchronization is implemented in:

`src/upsert_relationships.py`

Repeated executions update the same deterministic records rather than creating new relationship graphs.

---

## Identity Model

Growth OS identity:

`opportunity_id`

maps to:

`jmms_external_opportunity_id`

HubSpot's custom external ID property is configured to require unique values.

The native HubSpot Record ID remains independent.

Example:

~~~text
Growth OS
opportunity_id = test_growth_os_001

            ↓

HubSpot
jmms_external_opportunity_id = test_growth_os_001

HubSpot Record ID = <LAB_DEAL_ID>
~~~

This enables deterministic reconciliation across systems.

---

## Idempotency Model

Synchronization follows:

~~~text
external opportunity ID absent
        ↓
CREATE

external opportunity ID present
        ↓
UPDATE EXISTING RECORD
~~~

Acceptance testing proved that repeated executions retained the same HubSpot Record ID.

Idempotency prevents duplicate Deals from repeated automation runs.

---

## Growth OS Approval Gate

Growth OS opportunities are eligible for HubSpot synchronization only when:

`pipeline_status = APPROVED`

This creates an explicit human-controlled boundary between opportunity intelligence and operational CRM entry.

The synchronizer defaults to dry-run behavior.

Real Growth OS writes require explicit authorization.

---

## Field Ownership Model

The architecture distinguishes source-owned and CRM-owned state.

### Growth OS-Owned

Growth OS may provide:

- external opportunity identity
- Deal name source data
- acquisition source
- qualification score
- known amount

---

### HubSpot-Owned

HubSpot owns ongoing commercial workflow state:

- Deal stage
- CRM owner
- activities
- tasks
- Next step
- pipeline progression
- customer-facing history

Normal Growth OS updates do not overwrite these fields.

---

### Revenue Leak Monitor-Owned

The Revenue Leak Monitor owns only:

`jmms_revenue_leak_status`

This prevents source synchronization and CRM diagnosis from competing over the same property.

---

## Stage Preservation

New Deals receive create-time CRM defaults.

Example:

`dealstage = appointmentscheduled`

which is displayed as:

`New Opportunity`

After creation, HubSpot owns Deal stage.

Acceptance testing confirmed:

~~~text
Growth OS creates Deal
        ↓
human moves Deal to Qualified
        ↓
Growth OS sync runs again
        ↓
Deal remains Qualified
~~~

This prevents integrations from reversing human CRM work.

---

## Revenue Leak Monitor

The Revenue Leak Monitor evaluates open HubSpot Deals using deterministic rules.

Current classifications:

- Healthy
- Data Incomplete
- Missing Next Step
- Follow-up Overdue
- Stale Opportunity
- Close Date Overdue

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

The monitor does not:

- move Deal stages
- change Deal amounts
- change owners
- create tasks
- modify Growth OS source data

---

## Revenue Leak Control Loop

Validated behavior:

~~~text
CRM problem
    ↓
deterministic diagnosis
    ↓
Revenue Leak Status
    ↓
human repairs CRM state
    ↓
monitor evaluates again
    ↓
new deterministic status
~~~

Acceptance transition:

~~~text
Data Incomplete
        ↓
owner + Contact repaired

Missing Next Step
        ↓
Next step added

Healthy
~~~

Repeated evaluation of unchanged Healthy state produces:

`NO_CHANGE`

This avoids unnecessary CRM writes.

---

## Automated Testing

Revenue Leak rules are covered by:

`tests/test_revenue_leak_monitor.py`

V1 test coverage validates:

- Data Incomplete
- Close Date Overdue
- Follow-up Overdue
- Missing Next Step
- Stale Opportunity
- Healthy
- New Opportunity next-step exception

Current acceptance result:

`7 / 7 PASS`

---

## n8n Orchestration Flow

~~~text
Operator
    ↓
Hugging Face n8n
    ↓
Runtime Config
    ↓
GitHub workflow dispatch
    ↓
Wait / poll exact run
    ↓
GitHub Actions
    ↓
Python
    ↓
HubSpot
    ↓
success / failure returned to n8n
~~~

Validated orchestration modes include:

- Growth OS fixture apply
- Growth OS dry-run
- Revenue Leak fixture apply
- Revenue Leak dry-run

---

## Scheduled Monitoring

GitHub Actions owns unattended Revenue Leak execution.

Scheduled mode:

`leak_dry_run`

Scheduled execution performs:

1. code validation
2. Growth OS opportunity-log validation
3. Revenue Leak unit tests
4. open Deal evaluation
5. zero HubSpot writes
6. execution evidence capture

Repeated native scheduled executions have completed successfully.

Scheduled dry-run remains intentionally non-mutating in V1.

---

## n8n Availability Monitor

A separate repository:

`external uptime monitor`

maintains the Hugging Face n8n readiness keepalive.

Its responsibility is limited to:

~~~text
GitHub schedule
    ↓
HF n8n readiness endpoint
    ↓
HTTP 200 required
~~~

Revenue Leak scheduling remains owned by:

`jmms-hubspot-revops`

This avoids coupling CRM monitoring to the availability of the n8n Space.

---

## Authentication

HubSpot system-to-system authentication uses a Service Key.

Secrets remain outside Git.

The local credential file:

`.env`

is excluded through `.gitignore`.

API access follows least privilege.

GitHub credentials are stored through GitHub repository secrets or n8n credential storage rather than source files.

---

## Safety Controls

V1 safety controls include:

- isolated Production and Lab HubSpot environments
- test-only mutation identities
- unique external Deal identity
- dry-run by default
- explicit approval gate
- explicit apply flags
- additional authorization for real Growth OS writes
- read-after-write verification
- preservation of HubSpot-owned Deal stage
- dedicated ownership of Revenue Leak Status
- scheduled Revenue Leak monitoring in read-only mode
- TLS verification enabled
- secrets excluded from Git
- human review for consequential CRM changes

---

## Observability

GitHub Actions records:

- trigger event
- target ref
- operation mode
- run ID
- validation output
- execution output
- final job status

V4 execution artifacts include:

- `run-context.txt`
- `validation.log`
- `hubspot-run.log`

Artifact retention:

`30 days`

n8n also exposes operator-facing success/failure routing for manually orchestrated runs.

---

## Architecture Principles

### HubSpot is the CRM

Do not rebuild standard CRM functionality in Growth OS.

### Deterministic Logic Before AI

Identity, synchronization, Revenue Leak rules, and consequential mutations remain deterministic.

### Human Review on Consequential Actions

Approval and operational repair remain human-controlled.

### Idempotency

Repeated execution must reconcile rather than duplicate.

### Least Privilege

Credentials receive only the permissions required by the current implementation.

### Environment Isolation

Development and mutation tests belong in the Lab environment.

### Clear Ownership Boundaries

Each field and system has an explicit owner.

### Observable Execution

Remote automation must leave enough evidence to explain what ran and whether it succeeded.

---

## V1 Status

The following capabilities are implemented and validated:

- HubSpot CRM architecture
- custom Deal schema
- Service Key authentication
- API Deal read/write
- read-after-write verification
- unique external opportunity identity
- idempotent Deal upsert
- Contact / Company / Deal associations
- stable Growth OS opportunity identity
- Growth OS approval gating
- deterministic field mapping
- Growth OS → HubSpot synchronization
- Deal-stage preservation
- n8n orchestration
- Revenue Leak monitoring
- automated Revenue Leak tests
- scheduled unattended dry-run
- execution observability
- Hugging Face n8n availability monitoring

V1 runtime engineering is complete.

Remaining work is portfolio packaging:

~~~text
FINAL DOCUMENTATION
        ↓
CASE STUDY
        ↓
ARCHITECTURE VISUAL
        ↓
DEMO
        ↓
PUBLIC PORTFOLIO EXTRACTION
~~~