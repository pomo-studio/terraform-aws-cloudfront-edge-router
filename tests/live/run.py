#!/usr/bin/env python3
"""Deploy, exercise, and destroy the private-origin fixture. AWS charges apply."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.cookies import SimpleCookie
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--expected-account", required=True)
    parser.add_argument("--name", default="router-it-" + uuid.uuid4().hex[:8])
    args = parser.parse_args()
    env = dict(os.environ, AWS_PROFILE=args.profile, AWS_DEFAULT_REGION="us-east-1",
               AWS_REGION="us-east-1", AWS_PAGER="", TF_IN_AUTOMATION="1")
    report_dir = HERE / "results" / args.name
    report_dir.mkdir(parents=True, exist_ok=False)
    evidence = {"name": args.name, "started": datetime.now(timezone.utc).isoformat(),
                "checks": [], "cleanup": "not needed"}
    def save():
        (report_dir / "result.json").write_text(json.dumps(evidence, indent=2) + "\n")
    def record(name, **data):
        evidence["checks"].append({"check": name, **data})
        print(json.dumps(evidence["checks"][-1]), flush=True)
        save()
    def command(argv, capture=True):
        result = subprocess.run(argv, cwd=HERE, env=env, text=True,
                                stdout=subprocess.PIPE if capture else None,
                                stderr=subprocess.PIPE if capture else None)
        if result.returncode:
            raise RuntimeError(f"{argv[0:3]} failed: {result.stderr or result.returncode}")
        return result.stdout or ""
    def aws(*argv):
        return json.loads(command(["aws", *argv, "--output", "json"]) or "{}")
    def tf(*argv, capture=True):
        return command(["terraform", *argv], capture)
    def tf_logged(label, *argv):
        with (report_dir / f"{label}.log").open("w") as log:
            proc = subprocess.Popen(["terraform", *argv], cwd=HERE, env=env,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in proc.stdout:
                log.write(line)
                log.flush()
                if any(word in line for word in ("Creating...", "Modifying...", "Destroying...",
                        "complete", "Still ", "Error:", "Success!", "Plan:")):
                    print(line, end="", flush=True)
            if proc.wait():
                raise RuntimeError(f"Terraform {label} failed; see {log.name}")
    def request(path="/probe", pin=None):
        headers = {} if pin is None else {"Cookie": f'{out["cookie"]}={pin}'}
        try:
            response = urllib.request.urlopen(urllib.request.Request(out["url"] + path, headers=headers), timeout=30)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return {"status": response.status, "body": response.read().decode(),
                    "cache": response.headers.get("X-Cache", ""),
                    "set_cookie": response.headers.get_all("Set-Cookie", []),
                    "pop": response.headers.get("X-Amz-Cf-Pop")}
    def wait_for(label, predicate, timeout=300):
        started = time.monotonic()
        last = None
        while time.monotonic() - started < timeout:
            try:
                last = predicate()
                if last:
                    record(label, seconds=round(time.monotonic() - started, 2))
                    return
            except (urllib.error.URLError, TimeoutError) as error:
                last = str(error)
            time.sleep(5)
        raise AssertionError(f"{label} timed out after {timeout}s; last={last}")
    def rollout(active, weight, pin_enabled=True):
        state = {"active": active, "weight": weight, "pin_cookie": out["cookie"] if pin_enabled else None}
        started = time.monotonic()
        aws("ssm", "put-parameter", "--name", out["parameter_name"], "--type", "String",
            "--overwrite", "--value", json.dumps(state))
        def synced():
            rows = aws("cloudfront-keyvaluestore", "list-keys", "--kvs-arn", out["kvs_arn"]).get("Items", [])
            actual = {row["Key"]: row["Value"] for row in rows}
            return all(actual.get(k) == ("null" if v is None else str(v)) for k, v in state.items())
        wait_for("parameter propagated to KVS", synced)
        record("rollout", active=active, weight=weight, seconds=round(time.monotonic() - started, 2))
    def check_response(response, deployment):
        assert response["status"] == 200, response
        assert response["body"] == deployment, response
    deployed = False
    out = None
    try:
        identity = aws("sts", "get-caller-identity")
        assert identity["Account"] == args.expected_account, "AWS account does not match --expected-account"
        assert args.name.startswith("router-it-"), "Test resource prefix required"
        evidence["identity"] = identity
        evidence["revision"] = command(["git", "rev-parse", "HEAD"]).strip()
        evidence["working_diff"] = command(["git", "diff"])
        tf_logged("init", "init", "-backend=false", "-input=false")
        evidence["module_manifest"] = json.loads((HERE / ".terraform/modules/modules.json").read_text())
        evidence["terraform_version"] = json.loads(tf("version", "-json"))
        # Refuse reuse of a populated state: cleanup must only own this test's resources.
        assert not (HERE / "terraform.tfstate").exists() or not tf("state", "list").strip(), "Fixture already has resources; clean up that run first"
        vars_ = [f"-var=name={args.name}", f"-var=expected_account={args.expected_account}"]
        tf_logged("plan", "plan", "-input=false", "-out=" + str(report_dir / "plan"), *vars_)
        plan = json.loads(tf("show", "-json", str(report_dir / "plan")))
        assert all(c["change"]["actions"] in (["create"], ["read"], ["no-op"])
                   for c in plan.get("resource_changes", [])), "Initial plan must not modify existing resources"
        evidence["planned_resources"] = [c["address"] for c in plan.get("resource_changes", [])
                                         if c["change"]["actions"] == ["create"]]
        deployed = True  # Also clean up a partially failed apply.
        evidence["cleanup"] = "pending"
        save()
        tf_logged("apply", "apply", "-input=false", str(report_dir / "plan"))
        out = json.loads(tf("output", "-json", "test"))
        evidence["outputs"] = out
        save()
        wait_for("initial green deployment serves traffic",
                 lambda: request()["body"] == "green", timeout=600)
        for color in ("blue", "green"):
            response = request(pin=color)
            check_response(response, color)
        record("explicit blue and green pinning", passed=True)
        first = request()
        check_response(first, "green")
        cookies = SimpleCookie()
        for value in first["set_cookie"]:
            cookies.load(value)
        assert out["cookie"] in cookies, f"Pin cookie not set: {first}"
        assert cookies[out["cookie"]].value == "green", first
        record("new viewer receives green pin", response=first)
        rollout("blue", 0)
        wait_for("promotion changes unpinned traffic", lambda: request()["body"] == "blue")
        check_response(request(pin="green"), "green")
        check_response(request(pin="invalid"), "blue")
        record("existing pins survive promotion; invalid pins ignored", passed=True)
        # Same URL, alternating deployment pins, including warm-cache requests.
        observations = []
        for i in range(12):
            color = ("blue", "green")[i % 2]
            response = request("/shared-cache", color)
            check_response(response, color)
            observations.append(response)
        assert any("Hit" in r["cache"] for r in observations), observations
        record("deployment cache isolation", responses=observations)
        rollout("blue", 25)
        # KVS-to-edge propagation is asynchronous; allow it before sampling.
        time.sleep(20)
        with ThreadPoolExecutor(max_workers=8) as executor:
            samples = list(executor.map(lambda _: request("/canary"), range(200)))
        assert all(r["status"] == 200 and r["body"] in ("blue", "green") for r in samples)
        for response in samples:
            assigned = SimpleCookie()
            for value in response["set_cookie"]:
                assigned.load(value)
            assert out["cookie"] in assigned, response
            assert assigned[out["cookie"]].value == response["body"], response
        green = sum(r["body"] == "green" for r in samples)
        assert 25 <= green <= 80, f"25% canary outside broad statistical bounds: {green}/200"
        record("25 percent canary", green=green, total=len(samples))
        rollout("blue", 100)
        wait_for("100 percent canary", lambda: request()["body"] == "green")
        rollout("blue", 0)
        wait_for("rollback returns unpinned traffic to blue", lambda: request()["body"] == "blue")
        check_response(request(pin="green"), "green")
        record("rollback retains existing green pins", passed=True)
        # Fresh paths bypass cached success; simulate application failure at green.
        failure_actions = [{"Type": "fixed-response", "FixedResponseConfig":
                            {"StatusCode": "503", "ContentType": "text/plain", "MessageBody": "unavailable"}}]
        aws("elbv2", "modify-listener", "--listener-arn", out["green_listener"],
            "--default-actions", json.dumps(failure_actions))
        wait_for("green origin failure is visible to pinned viewers",
                 lambda: request("/failure-" + uuid.uuid4().hex, "green")["status"] == 503)
        check_response(request("/healthy-" + uuid.uuid4().hex), "blue")
        record("healthy deployment continues; no automatic origin failover", passed=True)
        rollout("blue", 0, pin_enabled=False)
        wait_for("emergency rollback moves green-pinned viewers to blue",
                 lambda: request("/evacuate-" + uuid.uuid4().hex, "green")["body"] == "blue")
        healthy_actions = [{"Type": "fixed-response", "FixedResponseConfig":
                            {"StatusCode": "200", "ContentType": "text/plain", "MessageBody": "green"}}]
        aws("elbv2", "modify-listener", "--listener-arn", out["green_listener"],
            "--default-actions", json.dumps(healthy_actions))
        rollout("blue", 0)
        wait_for("green origin recovers",
                 lambda: request("/recovered-" + uuid.uuid4().hex, "green")["body"] == "green")
        rollout("blue", 0)
        # Disable only this fixture's event rule to test scheduled reconciliation.
        change_rule = out["name"] + "-edge-router-sync-on-change"
        schedule_rule = out["name"] + "-edge-router-sync"
        aws("events", "disable-rule", "--name", change_rule)
        rollout("green", 0)
        wait_for("schedule reconciles a missed change event", lambda: request()["body"] == "green")
        aws("events", "enable-rule", "--name", change_rule)
        # Remove rollout keys while both sync triggers are paused.
        aws("events", "disable-rule", "--name", change_rule)
        aws("events", "disable-rule", "--name", schedule_rule)
        time.sleep(35)  # Let an already-started sync invocation finish.
        metadata = aws("cloudfront-keyvaluestore", "describe-key-value-store", "--kvs-arn", out["kvs_arn"])
        aws("cloudfront-keyvaluestore", "update-keys", "--kvs-arn", out["kvs_arn"],
            "--if-match", metadata["ETag"], "--deletes",
            json.dumps([{"Key": key} for key in ("active", "weight", "pin_cookie")]))
        wait_for("missing rollout settings fall back to blue", lambda: request()["body"] == "blue")
        check_response(request(pin="green"), "blue")
        aws("events", "enable-rule", "--name", schedule_rule)
        aws("events", "enable-rule", "--name", change_rule)
        rollout("blue", 0)
        wait_for("routing recovers after restoring rollout settings",
                 lambda: request(pin="green")["body"] == "green")
        # Prove a subsequent Terraform apply does not reset operational rollout state.
        tf_logged("reapply", "apply", "-input=false", "-auto-approve", *vars_)
        state = json.loads(aws("ssm", "get-parameter", "--name", out["parameter_name"])["Parameter"]["Value"])
        assert state["active"] == "blue" and state["weight"] == 0, state
        record("terraform reapply preserves rollout state", passed=True)
        evidence["status"] = "passed"
    except BaseException as error:
        evidence["status"] = "failed"
        evidence["error"] = repr(error)
        save()
        if out:
            try:
                evidence["sync_logs"] = aws("logs", "filter-log-events",
                    "--log-group-name", "/aws/lambda/" + out["sync_function_name"],
                    "--limit", "30")
            except Exception as diagnostic_error:
                evidence["diagnostic_error"] = repr(diagnostic_error)
        raise
    finally:
        if deployed:
            try:
                tf_logged("destroy", "destroy", "-input=false", "-auto-approve",
                          f"-var=name={args.name}", f"-var=expected_account={args.expected_account}")
                assert not tf("state", "list").strip(), "Resources remain in Terraform state"
                evidence["cleanup"] = "passed"
            except BaseException as error:
                evidence["cleanup"] = "failed"
                evidence["cleanup_error"] = repr(error)
                print(f"CLEANUP FAILED: {error}", file=sys.stderr)
        evidence["finished"] = datetime.now(timezone.utc).isoformat()
        save()
        print(f"Evidence: {report_dir / 'result.json'}", flush=True)
    if evidence["cleanup"] == "failed":
        raise SystemExit(1)

if __name__ == "__main__":
    main()