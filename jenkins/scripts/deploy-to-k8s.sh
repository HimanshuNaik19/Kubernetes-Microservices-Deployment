#!/bin/bash
set -e

NAMESPACE=${1:-dev}

echo "Deploying to Kubernetes namespace: $NAMESPACE"

# Create namespace
echo "Creating namespace..."
kubectl apply -f k8s/base/namespaces/${NAMESPACE}.yaml

# Apply configurations
echo "Applying ConfigMaps and Secrets..."
kubectl apply -f k8s/base/configmaps/ -n $NAMESPACE
kubectl apply -f k8s/base/secrets/ -n $NAMESPACE

# Apply RBAC
echo "Applying RBAC..."
kubectl apply -f k8s/base/rbac/ -n $NAMESPACE

# Deploy database
echo "Deploying database..."
kubectl apply -f k8s/base/statefulsets/ -n $NAMESPACE
kubectl apply -f k8s/base/services/postgres-service.yaml -n $NAMESPACE

# Wait for database
echo "Waiting for database to be ready..."
kubectl wait --for=condition=ready --timeout=300s pod -l app=postgres -n $NAMESPACE

# Deploy applications
echo "Deploying applications..."
kubectl apply -f k8s/base/deployments/ -n $NAMESPACE
kubectl apply -f k8s/base/services/backend-service.yaml -n $NAMESPACE
kubectl apply -f k8s/base/services/frontend-service.yaml -n $NAMESPACE

# Deploy ingress
echo "Deploying ingress..."
kubectl apply -f k8s/base/ingress/ -n $NAMESPACE

# Deploy autoscaling
echo "Deploying HPA..."
kubectl apply -f k8s/base/autoscaling/ -n $NAMESPACE

# Deploy network policies
echo "Deploying network policies..."
kubectl apply -f k8s/base/network/ -n $NAMESPACE

# Wait for deployments
echo "Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment --all -n $NAMESPACE

echo "Deployment completed successfully!"
echo ""
echo "Resources in namespace $NAMESPACE:"
kubectl get all -n $NAMESPACE
