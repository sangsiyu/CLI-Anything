import json
import click
from typing import Optional
from .utils.jenkins_backend import (
    resolve_server,
    load_config,
    save_config,
    server_info,
    job_list,
    job_info,
    job_build,
    build_status,
    build_poll,
    artifact_list,
)

_json_output = False
_repl_mode = False

def _out(data, message: str = ""):
    if _json_output:
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        if message:
            click.echo(message)
        if isinstance(data, dict):
            for k, v in data.items():
                click.echo(f"{k}: {v}" if not isinstance(v, (list, dict)) else f"{k}:")
                if isinstance(v, list):
                    for i, it in enumerate(v):
                        click.echo(f"  [{i}] {it}")
                if isinstance(v, dict):
                    for kk, vv in v.items():
                        click.echo(f"  {kk}: {vv}")
        else:
            click.echo(str(data))

def _wrap(func):
    def w(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if _json_output:
                click.echo(json.dumps({"error": str(e)}))
            else:
                click.echo(f"Error: {e}", err=True)
            if not _repl_mode:
                raise SystemExit(1)
    w.__name__ = func.__name__
    return w

@click.group(invoke_without_command=True)
@click.option("--json", "use_json", is_flag=True, help="Output as JSON")
@click.pass_context
def cli(ctx, use_json):
    global _json_output
    _json_output = use_json
    ctx.ensure_object(dict)
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)

@cli.command()
@click.option("--url", type=str, default=None)
@click.option("--user", type=str, default=None)
@click.option("--token", type=str, default=None)
@click.option("--verify/--no-verify", default=None)
@_wrap
def server_config(url, user, token, verify):
    cfg = load_config()
    if url is not None:
        cfg["url"] = url
    if user is not None:
        cfg["user"] = user
    if token is not None:
        cfg["token"] = token
    if verify is not None:
        cfg["verify"] = bool(verify)
    save_config(cfg)
    _out({"config": cfg}, "✓ Saved Jenkins config")

@cli.command()
@click.option("--url", type=str, default=None)
@click.option("--user", type=str, default=None)
@click.option("--token", type=str, default=None)
@click.option("--verify/--no-verify", default=None)
@_wrap
def server_info_cmd(url, user, token, verify):
    s = resolve_server(url, user, token, verify)
    info = server_info(s["url"], s["user"], s["token"], s["verify"])
    _out(info, "✓ Server info")

@cli.group()
def job():
    pass

@job.command("list")
@click.option("--url", type=str, default=None)
@click.option("--user", type=str, default=None)
@click.option("--token", type=str, default=None)
@click.option("--verify/--no-verify", default=None)
@_wrap
def job_list_cmd(url, user, token, verify):
    s = resolve_server(url, user, token, verify)
    result = job_list(s["url"], s["user"], s["token"], s["verify"])
    _out(result, f"✓ Jobs: {result['count']}")

@job.command("info")
@click.argument("name")
@click.option("--url", type=str, default=None)
@click.option("--user", type=str, default=None)
@click.option("--token", type=str, default=None)
@click.option("--verify/--no-verify", default=None)
@_wrap
def job_info_cmd(name, url, user, token, verify):
    s = resolve_server(url, user, token, verify)
    result = job_info(s["url"], s["user"], s["token"], s["verify"], name)
    _out(result, f"✓ Job: {name}")

@job.command("build")
@click.argument("name")
@click.option("--param", "param", multiple=True)
@click.option("--url", type=str, default=None)
@click.option("--user", type=str, default=None)
@click.option("--token", type=str, default=None)
@click.option("--verify/--no-verify", default=None)
@_wrap
def job_build_cmd(name, param, url, user, token, verify):
    s = resolve_server(url, user, token, verify)
    p = {}
    for kv in param:
        if "=" in kv:
            k, v = kv.split("=", 1)
            p[k] = v
    result = job_build(s["url"], s["user"], s["token"], s["verify"], name, p if p else None)
    _out(result, f"✓ Triggered: {name}")

@cli.group()
def build():
    pass

@build.command("status")
@click.argument("name")
@click.argument("number")
@click.option("--url", type=str, default=None)
@click.option("--user", type=str, default=None)
@click.option("--token", type=str, default=None)
@click.option("--verify/--no-verify", default=None)
@_wrap
def build_status_cmd(name, number, url, user, token, verify):
    s = resolve_server(url, user, token, verify)
    result = build_status(s["url"], s["user"], s["token"], s["verify"], name, number)
    _out(result, f"✓ Build {name} #{number}")

@build.command("poll")
@click.argument("name")
@click.argument("number")
@click.option("--interval", type=int, default=3)
@click.option("--timeout", type=int, default=1200)
@click.option("--url", type=str, default=None)
@click.option("--user", type=str, default=None)
@click.option("--token", type=str, default=None)
@click.option("--verify/--no-verify", default=None)
@_wrap
def build_poll_cmd(name, number, interval, timeout, url, user, token, verify):
    s = resolve_server(url, user, token, verify)
    def onp(status, pct):
        if not _json_output:
            click.echo(f"  ● {status}: {pct}s")
    result = build_poll(s["url"], s["user"], s["token"], s["verify"], name, number, interval, timeout, on_progress=onp)
    _out(result, f"✓ Completed {name} #{number}: {result.get('result')}")

@cli.group()
def artifact():
    pass

@artifact.command("list")
@click.argument("name")
@click.argument("number")
@click.option("--url", type=str, default=None)
@click.option("--user", type=str, default=None)
@click.option("--token", type=str, default=None)
@click.option("--verify/--no-verify", default=None)
@_wrap
def artifact_list_cmd(name, number, url, user, token, verify):
    s = resolve_server(url, user, token, verify)
    result = artifact_list(s["url"], s["user"], s["token"], s["verify"], name, number)
    _out(result, f"✓ Artifacts: {result['count']}")

@cli.command()
def repl():
    global _repl_mode
    _repl_mode = True
    click.echo("CLI-Anything Jenkins REPL")
    click.echo("Type commands like: job list | job build <name> --param KEY=VAL | build status <name> <number>")
    click.echo("Use --json on any command for machine-readable output")

def main():
    cli()
