# JMMS HubSpot RevOps V1 — Architecture Overview

This diagram summarizes the implemented JMMS HubSpot-centered RevOps system.

~~~mermaid
flowchart LR

    A[Opportunity Sources<br/>LinkedIn • Referral • Inbound • Marketplaces]

    B[JMMS Growth OS<br/>Discovery • Qualification • Pursuit Decision]

    C{Human Approval<br/>pipeline_status = APPROVED}

    D[Python Integration Layer<br/>Identity • Mapping • Idempotency • Validation]

    E[HubSpot CRM<br/>Contacts • Companies • Deals • Pipeline]

    F[Revenue Leak Monitor<br/>Deterministic CRM Health Rules]

    G[JMMS Revenue Leak Status<br/>Healthy • Missing Next Step • Stale • Overdue]

    H[n8n<br/>Operator Orchestration]

    I[GitHub Actions<br/>Remote Execution • Tests • Scheduling • Logs]

    J[AI Assistance<br/>Research • Enrichment • Recommendations]

    K[external uptime monitor<br/>Hugging Face n8n Keepalive]

    A --> B
    B --> C
    C -->|Approved| D
    D --> E
    E --> F
    F --> G

    H --> I
    I --> D
    I --> F

    J -. Intelligence support only .-> B
    K -. Availability monitoring .-> H
~~~

## System Responsibilities

| Layer | Responsibility |
|---|---|
| JMMS Growth OS | Opportunity intelligence, qualification, pursuit decisions, approval |
| Python | Deterministic integration logic, mapping, identity, validation, Revenue Leak rules |
| HubSpot | Operational CRM and system of record |
| n8n | Operator-facing orchestration |
| GitHub Actions | Remote execution, automated tests, scheduling, logs, run artifacts |
| AI | Research, enrichment, recommendations; not consequential CRM state |
| external uptime monitor | Hugging Face n8n readiness keepalive |

## Core Design Principle

~~~text
AI provides intelligence.

Deterministic software controls identity,
synchronization, and CRM health rules.

Humans retain authority over consequential
commercial decisions and CRM progression.
~~~

## Revenue Leak Control Loop

~~~mermaid
flowchart LR

    A[Open HubSpot Deal]
    B[Evaluate CRM State]
    C{Revenue Leak Rule}
    D[Data Incomplete]
    E[Missing Next Step]
    F[Follow-up Overdue]
    G[Close Date Overdue]
    H[Stale Opportunity]
    I[Healthy]
    J[Human CRM Repair]
    K[Re-evaluate]

    A --> B
    B --> C

    C --> D
    C --> E
    C --> F
    C --> G
    C --> H
    C --> I

    D --> J
    E --> J
    F --> J
    G --> J
    H --> J

    J --> K
    K --> B
~~~

## V1 Safety Boundary

The system intentionally does not allow scheduled automation to autonomously:

- move Deal stages
- modify Deal owners
- create consequential tasks
- invent commercial amounts
- approve Growth OS opportunities
- make AI-controlled CRM decisions

Scheduled Revenue Leak monitoring operates in dry-run mode.