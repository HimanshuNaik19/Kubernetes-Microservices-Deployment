# Kubernetes Architecture Guide

## System Architecture

This project implements a three-tier microservices architecture deployed on Kubernetes:

```
┌─────────────────────────────────────────────────────────────────┐
│                      INGRESS CONTROLLER                          │
│                   (nginx-ingress)                                │
│                                                                   │
│  Rules:                                                          │
│  • /     → Frontend Service                                     │
│  • /api/ → Backend Service                                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
         ▼                               ▼
┌─────────────────┐            ┌─────────────────┐
│ Frontend Service│            │ Backend Service │
│  (NodePort)     │            │  (ClusterIP)    │
│  Port: 30080    │            │  Port: 8080     │
└────────┬────────┘            └────────┬────────┘
         │                               │
         │                               │
         ▼                               ▼
┌─────────────────┐            ┌─────────────────┐
│ Frontend Pods   │            │  Backend Pods   │
│ (Deployment)    │            │  (Deployment)   │
│                 │            │                 │
│ • Replicas: 3   │            │ • Replicas: 2   │
│ • HPA: 2-10     │            │ • HPA: 2-8      │
│ • CPU: 100m     │            │ • CPU: 100m     │
│ • Mem: 128Mi    │            │ • Mem: 128Mi    │
│                 │            │                 │
│ Health Checks:  │            │ Health Checks:  │
│ • Liveness      │            │ • Liveness      │
│ • Readiness     │            │ • Readiness     │
└─────────────────┘            └────────┬────────┘
                                        │
                                        │
                                        ▼
                             ┌─────────────────┐
                             │ PostgreSQL      │
                             │ (StatefulSet)   │
                             │                 │
                             │ • Replicas: 1   │
                             │ • CPU: 250m     │
                             │ • Mem: 256Mi    │
                             │ • Storage: 10Gi │
                             │                 │
                             │ Persistent:     │
                             │ • PVC Template  │
                             │ • Stable ID     │
                             └─────────────────┘
```

## Network Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    NETWORK POLICIES                          │
└─────────────────────────────────────────────────────────────┘

Frontend Pods
  ↓ (Allow all ingress from Ingress Controller)
  ↓ (Allow egress to Backend)
  
Backend Pods
  ↑ (Allow ingress ONLY from Frontend)
  ↓ (Allow egress ONLY to Database)
  
Database Pods
  ↑ (Allow ingress ONLY from Backend)
  ✗ (Deny all other traffic)
```

## Kubernetes Resources Breakdown

### 1. Namespaces

**Purpose**: Environment isolation and resource management

- **dev**: Development environment with relaxed policies
- **staging**: Pre-production testing
- **prod**: Production with ResourceQuotas

**ResourceQuota (prod)**:
```yaml
CPU Requests: 16 cores
Memory Requests: 32Gi
CPU Limits: 32 cores
Memory Limits: 64Gi
Max Pods: 100
```

### 2. Deployments

**Frontend Deployment**:
- **Replicas**: 3 (high availability)
- **Update Strategy**: RollingUpdate (maxSurge: 1, maxUnavailable: 0)
- **Anti-Affinity**: Spread pods across nodes
- **Probes**: 
  - Liveness: `/health` every 10s
  - Readiness: `/health` every 5s

**Backend Deployment**:
- **Replicas**: 2
- **Update Strategy**: RollingUpdate (zero-downtime)
- **Anti-Affinity**: Prevent single point of failure
- **Environment**: ConfigMap + Secrets injection
- **Probes**:
  - Liveness: `/health` every 10s
  - Readiness: `/ready` every 5s (checks DB connection)

### 3. StatefulSet (PostgreSQL)

**Why StatefulSet?**
- Stable network identity (`postgres-0.postgres.dev.svc.cluster.local`)
- Persistent storage that survives pod restarts
- Ordered deployment and scaling
- Headless service for direct pod access

**Features**:
- **VolumeClaimTemplate**: Automatic PVC creation per pod
- **Storage**: 10Gi persistent volume
- **Probes**: `pg_isready` for health checks

### 4. Services

**Service Types**:

| Service | Type | Purpose |
|---------|------|---------|
| Frontend | NodePort | External access (port 30080) |
| Backend | ClusterIP | Internal only (via Ingress) |
| PostgreSQL | ClusterIP (Headless) | StatefulSet DNS |

**Session Affinity**: Frontend service uses ClientIP affinity for sticky sessions

### 5. Ingress

**Path-Based Routing**:
- `/` → Frontend (SPA routing)
- `/api/*` → Backend (REST API)

**Features**:
- CORS configuration
- SSL redirect disabled (for local dev)
- Rewrite rules for clean URLs

### 6. Horizontal Pod Autoscaler (HPA)

**Frontend HPA**:
```yaml
Min Replicas: 2
Max Replicas: 10
Target CPU: 70%
Target Memory: 80%
Scale-up: 2 pods every 30s (or 50% increase)
Scale-down: 1 pod every 5 minutes
```

**Backend HPA**:
```yaml
Min Replicas: 2
Max Replicas: 8
Target CPU: 70%
Target Memory: 75%
Scale-up: 1 pod every 30s (or 100% increase)
Scale-down: 1 pod every 2 minutes
```

**How it works**:
1. Metrics Server collects CPU/memory usage
2. HPA controller checks metrics every 15s
3. If usage > target, scale up
4. If usage < target (for stabilization window), scale down

### 7. NetworkPolicies

**Micro-segmentation Strategy**:

**Backend Policy**:
- **Ingress**: Allow ONLY from Frontend pods
- **Egress**: Allow ONLY to Database + DNS

**Database Policy**:
- **Ingress**: Allow ONLY from Backend pods
- **Egress**: Allow ONLY DNS (for updates)

**Security Benefits**:
- Prevents lateral movement
- Limits blast radius of compromised pods
- Enforces least-privilege networking

### 8. ConfigMaps & Secrets

**ConfigMap** (`app-config`):
- Database connection details (non-sensitive)
- API configuration
- Feature flags

**Secret** (`db-secrets`):
- Database credentials (base64 encoded)
- API keys
- TLS certificates

**Injection Methods**:
- Environment variables
- Volume mounts (for files)

### 9. RBAC

**Components**:
- **ServiceAccount**: `task-manager-sa`
- **Role**: Read-only access to pods, services, configmaps
- **RoleBinding**: Associates SA with Role

**Principle**: Least privilege - only necessary permissions

## Data Flow

### User Request Flow

```
1. User → Ingress Controller
   ↓
2. Ingress → Frontend Service (based on path)
   ↓
3. Frontend Service → Frontend Pod (load balanced)
   ↓
4. Frontend Pod → Serves React app
   ↓
5. React App → API call to /api/tasks
   ↓
6. Ingress → Backend Service
   ↓
7. Backend Service → Backend Pod (load balanced)
   ↓
8. Backend Pod → PostgreSQL Service
   ↓
9. PostgreSQL Service → PostgreSQL Pod (StatefulSet)
   ↓
10. PostgreSQL → Returns data
    ↓
11. Backend → Processes and returns JSON
    ↓
12. Frontend → Renders UI
```

### Auto-scaling Flow

```
1. Load increases → CPU/Memory usage rises
   ↓
2. Metrics Server → Collects pod metrics
   ↓
3. HPA Controller → Checks metrics every 15s
   ↓
4. If usage > 70% CPU or 80% Memory:
   ↓
5. HPA → Increases replica count
   ↓
6. Deployment → Creates new pods
   ↓
7. Service → Adds new pods to load balancer
   ↓
8. Load distributed across more pods
   ↓
9. When load decreases (after stabilization):
   ↓
10. HPA → Decreases replica count
```

## Deployment Strategies

### Rolling Update (Default)

```
Current: v1 [Pod1] [Pod2] [Pod3]
         ↓
Step 1:  v1 [Pod1] [Pod2] [Pod3] v2 [Pod4]
         ↓
Step 2:  v1 [Pod2] [Pod3] v2 [Pod4] [Pod5]
         ↓
Step 3:  v1 [Pod3] v2 [Pod4] [Pod5] [Pod6]
         ↓
Final:   v2 [Pod4] [Pod5] [Pod6]
```

**Benefits**:
- Zero downtime
- Gradual rollout
- Easy rollback

### Canary Deployment (Staging)

```
Production: v1 [90% traffic]
Canary:     v2 [10% traffic]
            ↓
Monitor metrics, errors
            ↓
If OK: Gradually increase v2 traffic
If NOT OK: Rollback to v1
```

## Monitoring & Observability

### Health Checks

**Liveness Probe**:
- **Purpose**: Detect deadlocked containers
- **Action**: Restart pod if fails
- **Interval**: Every 10s

**Readiness Probe**:
- **Purpose**: Detect if pod can serve traffic
- **Action**: Remove from service if fails
- **Interval**: Every 5s

### Resource Monitoring

**Metrics Server**:
- Collects CPU and memory metrics
- Powers HPA decisions
- Provides `kubectl top` data

### Logging Strategy

- **stdout/stderr**: Captured by Kubernetes
- **kubectl logs**: View pod logs
- **Centralized logging**: (Optional) Fluentd → Elasticsearch → Kibana

## High Availability

**Strategies Implemented**:

1. **Multiple Replicas**: Frontend (3), Backend (2)
2. **Anti-Affinity**: Spread pods across nodes
3. **Health Probes**: Auto-restart unhealthy pods
4. **HPA**: Auto-scale based on load
5. **Rolling Updates**: Zero-downtime deployments
6. **StatefulSet**: Persistent database storage

## Disaster Recovery

**Database Backup**:
- PersistentVolume snapshots
- Regular backups to external storage
- Point-in-time recovery

**Application Recovery**:
- Rollback deployments: `kubectl rollout undo`
- ConfigMap/Secret versioning
- GitOps for infrastructure state

## Performance Optimization

1. **Resource Limits**: Prevent resource exhaustion
2. **HPA**: Auto-scale to meet demand
3. **Anti-Affinity**: Distribute load across nodes
4. **Caching**: Nginx caching for static assets
5. **Connection Pooling**: Database connection reuse

## Security Best Practices

✅ **Implemented**:
- NetworkPolicies for micro-segmentation
- RBAC for least-privilege access
- Secrets for sensitive data
- Non-root containers
- Resource quotas to prevent DoS
- Health checks for availability

🔜 **Future Enhancements**:
- Pod Security Policies/Standards
- Image scanning
- TLS/mTLS for service mesh
- OPA for policy enforcement
- Vault for secret management
