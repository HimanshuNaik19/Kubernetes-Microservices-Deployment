.PHONY: help start stop deploy-dev deploy-staging deploy-prod clean test

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

start: ## Start local Kubernetes cluster (Minikube)
	minikube start --cpus=4 --memory=8192
	minikube addons enable ingress
	minikube addons enable metrics-server

stop: ## Stop local Kubernetes cluster
	minikube stop

build: ## Build Docker images locally
	cd app && docker-compose build

deploy-dev: ## Deploy to dev namespace
	kubectl apply -f k8s/base/namespaces/dev.yaml
	kubectl apply -f k8s/base/configmaps/ -n dev
	kubectl apply -f k8s/base/secrets/ -n dev
	kubectl apply -f k8s/base/storage/ -n dev
	kubectl apply -f k8s/base/rbac/ -n dev
	kubectl apply -f k8s/base/statefulsets/ -n dev
	kubectl apply -f k8s/base/deployments/ -n dev
	kubectl apply -f k8s/base/services/ -n dev
	kubectl apply -f k8s/base/ingress/ -n dev
	kubectl apply -f k8s/base/autoscaling/ -n dev
	kubectl apply -f k8s/base/network/ -n dev
	@echo "Waiting for deployments to be ready..."
	kubectl wait --for=condition=available --timeout=300s deployment --all -n dev

deploy-staging: ## Deploy to staging namespace
	kubectl apply -f k8s/base/namespaces/staging.yaml
	kubectl apply -f k8s/base/ -n staging

deploy-prod: ## Deploy to prod namespace
	kubectl apply -f k8s/base/namespaces/prod.yaml
	kubectl apply -f k8s/base/ -n prod

status: ## Check deployment status
	@echo "=== Namespaces ==="
	kubectl get namespaces
	@echo "\n=== Pods (dev) ==="
	kubectl get pods -n dev
	@echo "\n=== Services (dev) ==="
	kubectl get svc -n dev
	@echo "\n=== Ingress (dev) ==="
	kubectl get ingress -n dev
	@echo "\n=== HPA (dev) ==="
	kubectl get hpa -n dev

logs-frontend: ## View frontend logs
	kubectl logs -f -l app=frontend -n dev

logs-backend: ## View backend logs
	kubectl logs -f -l app=backend -n dev

logs-db: ## View database logs
	kubectl logs -f -l app=postgres -n dev

test: ## Run tests
	cd app && docker-compose up -d
	@echo "Running tests..."
	# Add test commands here
	cd app && docker-compose down

clean: ## Clean up all resources
	kubectl delete namespace dev --ignore-not-found=true
	kubectl delete namespace staging --ignore-not-found=true
	kubectl delete namespace prod --ignore-not-found=true

validate: ## Validate Kubernetes manifests
	kubectl apply --dry-run=client -f k8s/base/

port-forward: ## Port forward to frontend service
	kubectl port-forward svc/frontend 8080:80 -n dev
