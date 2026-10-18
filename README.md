# Zero Trust IoT Security Framework for GPS-Based Sandalwood Tree Tracking and Environmental Monitoring

An enterprise-grade, Zero Trust monitoring system and modern React operational web console for registering verified Sandalwood (*Santalum album*) trees, tracking long-lived GPS identities, ingesting environmental sensor telemetry (Temperature, Humidity, Soil Moisture), detecting microclimatic anomalies using Isolation Forest AI, sealing records with SHA-256 cryptographic hashes, and anchoring security audit ledgers to an Ethereum-compatible blockchain contract.

---

## 1. System Architecture

```
FIELD / FOREST AREA
 |
 +-- GPS Location (Lat/Lon)
 +-- Temperature (°C)
 +-- Humidity (%)
 +-- Soil Moisture (%)
 |
 v
FIELD IoT DEVICE (Stationary Node / Mobile Surveyor)
 |
 v
SECURE INGESTION GATE (HTTP / MQTT)
 |
 v
ZERO TRUST SECURITY GATE
 |-- Device Identity & Status (ACTIVE / REVOKED)
 |-- Key Signature Verification (HMAC / Cryptographic Hash)
 |-- Point-in-Polygon Region GPS Boundary Validation
 |-- Physical Sensor Bound Verification (Physics Sanity Rules)
 |-- Anti-Replay Timestamp Tolerance Window (X-Timestamp)
 +-- Deterministic SHA-256 Canonical Integrity Sealing
 |
 v
TREE + ENVIRONMENTAL DATA PROCESSING
 |
 +--> SQLite / PostgreSQL Ledger
 |
 +--> AI Anomaly Detection Engine (Isolation Forest + VPD Feature Engineering)
 |     |
 |     +--> NORMAL: Stored cleanly
 |     +--> ANOMALY: Triggers Alert Lifecycle (LOW / MEDIUM / HIGH / CRITICAL)
 |
 v
AUDIT TRAIL SERVICE (Cryptographic Hash Chaining)
 |
 v
BLOCKCHAIN EVIDENCE ANCHORING (Merkle Root Batching on Smart Contract)
 |
 v
ENTERPRISE REACT GIS OPERATIONS DASHBOARD & REST API
```

---

## 2. Directory Structure

```
zero-trust-sandalwood/
├── app/                                    # FastAPI Backend Architecture
│   ├── main.py                             # FastAPI app factory & lifespan
│   ├── core/                               # Security, encryption, integrity, config
│   ├── database/                           # SQLAlchemy engine, base, models & seeder
│   │   └── models/                         # User, Device, Tree, Measurement, Alert, AuditLog, Session
│   ├── schemas/                            # Pydantic v2 schemas
│   ├── api/                                # REST API routers & routes
│   │   └── routes/                         # auth, devices, trees, measurements, alerts, dashboard, audit, map
│   ├── services/                           # Business logic coordinators
│   ├── mqtt/                               # IoT MQTT client, subscriber & Zero Trust handlers
│   ├── ai/                                 # Feature engineering, Isolation Forest model & detector
│   ├── blockchain/                         # Web3 RPC client, contract wrapper & audit logger
│   └── middleware/                         # Zero Trust authentication, authorization & anti-replay
├── blockchain/
│   ├── contracts/
│   │   └── SandalwoodAuditRegistry.sol     # Solidity smart contract
│   └── scripts/
│       └── deploy.py                       # Contract deployment script
├── frontend/                               # Clean, Modern React TypeScript Frontend
│   ├── src/
│   │   ├── api/                            # Zero Trust Axios client with anti-replay headers
│   │   ├── components/                     # Leaflet GIS Radar, Charts, Drawers, Modals, Badges
│   │   ├── context/                        # AuthContext & ToastContext
│   │   ├── pages/                          # Overview, Map, Trees, Devices, Regions, Anomaly, Alerts, Audit, System
│   │   └── types/                          # TypeScript interface declarations
│   ├── package.json
│   └── vite.config.ts
├── tests/                                  # Full automated pytest test suite (125 tests passing)
├── Dockerfile                              # Multi-stage production container
├── docker-compose.yml                      # Full orchestration stack
├── requirements.txt
└── README.md
```

---

## 3. Quick Start & Execution

### 1. Backend Server (FastAPI)
```powershell
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Run FastAPI backend server (Port 8000)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend Application (React + Vite)
```powershell
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies (if not already installed)
npm install

# 3. Launch Vite Development Server (Port 3000)
npm run dev
```

---

## 4. Platform Access Points & Credentials

- **Frontend Operational Console**: [http://127.0.0.1:3000](http://127.0.0.1:3000)
- **Interactive Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Diagnostics**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### Seeded accounts

Usernames are `admin` and `operator`. Passwords come from `SEED_ADMIN_PASSWORD` and `SEED_OPERATOR_PASSWORD` in `.env`. Public self-registration is off unless `ALLOW_PUBLIC_REGISTRATION=true`.

---

## 5. Clean Operational Modules

1. **🛡️ Zero Trust Security Layer**: Automated `X-Timestamp` anti-replay header injection, cryptographic SHA-256 seals, and JWT session handling.
2. **🗺️ GIS Sandalwood Radar Map**: Real-time Leaflet GIS mapping with Karnataka reserve polygon overlays (Shivamogga, Mysore, Coorg), health-colored tree markers, IoT node markers, tactical radar concentric rings, and spatial radius proximity scan.
3. **📊 Executive Command Dashboard**: Real-time KPI summaries, interactive environmental time-series charts (Temp, Humidity, Soil, VPD), health distribution donuts, and live incident stream.
4. **🌲 Sandalwood Tree Registry**: Searchable asset catalog, physical traits tracking, GPS in-polygon verification wizard, and microclimate telemetry history drawer.
5. **📡 IoT Field Hardware Fleet**: Fleet status management, one-click device quarantine revocation, hardware provisioning with one-time API keys, and an interactive telemetry ingestion & attack simulator.
6. **🌱 Forest Reserves & Sectors**: Protected Karnataka state agroforestry zones, polygon centroid & vertex inspection, and GPS point-in-polygon verification tester.
7. **📈 Telemetry Logs & Cryptographic Sealing**: Live microclimate telemetry stream with single-record SHA-256 validation and bulk database integrity audit scanner.
8. **🧠 AI Anomaly Detection Engine**: Live parameter sandbox to test microclimatic variations against the Isolation Forest model, VPD stress calculation, model diagnostics, and one-click model retraining.
9. **🚨 Incident & Alert Operations Center**: Multi-status workflow (Active, Acknowledged, Resolved, Dismissed) with operator resolution notes and manual dispatch tool.
10. **⛓️ Cryptographic Audit Ledger & Blockchain Explorer**: SHA-256 backward hash-chain timeline, one-click chain integrity verification backwards to genesis, and Ethereum Merkle root smart contract anchoring.
11. **⚙️ System Diagnostics & RBAC Management**: Comprehensive telemetry health, database connectivity, and administrative user account management.

---

## 6. Automated Testing

Run the automated backend test suite (125 tests):
```powershell
python -m pytest -v
```

Run the frontend production build & TypeScript check:
```powershell
cd frontend
npm run build
```
