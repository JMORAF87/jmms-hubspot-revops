# JMMS Growth OS → HubSpot Mappings

## Purpose

This document defines the implemented deterministic synchronization contract between JMMS Growth OS opportunity data and HubSpot CRM.

It describes V1 behavior that has been implemented and validated in the JMMS RevOps Lab.

## System Ownership

### JMMS Growth OS

Growth OS owns:

- opportunity discovery
- opportunity identity
- qualification intelligence
- pursuit decisions
- source metadata
- known opportunity value
- approval state

### HubSpot

HubSpot is the operational CRM and system of record for:

- Contacts
- Companies
- Deals
- Deal pipeline stage
- commercial activities
- tasks
- next steps
- CRM ownership
- customer-facing CRM history

### Revenue Leak Monitor

The Revenue Leak Monitor owns:

`jmms_revenue_leak_status`

It diagnoses CRM operational conditions without changing the commercial pipeline.

---

## Synchronization Gate

A Growth OS opportunity is eligible for HubSpot synchronization only when:

`pipeline_status = APPROVED`

Records that are not explicitly approved are excluded from the synchronization path.

The synchronizer defaults to dry-run behavior.

Real Growth OS writes require explicit execution authorization.

---

## Deal Identity

Growth OS field:

`opportunity_id`

maps to HubSpot:

`jmms_external_opportunity_id`

The HubSpot property is configured to require unique values.

This field is the deterministic idempotency key.

Behavior:

~~~text
external opportunity ID absent
        ↓
CREATE Deal

external opportunity ID present
        ↓
UPDATE same Deal
~~~

HubSpot's native Record ID remains separate from the Growth OS external identity.

---

## Growth OS → HubSpot Field Mapping

| Growth OS Field | HubSpot Property | Behavior |
|---|---|---|
| `opportunity_id` | `jmms_external_opportunity_id` | Stable external identity / idempotency key |
| `company` + `opportunity` | `dealname` | Combined into the Lab Deal name |
| `source` | `jmms_acquisition_source` | Normalized to the JMMS acquisition-source vocabulary |
| `pursuit_score` | `jmms_qualification_score` | Numeric qualification score |
| `revenue_value` | `amount` | Written only when value is unambiguous numeric currency |
| `pipeline_status` | synchronization gate | Must equal `APPROVED`; not written directly to HubSpot |

---

## Acquisition Source Normalization

Recognized Growth OS source values are normalized into the HubSpot custom property:

`jmms_acquisition_source`

Supported normalized values include:

- LinkedIn
- Contra
- Referral
- Website
- Inbound Email
- Partner
- Existing Relationship
- Direct Outreach
- Other

Unknown or unmatched sources fall back to:

`Other`

---

## Revenue Value Normalization

The synchronizer writes HubSpot `amount` only when `revenue_value` is an unambiguous numeric amount.

Accepted examples:

- `4000`
- `4,000`
- `$4000`
- `$4,000.00`

Ambiguous values are intentionally not converted into HubSpot amount.

Examples intentionally rejected:

- `1500/mo`
- `75-100/hr`
- `TBD`
- `negotiable`

This prevents the integration from inventing commercial values.

---

## Create-Only CRM Defaults

When a Growth OS opportunity creates a new HubSpot Deal, V1 assigns:

`pipeline = default`

and:

`dealstage = appointmentscheduled`

In the JMMS pipeline UI, this corresponds to:

`New Opportunity`

These fields are create-time defaults.

---

## Update Ownership Boundary

On an existing Deal, Growth OS updates only Growth-OS-owned synchronization fields.

The normal update path does not overwrite:

- `pipeline`
- `dealstage`
- `jmms_revenue_leak_status`
- HubSpot activities
- HubSpot tasks
- HubSpot Next step
- CRM ownership state

This prevents synchronization from reversing human CRM work.

Acceptance testing confirmed that a Deal manually moved to `Qualified` remained in `Qualified` after Growth OS synchronization.

---

## Revenue Leak Status Ownership

Growth OS synchronization does not control:

`jmms_revenue_leak_status`

That property is owned by:

`src/revenue_leak_monitor.py`

The monitor currently supports:

- Healthy
- Data Incomplete
- Missing Next Step
- Follow-up Overdue
- Stale Opportunity
- Close Date Overdue

This separates source synchronization from CRM operational diagnosis.

---

## Relationship Synchronization

Contact / Company / Deal relationship synchronization is implemented separately in:

`src/upsert_relationships.py`

Validated associations include:

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

Relationship synchronization is deterministic and was validated across repeated executions.

---

## Synchronization Safety

V1 safety behavior includes:

- dry-run by default
- explicit approval gate
- explicit apply flag for writes
- additional explicit authorization for real Growth OS writes
- stable unique external opportunity identity
- read-after-write verification
- preservation of HubSpot-owned Deal stage
- no AI-generated CRM mutations
- human review for consequential operational changes

---

## Validated Acceptance Records

Idempotent Deal upsert:

`test_opp_002`

HubSpot Deal ID:

`<LAB_UPSERT_DEAL_ID>`

Growth OS synchronization fixture:

`test_growth_os_001`

HubSpot Deal ID:

`<LAB_DEAL_ID>`

Both acceptance paths demonstrated stable HubSpot Record IDs across repeated executions.

---

## V1 Contract

The final V1 system boundary is:

~~~text
JMMS Growth OS
      ↓
explicit approval
      ↓
deterministic field mapping
      ↓
stable external identity
      ↓
HubSpot Deal create / update
      ↓
HubSpot owns commercial workflow state
      ↓
Revenue Leak Monitor evaluates CRM health
~~~

HubSpot remains the operational CRM.

Growth OS remains the opportunity intelligence and orchestration layer.