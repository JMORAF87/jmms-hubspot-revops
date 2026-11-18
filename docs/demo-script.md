# JMMS HubSpot RevOps V1 - Demo Script

## Demo Objective

Demonstrate a working HubSpot-centered RevOps system that connects:

- opportunity intelligence
- deterministic CRM synchronization
- idempotent Deal reconciliation
- CRM ownership boundaries
- Revenue Leak detection
- n8n orchestration
- GitHub Actions scheduling and observability

Target duration:

`2.5-4 minutes`

Audience:

- recruiters
- hiring managers
- RevOps leaders
- HubSpot implementation teams
- technical consulting prospects

Use only JMMS RevOps Lab / test data during the recording.

---

## Pre-Demo Setup

Before recording, prepare these tabs/windows:

1. `architecture-visual.md` rendered in GitHub or VS Code Markdown Preview
2. JMMS RevOps Lab HubSpot Deal
3. GitHub Actions successful Revenue Leak run
4. n8n orchestration workflow or evidence screenshot
5. terminal or source-code view only if needed

Recommended Lab Deal:

`LAB | TEST | Growth OS Company | Growth OS HubSpot Sync`

External opportunity ID:

`test_growth_os_001`

Do not show:

- Service Keys
- `.env`
- GitHub tokens
- credentials
- Production client records
- private opportunity-log data

---

## 0:00-0:20 - Problem

### Screen

Show the project title or architecture overview.

### Narration

> I built this HubSpot-centered RevOps system for JM Multiservices to connect opportunity intelligence with structured CRM execution without building another custom CRM.
>
> HubSpot remains the operational system of record, while Growth OS handles opportunity intelligence and approval.

---

## 0:20-0:45 - Architecture

### Screen

Show:

`docs/architecture-visual.md`

Focus on the primary flow:

~~~text
Growth OS
→ Human Approval
→ Python Integration
→ HubSpot
→ Revenue Leak Monitor
~~~

Then point out:

~~~text
n8n
→ GitHub Actions
→ Python
~~~

### Narration

> The architecture separates responsibilities intentionally.
>
> Growth OS handles discovery and qualification. Python owns deterministic identity, mapping, and business rules. HubSpot owns Contacts, Companies, Deals, and commercial workflow state.
>
> n8n handles operator orchestration, and GitHub Actions provides remote execution, testing, scheduling, and logs.

---

## 0:45-1:15 - Stable Identity and Idempotency

### Screen

Show the Lab HubSpot Deal.

Highlight:

`JMMS External Opportunity ID`

Example:

`test_growth_os_001`

Optionally show the corresponding architecture or mapping documentation.

### Narration

> Every Growth OS opportunity receives a stable external ID.
>
> That ID maps to a unique HubSpot Deal property and becomes the idempotency key.
>
> If HubSpot does not contain that ID, the integration creates the Deal. If it already exists, the integration updates the same record instead of creating a duplicate.
>
> Repeated acceptance tests preserved the same HubSpot Record ID.

---

## 1:15-1:40 - CRM Ownership Boundary

### Screen

Show the Deal currently in:

`Qualified`

Show the relevant property values without editing them.

### Narration

> A key design decision was separating source-owned data from CRM-owned state.
>
> Growth OS can update fields such as qualification score or acquisition source, but after a Deal enters HubSpot, HubSpot owns operational state like Deal stage, owner, activities, and next step.
>
> I validated this by manually moving the test Deal to Qualified, running Growth OS synchronization again, and confirming that the integration did not move the Deal backward.

---

## 1:40-2:15 - Revenue Leak Monitor

### Screen

Show:

`JMMS Revenue Leak Status = Healthy`

If useful, briefly show evidence of previous states from the documented acceptance test.

Validated transition:

~~~text
Data Incomplete
        ↓
owner + Contact repaired

Missing Next Step
        ↓
Next step added

Healthy
~~~

### Narration

> I then added a deterministic Revenue Leak Monitor.
>
> It checks open Deals for operational problems such as incomplete CRM data, overdue follow-up, missing next steps, stale opportunities, or overdue close dates.
>
> In this acceptance test, the Deal first classified as Data Incomplete. After repairing the owner and Contact relationship, it became Missing Next Step. After adding the next action, it became Healthy.
>
> The monitor changes only the dedicated Revenue Leak Status property.

---

## 2:15-2:35 - Automated Testing

### Screen

Show the successful test evidence or GitHub Actions validation step.

### Narration

> The Revenue Leak rules are covered with automated tests.
>
> V1 currently validates seven deterministic cases, including overdue follow-up, stale opportunities, missing next steps, incomplete data, and the Healthy state.
>
> Those tests run locally and as part of the GitHub Actions execution path.

---

## 2:35-3:00 - n8n and GitHub Actions

### Screen

Show either:

- the n8n orchestration workflow, or
- `10-n8n-github-orchestration-pass.png`

Then show the successful GitHub Actions run.

### Narration

> n8n acts as the operator-facing orchestration layer.
>
> Rather than duplicating business logic inside workflow nodes, it dispatches GitHub Actions, which executes the version-controlled Python integration.
>
> This gives me one deterministic implementation that can be run locally, manually through n8n, or remotely through GitHub Actions.

---

## 3:00-3:20 - Scheduled Monitoring and Observability

### Screen

Show the successful scheduled Revenue Leak GitHub Actions run.

Point out:

- schedule event
- `leak_dry_run`
- successful job
- artifacts

### Narration

> Revenue Leak monitoring also runs unattended through GitHub Actions.
>
> The scheduled V1 mode is intentionally read-only. It validates the code and tests, evaluates open Deals, records the result, and performs zero CRM writes.
>
> Each run preserves logs, execution context, and downloadable artifacts for troubleshooting.

---

## 3:20-3:40 - Close

### Screen

Return to the architecture visual.

### Narration

> The result is a HubSpot-centered RevOps control system with stable identity, idempotent synchronization, explicit ownership boundaries, deterministic Revenue Leak monitoring, orchestration, testing, scheduling, and observability.
>
> The main design principle is simple: AI can assist with intelligence, but deterministic software and human approval control consequential CRM state.

---

## Optional Short Version

If the final recording needs to stay under two minutes, keep only:

1. problem
2. architecture
3. idempotent HubSpot synchronization
4. Revenue Leak Monitor
5. GitHub Actions scheduled execution
6. closing principle

Remove the detailed CRM ownership and automated-testing sections from the spoken walkthrough while leaving them visible in the repository.

---

## Recording Guidelines

Keep the recording technical but commercial.

Prefer:

- visible working software
- one architecture visual
- one HubSpot Lab Deal
- one successful automation execution
- one Revenue Leak example
- one scheduled run

Avoid:

- reading documentation line-by-line
- opening many source files
- exposing credentials
- explaining every API endpoint
- showing Production client records
- spending time navigating menus
- making unsupported ROI claims

The goal is not to teach HubSpot.

The goal is to demonstrate that the system was designed, implemented, tested, and operated end-to-end.

---

## Public Portfolio Message

The project should communicate:

~~~text
I can design the CRM operating model.

I can integrate external systems through APIs.

I can build deterministic automation.

I understand idempotency and data ownership.

I can orchestrate workflows.

I can test and monitor operational logic.

I can add AI without making it the source of truth.
~~~