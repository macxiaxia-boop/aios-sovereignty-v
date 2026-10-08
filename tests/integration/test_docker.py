"""test_docker.py - E006."""
import yaml
from pathlib import Path


def test_dockerfile_exists():
    p = Path(r"D:\AIOS\kernel\Dockerfile")
    assert p.exists()


def test_dockerfile_uses_python311():
    p = Path(r"D:\AIOS\kernel\Dockerfile")
    content = p.read_text()
    assert "python:3.11" in content


def test_compose_valid():
    p = Path(r"D:\AIOS\kernel\docker-compose.yml")
    content = p.read_text()
    parsed = yaml.safe_load(content)
    assert "services" in parsed
    assert "kernel" in parsed["services"]
    assert "postgres" in parsed["services"]


def test_airgap_internal_network():
    p = Path(r"D:\AIOS\kernel\docker-compose.yml")
    content = p.read_text()
    parsed = yaml.safe_load(content)
    airgap_net = parsed["networks"]["airgap"]
    assert airgap_net.get("internal") is True


def test_no_external_apis():
    p = Path(r"D:\AIOS\kernel\docker-compose.yml")
    content = p.read_text()
    # No internet-gated services like image pull from public registry
    assert "openai.com" not in content.lower()
    assert "anthropic.com" not in content.lower()
