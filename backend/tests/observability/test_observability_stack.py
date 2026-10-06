import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def read(path: Path) -> str:
    assert path.exists(), f"Required observability file is missing: {path}"
    return path.read_text(encoding="utf-8")


def test_compose_declares_prometheus_and_grafana():
    compose = read(ROOT / "compose.yaml")

    assert "prometheus:" in compose
    assert "grafana:" in compose


def test_prometheus_scrapes_waaxalma_backend():
    config = read(
        ROOT
        / "observability"
        / "prometheus"
        / "prometheus.yml"
    )

    assert "job_name: waaxalma-backend" in config
    assert "metrics_path: /metrics" in config
    assert "backend:8000" in config


def test_grafana_prometheus_datasource():
    config = read(
        ROOT
        / "observability"
        / "grafana"
        / "provisioning"
        / "datasources"
        / "prometheus.yml"
    )

    assert "type: prometheus" in config
    assert "uid: waaxalma-prometheus" in config
    assert "url: http://prometheus:9090" in config


def test_grafana_dashboard_provisioning():
    config = read(
        ROOT
        / "observability"
        / "grafana"
        / "provisioning"
        / "dashboards"
        / "dashboards.yml"
    )

    assert "type: file" in config
    assert "path: /var/lib/grafana/dashboards" in config


def test_waaxalma_dashboard_is_valid():
    path = (
        ROOT
        / "observability"
        / "grafana"
        / "dashboards"
        / "waaxalma-overview.json"
    )

    dashboard = json.loads(read(path))

    assert dashboard["uid"] == "waaxalma-overview"
    assert dashboard["title"] == "Waaxalma — Overview"
    assert dashboard["panels"]


def test_dashboard_uses_prometheus_datasource():
    path = (
        ROOT
        / "observability"
        / "grafana"
        / "dashboards"
        / "waaxalma-overview.json"
    )

    dashboard = json.loads(read(path))

    panels = [
        panel
        for panel in dashboard["panels"]
        if panel.get("type") != "row"
    ]

    assert panels

    for panel in panels:
        datasource = panel.get("datasource")

        assert datasource is not None
        assert datasource["type"] == "prometheus"
        assert datasource["uid"] == "waaxalma-prometheus"