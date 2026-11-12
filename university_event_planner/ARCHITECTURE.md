# Architecture Documentation: Intelligent University Event Planner

## 1. Overall System Architecture

The **Intelligent University Event Planner** is an AI-driven, constraint-aware scheduling, venue allocation, and policy verification system designed for academic campuses. It resolves complex event scheduling requests by navigating state spaces, rigorously enforcing university venue policies, coordinating specialized autonomous agents, benchmarking AI approaches, and providing grounded, hallucination-free policy assistance via Retrieval-Augmented Generation (RAG).

The system features a **Chat-First, Intent-Driven Conversational Interface** governed by an **Orchestrator Agent**. Users express their planning needs in natural language (e.g. _"I need a hall for 200 people next Thursday with a projector"_ or _"Can a student club book the main auditorium past 8 PM?"_). The Orchestrator automatically abstracts the underlying AI engine, extracting entities, evaluating campus rules, and dynamically delegating work to CSP, A*, Policy RAG, or specialized sub-agents.

```mermaid
flowchart TD
    subgraph ClientLayer["Presentation Layer (Chat-First & Conversational)"]
        UI["Conversational Web Interface (HTML5 / Modern CSS / Vanilla JS)"]
        ChatInput["Natural Language Input Bar ('Tell us what event you're planning...')"]
        TraceInspector["Behind-the-Scenes Sub-agent Dialogue Inspector"]
        CLI["CLI Benchmark Tool (scripts/run_benchmark.py)"]
        Swagger["OpenAPI / Swagger Explorer (/docs)"]
    end

    subgraph APILayer["FastAPI Gateway (/chat & REST Subsystems)"]
        Main["FastAPI Application (app/main.py)"]
        ChatRouter["Conversational Endpoint (POST /chat)"]
        CoreRouter["Core Routes (/venues, /bookings)"]
        SchedRouter["Scheduling Routes (/schedule/search, /schedule/export-ics)"]
        RulesRouter["Rules Routes (/rules/evaluate)"]
        AgentRouter["Agent Routes (/agents/plan)"]
        RAGRouter["Policy RAG Routes (/rag/query, /rag/documents)"]
        EvalRouter["Evaluation Routes (/evaluation/benchmark, /evaluation/scenarios)"]
    end

    subgraph OrchestrationLayer["Orchestrator & Multi-Agent Coordination Engine"]
        Orchestrator["OrchestratorAgent (Central Router & Intent Resolver)"]
        NLU["IntentParser (Entity Extractor & Algorithmic Router)"]
        Coordinator["CoordinatorAgent (Multi-turn Negotiation & Consensus)"]
        SchedAgent["SchedulingAgent (State-Space Search Driver)"]
        PolicyAgent["PolicyComplianceAgent (Rules & RAG Verification)"]
        LogisticsAgent["LogisticsAgent (AV, Facilities & Buffer Operations)"]
    end

    subgraph EngineLayer["Core AI & Algorithmic Subsystems"]
        SearchEng["State-Space Search Subsystem\n(CSP MRV/LCV, A*, Min-Conflicts, Greedy)"]
        RuleEng["Venue Rule & Policy Engine\n(Hard Constraints & Soft Compliance)"]
        RAGEng["Policy-Aware RAG Engine\n(Hybrid BM25 + Dense Semantic Vector Store)"]
        BenchEng["AI Evaluation & Benchmarking Suite"]
    end

    subgraph DataLayer["Persistence & Knowledge Corpus"]
        DB[("SQLAlchemy 2.0 ORM\n(SQLite / PostgreSQL)")]
        PolicyCorpus[("Official Campus Policy Documents\n(*.md Corpus)")]
    end

    ClientLayer --> APILayer
    Main --> ChatRouter & CoreRouter & SchedRouter & RulesRouter & AgentRouter & RAGRouter & EvalRouter
    ChatRouter --> Orchestrator
    Orchestrator --> NLU
    Orchestrator --> Coordinator
    Coordinator <--> SchedAgent & PolicyAgent & LogisticsAgent
    SchedAgent --> SearchEng
    PolicyAgent --> RuleEng & RAGEng
    LogisticsAgent --> RuleEng
    SchedRouter --> SearchEng
    RulesRouter --> RuleEng
    RAGRouter --> RAGEng
    EvalRouter --> BenchEng
    BenchEng --> SearchEng
    SearchEng --> DB
    RuleEng --> DB
    RAGEng --> PolicyCorpus
```

---

## 2. Dynamic Routing Decision-Making Logic

Instead of forcing users to manually choose technical knobs (such as clicking between "Run CSP Search" or "Run A* Heuristic Search"), the **Orchestrator Agent** acts as the central router, inspecting problem characteristics and delegating dynamically:

```mermaid
flowchart TD
    UserQuery["User Natural Language Input"] --> NLU["IntentParser NLU"]
    NLU --> Classify{"Intent & Characteristic Analysis"}

    Classify -- "Rule, Curfew, Guideline or Exemption Inquiry?" --> RouteRAG["Route to Policy RAG Engine\n(Hybrid BM25 + Dense Vector Store)"]
    Classify -- "Venue Directory / Inventory Inquiry?" --> RouteDir["Route to Campus Venue Directory"]
    Classify -- "Algorithm Comparison / Performance Request?" --> RouteBench["Route to AI Benchmark Suite"]
    
    Classify -- "Event Scheduling Request" --> CheckOptimization{"Optimization Requested?\n(e.g., 'minimal waste', 'best fit', 'optimal')"}
    
    CheckOptimization -- "Yes: Seating Waste / Energy Minimization" --> RouteAStar["Route to A* Heuristic Search\n(Admissible Lower-Bound h(n) <= h*(n))"]
    CheckOptimization -- "No: Hard Feasibility Constraints" --> RouteCSP["Route to CSP Solver\n(MRV + LCV + Forward Checking + AC-3)"]

    RouteAStar & RouteCSP --> SubAgentCoord["Multi-Agent Consensus Verification"]
    SubAgentCoord --> PolicyCheck["PolicyComplianceAgent (Rules & Acoustic Curfews)"]
    SubAgentCoord --> LogisticsCheck["LogisticsAgent (AV, Staging & Setup Buffers)"]
    PolicyCheck & LogisticsCheck --> FinalPlan["Synthesize Coordinated Event Plan with .ics Export"]
```

### Routing Rules Explained

1. **When to use CSP (Constraint Satisfaction Problem)**:
   - **Trigger**: The scheduling request imposes strict feasibility criteria—such as minimum room capacity ($capacity \ge attendees$), mandatory equipment (projector, stage, lab computers), venue type (indoor/outdoor), and zero time-slot collisions with pre-existing bookings.
   - **Mechanism**: The Orchestrator delegates to `solve_csp()`, invoking Backtracking Search with Minimum Remaining Values (MRV), Degree heuristic tie-breaking, Least Constraining Value (LCV) ordering, and Forward Checking domain pruning.

2. **When to use A\* Heuristic Search**:
   - **Trigger**: The user's request prioritizes optimization rather than just any valid slot—such as minimizing unused seating capacity waste, reducing walking distances between consecutive sessions, or selecting the single best venue among multiple candidates.
   - **Mechanism**: The Orchestrator delegates to `solve_astar()`, sorting states in a priority queue via $f(n) = g(n) + h(n)$ where $h(n)$ is an admissible lower bound on remaining unassigned events' capacity waste.

3. **When to use Policy RAG (Retrieval-Augmented Generation)**:
   - **Trigger**: The query asks about institutional regulations, acoustic quiet-hours curfews, food/catering prohibitions, crowd security tiers, cancellation deadlines, or alcohol policies (e.g., _"Can a student club book the main auditorium past 8 PM?"_).
   - **Mechanism**: Routes to `PolicyRAGEngine` using hybrid BM25 lexical scoring and dense character-trigram cosine similarity over official policy documents, returning grounded answers with exact clause citations `[Clause X.Y: Doc Title]`.

4. **When to use Logistics & Policy Sub-Agents**:
   - **Trigger**: When candidate venue allocations must be verified for physical operational readiness.
   - **Mechanism**: The Orchestrator delegates AV equipment inspection and buffer calculations (15m standard, 30m for $>200$ attendees, 45m for stage setups) to `LogisticsAgent`, and rules verification to `PolicyComplianceAgent`. If a venue fails policy (e.g., catering in a computer lab), the Coordinator executes multi-turn negotiation to re-search the state space for an alternative venue.

---

## 3. Folder and File Responsibilities

```text
university_event_planner/
├── app/
│   ├── api/
│   │   ├── __init__.py               # API package marker
│   │   ├── routes.py                 # Core endpoints for Venues and Bookings CRUD
│   │   ├── scheduling_routes.py      # Endpoints for CSP, A*, and RFC 5545 iCalendar (.ics) export
│   │   ├── rules_routes.py           # Endpoints for granular venue rule & policy evaluations
│   │   ├── agent_routes.py           # Endpoints for multi-agent planning and conversational POST /chat
│   │   ├── rag_routes.py             # Endpoints for grounded policy retrieval and FAQ answering
│   │   └── evaluation_routes.py      # Endpoints for AI algorithm comparative benchmarking
│   ├── core/
│   │   ├── __init__.py               # Core config package
│   │   └── config.py                 # Absolute database path resolution and Pydantic BaseSettings
│   ├── db/
│   │   ├── __init__.py               # Database package
│   │   ├── base.py                   # SQLAlchemy DeclarativeBase base class
│   │   └── session.py                # Database engine configuration and SessionLocal dependency
│   ├── models/
│   │   ├── __init__.py               # Model exports
│   │   └── entities.py               # SQLAlchemy ORM models: Venue, Facility, Event, Booking
│   ├── schemas/
│   │   ├── __init__.py               # Unified Pydantic schema exports
│   │   ├── scheduling.py             # Request/response schemas for scheduling and state search
│   │   ├── rules.py                  # Schemas for rule checking and compliance scores
│   │   ├── agents.py                 # Schemas for ChatMessageRequest, ChatMessageResponse, AgentPlanResponse
│   │   ├── rag.py                    # Schemas for policy queries, citations, and answers
│   │   └── evaluation.py             # Schemas for AI benchmark comparisons and scenario metrics
│   ├── services/
│   │   ├── __init__.py               # Service package
│   │   ├── scheduler.py              # Baseline single-event candidate filtering utility
│   │   ├── search/                   # State-Space Search Algorithms
│   │   │   ├── __init__.py           # Unified solve_schedule interface
│   │   │   ├── state.py              # Core data classes: TimeSlot, VenueSpec, EventSpec, SearchResult
│   │   │   ├── csp.py                # CSP Backtracking Solver (MRV, Degree, LCV, Forward Checking, AC-3)
│   │   │   ├── astar.py              # A* Search with admissible capacity waste lower-bound heuristic
│   │   │   ├── min_conflicts.py      # Min-Conflicts local search with random walk escape
│   │   │   └── greedy.py             # Baseline greedy first-fit/best-fit heuristic
│   │   ├── rules/                    # Venue Rules & Compliance Engine
│   │   │   ├── __init__.py           # Rule engine exports
│   │   │   ├── engine.py             # Rule protocol and RuleEvaluationReport definitions
│   │   │   └── constraints.py        # Hard constraints (capacity, facilities, buffer, hours) & soft policies
│   │   ├── agents/                   # Multi-Agent Coordination Framework
│   │   │   ├── __init__.py           # Agent exports
│   │   │   ├── base.py               # AgentMessage, CoordinatedEventPlan models
│   │   │   ├── nlu.py                # IntentParser extracting entities and determining algorithm routing
│   │   │   ├── orchestrator.py       # OrchestratorAgent managing conversational chat turns & routing
│   │   │   ├── coordinator.py        # CoordinatorAgent managing multi-turn negotiation & consensus
│   │   │   ├── scheduling_agent.py   # SchedulingAgent executing state search with venue exclusion
│   │   │   ├── policy_agent.py       # PolicyComplianceAgent verifying rules and RAG citations
│   │   │   └── logistics_agent.py    # LogisticsAgent checking AV, setups, and buffers
│   │   ├── rag/                      # Grounded Policy RAG Subsystem
│   │   │   ├── __init__.py           # RAG exports
│   │   │   ├── documents/            # Official campus policy documents (*.md)
│   │   │   ├── vector_store.py       # Hybrid BM25 lexical + dense trigram vector store
│   │   │   └── engine.py             # Grounded policy answering and citation extractor
│   │   └── evaluation/               # AI Approach Benchmarking
│   │       ├── __init__.py           # Evaluation exports
│   │       ├── scenarios.py          # Benchmark workload generators (light, contested, fest, stress)
│   │       └── benchmark.py          # Multi-algorithm performance comparison runner
│   ├── static/                       # Conversational Web Dashboard (Chat-First)
│   │   ├── index.html                # Conversational input, message stream, and modal views
│   │   ├── app.js                    # Chat UI controller, markdown formatter, and .ics downloader
│   │   └── style.css                 # Clean modern typography, message bubbles, and status badges
│   └── main.py                       # FastAPI application entrypoint with automatic startup lifespan
├── scripts/
│   ├── __init__.py
│   ├── seed_demo.py                  # Database seeder with realistic university venues and bookings
│   └── run_benchmark.py              # CLI benchmark utility for terminal evaluation
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # Automatic test database fixture
│   ├── test_agents.py                # Tests for multi-agent coordination and multi-turn negotiation
│   ├── test_chat.py                  # Tests for conversational POST /chat and NLU routing
│   ├── test_api.py                   # Full end-to-end FastAPI test suite
│   ├── test_benchmark.py             # Tests for scenario evaluation engine
│   ├── test_rag.py                   # Tests for BM25/Vector retrieval and citations
│   ├── test_rules.py                 # Tests for hard and soft constraint engine
│   ├── test_scheduler.py             # Tests for baseline scheduler
│   └── test_search.py                # Tests for CSP, A*, Greedy, and Min-Conflicts
├── run.py                            # Self-bootstrapping launcher with virtual environment auto-detection
├── start.bat                         # 1-Click Windows Batch launcher
├── start.ps1                         # 1-Click PowerShell launcher
├── pytest.ini                        # Pytest configuration mapping pythonpath and testpaths
├── requirements.txt                  # Python dependencies
└── ARCHITECTURE.md                   # Living system architecture documentation
```

---

## 4. Data Flow Between Components

### 4.1 Conversational Chat Turn Flow
```mermaid
sequenceDiagram
    autonumber
    actor User as User (Natural Language)
    participant ChatAPI as POST /chat
    participant Orch as OrchestratorAgent
    participant NLU as IntentParser
    participant Coord as CoordinatorAgent
    participant Sched as SchedulingAgent (CSP/A*)
    participant Policy as PolicyComplianceAgent (RAG/Rules)
    participant Log as LogisticsAgent

    User->>ChatAPI: {"message": "I need a hall for 200 people next Thursday with a projector"}
    ChatAPI->>Orch: process_message(text)
    Orch->>NLU: parse(text)
    NLU-->>Orch: NLUParseResult(intent=PLAN_EVENT, route=CSP, entities={attendees: 200, ...})
    
    Orch->>Coord: plan_event(EventSpec)
    Coord->>Sched: REQUEST (Search states for 200 attendees with projector)
    Sched-->>Coord: PROPOSAL (Venue: Demo Multipurpose Hall, Waste: 50 seats)
    
    par Multi-Agent Verification
        Coord->>Policy: REQUEST (Verify rules & acoustic limits)
        Policy-->>Coord: APPROVAL (Compliance: 100%)
    and
        Coord->>Log: REQUEST (Verify projector & 30m buffer)
        Log-->>Coord: APPROVAL (Checklist: IT Media projector check, entry marshals)
    end

    Coord-->>Orch: CoordinatedEventPlan(Status=APPROVED, Venue=Demo Multipurpose Hall)
    Orch-->>ChatAPI: ChatTurnResponse(reply, route=CSP, plan, dialogue)
    ChatAPI-->>User: Conversational Response + Allocation Card + ICS Download Button
```

---

## 5. Mathematical Formulation of Algorithms

### 5.1 Constraint Satisfaction Problem (CSP)
- **Variables**: $X = \{E_1, E_2, \dots, E_n\}$, where each $E_i$ is an event.
- **Domains**: $D(E_i) = \{v \in \text{Venues} \mid v.\text{capacity} \ge E_i.\text{attendees} \land E_i.\text{facilities} \subseteq v.\text{facilities} \land v.\text{open} \le E_i.\text{start} \land v.\text{close} \ge E_i.\text{end}\}$.
- **Binary Non-Overlap Constraint**:
  $$\forall i \ne j, \quad \text{Overlaps}(E_i, E_j, \text{buffer}) \implies \text{Venue}(E_i) \ne \text{Venue}(E_j)$$
- **MRV Heuristic**:
  $$\operatorname{select\_variable}() = \arg\min_{E_i \in \text{Unassigned}} |D(E_i)|$$
- **Degree Heuristic Tie-Breaker**:
  $$\operatorname{degree}(E_i) = \sum_{E_j \in \text{Unassigned}, j \ne i} \mathbb{I}(\text{Overlaps}(E_i, E_j))$$
- **LCV Heuristic**:
  $$\operatorname{order\_values}(E_i) = \operatorname{sort\_by\_ascending}\left( \sum_{E_j \in \text{Unassigned}} \mathbb{I}(v \in D(E_j)) \right)$$

### 5.2 A\* Search Formulation
- **Cost Function**: $f(n) = g(n) + h(n)$
- **Path Cost $g(n)$**:
  $$g(n) = \sum_{(E_i, v) \in \text{assigned}} (v.\text{capacity} - E_i.\text{attendees}) + \text{PreferencePenalty}(E_i, v)$$
- **Admissible Heuristic $h(n)$**:
  $$h(n) = \sum_{E_k \in \text{unassigned}} \min_{v \in \text{CapableVenues}(E_k)} (v.\text{capacity} - E_k.\text{attendees})$$
  *Admissibility Guarantee*: $h(n) \le h^*(n)$ for all states $n$, ensuring optimal search expansion.

---

## 6. External Dependencies and Integrations

| Dependency | Architectural Responsibility |
|:---|:---|
| **FastAPI** | Conversational `/chat` routing, OpenAPI schema, and static file mounting. |
| **Pydantic v2** | Request validation, entity schemas, and response serialization. |
| **SQLAlchemy 2.0** | Relational mapping for venues, bookings, and facility inventories. |
| **Psycopg[binary] 3** | High-throughput PostgreSQL driver for production environments. |
| **SQLite3** | Embedded local database with absolute path anchoring in `config.py`. |
| **Uvicorn** | ASGI server invoked via self-bootstrapping `run.py`. |
| **Pytest** | Automated test runner with automated test database setup. |
| **RFC 5545 iCalendar** | Generates `.ics` calendar invitation files directly downloadable from chat. |
