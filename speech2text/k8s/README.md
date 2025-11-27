# Kubernetes Deployment Guide

This directory contains Kubernetes manifests for deploying the SMAP Speech-to-Text API with **production-ready chunking support**.

## Prerequisites

- Kubernetes cluster (1.21+)
- `kubectl` configured
- Container registry access
- PersistentVolume provisioner (for model storage)
- Ingress controller (optional, for external access)

---

## Quick Deployment

### 1. Build and Push Docker Image

```bash
# Build image
cd /Users/tantai/Workspaces/smap/smap-ai-internal/speech2text
docker build -t your-registry/smap-stt-api:latest -f cmd/api/Dockerfile .

# Push to registry
docker push your-registry/smap-stt-api:latest
```

### 2. Update Configuration

Edit the following files with your specific values:

**`k8s/secret.yaml`:**
```yaml
# Change these in production
INTERNAL_API_KEY: "your-secure-api-key"
MINIO_ACCESS_KEY: "your-minio-access-key"
MINIO_SECRET_KEY: "your-minio-secret-key"
```

**`k8s/deployment.yaml`:**
```yaml
# Update image URL
image: your-registry/smap-stt-api:latest
```

**`k8s/service.yaml`:**
```yaml
# Update domain (if using Ingress)
host: stt.yourdomain.com
```

### 3. Deploy to Kubernetes

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Create secrets and config
kubectl apply -f k8s/secret.yaml

# Create PVC for model storage
kubectl apply -f k8s/pvc.yaml

# Deploy application
kubectl apply -f k8s/deployment.yaml

# Create service
kubectl apply -f k8s/service.yaml
```

### 4. Verify Deployment

```bash
# Check pods
kubectl get pods -n smap-stt

# Check deployment status
kubectl rollout status deployment/smap-stt-api -n smap-stt

# View logs
kubectl logs -f deployment/smap-stt-api -n smap-stt

# Test health endpoint
kubectl port-forward -n smap-stt deployment/smap-stt-api 8000:8000
curl http://localhost:8000/health
```

---

## Resource Configuration

### Small Model (Default)

Optimized for **development** and **fast transcription**:

```yaml
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
    ephemeral-storage: "2Gi"
  limits:
    memory: "2Gi"
    cpu: "4000m"
    ephemeral-storage: "5Gi"
```

**Specifications:**
- **Memory:** 500MB base + 500MB buffer = 1GB request
- **CPU:** 4 cores limit for optimal Whisper threading
- **Storage:** 5GB for chunking temp files (long audio)

### Medium Model

For **production** with **higher accuracy**:

1. Update `k8s/secret.yaml`:
```yaml
WHISPER_MODEL_SIZE: "medium"
```

2. Update resource limits in `k8s/deployment.yaml`:
```yaml
resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
    ephemeral-storage: "3Gi"
  limits:
    memory: "4Gi"
    cpu: "4000m"
    ephemeral-storage: "10Gi"
```

3. Update PVC size in `k8s/pvc.yaml`:
```yaml
resources:
  requests:
    storage: 3Gi
```

---

## Chunking Configuration

**Production-ready chunking** is enabled by default for long audio files:

```yaml
# In k8s/secret.yaml ConfigMap
WHISPER_CHUNK_ENABLED: "true"
WHISPER_CHUNK_DURATION: "30"  # seconds
WHISPER_CHUNK_OVERLAP: "1"    # seconds
TRANSCRIBE_TIMEOUT_SECONDS: "90"
WHISPER_N_THREADS: "0"  # Auto-detect (recommended)
```

### Chunking Benefits

✅ **No Timeouts:** Handles audio up to 30+ minutes  
✅ **Flat Memory:** ~500MB regardless of audio length  
✅ **High Performance:** 4-5x faster than realtime  
✅ **Quality Maintained:** 98% confidence across all tests

### Test Results

| Audio Duration | Processing Time | Status |
|----------------|-----------------|--------|
| 3 minutes      | 75s             | ✅ PASS |
| 9 minutes      | 109s            | ✅ PASS |
| 13 minutes     | 171s            | ✅ PASS |
| 18 minutes     | 270s            | ✅ PASS |

See `CHUNKING_TEST_REPORT.md` for full test results.

---

## Scaling

### Manual Scaling

```bash
# Scale to 5 replicas
kubectl scale deployment/smap-stt-api -n smap-stt --replicas=5
```

### Auto-Scaling (HPA)

The deployment includes an optional HPA configuration:

```yaml
# In k8s/deployment.yaml
minReplicas: 2
maxReplicas: 10
metrics:
- cpu: 70%
- memory: 80%
```

Enable HPA:
```bash
kubectl apply -f k8s/deployment.yaml
kubectl get hpa -n smap-stt
```

---

## Security

### Secrets Management

**DO NOT** commit sensitive credentials to git. Use one of these approaches:

#### Option 1: Sealed Secrets
```bash
# Install Sealed Secrets
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.18.0/controller.yaml

# Seal your secret
kubeseal --format=yaml < k8s/secret.yaml > k8s/sealed-secret.yaml
```

#### Option 2: External Secrets Operator
```bash
# Use AWS Secrets Manager, HashiCorp Vault, etc.
kubectl apply -f https://raw.githubusercontent.com/external-secrets/external-secrets/main/deploy/crds/bundle.yaml
```

#### Option 3: Manual Creation
```bash
# Create secret manually (not in git)
kubectl create secret generic smap-stt-secrets \
  --from-literal=INTERNAL_API_KEY="your-secure-key" \
  --from-literal=MINIO_ACCESS_KEY="your-minio-key" \
  --from-literal=MINIO_SECRET_KEY="your-minio-secret" \
  -n smap-stt
```

---

## Monitoring

### Health Checks

```bash
# Check pod health
kubectl get pods -n smap-stt

# Describe pod for events
kubectl describe pod <pod-name> -n smap-stt

# View logs
kubectl logs -f <pod-name> -n smap-stt
```

### Resource Usage

```bash
# Check resource consumption
kubectl top pods -n smap-stt

# Check node allocation
kubectl top nodes
```

### Prometheus Metrics (Optional)

The deployment is annotated for Prometheus scraping:

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8000"
  prometheus.io/path: "/metrics"
```

---

## Troubleshooting

### Pod Not Starting

```bash
# Check events
kubectl describe pod <pod-name> -n smap-stt

# Check logs
kubectl logs <pod-name> -n smap-stt

# Common issues:
# - Image pull errors: Check registry access
# - OOMKilled: Increase memory limits
# - CrashLoopBackOff: Check application logs
```

### Model Loading Issues

```bash
# Check PVC status
kubectl get pvc -n smap-stt

# Check PV binding
kubectl get pv

# Exec into pod
kubectl exec -it <pod-name> -n smap-stt -- /bin/bash
ls -la /app/whisper_small_xeon/
```

### High Memory Usage

```bash
# Check current usage
kubectl top pods -n smap-stt

# If consistently high:
# 1. Verify chunking is enabled (WHISPER_CHUNK_ENABLED=true)
# 2. Check for memory leaks in logs
# 3. Consider increasing memory limits
```

### Slow Transcription

```bash
# Check CPU allocation
kubectl top pods -n smap-stt

# Verify threading configuration
kubectl exec -it <pod-name> -n smap-stt -- env | grep WHISPER_N_THREADS

# Should be "0" for auto-detect or "8" for manual
```

---

## Maintenance

### Rolling Update

```bash
# Update image
kubectl set image deployment/smap-stt-api \
  smap-stt-api=your-registry/smap-stt-api:v2 \
  -n smap-stt

# Watch rollout
kubectl rollout status deployment/smap-stt-api -n smap-stt

# Rollback if needed
kubectl rollout undo deployment/smap-stt-api -n smap-stt
```

### Backup

```bash
# Backup all manifests
kubectl get all -n smap-stt -o yaml > backup-$(date +%Y%m%d).yaml
```

### Cleanup

```bash
# Delete all resources
kubectl delete namespace smap-stt

# Or delete individually
kubectl delete -f k8s/
```

---

## Production Checklist

Before deploying to production:

- [ ] Update `INTERNAL_API_KEY` in secrets
- [ ] Update `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY`
- [ ] Set `DEBUG: "false"` in ConfigMap
- [ ] Set `ENVIRONMENT: "production"` in ConfigMap
- [ ] Configure Ingress with TLS/SSL
- [ ] Set up monitoring and alerting
- [ ] Configure resource limits based on load testing
- [ ] Enable HPA if needed
- [ ] Set up log aggregation (ELK, Loki, etc.)
- [ ] Configure backup strategy for PVCs
- [ ] Test rolling updates
- [ ] Document runbooks for common issues

---

## Support

For issues or questions:
- Check logs: `kubectl logs -f deployment/smap-stt-api -n smap-stt`
- Review test report: `CHUNKING_TEST_REPORT.md`
- Contact: nguyentantai.dev@gmail.com

