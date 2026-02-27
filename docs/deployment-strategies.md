# Deployment Strategies

## Overview

This document explains the different deployment strategies implemented in this Kubernetes project and when to use each one.

## 1. Rolling Update (Default)

### Description
Gradually replace old pods with new ones, ensuring zero downtime.

### Configuration
```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1        # Max 1 extra pod during update
    maxUnavailable: 0  # Never go below desired count
```

### How It Works
```
Initial State: [v1] [v1] [v1]
Step 1:        [v1] [v1] [v1] [v2]  ← Create new pod
Step 2:        [v1] [v1] [v2]       ← Terminate old pod
Step 3:        [v1] [v1] [v2] [v2]  ← Create new pod
Step 4:        [v1] [v2] [v2]       ← Terminate old pod
Step 5:        [v1] [v2] [v2] [v2]  ← Create new pod
Final:         [v2] [v2] [v2]       ← Terminate old pod
```

### Pros
✅ Zero downtime  
✅ Automatic rollback on failure  
✅ Resource efficient  
✅ Simple to implement  

### Cons
❌ Both versions running simultaneously  
❌ Gradual rollout (not instant)  
❌ Potential for version compatibility issues  

### Use Cases
- **Development**: Quick iterations
- **Staging**: Testing new versions
- **Production**: Standard deployments

### Commands
```bash
# Deploy new version
kubectl set image deployment/frontend frontend=frontend:v2

# Monitor rollout
kubectl rollout status deployment/frontend

# Pause rollout
kubectl rollout pause deployment/frontend

# Resume rollout
kubectl rollout resume deployment/frontend

# Rollback
kubectl rollout undo deployment/frontend
```

---

## 2. Blue-Green Deployment

### Description
Run two identical environments (blue and green). Switch traffic from one to the other.

### How It Works
```
Blue (v1):  [v1] [v1] [v1]  ← 100% traffic
Green (v2): [v2] [v2] [v2]  ← 0% traffic (ready)
            ↓
Switch traffic
            ↓
Blue (v1):  [v1] [v1] [v1]  ← 0% traffic (standby)
Green (v2): [v2] [v2] [v2]  ← 100% traffic
```

### Implementation
```yaml
# Blue deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend-blue
spec:
  replicas: 3
  selector:
    matchLabels:
      app: frontend
      version: blue
  template:
    metadata:
      labels:
        app: frontend
        version: blue
    spec:
      containers:
      - name: frontend
        image: frontend:v1

---
# Green deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend-green
spec:
  replicas: 3
  selector:
    matchLabels:
      app: frontend
      version: green
  template:
    metadata:
      labels:
        app: frontend
        version: green
    spec:
      containers:
      - name: frontend
        image: frontend:v2

---
# Service (switch by changing selector)
apiVersion: v1
kind: Service
metadata:
  name: frontend
spec:
  selector:
    app: frontend
    version: blue  # Change to 'green' to switch
  ports:
  - port: 80
```

### Switching Traffic
```bash
# Switch to green
kubectl patch service frontend -p '{"spec":{"selector":{"version":"green"}}}'

# Rollback to blue
kubectl patch service frontend -p '{"spec":{"selector":{"version":"blue"}}}'
```

### Pros
✅ Instant rollback  
✅ Full testing before switch  
✅ Zero downtime  
✅ Clean separation of versions  

### Cons
❌ Double resources required  
❌ Database migrations challenging  
❌ More complex setup  

### Use Cases
- **Production**: Critical deployments
- **Major releases**: Significant changes
- **Compliance**: Audit requirements

---

## 3. Canary Deployment

### Description
Gradually shift traffic from old version to new version, starting with a small percentage.

### How It Works
```
Step 1: v1 [90%] v2 [10%]  ← Test with 10% traffic
        ↓
Step 2: v1 [70%] v2 [30%]  ← Increase if metrics good
        ↓
Step 3: v1 [50%] v2 [50%]  ← Continue increasing
        ↓
Step 4: v1 [0%]  v2 [100%] ← Full rollout
```

### Implementation (Using Replica Count)
```yaml
# Old version (9 replicas = 90%)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend-stable
spec:
  replicas: 9
  selector:
    matchLabels:
      app: frontend
      track: stable
  template:
    metadata:
      labels:
        app: frontend
        track: stable
    spec:
      containers:
      - name: frontend
        image: frontend:v1

---
# New version (1 replica = 10%)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend-canary
spec:
  replicas: 1
  selector:
    matchLabels:
      app: frontend
      track: canary
  template:
    metadata:
      labels:
        app: frontend
        track: canary
    spec:
      containers:
      - name: frontend
        image: frontend:v2

---
# Service (selects both)
apiVersion: v1
kind: Service
metadata:
  name: frontend
spec:
  selector:
    app: frontend  # Matches both stable and canary
  ports:
  - port: 80
```

### Gradual Rollout
```bash
# 10% canary
kubectl scale deployment frontend-stable --replicas=9
kubectl scale deployment frontend-canary --replicas=1

# 30% canary
kubectl scale deployment frontend-stable --replicas=7
kubectl scale deployment frontend-canary --replicas=3

# 50% canary
kubectl scale deployment frontend-stable --replicas=5
kubectl scale deployment frontend-canary --replicas=5

# 100% canary (complete)
kubectl scale deployment frontend-stable --replicas=0
kubectl scale deployment frontend-canary --replicas=10
```

### Pros
✅ Gradual risk mitigation  
✅ Real user testing  
✅ Easy rollback  
✅ Metrics-driven decisions  

### Cons
❌ Complex traffic management  
❌ Requires monitoring  
❌ Both versions running  

### Use Cases
- **Production**: Risk-averse deployments
- **A/B Testing**: Feature validation
- **Performance Testing**: Load validation

---

## 4. Recreate Strategy

### Description
Terminate all old pods before creating new ones.

### Configuration
```yaml
strategy:
  type: Recreate
```

### How It Works
```
Initial: [v1] [v1] [v1]
         ↓
Terminate all
         ↓
Downtime: [ ] [ ] [ ]
         ↓
Create new
         ↓
Final:   [v2] [v2] [v2]
```

### Pros
✅ Simple  
✅ No version conflicts  
✅ Resource efficient  

### Cons
❌ Downtime  
❌ Not production-ready  

### Use Cases
- **Development**: Local testing
- **Maintenance windows**: Scheduled downtime
- **Incompatible versions**: Breaking changes

---

## Comparison Matrix

| Strategy | Downtime | Resources | Complexity | Rollback Speed | Use Case |
|----------|----------|-----------|------------|----------------|----------|
| **Rolling Update** | None | 1x + surge | Low | Medium | Standard deployments |
| **Blue-Green** | None | 2x | Medium | Instant | Critical deployments |
| **Canary** | None | 1x + canary | High | Fast | Risk mitigation |
| **Recreate** | Yes | 1x | Very Low | Slow | Development only |

---

## Choosing a Strategy

### Use Rolling Update When:
- Standard application updates
- Resource constraints
- Simple rollback acceptable

### Use Blue-Green When:
- Zero-downtime critical
- Instant rollback required
- Resources available

### Use Canary When:
- High-risk changes
- Gradual validation needed
- Metrics-driven decisions

### Use Recreate When:
- Development environment
- Scheduled maintenance
- Breaking changes

---

## Monitoring Deployments

### Key Metrics
```bash
# Pod status
kubectl get pods -n dev -w

# Deployment status
kubectl rollout status deployment/frontend

# Events
kubectl get events -n dev --sort-by='.lastTimestamp'

# Logs
kubectl logs -f deployment/frontend
```

### Health Checks
- **Liveness**: Is the pod alive?
- **Readiness**: Can it serve traffic?
- **Startup**: Has it started?

### Rollback Triggers
- ❌ Increased error rate
- ❌ Failed health checks
- ❌ Performance degradation
- ❌ User complaints

---

## Best Practices

### 1. Always Use Health Probes
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
readinessProbe:
  httpGet:
    path: /ready
    port: 8080
```

### 2. Set Resource Limits
```yaml
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

### 3. Use PodDisruptionBudgets
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: frontend-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: frontend
```

### 4. Monitor Everything
- Application metrics
- Infrastructure metrics
- Business metrics
- User experience

### 5. Automate Rollbacks
```bash
# In CI/CD pipeline
if [ $ERROR_RATE -gt 5 ]; then
  kubectl rollout undo deployment/frontend
fi
```

---

## Advanced: GitOps with ArgoCD

### Declarative Deployments
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: task-manager
spec:
  source:
    repoURL: https://github.com/user/repo
    targetRevision: HEAD
    path: k8s/base
  destination:
    server: https://kubernetes.default.svc
    namespace: dev
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### Benefits
- Git as single source of truth
- Automatic synchronization
- Audit trail
- Easy rollback (git revert)

---

## Conclusion

Choose your deployment strategy based on:
- **Risk tolerance**
- **Resource availability**
- **Rollback requirements**
- **Complexity tolerance**

For most production workloads, **Rolling Update** with proper health checks is sufficient. Use **Blue-Green** for critical deployments and **Canary** for high-risk changes.
