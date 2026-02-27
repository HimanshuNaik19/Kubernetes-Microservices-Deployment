# Kubernetes Deep Dive

## Why Kubernetes for This Project?

Kubernetes provides:
- **Orchestration**: Automated deployment, scaling, and management
- **Self-healing**: Automatic restart of failed containers
- **Service Discovery**: Built-in DNS and load balancing
- **Storage Orchestration**: Automatic mounting of storage systems
- **Secret Management**: Secure handling of sensitive data
- **Horizontal Scaling**: Easy scaling based on metrics

## Core Concepts Explained

### 1. Pods

**What**: Smallest deployable unit in Kubernetes

**In This Project**:
- Frontend pods run nginx + React build
- Backend pods run Python Flask with gunicorn
- Database pod runs PostgreSQL

**Key Features**:
- Shared network namespace (localhost communication)
- Shared storage volumes
- Atomic scheduling unit

### 2. Deployments vs StatefulSets

**Deployment** (Frontend, Backend):
- **Use Case**: Stateless applications
- **Pod Identity**: Interchangeable
- **Storage**: Ephemeral or shared
- **Scaling**: Any pod can be removed
- **DNS**: Service name only

**StatefulSet** (Database):
- **Use Case**: Stateful applications
- **Pod Identity**: Stable, unique (`postgres-0`)
- **Storage**: Persistent per pod
- **Scaling**: Ordered (0, 1, 2...)
- **DNS**: Individual pod DNS

**Why StatefulSet for Database?**
```
Regular Deployment:
  postgres-abc123 → Dies → postgres-xyz789 (NEW storage)
  ❌ Data lost!

StatefulSet:
  postgres-0 → Dies → postgres-0 (SAME storage)
  ✅ Data persists!
```

### 3. Services

**Service Types in This Project**:

**ClusterIP** (Backend, Database):
```yaml
type: ClusterIP
# Internal only, no external access
# Accessible via: backend.dev.svc.cluster.local
```

**NodePort** (Frontend):
```yaml
type: NodePort
nodePort: 30080
# Accessible via: <NodeIP>:30080
# Good for local development
```

**Headless** (Database):
```yaml
clusterIP: None
# Direct pod access
# DNS: postgres-0.postgres.dev.svc.cluster.local
```

**LoadBalancer** (Production):
```yaml
type: LoadBalancer
# Cloud provider creates external LB
# Gets external IP
```

### 4. Ingress

**What**: HTTP/HTTPS routing to services

**Why Not Just Services?**
- Single entry point for multiple services
- Path-based routing (`/` vs `/api`)
- SSL/TLS termination
- Name-based virtual hosting

**Our Configuration**:
```yaml
/     → frontend:80  (React SPA)
/api  → backend:8080 (REST API)
```

**Ingress Controller**: nginx-ingress (installed as Minikube addon)

### 5. ConfigMaps

**Purpose**: Non-sensitive configuration

**Usage Patterns**:

**Environment Variables**:
```yaml
env:
- name: DB_HOST
  valueFrom:
    configMapKeyRef:
      name: app-config
      key: DB_HOST
```

**Volume Mount** (for files):
```yaml
volumes:
- name: config
  configMap:
    name: nginx-config
volumeMounts:
- name: config
  mountPath: /etc/nginx/conf.d
```

**Benefits**:
- Decouple config from image
- Change config without rebuilding
- Share config across pods

### 6. Secrets

**Purpose**: Sensitive data (passwords, keys, certificates)

**Encoding**: Base64 (NOT encryption!)

**Best Practices**:
- Never commit secrets to Git
- Use external secret management (Vault, AWS Secrets Manager)
- Rotate secrets regularly
- Limit RBAC access

**In This Project**:
```bash
# Create secret
echo -n 'postgres' | base64  # cG9zdGdyZXM=

# Use in pod
env:
- name: DB_PASSWORD
  valueFrom:
    secretKeyRef:
      name: db-secrets
      key: DB_PASSWORD
```

### 7. Horizontal Pod Autoscaler (HPA)

**How It Works**:

```
1. Metrics Server collects pod metrics
   ↓
2. HPA controller queries metrics every 15s
   ↓
3. Calculate: currentReplicas * (currentMetric / targetMetric)
   ↓
4. If result > currentReplicas: Scale UP
   If result < currentReplicas: Scale DOWN (after stabilization)
```

**Example Calculation**:
```
Current: 3 replicas, 90% CPU
Target: 70% CPU

Desired = 3 * (90 / 70) = 3 * 1.28 = 3.84 ≈ 4 replicas
Action: Scale UP to 4 replicas
```

**Stabilization Windows**:
- **Scale-up**: 30s (react quickly to load)
- **Scale-down**: 5 minutes (avoid flapping)

### 8. NetworkPolicies

**Default Behavior**: Allow all traffic

**With NetworkPolicy**: Deny all, allow specific

**Our Policies**:

**Backend Policy**:
```yaml
Ingress:
  - from: frontend pods
    port: 8080
Egress:
  - to: postgres pods
    port: 5432
  - to: kube-dns
    port: 53
```

**Why DNS Egress?**
- Pods need DNS to resolve service names
- `backend` → `postgres.dev.svc.cluster.local`

**Testing NetworkPolicies**:
```bash
# Should work: frontend → backend
kubectl exec -it frontend-pod -- curl backend:8080/health

# Should fail: frontend → postgres
kubectl exec -it frontend-pod -- curl postgres:5432
```

### 9. PersistentVolumes (PV) & PersistentVolumeClaims (PVC)

**Concept**:
- **PV**: Actual storage (NFS, cloud disk, local)
- **PVC**: Request for storage
- **Binding**: Kubernetes matches PVC to PV

**StatefulSet VolumeClaimTemplate**:
```yaml
volumeClaimTemplates:
- metadata:
    name: postgres-storage
  spec:
    accessModes: ["ReadWriteOnce"]
    resources:
      requests:
        storage: 10Gi
```

**Result**:
- `postgres-0` → `postgres-storage-postgres-0` (10Gi PVC)
- Pod dies → New pod mounts SAME PVC
- Data persists!

### 10. RBAC (Role-Based Access Control)

**Components**:

**ServiceAccount**:
```yaml
kind: ServiceAccount
# Identity for pods
```

**Role**:
```yaml
kind: Role
# Permissions (verbs + resources)
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]
```

**RoleBinding**:
```yaml
kind: RoleBinding
# Binds SA to Role
subjects:
- kind: ServiceAccount
  name: task-manager-sa
roleRef:
  kind: Role
  name: task-manager-role
```

**Namespace vs Cluster**:
- **Role/RoleBinding**: Namespace-scoped
- **ClusterRole/ClusterRoleBinding**: Cluster-wide

## Advanced Kubernetes Features

### 1. Probes

**Liveness Probe**:
- **Question**: Is the container alive?
- **Failure**: Restart container
- **Use Case**: Detect deadlocks

**Readiness Probe**:
- **Question**: Is the container ready to serve traffic?
- **Failure**: Remove from service endpoints
- **Use Case**: Slow startup, temporary unavailability

**Startup Probe** (not used here):
- **Question**: Has the container started?
- **Use Case**: Very slow startup applications

**Probe Types**:
```yaml
# HTTP GET
httpGet:
  path: /health
  port: 8080

# TCP Socket
tcpSocket:
  port: 5432

# Command
exec:
  command: ["pg_isready", "-U", "postgres"]
```

### 2. Resource Requests & Limits

**Requests**: Guaranteed resources
**Limits**: Maximum allowed

```yaml
resources:
  requests:
    cpu: 100m      # 0.1 CPU core
    memory: 128Mi  # 128 MiB
  limits:
    cpu: 500m      # 0.5 CPU core
    memory: 512Mi  # 512 MiB
```

**QoS Classes**:
- **Guaranteed**: requests == limits
- **Burstable**: requests < limits
- **BestEffort**: no requests/limits

**Eviction Priority**: BestEffort → Burstable → Guaranteed

### 3. Affinity & Anti-Affinity

**Pod Anti-Affinity** (in our deployments):
```yaml
podAntiAffinity:
  preferredDuringSchedulingIgnoredDuringExecution:
  - weight: 100
    podAffinityTerm:
      labelSelector:
        matchExpressions:
        - key: app
          operator: In
          values:
          - frontend
      topologyKey: kubernetes.io/hostname
```

**Translation**: Try to schedule frontend pods on different nodes

**Benefits**:
- High availability
- Fault tolerance
- Better resource distribution

### 4. Rolling Updates

**Strategy**:
```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1        # Max 1 extra pod during update
    maxUnavailable: 0  # Always keep all pods available
```

**Update Process**:
```
1. Create 1 new pod (v2)
2. Wait for readiness
3. Terminate 1 old pod (v1)
4. Repeat until all updated
```

**Rollback**:
```bash
kubectl rollout undo deployment/frontend
kubectl rollout history deployment/frontend
kubectl rollout undo deployment/frontend --to-revision=2
```

## Kubernetes Networking

### DNS

**Service DNS**:
```
<service-name>.<namespace>.svc.cluster.local

Examples:
backend.dev.svc.cluster.local
postgres.dev.svc.cluster.local
```

**Pod DNS** (StatefulSet):
```
<pod-name>.<service-name>.<namespace>.svc.cluster.local

Example:
postgres-0.postgres.dev.svc.cluster.local
```

### Service Discovery

**Environment Variables** (automatic):
```bash
BACKEND_SERVICE_HOST=10.96.0.10
BACKEND_SERVICE_PORT=8080
```

**DNS** (preferred):
```python
# In backend pod
db_host = os.getenv('DB_HOST', 'postgres')
# Resolves to: postgres.dev.svc.cluster.local
```

## Troubleshooting Guide

### Pod Not Starting

```bash
# Check pod status
kubectl get pods -n dev

# Describe pod (events at bottom)
kubectl describe pod <pod-name> -n dev

# Check logs
kubectl logs <pod-name> -n dev

# Previous container logs (if crashed)
kubectl logs <pod-name> -n dev --previous
```

**Common Issues**:
- ImagePullBackOff: Wrong image name/tag
- CrashLoopBackOff: Application error
- Pending: Resource constraints

### Service Not Accessible

```bash
# Check service endpoints
kubectl get endpoints backend -n dev

# Test from another pod
kubectl run test --image=busybox -it --rm -- wget -O- backend:8080/health

# Check NetworkPolicies
kubectl get networkpolicies -n dev
```

### HPA Not Scaling

```bash
# Check HPA status
kubectl get hpa -n dev
kubectl describe hpa frontend-hpa -n dev

# Check metrics server
kubectl top pods -n dev
kubectl top nodes

# If metrics unavailable:
kubectl get apiservice v1beta1.metrics.k8s.io -o yaml
```

### Database Connection Issues

```bash
# Check StatefulSet
kubectl get statefulset postgres -n dev

# Check PVC
kubectl get pvc -n dev

# Test database connection
kubectl exec -it postgres-0 -n dev -- psql -U postgres -d taskdb

# Check secrets
kubectl get secret db-secrets -n dev -o yaml
echo "cG9zdGdyZXM=" | base64 -d  # Decode
```

## Best Practices

### 1. Resource Management
✅ Always set requests and limits
✅ Use HPA for auto-scaling
✅ Monitor resource usage

### 2. Security
✅ Use NetworkPolicies
✅ Implement RBAC
✅ Never hardcode secrets
✅ Use non-root containers
✅ Scan images for vulnerabilities

### 3. High Availability
✅ Run multiple replicas
✅ Use anti-affinity rules
✅ Implement health probes
✅ Use PodDisruptionBudgets

### 4. Observability
✅ Centralized logging
✅ Metrics collection
✅ Distributed tracing
✅ Health check endpoints

### 5. CI/CD
✅ Automate deployments
✅ Use GitOps
✅ Implement canary deployments
✅ Automated rollbacks

## Further Learning

**Official Docs**: https://kubernetes.io/docs/
**Interactive Tutorial**: https://kubernetes.io/docs/tutorials/
**CKAD Exam**: Certified Kubernetes Application Developer
**CKA Exam**: Certified Kubernetes Administrator
