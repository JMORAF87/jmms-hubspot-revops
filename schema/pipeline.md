# JMMS HubSpot Deal Pipeline

## Purpose

HubSpot stores qualified JMMS commercial opportunities.

Growth OS remains the upstream opportunity discovery and qualification layer.

A discovered lead does not automatically constitute a HubSpot Deal.

## Pipeline

| Order | Stage | Probability | Internal ID |
|---|---|---:|---|
| 1 | New Opportunity | 10% | `appointmentscheduled` |
| 2 | Qualified | 25% | `qualifiedtobuy` |
| 3 | Discovery / Diagnosis | 40% | `presentationscheduled` |
| 4 | Scoping | 55% | `decisionmakerboughtin` |
| 5 | Proposal Sent | 70% | `contractsent` |
| 6 | Decision Pending | 85% | portal-specific custom ID |
| 7 | Closed Won | 100% | `closedwon` |
| 8 | Closed Lost | 0% | `closedlost` |

Renaming a HubSpot stage changes its display label but does not change its stable internal identifier.

Custom stages may have different internal IDs between Production and Lab.

## Stage Semantics

### New Opportunity

A legitimate commercial opportunity has entered the CRM but has not been fully evaluated.

### Qualified

JMMS has confirmed a real business problem, reasonable solution fit, a plausible buyer, and a commercial path.

### Discovery / Diagnosis

JMMS is actively gathering requirements or diagnosing the opportunity.

### Scoping

Requirements, deliverables, architecture, timeline, and pricing are being defined.

### Proposal Sent

A formal commercial proposal, estimate, SOW, or offer has been delivered.

### Decision Pending

The buyer has the proposal and an explicit decision is pending.

### Closed Won

The engagement has been accepted.

### Closed Lost

The opportunity is no longer being pursued.

## CRM Entry Gate

V1:

```text
Opportunity discovered
→ Growth OS qualification
→ pursue candidate
→ human approval
→ HubSpot Deal