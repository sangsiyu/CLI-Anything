from __future__ import annotations
import os
import json
import time
from pathlib import Path
from typing import Callable, Dict, Any
import requests

CONFIG_DIR = Path.home() / ".cli-anything-jenkins"
CONFIG_FILE = CONFIG_DIR / "config.json"
ENV_URL = "JENKINS_URL"
ENV_USER = "JENKINS_USER"
ENV_TOKEN = "JENKINS_API_TOKEN"
ENV_VERIFY = "JENKINS_VERIFY_TLS"

def load_config() -> Dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_config(cfg: Dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    try:
        CONFIG_FILE.chmod(0o600)
    except Exception:
        pass

def resolve_server(url_opt: str | None, user_opt: str | None, token_opt: str | None, verify_opt: bool | None) -> Dict[str, Any]:
    cfg = load_config()
    url = url_opt or os.environ.get(ENV_URL) or cfg.get("url")
    user = user_opt or os.environ.get(ENV_USER) or cfg.get("user")
    token = token_opt or os.environ.get(ENV_TOKEN) or cfg.get("token")
    v = os.environ.get(ENV_VERIFY)
    verify_env = None if v is None else (v.strip() not in ("0", "false", "False"))
    verify = verify_opt if verify_opt is not None else (verify_env if verify_env is not None else cfg.get("verify", True))
    if not url or not user or not token:
        raise RuntimeError("Missing Jenkins connection. Provide --url --user --token or set environment variables.")
    return {"url": url.rstrip("/"), "user": user, "token": token, "verify": verify}

def _req(method: str, base: str, path: str, auth: tuple[str,str], verify: bool, params: Dict[str, Any] | None = None, data: Dict[str, Any] | None = None) -> requests.Response:
    u = f"{base}{path}"
    r = requests.request(method, u, params=params, data=data, auth=auth, verify=verify, timeout=60)
    if r.status_code >= 400:
        msg = r.text[:400]
        raise RuntimeError(f"HTTP {r.status_code}: {msg}")
    return r

def server_info(url: str, user: str, token: str, verify: bool) -> Dict[str, Any]:
    r = _req("GET", url, "/api/json", (user, token), verify)
    return r.json()

def job_list(url: str, user: str, token: str, verify: bool) -> Dict[str, Any]:
    r = _req("GET", url, "/api/json", (user, token), verify)
    j = r.json()
    jobs = j.get("jobs", [])
    return {"count": len(jobs), "jobs": [{"name": i.get("name"), "url": i.get("url"), "color": i.get("color")} for i in jobs]}

def job_info(url: str, user: str, token: str, verify: bool, name: str) -> Dict[str, Any]:
    r = _req("GET", url, f"/job/{name}/api/json", (user, token), verify)
    return r.json()

def job_build(url: str, user: str, token: str, verify: bool, name: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    path = f"/job/{name}/buildWithParameters" if params else f"/job/{name}/build"
    r = _req("POST", url, path, (user, token), verify, params=params or None)
    loc = r.headers.get("Location")
    return {"queued": True, "queue_url": loc}

def build_status(url: str, user: str, token: str, verify: bool, name: str, build_number: str) -> Dict[str, Any]:
    r = _req("GET", url, f"/job/{name}/{build_number}/api/json", (user, token), verify)
    j = r.json()
    return {
        "building": j.get("building"),
        "result": j.get("result"),
        "duration": j.get("duration"),
        "timestamp": j.get("timestamp"),
        "url": j.get("url"),
        "artifacts": j.get("artifacts", []),
        "number": j.get("number"),
    }

def build_poll(url: str, user: str, token: str, verify: bool, name: str, build_number: str, interval: int, timeout: int, on_progress: Callable[[str,int], None] | None = None) -> Dict[str, Any]:
    start = time.time()
    last = None
    while True:
        s = build_status(url, user, token, verify, name, build_number)
        if s.get("building") is False and s.get("result") is not None:
            return s
        if on_progress:
            now = int(time.time() - start)
            on_progress("building", now)
        time.sleep(max(1, interval))
        last = s
        if timeout and time.time() - start > timeout:
            raise TimeoutError("Polling timeout")

def artifact_list(url: str, user: str, token: str, verify: bool, name: str, build_number: str) -> Dict[str, Any]:
    s = build_status(url, user, token, verify, name, build_number)
    arts = s.get("artifacts", [])
    base = s.get("url", "").rstrip("/")
    items = []
    for a in arts:
        items.append({"fileName": a.get("fileName"), "relativePath": a.get("relativePath"), "url": f"{base}/artifact/{a.get('relativePath')}"})
    return {"count": len(items), "artifacts": items}
