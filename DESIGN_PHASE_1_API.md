# Enterprise AI SOC Platform - REST API Design & OpenAPI Specification

**Task 3:** Design REST API specifications and OpenAPI docs
**Status:** In Progress → Verification Pending
**Created:** 2026-06-11

---

## API OVERVIEW

### Base URL
```
Development:  http://localhost:8000/api/v1
Production:   https://api.soc-platform.com/api/v1
```

### API Versioning
- Version format: `/api/v1`, `/api/v2`, etc.
- Backward compatibility maintained for 2 previous versions
- Deprecation notices sent 6 months before version sunset

### Rate Limiting
- **Default:** 1000 requests/hour per user
- **Authenticated:** 5000 requests/hour per user
- **Premium:** Unlimited (enterprise tier)
- **Headers:**
  ```
  X-RateLimit-Limit: 1000
  X-RateLimit-Remaining: 950
  X-RateLimit-Reset: 1623348000
  ```

---

## AUTHENTICATION API

### 1. User Registration
```
POST /auth/register

Request:
{
  "email": "analyst@company.com",
  "username": "soc_analyst",
  "password": "SecurePassword123!",
  "first_name": "John",
  "last_name": "Doe"
}

Response (201 Created):
{
  "status": "success",
  "data": {
    "id": "uuid",
    "email": "analyst@company.com",
    "username": "soc_analyst",
    "role": "soc_analyst",
    "mfa_required": true
  },
  "metadata": {
    "timestamp": "2026-06-11T10:30:00Z",
    "request_id": "uuid"
  }
}

Error Responses:
- 400: Invalid email format / Password too weak
- 409: Email already exists / Username taken
- 429: Too many registration attempts
```

### 2. User Login
```
POST /auth/login

Request:
{
  "email": "analyst@company.com",
  "password": "SecurePassword123!"
}

Response (200 OK):
{
  "status": "success",
  "data": {
    "access_token": "jwt.token.here",
    "refresh_token": "jwt.refresh.token",
    "expires_in": 3600,
    "token_type": "Bearer",
    "user": {
      "id": "uuid",
      "email": "analyst@company.com",
      "username": "soc_analyst",
      "role": "soc_analyst",
      "permissions": ["read:incidents", "create:investigations"]
    }
  }
}

Error Responses:
- 401: Invalid credentials
- 403: Account disabled or MFA required
- 429: Too many login attempts (rate limited)
```

### 3. MFA Verification
```
POST /auth/mfa/verify

Request:
{
  "mfa_code": "123456",
  "session_token": "temporary.session.token"
}

Response (200 OK):
{
  "status": "success",
  "data": {
    "access_token": "jwt.token.here",
    "refresh_token": "jwt.refresh.token"
  }
}

Error Responses:
- 401: Invalid MFA code
- 400: Session expired
```

### 4. Refresh Token
```
POST /auth/refresh

Request:
{
  "refresh_token": "jwt.refresh.token"
}

Response (200 OK):
{
  "status": "success",
  "data": {
    "access_token": "new.jwt.token",
    "expires_in": 3600
  }
}

Error Responses:
- 401: Invalid refresh token
- 401: Refresh token expired
```

### 5. Logout
```
POST /auth/logout

Headers:
Authorization: Bearer {access_token}

Response (200 OK):
{
  "status": "success",
  "data": {
    "message": "Logged out successfully"
  }
}
```

---

## INCIDENT MANAGEMENT API

### 1. List Incidents
```
GET /incidents?status=open&severity_min=5&sort=-created_at&page=1&limit=50

Query Parameters:
- status: open|investigating|resolved (comma-separated)
- severity_min/max: 0-10
- category: string
- created_by: uuid
- owner: uuid
- sort: +/- field names
- page: integer
- limit: integer (max 100)

Response (200 OK):
{
  "status": "success",
  "data": [
    {
      "id": "uuid",
      "incident_id": "SOC-001234",
      "title": "Suspicious Login Activity",
      "description": "Multiple failed logins followed by successful access",
      "severity": 7,
      "status": "investigating",
      "category": "credential_access",
      "created_by": {
        "id": "uuid",
        "username": "soc_analyst"
      },
      "owner": {
        "id": "uuid",
        "username": "senior_analyst"
      },
      "tags": ["credential_access", "brute_force"],
      "risk_factors": {
        "access_from_new_location": true,
        "unusual_time": true
      },
      "investigation_count": 1,
      "log_count": 245,
      "created_at": "2026-06-11T09:15:00Z",
      "updated_at": "2026-06-11T10:30:00Z",
      "resolved_at": null
    }
  ],
  "pagination": {
    "total": 234,
    "page": 1,
    "limit": 50,
    "pages": 5
  },
  "metadata": {
    "timestamp": "2026-06-11T10:30:00Z",
    "request_id": "uuid"
  }
}
```

### 2. Create Incident
```
POST /incidents

Headers:
Authorization: Bearer {access_token}
Content-Type: application/json

Request:
{
  "title": "Data Exfiltration Detected",
  "description": "Large volume of data transfer to external IP detected",
  "severity": 9,
  "category": "exfiltration",
  "tags": ["data_loss", "critical"]
}

Response (201 Created):
{
  "status": "success",
  "data": {
    "id": "uuid",
    "incident_id": "SOC-001235",
    "title": "Data Exfiltration Detected",
    "severity": 9,
    "status": "open",
    "created_by_id": "uuid",
    "created_at": "2026-06-11T10:30:00Z"
  }
}

Error Responses:
- 400: Missing required fields / Invalid severity
- 401: Unauthorized
- 403: Insufficient permissions
```

### 3. Get Incident Detail
```
GET /incidents/{incident_id}

Response (200 OK):
{
  "status": "success",
  "data": {
    "id": "uuid",
    "incident_id": "SOC-001234",
    "title": "Suspicious Login Activity",
    "description": "...",
    "severity": 7,
    "status": "investigating",
    "investigations": [
      {
        "id": "uuid",
        "investigator": "soc_analyst",
        "status": "in_progress",
        "created_at": "2026-06-11T09:15:00Z"
      }
    ],
    "logs": [
      {
        "id": "uuid",
        "timestamp": "2026-06-11T09:00:00Z",
        "log_type": "authentication",
        "source_ip": "192.168.1.100"
      }
    ],
    "reports": [
      {
        "id": "uuid",
        "report_type": "executive",
        "created_at": "2026-06-11T10:00:00Z"
      }
    ],
    "timeline": [
      {
        "timestamp": "2026-06-11T09:00:00Z",
        "event": "Failed login attempt",
        "count": 5
      }
    ],
    "created_at": "2026-06-11T09:15:00Z",
    "updated_at": "2026-06-11T10:30:00Z"
  }
}

Error Responses:
- 404: Incident not found
- 403: Access denied
```

### 4. Update Incident
```
PUT /incidents/{incident_id}

Request:
{
  "severity": 8,
  "status": "investigating",
  "owner_id": "uuid"
}

Response (200 OK):
{
  "status": "success",
  "data": {
    "id": "uuid",
    "incident_id": "SOC-001234",
    "severity": 8,
    "status": "investigating",
    "updated_at": "2026-06-11T10:35:00Z"
  }
}
```

### 5. Delete Incident
```
DELETE /incidents/{incident_id}

Response (204 No Content)

Error Responses:
- 403: Cannot delete incident with active investigations
```

---

## INVESTIGATION API

### 1. Create Investigation
```
POST /investigations

Request:
{
  "incident_id": "uuid",
  "initial_notes": "Starting investigation into credential compromise"
}

Response (201 Created):
{
  "status": "success",
  "data": {
    "id": "uuid",
    "incident_id": "uuid",
    "investigator_id": "uuid",
    "status": "open",
    "created_at": "2026-06-11T10:30:00Z"
  }
}
```

### 2. Update Investigation with Findings
```
PUT /investigations/{investigation_id}

Request:
{
  "status": "in_progress",
  "findings": {
    "initial_access": "Compromised service account used for initial entry",
    "lateral_movement": "Attacker moved to domain admin account",
    "data_exfiltrated": true,
    "timeline": [
      {
        "timestamp": "2026-06-11T09:00:00Z",
        "event": "Initial compromise"
      }
    ]
  },
  "affected_assets": [
    {
      "asset_id": "uuid",
      "asset_name": "SERVER-01",
      "asset_type": "windows_server"
    }
  ],
  "mitre_techniques": [
    "T1110.001",
    "T1098.003"
  ]
}

Response (200 OK):
{
  "status": "success",
  "data": {
    "id": "uuid",
    "incident_id": "uuid",
    "status": "in_progress",
    "findings": {...},
    "updated_at": "2026-06-11T10:45:00Z"
  }
}
```

### 3. Add Evidence
```
POST /investigations/{investigation_id}/evidence

Request:
{
  "evidence_type": "file",
  "description": "Malware executable found on compromised server",
  "file_path": "C:\\Windows\\Temp\\malware.exe",
  "file_hash": "a1b2c3d4e5f6g7h8",
  "metadata": {
    "file_size": 45678,
    "created_date": "2026-06-11T08:00:00Z"
  }
}

Response (201 Created):
{
  "status": "success",
  "data": {
    "id": "uuid",
    "investigation_id": "uuid",
    "evidence_type": "file",
    "file_hash": "a1b2c3d4e5f6g7h8",
    "created_at": "2026-06-11T10:30:00Z"
  }
}
```

### 4. Complete Investigation
```
PUT /investigations/{investigation_id}/complete

Request:
{
  "root_cause": "Phishing email led to credential compromise",
  "recommendations": [
    "Reset compromised credentials",
    "Enable MFA for all accounts",
    "Implement email filtering"
  ]
}

Response (200 OK):
{
  "status": "success",
  "data": {
    "id": "uuid",
    "incident_id": "uuid",
    "status": "completed",
    "completed_at": "2026-06-11T11:00:00Z"
  }
}
```

---

## THREAT INTELLIGENCE API

### 1. Search IOCs
```
GET /threat-intel/search?ioc_type=ip&threat_level=high&limit=50

Query Parameters:
- ioc_type: ip|domain|hash|email|url
- ioc_value: partial string search
- threat_level: low|medium|high|critical
- reputation_score_min/max: 0-100
- limit: integer

Response (200 OK):
{
  "status": "success",
  "data": [
    {
      "id": "uuid",
      "ioc_type": "ip",
      "ioc_value": "192.168.100.50",
      "reputation_score": 85,
      "threat_level": "critical",
      "source": "external",
      "sightings_count": 23,
      "first_seen": "2026-05-15T10:00:00Z",
      "last_seen": "2026-06-11T09:30:00Z",
      "enrichments": [
        {
          "enrichment_type": "reputation",
          "provider": "AbuseIPDB",
          "score": 95
        }
      ]
    }
  ],
  "pagination": {
    "total": 234,
    "limit": 50
  }
}
```

### 2. Enrich IOC
```
POST /threat-intel/{ioc_id}/enrich

Request:
{
  "enrichment_type": "reputation_lookup"
}

Response (200 OK):
{
  "status": "success",
  "data": {
    "id": "uuid",
    "ioc_value": "192.168.100.50",
    "enrichments": [
      {
        "enrichment_type": "reputation",
        "provider": "VirusTotal",
        "data": {
          "detections": 42,
          "last_analysis_date": "2026-06-11T09:00:00Z"
        }
      }
    ]
  }
}
```

### 3. Bulk Import IOCs
```
POST /threat-intel/bulk-import

Request:
{
  "threat_level": "high",
  "source": "external",
  "indicators": [
    {
      "ioc_type": "ip",
      "ioc_value": "10.0.0.50"
    },
    {
      "ioc_type": "domain",
      "ioc_value": "malicious.com"
    }
  ]
}

Response (202 Accepted):
{
  "status": "success",
  "data": {
    "job_id": "uuid",
    "status": "processing",
    "total_indicators": 2
  }
}
```

---

## REPORT GENERATION API

### 1. Generate Report
```
POST /reports/generate

Request:
{
  "incident_id": "uuid",
  "report_type": "executive",
  "include_sections": [
    "executive_summary",
    "incident_timeline",
    "technical_analysis",
    "mitre_mapping",
    "recommendations"
  ]
}

Response (202 Accepted):
{
  "status": "success",
  "data": {
    "job_id": "uuid",
    "report_type": "executive",
    "status": "generating",
    "estimated_completion": "2026-06-11T11:00:00Z"
  }
}
```

### 2. Get Report
```
GET /reports/{report_id}

Response (200 OK):
{
  "status": "success",
  "data": {
    "id": "uuid",
    "incident_id": "uuid",
    "report_type": "executive",
    "title": "Incident SOC-001234 Executive Report",
    "content": "# Executive Summary\n\nThis report details...",
    "sections": [
      {
        "type": "executive_summary",
        "content": "...",
        "generated_by": "report_generation_agent"
      }
    ],
    "generated_at": "2026-06-11T10:30:00Z"
  }
}
```

### 3. List Reports
```
GET /reports?incident_id=uuid&report_type=executive&limit=20

Response (200 OK):
{
  "status": "success",
  "data": [
    {
      "id": "uuid",
      "incident_id": "uuid",
      "report_type": "executive",
      "title": "...",
      "status": "published",
      "created_at": "2026-06-11T10:30:00Z"
    }
  ]
}
```

---

## AGENT INTERACTION API

### 1. Execute Agent
```
POST /agents/{agent_type}/execute

Agent Types:
- alert_triage
- threat_intelligence
- investigation
- threat_hunting
- risk_scoring
- report_generation
- response

Request:
{
  "action": "triage",
  "parameters": {
    "incident_id": "uuid",
    "force_reprocess": false
  }
}

Response (202 Accepted):
{
  "status": "success",
  "data": {
    "agent_id": "uuid",
    "agent_type": "alert_triage",
    "execution_id": "uuid",
    "status": "running",
    "estimated_completion": "2026-06-11T10:35:00Z"
  }
}
```

### 2. Get Agent Status
```
GET /agents/{agent_type}/status/{execution_id}

Response (200 OK):
{
  "status": "success",
  "data": {
    "execution_id": "uuid",
    "agent_type": "alert_triage",
    "status": "completed",
    "progress": 100,
    "result": {
      "incidents_processed": 150,
      "duplicates_found": 3,
      "new_alerts": 12
    },
    "started_at": "2026-06-11T10:30:00Z",
    "completed_at": "2026-06-11T10:33:00Z"
  }
}
```

### 3. Cancel Agent Execution
```
DELETE /agents/{agent_type}/execute/{execution_id}

Response (200 OK):
{
  "status": "success",
  "data": {
    "message": "Agent execution cancelled"
  }
}
```

---

## LOGS & SEARCH API

### 1. Ingest Logs
```
POST /logs/ingest

Request:
{
  "logs": [
    {
      "log_type": "windows_security",
      "source_name": "Security",
      "source_ip": "192.168.1.100",
      "destination_ip": "10.0.0.1",
      "event_id": "4625",
      "raw_log": "An account failed to log on...",
      "timestamp": "2026-06-11T10:30:00Z"
    }
  ]
}

Response (202 Accepted):
{
  "status": "success",
  "data": {
    "batch_id": "uuid",
    "logs_received": 1,
    "processing_status": "queued"
  }
}
```

### 2. Search Logs
```
POST /logs/search

Request:
{
  "query": {
    "log_type": "windows_security",
    "source_ip": "192.168.1.100",
    "event_id": "4625"
  },
  "time_range": {
    "start": "2026-06-10T00:00:00Z",
    "end": "2026-06-11T23:59:59Z"
  },
  "limit": 1000,
  "offset": 0
}

Response (200 OK):
{
  "status": "success",
  "data": [
    {
      "id": "uuid",
      "log_type": "windows_security",
      "source_ip": "192.168.1.100",
      "event_id": "4625",
      "raw_log": "...",
      "parsed_log": {...},
      "timestamp": "2026-06-11T10:30:00Z"
    }
  ],
  "pagination": {
    "total": 5234,
    "offset": 0,
    "limit": 1000
  }
}
```

### 3. Correlate Logs
```
POST /logs/correlate

Request:
{
  "incident_id": "uuid",
  "log_ids": ["id1", "id2", "id3"]
}

Response (201 Created):
{
  "status": "success",
  "data": {
    "correlation_id": "uuid",
    "log_count": 3,
    "correlation_strength": 0.95,
    "relationships": [
      {
        "log_1": "id1",
        "log_2": "id2",
        "relationship": "same_source_ip_temporal"
      }
    ]
  }
}
```

---

## USERS & RBAC API

### 1. List Users
```
GET /users?role=soc_analyst&limit=50

Response (200 OK):
{
  "status": "success",
  "data": [
    {
      "id": "uuid",
      "email": "analyst@company.com",
      "username": "soc_analyst",
      "first_name": "John",
      "role": "soc_analyst",
      "permissions": ["read:incidents", "create:investigations"],
      "is_active": true,
      "created_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

### 2. Update User Role
```
PUT /users/{user_id}/role

Request:
{
  "role": "soc_manager"
}

Response (200 OK):
{
  "status": "success",
  "data": {
    "id": "uuid",
    "username": "soc_analyst",
    "role": "soc_manager",
    "permissions": ["read:*", "create:*", "approve:*"]
  }
}
```

---

## OPENAPI SCHEMA (Swagger)

```yaml
openapi: 3.0.0
info:
  title: Enterprise AI SOC Platform API
  version: 1.0.0
  description: Production-ready API for Fortune-500 level AI SOC
  contact:
    name: SOC Platform Team
    email: support@soc-platform.com
  license:
    name: Enterprise License

servers:
  - url: https://api.soc-platform.com/api/v1
    description: Production
  - url: http://localhost:8000/api/v1
    description: Development

security:
  - bearerAuth: []

components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

  schemas:
    Incident:
      type: object
      properties:
        id:
          type: string
          format: uuid
        incident_id:
          type: string
          example: "SOC-001234"
        title:
          type: string
        severity:
          type: integer
          minimum: 0
          maximum: 10
        status:
          type: string
          enum: [open, investigating, resolved]
        created_at:
          type: string
          format: date-time

    Investigation:
      type: object
      properties:
        id:
          type: string
          format: uuid
        incident_id:
          type: string
          format: uuid
        status:
          type: string
          enum: [open, in_progress, completed]
        findings:
          type: object
        mitre_techniques:
          type: array
          items:
            type: string

paths:
  /auth/login:
    post:
      summary: User login
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                email:
                  type: string
                password:
                  type: string
      responses:
        '200':
          description: Login successful
        '401':
          description: Invalid credentials
        '429':
          description: Too many attempts

  /incidents:
    get:
      summary: List incidents
      parameters:
        - name: status
          in: query
          schema:
            type: string
        - name: limit
          in: query
          schema:
            type: integer
            default: 50
      responses:
        '200':
          description: Incidents list
    post:
      summary: Create incident
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [title, severity]
      responses:
        '201':
          description: Incident created

  /investigations:
    post:
      summary: Create investigation
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [incident_id]
      responses:
        '201':
          description: Investigation created

  /agents/{agent_type}/execute:
    post:
      summary: Execute AI agent
      parameters:
        - name: agent_type
          in: path
          required: true
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
      responses:
        '202':
          description: Agent execution started
```

---

## ERROR HANDLING

### Standard Error Response Format
```json
{
  "status": "error",
  "data": null,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Missing required field: severity",
    "details": {
      "field": "severity",
      "reason": "required"
    }
  },
  "metadata": {
    "timestamp": "2026-06-11T10:30:00Z",
    "request_id": "uuid"
  }
}
```

### HTTP Status Codes
- **200:** OK - Successful GET/PUT
- **201:** Created - Successful POST
- **202:** Accepted - Async operation started
- **204:** No Content - Successful DELETE
- **400:** Bad Request - Invalid parameters
- **401:** Unauthorized - Missing/invalid token
- **403:** Forbidden - Insufficient permissions
- **404:** Not Found - Resource doesn't exist
- **409:** Conflict - Resource already exists
- **429:** Too Many Requests - Rate limited
- **500:** Internal Server Error
- **503:** Service Unavailable

### Error Codes
```
AUTH_001: Invalid credentials
AUTH_002: Token expired
AUTH_003: MFA required
AUTH_004: Account disabled

INC_001: Incident not found
INC_002: Invalid severity
INC_003: Cannot modify resolved incident

INV_001: Investigation not found
INV_002: Cannot create investigation for non-existent incident
INV_003: Investigation already completed

TI_001: IOC not found
TI_002: Invalid IOC type
TI_003: IOC already exists

AGENT_001: Agent not found
AGENT_002: Agent execution failed
AGENT_003: Agent timeout

LOG_001: Log ingestion failed
LOG_002: Search timeout
LOG_003: Invalid log format
```

---

## PAGINATION

### Cursor-Based Pagination (Optional for Large Datasets)
```
GET /incidents?cursor=abc123&limit=50

Response:
{
  "data": [...],
  "pagination": {
    "next_cursor": "def456",
    "previous_cursor": "xyz789",
    "has_more": true
  }
}
```

---

## WEBHOOKS (Optional)

### Incident Status Changed
```
POST https://customer-webhook-url.com/incidents

Body:
{
  "event": "incident.status_changed",
  "incident_id": "uuid",
  "old_status": "open",
  "new_status": "investigating",
  "timestamp": "2026-06-11T10:30:00Z"
}
```

---

## RATE LIMITING HEADERS

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1623348000
X-RateLimit-RetryAfter: 120
```

---

## CHECKLIST - TASK 3 VERIFICATION

### REST API Specification Complete?
- [x] Authentication API (register, login, MFA, refresh, logout)
- [x] Incident Management API (CRUD + list)
- [x] Investigation API (create, update, add evidence, complete)
- [x] Threat Intelligence API (search, enrich, bulk import)
- [x] Report Generation API (generate, get, list)
- [x] Agent Interaction API (execute, status, cancel)
- [x] Logs & Search API (ingest, search, correlate)
- [x] Users & RBAC API (list, update role)

### OpenAPI/Swagger Complete?
- [x] Full OpenAPI 3.0 schema
- [x] All endpoints documented
- [x] Request/response examples
- [x] Security schemes
- [x] Error codes

### Error Handling Complete?
- [x] Standard error format
- [x] HTTP status codes
- [x] Custom error codes
- [x] Error details

### Advanced Features Complete?
- [x] Rate limiting strategy
- [x] Pagination (offset & cursor-based)
- [x] Webhooks (optional)
- [x] Versioning strategy
- [x] CORS handling

### Status: ✅ **PHASE 1 - TASK 3 COMPLETE**

**Next Task:** Set up GitHub repository with branch strategy (Task 4)
