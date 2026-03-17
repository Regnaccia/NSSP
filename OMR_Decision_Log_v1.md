# OMR Operations Layer — Decision Log v1

Status: Active  
Project: OMR Operations Layer  
Date: 2026-03-17  
Owner: OMR / ChatGPT working draft

---

## Purpose

This document records the foundational architectural decisions for the new OMR operations project.
Its purpose is to preserve reasoning, reduce ambiguity, and provide a stable reference for future design and implementation work.

The scope of the project is to introduce a digital operational layer above EasyJob ("Easy"), with future support for analytics, workflow optimization, and AI agents.

---

# DL-001 — Easy remains the administrative source of truth

## Decision
Easy remains the official administrative/master system for:
- customers
- destinations
- articles
- orders
- historical orders
- stock and inventory balances already managed in Easy
- shipping documents and related historical records already present in Easy

## Rationale
OMR already uses Easy as the established ERP-like business system. Replacing it would add unnecessary migration risk, cost, and process disruption.

The new project should therefore not attempt to rebuild the ERP layer. Its role is to create an operational layer synchronized with Easy.

## Consequences
- The new platform must import and normalize data from Easy.
- Core administrative entities should not be manually duplicated in the new system unless required for sync/cache purposes.
- Conflicts between Easy and the operational layer must be explicitly modeled.
- The new layer is operational, not administrative.

---

# DL-002 — The new platform is an operations layer, not a new ERP

## Decision
The project will be positioned as an **Operations Layer** above Easy rather than as a complete replacement ERP.

## Rationale
The current problem is not lack of a database, but lack of a live, shared, cross-department operational system.
The real workflow currently passes through paper, calls, emails, and individual know-how.

The value therefore lies in:
- operational state visibility
- digital handoffs between departments
- shared decision support
- event tracking
- future automation and AI support

## Consequences
The design priority is:
1. sync
2. operational state
3. workflows
4. rules
5. analytics
6. AI

Not:
1. full ERP rebuild
2. deep accounting/admin features

---

# DL-003 — The architecture is registry-based

## Decision
The core architecture will be built around one or more **operational registries**.

## Rationale
A registry-based model is coherent with the conceptual direction already explored in ActiveThermo:
- entities represented in a normalized internal form
- state stored in a structured registry
- derived fields calculated from source data and dependencies
- rules attached to entities or related context
- downstream tools reading from shared state rather than re-implementing business logic

This is preferable to a module-first or page-first architecture.

## Consequences
- The system core becomes a state engine, not just a CRUD application.
- UI modules should consume registry state instead of owning business logic.
- Rules and derived operational status should live in the core model.
- Future agents can operate on registry state rather than raw ERP data.

---

# DL-004 — Multiple registries are allowed and encouraged

## Decision
The system will support multiple registries, separated by domain, instead of a single monolithic registry.

## Initial candidate registries
- Order Registry
- Inventory Registry
- Logistics Registry
- Production Registry (future)
- Commercial Registry (future, optional)

## Rationale
Different business domains have different update frequencies, ownership, and logic.
A multi-registry design improves:
- modularity
- maintainability
- extensibility
- bounded contexts
- testability

## Consequences
- Cross-registry dependencies must be explicitly modeled.
- The system will need a dependency/update strategy.
- A shared core abstraction for entity/state/rules/events is desirable.

---

# DL-005 — The first class operational object is the digital fabbisogno

## Decision
The first core operational object will not simply be the raw order imported from Easy, but a derived operational object conceptually aligned with the current paper-based **fabbisogno**.

## Rationale
In the current business flow, the fabbisogno is the real object that moves through departments.
Although Easy stores the customer order, the operational work starts when that order becomes something to analyze, produce, prepare, and ship.

Digitizing this object is the cleanest way to bridge the real process and the new platform.

## Consequences
- The operational layer must define a digital representation of fabbisogno.
- This object will likely aggregate one or more order lines and operational metadata.
- Department handoffs should occur on this object or on directly linked operational tasks.

---

# DL-006 — The system must be state-based and event-aware

## Decision
The architecture will combine:
- current state representation
- event history / audit trail

## Rationale
State alone answers: "what is true now?"
Events answer:
- what changed?
- when?
- who changed it?
- how did we arrive here?
- where are delays occurring?

A purely state-based system would lose process intelligence and make analytics/AI much weaker.
A purely event-sourced architecture would be unnecessarily heavy at this stage.

## Consequences
- Each core entity should have a current state view.
- Material operational changes should generate events.
- The platform should preserve enough history for process analysis and future agent training.

---

# DL-007 — Rules belong to the core operational model, not to UI pages

## Decision
Business rules must be represented in the operational layer and not embedded primarily inside frontend views.

## Rule families already identified
- shipping day rules
- threshold-based shipment rules
- urgent override rules
- customer-specific logistics preferences
- destination-specific handling logic
- carrier selection logic

## Rationale
OMR already has non-trivial operational logic. If these rules are hidden in pages, operators, or ad-hoc scripts, the system will become inconsistent and fragile.

## Consequences
- Rules should be modeled explicitly.
- UI acts as a surface for visualization and interaction.
- Future AI agents should read and reason over formalized rules.

---

# DL-008 — Department tools must be derived from shared state

## Decision
Department-specific tools (warehouse, logistics, production office, etc.) will be built as specialized views/workflows on top of the shared operational registries.

## Rationale
The business should not fragment again into isolated department tools with duplicated logic.
The new platform must connect departments through shared operational truth.

## Consequences
- The same order/fabbisogno state must be visible differently by department.
- A common API/domain model is preferred over department-specific silos.
- The frontend should eventually provide role-specific work queues on top of shared state.

---

# DL-009 — Scope Exclusion: Commerciale

### Decision
Il reparto commerciale è escluso dalla fase iniziale del progetto.

### Rationale
- Alta variabilità decisionale
- Forte dipendenza da esperienza individuale
- Basso impatto immediato sull'efficienza operativa
- Priorità a execution layer (produzione, magazzino, logistica)

### Consequences
- Il sistema parte dagli ordini già acquisiti
- Easy resta unico punto per offerte e conferme ordine
- Possibile integrazione futura con AI support (pricing, offerte)

# DL-010 — AI is a later decision-support layer, not the foundation

## Decision
AI will be introduced as a support layer after the operational registries, state logic, and event tracking are stable enough.

## Rationale
Without structured operational data, AI would amplify confusion rather than improve decisions.
The company first needs digital visibility and consistent state.

## Consequences
Initial phases prioritize:
- sync
- registry model
- digital fabbisogno
- workflow/handoffs
- event tracking
- explicit rules

AI is expected later for:
- commercial memory/support
- fabbisogno analysis
- shipping suggestions
- operational anomaly detection
- management dashboards and explanations

---

# DL-011 — The first implementation perimeter must stay narrow

## Decision
The first implementation scope must stay intentionally constrained.

## Proposed initial perimeter
- import/sync from Easy
- initial Order Registry
- initial Inventory Registry
- digital fabbisogno representation
- basic operational states
- basic event taxonomy
- minimal departmental handoff flow

## Excluded from first implementation
- full production live tracking
- advanced scheduling engine
- carrier portal integrations
- autonomous AI decisioning
- broad generic platform abstractions not yet justified by real usage

## Rationale
The previous project stalled partly because the scope became too large relative to the available operational foundation.

## Consequences
- Each phase should produce a directly useful operational improvement.
- Architecture should remain extensible without overbuilding.

---

# DL-010 — UPR come Production Intelligence Layer

UPR non si limita a determinare la necessità di produzione, ma calcola quantità ottimali considerando:
- fabbisogno immediato
- fabbisogni futuri
- consumo storico

---

# DL-011 — Introduzione Demand Registry

Viene introdotto un registry dedicato alla domanda (storico e previsione) per supportare decisioni di produzione.

---

# DL-012 — Priority Engine

La priorità è dinamica e deriva da:
- ordine
- eventi esterni (cliente, magazzino, logistica)

---

# DL-013 — Multi-dimensional State Model

Lo stato delle entità non è lineare ma multidimensionale (produzione, magazzino, logistica).

---

# DL-014 — Parallel Handoff

UPR genera output paralleli:
- produzione
- magazzino


# Open Questions

## OQ-001 — Granularity of digital fabbisogno
Should one fabbisogno map to:
- one order,
- one destination subset of an order,
- one operational batch,
- or a flexible container of order lines?

## OQ-002 — Order Registry primary unit
Should the registry center on:
- order header,
- order line,
- or operational fulfillment unit?

## OQ-003 — Inventory truth model
How should Easy stock, reserved stock, and operational availability be separated conceptually?

## OQ-004 — Department handoff model
Should handoffs be represented as:
- entity state transitions,
- explicit tasks,
- or both?

## OQ-005 — Rules attachment point
Should rules attach to:
- customer,
- destination,
- order,
- article family,
- or dedicated logistics profile objects?

---

# Immediate Next Design Activities

1. Analyze each department operationally and identify:
   - inputs
   - outputs
   - decisions
   - handoffs
   - missing data
   - candidate registry ownership

2. Define initial registry structure:
   - Order Registry
   - Inventory Registry
   - Logistics Registry (or defer)

3. Define the digital fabbisogno model.

4. Define the first event taxonomy.

5. Define sync boundaries with Easy.

---

# Working Summary

The project direction is now formally set as follows:

- Easy remains the administrative source of truth.
- OMR will build an operational layer above Easy.
- The operational layer will be registry-based.
- Multiple registries are preferred over a monolith.
- The digital fabbisogno is the first key operational object.
- The system must combine current state and event history.
- Rules belong in the core model.
- Department tools are views on shared state.
- AI comes after the operational foundation.
- Scope must remain narrow in the first implementation phase.

