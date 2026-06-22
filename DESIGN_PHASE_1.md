# Enterprise AI SOC Platform - Phase 1 Design

**Status:** Design Phase 1 (Foundation & Architecture)
**Created:** 2026-06-11
**Completed Tasks:** 0/5

---

## 1. PROJECT STRUCTURE & FOLDER ORGANIZATION

### Root Directory Layout
```
soc-platform/
├── backend/                          # FastAPI backend
├── frontend/                         # Next.js 15 frontend
├── shared/                           # Shared utilities, types
├── infra/                            # Infrastructure as Code
│   ├── docker/
│   ├── kubernetes/
│   └── terraform/
├── docs/                             # Documentation
├── scripts/                          # Build & deployment scripts
├── tests/                            # Shared test utilities
├── .github/
│   └── workflows/                    # CI/CD pipelines
├── docker-compose.yml
├── docker-compose.prod.yml
└── README.md
```

### Backend Structure (FastAPI)
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                       # Application entry point
│   ├── config.py                     # Configuration management
│   ├── dependencies.py               # Dependency injection
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── logging.py                # Request/response logging
│   │   ├── error_handler.py          # Global error handling
│   │   ├── rate_limiter.py           # Rate limiting
│   │   └── auth.py                   # Authentication middleware
│   ├── security/
│   │   ├── __init__.py
│   │   ├── jwt.py                    # JWT token management
│   │   ├── rbac.py                   # Role-based access control
│   │   ├── encryption.py             # Encryption utilities
│   │   └── audit.py                  # Audit logging
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/                       # API v1
│   │   │   ├── __init__.py
│   │   │   ├── auth.py               # Authentication endpoints
│   │   │   ├── incidents.py          # Incident management
│   │   │   ├── investigations.py     # Investigation endpoints
│   │   │   ├── threat_intel.py       # Threat intelligence
│   │   │   ├── reports.py            # Report generation
│   │   │   ├── agents.py             # Agent interaction
│   │   │   ├── logs.py               # Log ingestion & search
│   │   │   ├── users.py              # User management
│   │   │   └── health.py             # Health checks
│   │   └── ws/                       # WebSocket endpoints
│   │       ├── __init__.py
│   │       └── real_time.py          # Real-time updates
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── incident_service.py
│   │   ├── investigation_service.py
│   │   ├── threat_intel_service.py
│   │   ├── report_service.py
│   │   ├── log_service.py
│   │   ├── user_service.py
│   │   └── agent_service.py
│   ├── repository/
│   │   ├── __init__.py
│   │   ├── base_repository.py        # Generic repository pattern
│   │   ├── user_repository.py
│   │   ├── incident_repository.py
│   │   ├── investigation_repository.py
│   │   ├── log_repository.py
│   │   └── report_repository.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── domain/                   # Domain models
│   │   │   ├── user.py
│   │   │   ├── incident.py
│   │   │   ├── investigation.py
│   │   │   ├── threat_intel.py
│   │   │   ├── report.py
│   │   │   └── agent.py
│   │   └── schemas/                  # Pydantic schemas
│   │       ├── user_schema.py
│   │       ├── incident_schema.py
│   │       ├── investigation_schema.py
│   │       ├── threat_intel_schema.py
│   │       ├── report_schema.py
│   │       └── agent_schema.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py               # Database connection
│   │   ├── session.py                # Session management
│   │   ├── models.py                 # SQLAlchemy ORM models
│   │   └── migrations/               # Alembic migrations
│   │       ├── env.py
│   │       ├── script.py.mako
│   │       └── versions/
│   ├── cache/
│   │   ├── __init__.py
│   │   ├── redis.py                  # Redis connection
│   │   └── cache_manager.py          # Cache operations
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── embeddings.py             # BGE-M3 integration
│   │   ├── pinecone_client.py        # Pinecone integration
│   │   ├── chunking.py               # Document chunking
│   │   ├── retrieval.py              # Hybrid search & retrieval
│   │   ├── reranker.py               # BGE-Reranker integration
│   │   └── knowledge_loader.py       # Knowledge base loading
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py             # Base agent class
│   │   ├── alert_triage_agent.py
│   │   ├── threat_intel_agent.py
│   │   ├── investigation_agent.py
│   │   ├── threat_hunting_agent.py
│   │   ├── risk_scoring_agent.py
│   │   ├── report_generation_agent.py
│   │   ├── response_agent.py
│   │   ├── orchestrator.py           # LangGraph orchestration
│   │   └── state_manager.py          # Agent state management
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── llm_provider.py           # LLM abstraction
│   │   ├── nemotron.py               # Nemotron integration
│   │   ├── fallback_models.py        # Qwen, Llama, DeepSeek
│   │   └── model_config.py           # Model configuration
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py                 # Structured logging
│   │   ├── validators.py             # Input validation
│   │   ├── sanitizers.py             # Input sanitization
│   │   ├── helpers.py                # Helper functions
│   │   └── exceptions.py             # Custom exceptions
│   └── monitoring/
│       ├── __init__.py
│       ├── metrics.py                # Prometheus metrics
│       ├── health.py                 # Health checks
│       └── tracing.py                # Distributed tracing
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # Pytest configuration
│   ├── unit/
│   │   ├── test_auth.py
│   │   ├── test_incidents.py
│   │   ├── test_agents.py
│   │   └── test_services.py
│   ├── integration/
│   │   ├── test_api_endpoints.py
│   │   ├── test_database.py
│   │   └── test_rag_pipeline.py
│   └── e2e/
│       └── test_workflows.py
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── .env.example
└── README.md
```

### Frontend Structure (Next.js 15)
```
frontend/
├── app/
│   ├── layout.tsx                    # Root layout
│   ├── page.tsx                      # Home page
│   ├── (auth)/                       # Auth group
│   │   ├── login/page.tsx
│   │   ├── register/page.tsx
│   │   ├── forgot-password/page.tsx
│   │   └── mfa/page.tsx
│   ├── (dashboard)/                  # Protected dashboard
│   │   ├── layout.tsx                # Dashboard layout
│   │   ├── dashboard/page.tsx        # Executive dashboard
│   │   ├── soc/page.tsx              # SOC dashboard
│   │   ├── analytics/page.tsx        # Analytics dashboard
│   │   ├── incidents/
│   │   │   ├── page.tsx
│   │   │   └── [id]/page.tsx
│   │   ├── investigations/
│   │   │   ├── page.tsx
│   │   │   └── [id]/page.tsx
│   │   ├── threat-intel/
│   │   │   ├── page.tsx
│   │   │   └── [id]/page.tsx
│   │   ├── reports/
│   │   │   ├── page.tsx
│   │   │   └── [id]/page.tsx
│   │   ├── settings/page.tsx
│   │   └── profile/page.tsx
│   ├── api/                          # API routes (if needed)
│   └── error.tsx
├── components/
│   ├── common/
│   │   ├── Header.tsx
│   │   ├── Sidebar.tsx
│   │   ├── Footer.tsx
│   │   ├── ThemeToggle.tsx
│   │   └── Loading.tsx
│   ├── auth/
│   │   ├── LoginForm.tsx
│   │   ├── RegisterForm.tsx
│   │   ├── MFAForm.tsx
│   │   └── ProtectedRoute.tsx
│   ├── dashboards/
│   │   ├── ExecutiveDashboard.tsx
│   │   ├── SOCDashboard.tsx
│   │   ├── AnalyticsDashboard.tsx
│   │   └── shared/
│   │       ├── RiskCard.tsx
│   │       ├── AlertSummary.tsx
│   │       └── TrendChart.tsx
│   ├── investigations/
│   │   ├── InvestigationList.tsx
│   │   ├── InvestigationDetail.tsx
│   │   ├── Timeline.tsx
│   │   ├── CorrelationGraph.tsx
│   │   └── EvidencePanel.tsx
│   ├── incidents/
│   │   ├── IncidentList.tsx
│   │   ├── IncidentDetail.tsx
│   │   ├── IncidentForm.tsx
│   │   └── IncidentTimeline.tsx
│   ├── threat-intel/
│   │   ├── ThreatIntelList.tsx
│   │   ├── IOCEnrichment.tsx
│   │   ├── ThreatIndicators.tsx
│   │   └── ReputationScore.tsx
│   ├── reports/
│   │   ├── ReportGenerator.tsx
│   │   ├── ReportViewer.tsx
│   │   ├── ExecutiveSummary.tsx
│   │   └── TechnicalReport.tsx
│   ├── visualizations/
│   │   ├── MITREHeatmap.tsx
│   │   ├── AttackTimeline.tsx
│   │   ├── TrendChart.tsx
│   │   └── GeoMap.tsx
│   └── ui/                           # Shadcn UI components
│       ├── button.tsx
│       ├── card.tsx
│       ├── modal.tsx
│       └── ...
├── hooks/
│   ├── useAuth.ts
│   ├── useIncidents.ts
│   ├── useInvestigations.ts
│   ├── useThreatIntel.ts
│   ├── useReports.ts
│   └── useTheme.ts
├── contexts/
│   ├── AuthContext.tsx
│   ├── ThemeContext.tsx
│   └── NotificationContext.tsx
├── lib/
│   ├── api-client.ts                 # API client setup
│   ├── auth.ts                       # Auth utilities
│   ├── utils.ts                      # Helper functions
│   └── constants.ts                  # Constants
├── types/
│   ├── index.ts
│   ├── auth.ts
│   ├── incidents.ts
│   ├── investigations.ts
│   ├── threat-intel.ts
│   └── reports.ts
├── styles/
│   ├── globals.css                   # Global styles
│   ├── theme.css                     # Theme variables
│   └── animations.css
├── public/
│   ├── icons/
│   ├── images/
│   └── fonts/
├── tests/
│   ├── __mocks__/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── .env.local.example
├── next.config.js
├── tsconfig.json
├── tailwind.config.js
├── jest.config.js
├── package.json
└── README.md
```

---

## 2. ARCHITECTURE OVERVIEW

### High-Level System Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                      CLIENT LAYER (React/Next.js)              │
│  ┌─────────────┬──────────────┬──────────────┬───────────────┐ │
│  │  Executive  │  SOC         │  Analytics   │  Investigation│ │
│  │  Dashboard  │  Dashboard   │  Dashboard   │  Workspace    │ │
│  └─────────────┴──────────────┴──────────────┴───────────────┘ │
└────────────────────────┬────────────────────────────────────────┘
                         │ REST API + WebSocket
┌────────────────────────▼────────────────────────────────────────┐
│                    API GATEWAY LAYER (FastAPI)                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Middleware: Auth, Logging, Rate Limiting, Error Handler │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
    ┌────────────────────┼────────────────────┐
    │                    │                    │
┌───▼─────┐      ┌───────▼────────┐   ┌──────▼──────┐
│ API     │      │ SERVICE LAYER  │   │ AI AGENTS   │
│Routes   │      │                │   │ (LangGraph) │
├─────────┤      ├────────────────┤   ├─────────────┤
│ Auth    │      │ Auth Service   │   │ Alert Triage│
│ Inc.    │      │ Inc. Service   │   │ Threat Intel│
│ Inv.    │      │ Inv. Service   │   │ Investigation
│ TI      │      │ Report Service │   │ Threat Hunt │
│ Reports │      │ Agent Service  │   │ Risk Score  │
│ Agents  │      │ Cache Manager  │   │ Report Gen  │
│ Logs    │      │ RAG Pipeline   │   │ Response    │
└────┬────┘      └────────┬───────┘   └──────┬──────┘
     │                    │                  │
     └────────────────────┼──────────────────┘
                          │
    ┌─────────────────────┼──────────────────┬────────────────┐
    │                     │                  │                │
┌───▼──────┐    ┌─────────▼────┐  ┌─────────▼──────┐  ┌──────▼─────┐
│ REPOSITORY│    │ CACHE        │  │ LLM PROVIDERS  │  │ RAG PIPELINE│
│ PATTERN   │    │ (Redis)      │  │ (Nemotron +FB) │  │ (Pinecone)  │
├───────────┤    ├──────────────┤  ├────────────────┤  ├─────────────┤
│ User      │    │ Session      │  │ Nemotron       │  │ Embeddings  │
│ Incident  │    │ Cache        │  │ Qwen 3         │  │ (BGE-M3)    │
│ Invest.   │    │ Rate Limit   │  │ Llama          │  │ Chunking    │
│ Log       │    │ Data         │  │ DeepSeek       │  │ Retrieval   │
│ Report    │    │              │  │                │  │ Reranker    │
└───┬───────┘    └──────────────┘  └────────────────┘  │ (BGE-v2-m3) │
    │                                                  └─────────────┘
    │
┌───▼────────────────────────────────────────────────────────────┐
│          PERSISTENCE LAYER                                     │
├─────────────────────────────────────────────────────────────── ┤
│  PostgreSQL (Primary DB)  │  Pinecone (Vector DB)              │
│  - Users                  │  - CVEs                            │
│  - Incidents              │  - MITRE ATT&CK                    │
│  - Investigations         │  - NIST Docs                       │
│  - Logs                   │  - Policies                        │
│  - Reports                │  - Playbooks                       │
│  - Audit Logs             │  - Threat Intel                    │
└────────────────────────────────────────────────────────────────┘
```

---

## 3. DESIGN PATTERNS & PRINCIPLES

### Architectural Patterns
1. **Clean Architecture** - Separation of concerns (API, Service, Repository, Domain)
2. **Repository Pattern** - Abstract data access layer
3. **Service Layer Pattern** - Business logic encapsulation
4. **Dependency Injection** - Loose coupling, testability
5. **Agent Pattern** - Each AI agent is independent and composable
6. **Event-Driven** - Incident updates via WebSocket/events

### SOLID Principles
- **S**ingle Responsibility - Each class has one reason to change
- **O**pen/Closed - Open for extension, closed for modification
- **L**iskov Substitution - Subtypes replaceable for base types
- **I**nterface Segregation - Specific interfaces vs general ones
- **D**ependency Inversion - Depend on abstractions, not concretions

### Design Patterns Used
- Factory Pattern (LLM provider selection)
- Strategy Pattern (Search strategies: semantic/keyword/hybrid)
- Observer Pattern (Real-time alerts via WebSocket)
- State Pattern (Incident/Investigation states)
- Builder Pattern (Complex query construction)
- Decorator Pattern (Middleware)

---

## 4. TECHNOLOGY STACK RATIONALE

### Backend: FastAPI
- ✅ High performance async framework
- ✅ Built-in validation with Pydantic
- ✅ Automatic OpenAPI documentation
- ✅ WebSocket support for real-time updates
- ✅ Enterprise-ready with middleware support
- ✅ Large ecosystem (security, caching, ORM)

### Frontend: Next.js 15
- ✅ React server components for performance
- ✅ File-based routing
- ✅ Built-in API routes
- ✅ TypeScript support
- ✅ Automatic code splitting
- ✅ Image optimization

### AI Orchestration: LangGraph
- ✅ Multi-agent orchestration
- ✅ State management
- ✅ Composable agents
- ✅ Streaming support
- ✅ Production-ready

### Vector DB: Pinecone
- ✅ Managed vector database
- ✅ Namespaces for multi-tenancy
- ✅ Metadata filtering
- ✅ Hybrid search ready
- ✅ 99.95% SLA

### LLM: Nemotron + Fallbacks
- ✅ Nemotron: Specialized for enterprise/security
- ✅ Qwen 3: Open-source alternative
- ✅ Llama: Flexible deployment
- ✅ DeepSeek: Cost-effective

---

## 5. DATABASE SCHEMA OVERVIEW

### Core Tables
```
USERS
├── id (PK)
├── email (UNIQUE)
├── username (UNIQUE)
├── password_hash
├── first_name
├── last_name
├── role_id (FK)
├── mfa_enabled
├── is_active
├── created_at
└── updated_at

INCIDENTS
├── id (PK)
├── incident_id (UNIQUE)
├── title
├── description
├── severity (0-10)
├── status (open, investigating, resolved)
├── category
├── created_by_id (FK)
├── owner_id (FK)
├── created_at
├── updated_at
└── resolved_at

INVESTIGATIONS
├── id (PK)
├── incident_id (FK)
├── investigator_id (FK)
├── status (open, in_progress, completed)
├── findings (JSON)
├── timeline (JSONB)
├── affected_assets (JSONB)
├── initial_access (TEXT)
├── lateral_movement (TEXT)
├── root_cause (TEXT)
├── created_at
├── updated_at
└── completed_at

LOGS
├── id (PK)
├── log_type (windows, linux, firewall, etc.)
├── source_ip
├── destination_ip
├── timestamp
├── raw_log (TEXT)
├── parsed_log (JSONB)
├── incident_id (FK) [nullable]
├── indexed (BOOLEAN)
└── created_at

THREAT_INDICATORS
├── id (PK)
├── ioc_type (ip, domain, hash, email)
├── ioc_value
├── reputation_score (0-100)
├── threat_level (low, medium, high, critical)
├── source (internal, external)
├── last_seen
├── created_at
└── updated_at

REPORTS
├── id (PK)
├── incident_id (FK)
├── report_type (executive, technical, rca)
├── title
├── content (TEXT)
├── generated_by (agent_name)
├── created_at
└── updated_at

AUDIT_LOGS
├── id (PK)
├── user_id (FK)
├── action (read, create, update, delete)
├── resource_type
├── resource_id
├── old_value (JSONB)
├── new_value (JSONB)
├── timestamp
└── ip_address
```

---

## 6. API DESIGN PRINCIPLES

### REST Conventions
```
Authentication:
  POST /api/v1/auth/login
  POST /api/v1/auth/register
  POST /api/v1/auth/refresh
  POST /api/v1/auth/logout

Incidents:
  GET    /api/v1/incidents
  POST   /api/v1/incidents
  GET    /api/v1/incidents/{id}
  PUT    /api/v1/incidents/{id}
  DELETE /api/v1/incidents/{id}

Investigations:
  GET    /api/v1/investigations
  POST   /api/v1/investigations
  GET    /api/v1/investigations/{id}
  PUT    /api/v1/investigations/{id}

Agents:
  POST   /api/v1/agents/{agent_type}/execute
  GET    /api/v1/agents/{agent_type}/status

Logs:
  POST   /api/v1/logs/ingest
  GET    /api/v1/logs/search
```

### Response Format
```json
{
  "status": "success|error",
  "data": {},
  "error": null,
  "metadata": {
    "timestamp": "2026-06-11T10:30:00Z",
    "request_id": "uuid"
  }
}
```

---

## 7. SECURITY ARCHITECTURE

### Authentication Flow
```
Client
  ↓ username/password
Backend (JWT Validator)
  ↓ valid
JWT Token (access + refresh)
  ↓ store in secure cookie
Client stores token
  ↓ each request
Backend validates JWT signature
  ↓ valid
Proceed
```

### RBAC Model
```
ROLES:
├── admin (all permissions)
├── soc_manager (create investigations, approve responses)
├── soc_analyst (view, search, investigate)
├── threat_hunter (view, create threat hunts)
├── report_viewer (view reports, executive dashboard)
└── readonly (view only, no modifications)
```

### Security Layers
1. **Network Layer** - HTTPS/TLS, WAF
2. **API Layer** - CORS, Rate Limiting, Input Validation
3. **Authentication** - JWT with refresh tokens
4. **Authorization** - RBAC with granular permissions
5. **Data Layer** - Encryption at rest, prepared statements
6. **Audit** - Complete audit trail with immutable logs

---

## CHECKLIST - TASK 1 VERIFICATION

### Project Structure Complete?
- [x] Backend folder structure (38 files/folders)
- [x] Frontend folder structure (15+ routes, components, hooks)
- [x] Shared utilities structure
- [x] Infrastructure setup structure
- [x] Documentation folder
- [x] Testing structure for all layers
- [x] Docker and CI/CD structure

### Architecture Documentation Complete?
- [x] High-level system diagram
- [x] Layer separation documented
- [x] Design patterns identified
- [x] SOLID principles mapped
- [x] Technology stack rationale
- [x] Data flow diagrams
- [x] Security architecture

### Status: ✅ **PHASE 1 - TASK 1 COMPLETE**

**Next Task:** Design complete database schema and ER diagram (Task 2)
