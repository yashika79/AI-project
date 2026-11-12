# University Event Planner — Intelligent AI Scheduling & Allocation System

An intelligent university event scheduling, venue allocation, multi-agent coordination, and policy verification system.

## 🚀 How to Run the Project (1-Click)

### Option 1: Double-Click or Run `start.bat` (Windows)
```cmd
start.bat
```
This automatically boots the server and opens:
- **Interactive Web Dashboard**: `http://127.0.0.1:8000/`
- **Swagger API Documentation**: `http://127.0.0.1:8000/docs`

### Option 2: PowerShell
```powershell
.\start.ps1
```
Or directly with the virtual environment Python:
```powershell
.\university_event_planner\venv\Scripts\python.exe run.py
```

### Option 3: Run Automated Tests
```powershell
.\university_event_planner\venv\Scripts\python.exe -m pytest
```

### Option 4: Run AI Benchmark via CLI
```powershell
.\university_event_planner\venv\Scripts\python.exe scripts/run_benchmark.py --scenario medium
```

---

## Architecture Documentation

For complete architectural details, mathematical formulations, data flow sequence diagrams, and design trade-offs, refer to:
- [`ARCHITECTURE.md`](file:///c:/Users/yashi\Downloads\university_event_planner_starter\ARCHITECTURE.md)

---

## Key Capabilities

1. **State-Space Search Subsystem (`app/services/search/`)**:
   - **CSP Solver**: Constraint Satisfaction Problem with Backtracking, Minimum Remaining Values (MRV), Degree Heuristic, Least Constraining Value (LCV), Forward Checking, and AC-3 Arc Consistency.
   - **A\* Heuristic Search**: Explores state spaces with an admissible capacity waste lower-bound heuristic $h(n) \le h^*(n)$ for optimal venue fit.
   - **Min-Conflicts Local Search**: Iterative repair metaheuristic with random-walk escape for resolving timetable collisions.
   - **Greedy Best-Fit Baseline**: Rapid heuristic allocation for benchmarking.

2. **Venue Rules & Compliance Engine (`app/services/rules/`)**:
   - **Hard Constraints**: Capacity check, required facilities, operating hours, buffer collisions (15m-45m setup/teardown), and venue type.
   - **Soft Policy & Compliance**: Campus quiet hours & acoustic curfew, food/catering restrictions, crowd management tiers (Security $\ge 200$, EMT $\ge 500$), and capacity utilization efficiency.

3. **Multi-Agent Coordination Framework (`app/services/agents/`)**:
   - **CoordinatorAgent**: Oversees scheduling workflow, negotiates agent trade-offs, and issues consensus plans.
   - **SchedulingAgent**: Formulates search states and drives CSP/A* solvers.
   - **PolicyComplianceAgent**: Evaluates campus rules and retrieves grounded policy clauses.
   - **LogisticsAgent**: Validates AV equipment, staging buffers, and dispatch checklists.

4. **Policy-Aware RAG Engine (`app/services/rag/`)**:
   - Hybrid Lexical (Okapi BM25) and Dense Semantic Vector retrieval over official campus policy documents.
   - Grounded answers with exact citations `[Clause X.Y: Doc Title]` and compliance checklists with zero hallucination.

5. **AI Approach Evaluation & Benchmarking (`app/services/evaluation/`)**:
   - Compares Greedy, CSP, A*, and Min-Conflicts across standardized workloads (Light, Contested, Campus Fest, Stress).
   - Generates comparative metrics on solve rates, execution times, state expansions, and capacity waste.

6. **Interactive Web Dashboard (`app/static/`)**:
   - Modern, responsive single-page web UI accessible at `/`.
   - Real-time event planning, agent trace visualization, policy RAG assistant, and benchmark runner.

---

## API Endpoints

- **Venues & Bookings**:
  - `GET /venues`: List all campus venues and facility inventories.
  - `GET /venues/{id}`: Detailed venue specifications.
  - `GET /bookings`: List active confirmed bookings.
  - `POST /bookings`: Reserve a time slot for a venue.

- **Scheduling & Search**:
  - `POST /schedule/recommend`: Baseline recommendation for a single event.
  - `POST /schedule/search`: State-space search with algorithm selection (`csp`, `astar`, `greedy`, `min_conflicts`).

- **Venue Rules & Policies**:
  - `POST /rules/evaluate`: Granular evaluation of hard constraints and soft campus policies.

- **Multi-Agent Coordination**:
  - `POST /agents/plan`: Orchestrates Coordinator, Scheduling, Policy, and Logistics agents.

- **Policy-Aware RAG**:
  - `POST /rag/query`: Grounded policy inquiries with verifiable citations.
  - `GET /rag/documents`: Indexed policy corpus index.

- **AI Approach Evaluation**:
  - `GET /evaluation/scenarios`: List evaluation scenarios.
  - `POST /evaluation/benchmark`: Execute comparative benchmarks across AI approaches.

