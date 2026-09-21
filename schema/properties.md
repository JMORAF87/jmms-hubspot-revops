# JMMS HubSpot Property Architecture

## Objective

Use HubSpot default properties wherever they accurately represent the required business data.

Custom properties are created only when JMMS has a business requirement that cannot be represented clearly using an existing HubSpot property.

HubSpot Free currently permits 10 custom properties total across Contacts, Companies, and Deals.

---

# Default Properties

## Contact

Use HubSpot defaults for:

- First name
- Last name
- Email
- Phone number
- Job title
- Employment Role
- Employment Seniority
- Contact owner
- Lifecycle stage
- Lead status
- LinkedIn URL
- Last activity date
- Last contacted
- Record ID
- Record Source

## Company

Use HubSpot defaults for:

- Company name
- Company domain name
- Company owner
- Industry
- Type
- Ideal Customer Profile Tier
- Lifecycle stage
- Lead status
- Website URL
- Phone number
- City
- State/Region
- Country/Region
- Number of associated contacts
- Number of associated deals
- Number of open deals
- Next activity date
- Last activity date
- Last contacted
- Total revenue
- Record ID
- Record Source

## Deal

Use HubSpot defaults for:

- Deal name
- Deal owner
- Deal stage
- Pipeline
- Deal type
- Amount
- Weighted amount
- Deal probability
- Close date
- Next step
- Next activity date
- Last activity date
- Last contacted
- Closed won reason
- Closed lost reason
- Record ID
- Record Source

---

# JMMS Custom Properties

Custom property budget: 10 total.

## 1. JMMS Service Line

Object: Deal

Purpose:
Categorizes the JMMS capability or commercial service associated with the opportunity.

Initial options:

- CRM / RevOps
- AI Automation
- Revenue Leak Audit
- Security Automation
- Systems Integration
- Operations Automation
- Other

---

## 2. JMMS Acquisition Source

Object: Deal

Purpose:
Captures the actual business channel through which the opportunity originated.

This differs from HubSpot Record Source, which represents how the CRM record was technically created.

Initial options:

- LinkedIn
- Referral
- Website
- Direct Outreach
- Existing Relationship
- Partner
- Contra
- Inbound Email
- Other

---

## 3. JMMS Qualification Score

Object: Deal

Type: Number

Expected range: 0–100

Purpose:
Stores the deterministic Growth OS opportunity qualification score.

This is an opportunity-level score and should not be confused with HubSpot contact lead scoring.

---

## 4. JMMS Revenue Leak Status

Object: Deal

Purpose:
Stores the current deterministic revenue-leak classification.

Initial options:

- Healthy
- Missing Next Step
- Follow-up Overdue
- Stale Opportunity
- Close Date Overdue
- Data Incomplete
- Review Required

---

## 5. JMMS External Opportunity ID

### Uniqueness

`JMMS External Opportunity ID` must use the HubSpot
"Require unique values for this property" rule.

This property is the external idempotency key used to reconcile
Growth OS opportunities with HubSpot Deals.

Internal name:

`jmms_external_opportunity_id`

The internal name must not be changed because integration code will
depend on it.

Object: Deal

Purpose:
Stores the stable Growth OS identifier associated with a HubSpot Deal.

Example:

opp_2026_0042

This property supports deterministic synchronization and idempotent upserts between Growth OS and HubSpot.

---

# Property Budget

| Property | Internal Name | Object |
|---|---|---|
| JMMS Service Line | `jmms_service_line` | Deal |
| JMMS Acquisition Source | `jmms_acquisition_source` | Deal |
| JMMS Qualification Score | `jmms_qualification_score` | Deal |
| JMMS Revenue Leak Status | `jmms_revenue_leak_status` | Deal |
| JMMS External Opportunity ID | `jmms_external_opportunity_id` | Deal |

Used: 5

Reserved: 5

Do not consume reserved custom-property capacity without a demonstrated production requirement.