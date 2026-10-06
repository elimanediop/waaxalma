# Waaxalma Metrics Observability

**Version:** 1.0.3  
**Status:** Production-ready  
**Stack:** Prometheus + Grafana

## Overview

Waaxalma provides built-in metrics observability for the HTTP API,
AI providers, voice processing pipeline, realtime sessions, token usage,
and estimated provider costs.

Prometheus collects metrics exposed by the Waaxalma backend, while
Grafana provides a pre-provisioned dashboard for visualization and
operational monitoring.

The observability stack is integrated into Docker Compose and requires
no manual Prometheus or Grafana configuration.

## Architecture

```text
┌─────────────┐
│  Streamlit  │
│    :8501    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   FastAPI   │
│    :8000    │
└──────┬──────┘
       │
       │ /metrics
       ▼
┌─────────────┐
│ Prometheus  │
│    :9090    │
└──────┬──────┘
       │
       │ PromQL
       ▼
┌─────────────┐
│   Grafana   │
│    :3000    │
└─────────────┘