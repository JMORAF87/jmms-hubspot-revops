# Case Study — HubSpot-Centered Revenue Leak Control System

## Executive Summary

JM Multiservices needed a practical CRM and RevOps system that could connect opportunity intelligence, structured sales execution, automation, and operational monitoring without replacing standard CRM functionality with another custom application.

The resulting V1 architecture uses:

- HubSpot as the operational CRM
- JMMS Growth OS as the opportunity intelligence and approval layer
- Python for deterministic synchronization and business rules
- n8n for operator-facing orchestration
- GitHub Actions for remote execution, scheduling, testing, and observability
- AI only where research, enrichment, or recommendations add value

The system was designed around a central principle:

~~~text
Use AI for intelligence.
Use deterministic software for consequential CRM state.
~~~

V1 implements and validates:

- HubSpot CRM architecture
- custom RevOps schema
- deterministic Growth OS → HubSpot synchronization
- stable external opportunity identity
- idempotent Deal reconciliation
- Contact / Company / Deal associations
- preservation of human-owned CRM state
- Revenue Leak detection
- automated rule testing
- n8n orchestration
- scheduled unattended monitoring
- execution logs and evidence artifacts

The project was built as an internal JMMS operating system and technical portfolio project rather than as a theoretical demo.

---

## Business Problem

Opportunity discovery and CRM execution solve different problems.

JMMS Growth OS can identify, qualify, and prioritize opportunities, but an opportunity-intelligence system should not become a replacement CRM.

HubSpot can manage:

- Contacts
- Companies
- Deals
- stages
- owners
- activities
- follow-ups
- commercial history

but it does not provide the same opportunity-research and orchestration layer as Growth OS.

The architecture therefore needed to answer several questions:

1. How can approved Growth OS opportunities enter HubSpot without creating duplicates?
2. Which system should own each field after a Deal enters CRM?
3. How can automation update source-owned fields without reversing human sales work?
4. How can missing CRM follow-up and data-quality issues be detected consistently?
5. How can the system run remotely without depending on a developer laptop?
6. How can automation remain auditable and safe enough for real commercial use?

---

## Design Decision

The project deliberately avoided building another custom CRM.

The system boundary is:

~~~text
JMMS Growth OS
= intelligence + approval

HubSpot
= operational CRM

Python
= deterministic integration logic

n8n
= orchestration

GitHub Actions
= remote runtime + scheduler + observability
~~~

This reduced unnecessary application development and kept HubSpot responsible for the CRM behaviors it already handles well.

---

## Architecture

The core business flow is:

~~~text
Opportunity Sources
        ↓
JMMS Growth OS
        ↓
Qualification
        ↓
Pursuit Decision
        ↓
Explicit Approval
        ↓
Deterministic Python Mapping
        ↓
Stable External Identity
        ↓
HubSpot Deal Create / Update
        ↓
Human CRM Execution
        ↓
Revenue Leak Monitor
        ↓
Operational CRM Health Signal
~~~

Remote execution is handled through:

~~~text
Hugging Face n8n
        ↓
GitHub workflow dispatch
        ↓
GitHub Actions
        ↓
Python integration
        ↓
HubSpot
~~~

Unattended Revenue Leak monitoring runs directly through GitHub Actions.

A separate operations-monitor repository maintains the Hugging Face n8n readiness keepalive.

---

## HubSpot CRM Model

The CRM implementation uses standard HubSpot objects:

### Contact

Represents the individual person involved in the commercial relationship.

### Company

Represents the organization.

### Deal

Represents the commercial opportunity.

The validated association graph is:

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

This model was tested through repeated API executions.

---

## JMMS Deal Schema

Five JMMS-specific Deal properties were added:

| Property | Purpose |
|---|---|
| `jmms_service_line` | JMMS service classification |
| `jmms_acquisition_source` | Normalized acquisition channel |
| `jmms_qualification_score` | Opportunity qualification score |
| `jmms_revenue_leak_status` | Operational CRM health state |
| `jmms_external_opportunity_id` | Stable cross-system identity |

The external opportunity property is configured to require unique values.

This creates a deterministic reconciliation key between Growth OS and HubSpot.

---

## Stable Opportunity Identity

Growth OS uses:

`opportunity_id`

HubSpot receives:

`jmms_external_opportunity_id`

These are separate from HubSpot's native Record ID.

Example:

~~~text
Growth OS
opportunity_id = test_growth_os_001

        ↓

HubSpot
jmms_external_opportunity_id = test_growth_os_001

HubSpot Record ID = <LAB_DEAL_ID>
~~~

This prevents repeated automation runs from creating duplicate Deals.

---

## Idempotent Deal Synchronization

The synchronization contract is:

~~~text
external opportunity ID absent
        ↓
CREATE Deal

external opportunity ID present
        ↓
UPDATE existing Deal
~~~

Acceptance testing used:

`test_opp_002`

First execution:

`CREATED`

Second execution:

`UPDATED`

Both executions referenced the same HubSpot Record ID:

`<LAB_UPSERT_DEAL_ID>`

Result:

`PASS`

This demonstrated actual idempotency rather than relying only on the HubSpot unique-property constraint.

---

## Growth OS Approval Gate

Not every discovered opportunity should automatically become a CRM Deal.

V1 requires:

`pipeline_status = APPROVED`

before a Growth OS record is eligible for synchronization.

This creates a human-controlled boundary between:

~~~text
opportunity intelligence
        ↓
human pursuit decision
        ↓
CRM execution
~~~

The synchronizer defaults to dry-run behavior.

Real Growth OS writes require explicit authorization.

---

## Deterministic Field Mapping

Growth OS fields are normalized before reaching HubSpot.

Examples include:

| Growth OS | HubSpot |
|---|---|
| `opportunity_id` | `jmms_external_opportunity_id` |
| company + opportunity | Deal name |
| source | `jmms_acquisition_source` |
| pursuit score | `jmms_qualification_score` |
| unambiguous revenue value | Deal amount |

Revenue values are only mapped when they are clearly numeric.

Accepted examples include:

- `4000`
- `$4,000`
- `$4,000.00`

Ambiguous values such as:

- `1500/mo`
- `75-100/hr`
- `TBD`
- `negotiable`

are intentionally rejected rather than converted into invented CRM amounts.

---

## CRM Ownership Boundary

A major design goal was preventing source synchronization from reversing human CRM work.

Growth OS may update source-owned fields.

HubSpot owns ongoing commercial execution fields such as:

- Deal stage
- Deal owner
- activities
- tasks
- Next step
- pipeline progression
- customer-facing CRM history

The Revenue Leak Monitor separately owns:

`jmms_revenue_leak_status`

This creates explicit field ownership instead of allowing every automation to update every property.

---

## Deal Stage Preservation

New Growth OS Deals receive a create-time stage:

`appointmentscheduled`

displayed in the JMMS pipeline as:

`New Opportunity`

After creation, HubSpot owns the Deal stage.

Acceptance testing moved a synchronized Deal manually to:

`Qualified`

The Growth OS synchronization was executed again.

The Deal remained:

`Qualified`

Result:

`PASS`

This proved that source reconciliation does not reverse human sales progression.

---

## Revenue Leak Problem

A CRM can contain valid Deals that are still operationally unhealthy.

Examples include:

- no owner
- no associated Contact
- missing next action
- overdue follow-up
- overdue Close date
- stale activity

The goal of the Revenue Leak Monitor was not to predict whether a Deal would close.

Its goal was to identify deterministic operational conditions that could cause opportunities to be neglected.

---

## Revenue Leak Monitor

The monitor evaluates open HubSpot Deals and assigns one operational state.

V1 statuses are:

- Healthy
- Data Incomplete
- Missing Next Step
- Follow-up Overdue
- Stale Opportunity
- Close Date Overdue

Rule precedence is deterministic:

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

The monitor writes only:

`jmms_revenue_leak_status`

It does not:

- move Deal stages
- change Deal amounts
- change owners
- create tasks
- alter Growth OS records

---

## Revenue Leak Acceptance Test

The primary Lab acceptance Deal was:

`<LAB_DEAL_ID>`

Initial condition:

- stage = Qualified
- no Deal owner
- no associated Contact
- no Next step

The monitor classified it as:

`Data Incomplete`

The CRM state was repaired by:

- assigning an owner
- associating an existing Contact

The next classification became:

`Missing Next Step`

Then:

`Next step = Send implementation plan`

was added.

The monitor classified the Deal as:

`Healthy`

Validated control loop:

~~~text
Data Incomplete
        ↓
repair missing CRM data

Missing Next Step
        ↓
define next action

Healthy
~~~

---

## Revenue Leak Idempotency

The Healthy Deal was evaluated again without changing the CRM state.

Observed behavior:

~~~text
current_status = Healthy
proposed_status = Healthy
changed = false
write = NO_CHANGE
~~~

This prevents unnecessary API writes during repeated monitoring.

---

## Automated Tests

Revenue Leak rules are covered through:

`tests/test_revenue_leak_monitor.py`

V1 validates:

- Data Incomplete
- Close Date Overdue
- Follow-up Overdue
- Missing Next Step
- Stale Opportunity
- Healthy
- New Opportunity next-step exception

Acceptance result:

`7 / 7 PASS`

These tests run locally and through GitHub Actions.

---

## n8n Orchestration

The operator-facing workflow runs on a Hugging Face-hosted n8n deployment.

The n8n workflow does not reproduce the Python business logic.

Instead it orchestrates:

~~~text
Manual Trigger
        ↓
Runtime Configuration
        ↓
GitHub Actions Dispatch
        ↓
Wait
        ↓
Poll Exact Run
        ↓
Success / Failure Routing
~~~

Validated execution modes include:

- Growth OS fixture apply
- Growth OS dry-run
- Revenue Leak fixture apply
- Revenue Leak dry-run

The workflow is version-controlled as JSON.

---

## GitHub Actions Runtime

GitHub Actions provides a remote execution environment for the system.

The workflow validates:

- Python syntax
- Growth OS opportunity data
- Revenue Leak unit tests

before executing the selected operation.

Supported execution modes include:

- `dry_run`
- `fixture_apply`
- `real_apply`
- `leak_dry_run`
- `leak_fixture_apply`

This makes the system runnable without depending on a local machine.

---

## Scheduled Monitoring

Revenue Leak monitoring runs unattended through GitHub Actions.

Scheduled mode:

`leak_dry_run`

The scheduled process:

1. validates code
2. validates source opportunity data
3. executes Revenue Leak unit tests
4. retrieves open HubSpot Deals
5. evaluates Revenue Leak state
6. performs zero CRM writes
7. records execution evidence

Native scheduled executions have completed successfully.

V1 intentionally keeps scheduled monitoring non-mutating.

---

## Execution Observability

V4 GitHub Actions execution captures:

- event type
- target ref
- execution mode
- run ID
- validation logs
- application logs
- final status

Each run uploads:

- `run-context.txt`
- `validation.log`
- `hubspot-run.log`

Artifact retention:

`30 days`

This provides enough evidence to investigate what happened during an automated execution.

---

## Hugging Face n8n Availability

The n8n instance runs on Hugging Face infrastructure.

A separate repository:

`external uptime monitor`

maintains a readiness keepalive.

The monitor checks:

`/healthz/readiness`

and requires:

`HTTP 200`

Its responsibility is limited to infrastructure availability.

Revenue Leak scheduling does not depend on this keepalive.

---

## Security and Safety Controls

V1 includes:

- separate Production and Lab HubSpot environments
- Service Key authentication
- secrets excluded from Git
- TLS verification enabled
- least-privilege API scopes
- test-only mutation identities
- stable unique external opportunity identity
- approval gating
- dry-run defaults
- explicit write flags
- additional authorization for real Growth OS writes
- read-after-write verification
- preservation of human-owned Deal stage
- isolated Revenue Leak property ownership
- read-only scheduled monitoring
- human review for consequential changes

The design favors controlled automation rather than maximum autonomy.

---

## Validation Evidence

The project maintains a version-controlled evidence set covering:

1. pipeline configuration
2. custom properties
3. unique external identity validation
4. API read
5. API write
6. UI write verification
7. idempotent Deal upsert
8. CRM object associations
9. stage preservation
10. n8n orchestration
11. GitHub Actions execution
12. Revenue Leak Healthy state
13. scheduled-mode manual validation
14. unattended scheduled execution
15. cross-repository dispatch validation

These artifacts provide implementation evidence beyond source code alone.

---

## Results

V1 demonstrated that JMMS can:

- connect an external opportunity-intelligence layer to HubSpot
- reconcile Deals without duplicate creation
- preserve human CRM workflow state
- synchronize CRM relationships
- separate data ownership between systems
- detect deterministic Revenue Leak conditions
- orchestrate operations through n8n
- execute remotely through GitHub Actions
- validate business rules automatically
- run Revenue Leak monitoring unattended
- retain execution evidence for troubleshooting

No revenue or conversion uplift is claimed from this Lab implementation because V1 was designed to validate system behavior rather than produce a controlled before/after business experiment.

---

## What This Project Demonstrates

From a CRM / RevOps delivery perspective, the project demonstrates practical experience with:

- HubSpot CRM architecture
- pipeline design
- lifecycle modeling
- custom property governance
- Contact / Company / Deal associations
- API integrations
- external identity design
- idempotent synchronization
- data normalization
- CRM ownership boundaries
- RevOps operational controls
- workflow orchestration
- Python automation
- n8n
- GitHub Actions
- automated testing
- scheduling
- observability
- security controls

From a systems-engineering perspective, it demonstrates separating intelligence, business rules, orchestration, execution, and systems of record instead of concentrating all behavior in one application.

---

## Limitations

V1 intentionally does not include:

- automated production CRM writes from scheduled monitoring
- autonomous stage changes
- autonomous follow-up creation
- predictive win-probability models
- AI-controlled consequential CRM decisions
- full enterprise observability infrastructure
- a custom CRM replacement

These exclusions are deliberate scope and safety decisions rather than missing dependencies.

---

## Future Extensions

Potential future work includes:

- production-approved synchronization
- human-approved Revenue Leak remediation tasks
- reporting dashboards
- Revenue Leak trend analysis
- controlled notification workflows
- additional CRM objects
- webhook-driven synchronization
- measured business-outcome experiments

Future functionality should preserve the same ownership, identity, and human-review boundaries established in V1.

---

## Final V1 Architecture

~~~text
OPPORTUNITY SOURCES
        ↓
JMMS GROWTH OS
        ↓
QUALIFICATION
        ↓
HUMAN APPROVAL
        ↓
DETERMINISTIC PYTHON SYNC
        ↓
HUBSPOT CRM
        ↓
HUMAN COMMERCIAL EXECUTION
        ↓
REVENUE LEAK MONITOR
        ↓
CRM HEALTH SIGNAL

ORCHESTRATION:
n8n → GitHub Actions → Python

UNATTENDED MONITORING:
GitHub Actions → Revenue Leak dry-run

SYSTEM OF RECORD:
HubSpot
~~~

JMMS HubSpot RevOps V1 is complete as an engineering implementation.

The next phase is portfolio extraction, demonstration, and professional packaging.