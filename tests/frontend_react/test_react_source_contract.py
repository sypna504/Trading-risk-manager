from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "app/frontend"

def read(path: str) -> str:
    return (FRONTEND / path).read_text(encoding="utf-8")

def test_react_typescript_vite_stack():
    package = json.loads(read("package.json"))
    for dep in ("react", "react-dom", "react-router-dom", "@tanstack/react-query", "recharts"):
        assert dep in package["dependencies"]
    for dep in ("vite", "typescript", "vitest", "@testing-library/react"):
        assert dep in package["devDependencies"]

def test_all_required_routes_exist():
    app = read("src/App.tsx")
    for route in ("/dashboard","/decision","/news","/events","/research","/backtest","/models","/monitoring","/agent","/paper","/system"):
        assert f'path="{route}"' in app

def test_single_typed_api_layer():
    client = read("src/api/client.ts")
    assert "const json = async <T>" in client
    assert "export const api" in client
    for path in FRONTEND.glob("src/pages/*.tsx"):
        text = path.read_text(encoding="utf-8")
        assert "fetch(" not in text

def test_no_unsafe_external_rendering():
    source = "\n".join(path.read_text(encoding="utf-8") for path in FRONTEND.rglob("*.tsx"))
    assert "innerHTML" not in source
    assert "dangerouslySetInnerHTML" not in source
    assert "outerHTML" not in source

def test_error_loading_and_empty_components_exist():
    state = read("src/components/State.tsx")
    assert "Loading" in state and "ErrorState" in state and "Empty" in state

def test_pages_cover_required_degraded_surfaces():
    assert "News context недоступен" in read("src/components/NewsContext.tsx")
    assert "optional unavailable" in read("src/pages/System.tsx")
    assert "paper trading" in read("src/pages/Paper.tsx").lower()
    assert "degraded" in read("src/pages/Agent.tsx") or "degraded" in read("src/models/api.ts")

def test_vitest_rtl_tests_exist():
    routes = read("src/__tests__/routes.test.tsx")
    api = read("src/__tests__/api.test.ts")
    assert "@testing-library/react" in routes
    assert "vitest" in routes and "vitest" in api

def test_frontend_dockerfile_builds_vite_bundle():
    docker = read("Dockerfile")
    assert "npm run build" in docker
    assert "nginx" in docker
