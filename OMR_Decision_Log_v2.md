# OMR Operations Layer — Decision Log v2

Status: Active  
Project: OMR Operations Layer  
Date: 2026-03-17  
Owner: OMR / ChatGPT working draft

* * *

## Purpose

This document records the foundational architectural decisions for the new OMR operations project. Its purpose is to preserve reasoning, reduce ambiguity, and provide a stable reference for future design and implementation work.

The scope of the project is to introduce a digital operational layer above EasyJob ("Easy"), with future support for analytics, workflow optimization, and AI agents.

* * *

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

* * *

# DL-002 — The new platform is an operations layer, not a new ERP
## Decision

The project will be positioned as an Operations Layer above Easy rather than as a complete replacement ERP.

## Rationale

The current problem is not lack of a database, but lack of a live, shared, cross-department operational system. The real workflow currently passes through paper, calls, emails, and individual know-how.

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

* * *

# DL-003 — The architecture is registry-based
## Decision

The core architecture will be built around one or more operational registries.

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

* * *

# DL-004 — Multiple registries are allowed and encouraged
## Decision

The system will support multiple registries, separated by domain, instead of a single monolithic registry.

## Initial candidate registries

- Order Registry
- Inventory Registry
- Demand Registry
- Stock Policy Registry
- Priority Signals Registry
- Logistics Registry
- Production Registry (future)
- Commercial Registry (future, optional)

## Rationale

Different business domains have different update frequencies, ownership, and logic. A multi-registry design improves:

- modularity
- maintainability
- extensibility
- bounded contexts
- testability

## Consequences

- Cross-registry dependencies must be explicitly modeled.
- The system will need a dependency/update strategy.
- A shared core abstraction for entity/state/rules/events is desirable.

* * *

# DL-005 — The first class operational object is the digital fabbisogno
## Decision

The first core operational object will not simply be the raw order imported from Easy, but a derived operational object conceptually aligned with the current paper-based fabbisogno.

## Rationale

In the current business flow, the fabbisogno is the real object that moves through departments. Although Easy stores the customer order, the operational work starts when that order becomes something to analyze, produce, prepare, and ship.

Digitizing this object is the cleanest way to bridge the real process and the new platform.

## Consequences

- The operational layer must define a digital representation of fabbisogno.
- This object will likely aggregate one or more order lines and operational metadata.
- Department handoffs should occur on this object or on directly linked operational tasks.

* * *

# DL-006 — The system must be state-based and event-aware
## Decision

The architecture will combine:

- current state representation
- event history / audit trail

## Rationale

State alone answers: "what is true now?" Events answer:

- what changed?
- when?
- who changed it?
- how did we arrive here?
- where are delays occurring?

A purely state-based system would lose process intelligence and make analytics/AI much weaker. A purely event-sourced architecture would be unnecessarily heavy at this stage.

## Consequences

- Each core entity should have a current state view.
- Material operational changes should generate events.
- The platform should preserve enough history for process analysis and future agent training.

* * *

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
- stock replenishment logic
- production quantity suggestion logic

## Rationale

OMR already has non-trivial operational logic. If these rules are hidden in pages, operators, or ad-hoc scripts, the system will become inconsistent and fragile.

## Consequences

- Rules should be modeled explicitly.
- UI acts as a surface for visualization and interaction.
- Future AI agents should read and reason over formalized rules.

* * *

# DL-008 — Department tools must be derived from shared state
## Decision

Department-specific tools (warehouse, logistics, production office, etc.) will be built as specialized views/workflows on top of the shared operational registries.

## Rationale

The business should not fragment again into isolated department tools with duplicated logic. The new platform must connect departments through shared operational truth.

## Consequences

- The same order/fabbisogno state must be visible differently by department.
- A common API/domain model is preferred over department-specific silos.
- The frontend should eventually provide role-specific work queues on top of shared state.

* * *

# DL-009 — AI is a later decision-support layer, not the foundation
## Decision

AI will be introduced as a support layer after the operational registries, state logic, and event tracking are stable enough.

## Rationale

Without structured operational data, AI would amplify confusion rather than improve decisions. The company first needs digital visibility and consistent state.

## Consequences

Initial phases prioritize:

- sync
- registry model
- digital fabbisogno
- workflow/handoffs
- event tracking
- explicit rules

AI is expected later for:

- fabbisogno analysis
- shipping suggestions
- operational anomaly detection
- management dashboards and explanations

* * *

# DL-010 — The first implementation perimeter must stay narrow
## Decision

The first implementation scope must stay intentionally constrained.

## Proposed initial perimeter

- import/sync from Easy
- initial Order Registry
- initial Inventory Registry
- initial Demand Registry
- initial Stock Policy Registry
- digital fabbisogno representation
- basic operational states
- basic event taxonomy
- minimal departmental handoff flow for UPR, warehouse, and logistics

## Excluded from first implementation

- commercial module
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

* * *

# DL-011 — Commercial is excluded from initial project scope
## Decision

The commercial office is excluded from the initial implementation scope.

## Rationale

Commercial processes involve high variability, pricing discretion, historical negotiation logic, and strong dependence on individual experience. They are important, but they are not the highest-leverage starting point for operational synchronization.

The first project phase should start from confirmed orders already present in Easy and focus on execution flow.

## Consequences

- The initial system entry point is the confirmed order already recorded in Easy.
- Offers, quotation workflows, and pricing support stay outside v1 scope.
- A future Commercial Registry remains possible but deferred.

* * *

# DL-012 — UPR is a Production Intelligence Layer, not a simple yes/no gate
## Decision

The UPR (ufficio produzione) is modeled as a production intelligence layer. Its role is not limited to deciding whether production is required, but extends to deciding how much should be produced and how the operational flow should branch.

## Rationale

In practice, UPR must consider not only current order shortage but also future commitments, recurring demand, and operational convenience. A binary "produce / do not produce" model is too weak and does not match the real decision process.

## Consequences

- UPR logic must calculate production quantity suggestions, not just production necessity.
- UPR needs access to cross-registry data, not only the current order.
- UPR output must support both production and warehouse in parallel.

* * *

# DL-013 — Demand Registry is introduced for recurring-demand intelligence
## Decision

A dedicated Demand Registry is introduced to represent recurring sales behavior and demand expectation for stockable standard items.

## Rationale

UPR production decisions for standard items depend not only on current shortage but also on historical demand and near-future expected needs. This requires a dedicated registry rather than ad-hoc calculations inside a single module.

## Consequences

The Demand Registry should eventually support, at minimum:

- recurring monthly eligibility
- cleaned sales history
- average monthly demand on 12 months
- average monthly demand on 6 months
- average monthly demand on 3 months
- blended monthly expectation
- optional future demand signals derived from open commitments

* * *

# DL-014 — Stock Policy Registry is introduced for governed replenishment
## Decision

A dedicated Stock Policy Registry is introduced to represent stock coverage policies and physical constraints for standard items.

## Rationale

Production beyond direct commitments must not be treated as uncontrolled overproduction. It should instead be modeled as governed replenishment, constrained by policy and warehouse capacity.

## Consequences

The Stock Policy Registry should eventually support, at minimum:

- months of stock target per item
- theoretical target stock
- maximum warehouse capacity per item
- effective target stock after capacity cap
- optional prudential replenishment limits

* * *

# DL-015 — Standard-item replenishment uses a blended multi-horizon demand method
## Decision

For standard items eligible for stock, monthly demand expectation is estimated by combining three cleaned historical views:

- previous 12 months average
- previous 6 months average
- previous 3 months average

The three averages are blended to derive the monthly expectation used by stock policy.

## Rationale

The method balances long-term stability with recent market trend. It is explainable, lightweight, and aligned with existing company practice.

## Consequences

- Demand estimation remains transparent and reviewable.
- The approach is simple enough for early implementation.
- Weighted or more advanced forecasting models can be introduced later without breaking the architectural role of the Demand Registry.

* * *

# DL-016 — Priority is dynamic and event-influenced
## Decision

Priority is not a static order attribute. It is modeled as a dynamic value derived from a base priority plus external signals.

## Rationale

Real operational priority can change due to customer urgency, blocked warehouse situations, shipping windows, or other cross-department events. The system must capture this without rewriting the order itself each time.

## Consequences

A Priority Signals Registry is introduced to support:

- base priority imported or derived from order context
- urgency signals from logistics or customer communication
- blocked-order signals from warehouse
- future extensible priority adjustments
- computed final priority for operational use

* * *

# DL-017 — Operational state is multidimensional, not linearly singular
## Decision

Operational entities must support multidimensional state instead of a single linear status field.

## Rationale

An order or fabbisogno can simultaneously be:
- partially ready in warehouse
- pending production for missing items
- under logistics attention for future shipment
- subject to an urgency signal

A single status field would collapse distinct realities and force lossy approximations.

## Consequences

State models should support separate but related dimensions such as:

- analysis state
- production state
- warehouse readiness state
- logistics/shipping state
- priority/urgency state

* * *

# DL-018 — UPR handoff is parallel, not exclusive
## Decision

Once UPR analysis is complete, the resulting operational flow can branch in parallel toward production and warehouse.

## Rationale

If some items require production, that does not prevent warehouse from starting work on already available items or on the operational preparation of the order/fabbisogno. The real process is not an exclusive "either warehouse or production" path.

## Consequences

- Handoff modeling must support parallel downstream work.
- Fabbisogno and related tasks must allow partial readiness visibility.
- Warehouse worklists should not depend on full production completion unless explicitly blocked.

* * *

# DL-019 — The architecture distinguishes Global Registries from Application-Specific Registries
## Decision

The architecture adopts a dual registry model composed of:

1. Global Registries
2. Application-Specific Registries

## Rationale

Some registries represent the canonical shared operational truth of the company, while others are local derived views, work queues, or recommendation spaces needed by a specific department or application.

Separating the two improves semantic clarity and avoids polluting the system core with temporary or UI-oriented structures.

## Consequences

### Global Registries
These represent shared operational truth and are expected to be stable core concepts. Initial candidates:

- Order Registry
- Inventory Registry
- Demand Registry
- Stock Policy Registry
- Priority Signals Registry
- Event Log / Event Registry

### Application-Specific Registries
These represent derived views or operational workspaces. Initial examples:

- UPR Worklist Registry
- UPR Production Suggestion Registry
- Warehouse Preparation Queue
- Warehouse Blocked Orders View
- Shipping Candidates Registry
- Shipment Decision Queue

### Design rule
Each new data structure should be classified as either:
- shared fact / canonical state → global registry
- derived local view / queue / recommendation → application-specific registry

* * *

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

## OQ-006 — Demand Registry ownership boundary

Should future commitments from open orders live directly in Demand Registry, stay in Order Registry, or be represented through a derived bridge layer?

## OQ-007 — Stock replenishment policy limits

Which prudential constraints should cap replenishment beyond commitments?

Possible candidates:
- max coverage months
- max extra quantity percentage versus commitments
- manual approval threshold

## OQ-008 — Priority calculation model

Should final priority be:
- pure additive scoring,
- weighted scoring by source,
- rules-based escalation,
- or a hybrid?

* * *

# Immediate Next Design Activities

1. Analyze the UPR, warehouse, and logistics departments operationally and identify:
   - inputs
   - outputs
   - decisions
   - handoffs
   - missing data
   - candidate registry ownership

2. Define initial global registry structure:
   - Order Registry
   - Inventory Registry
   - Demand Registry
   - Stock Policy Registry
   - Priority Signals Registry

3. Define the digital fabbisogno model.

4. Define the first event taxonomy.

5. Define sync boundaries with Easy.

6. Define the first UPR application-specific registries:
   - UPR Worklist Registry
   - UPR Production Suggestion Registry

* * *

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
- Commercial is excluded from v1.
- UPR is modeled as a production intelligence layer.
- Demand and stock policy are core registries for standard-item replenishment.
- Priority is dynamic.
- Operational state is multidimensional.
- UPR handoff is parallel.
- The architecture distinguishes global and application-specific registries.
