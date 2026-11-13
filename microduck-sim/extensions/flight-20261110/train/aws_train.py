#!/usr/bin/env python3
"""Run a MicroDuck training job on one AWS spot GPU instance (us-east-1) that terminates itself. Guide: AWS.md.

  python3 aws_train.py launch --run NAME --repo DIR --preset flight --dollars D [--hours H] [--resume] --cmd 'python ...'
  python3 aws_train.py status [--run NAME]     instance state, boot/job phase, setup and pull times, cost so far
  python3 aws_train.py logs --run NAME [--file job.log|setup.log|events.log] [-n 60]
  python3 aws_train.py fetch --run NAME [--now] -> train/aws/out/NAME/
  python3 aws_train.py stop --run NAME          final pull, then terminate (only instances tagged Project=microduck-train)
  python3 aws_train.py sweep                    everything this tool created that still exists (billable and free)

Design (why each part exists):
- Spot only (the 8-vCPU "G and VT Spot" quota): the account's 16 on-demand G vCPUs belong to another project's
  g5.4xlarge. On-demand is used only with --allow-on-demand, only g5.xlarge, and only after every spot candidate failed
  for capacity.
- The dollar cap becomes a wall-clock limit: limit = dollars / (spot max price + root volume + public IPv4) - 5 min, read
  from the current spot price; the max price is 1.25 x the current price (at most on demand), so the cap holds even if
  the price rises. The boot wrapper (aws_boot.sh) powers off when the command ends and at that limit; shutdown behaviour
  is terminate and the root volume is deleted on termination.
- Outputs live on the Mac mini: this CLI user has no S3 write and no IAM role permissions (AWS.md, "Permissions"), so
  the instance carries no credentials at all. aws_pull.py on the Mac mini uploads the code bundle over SSH and pulls
  /opt/mdt/out (checkpoints, logs, ONNX) every minute into ~/code/microduck-train-aws/<run>/; `--resume` uploads that
  mirror back, and the worker resumes from its newest model_<it>.pt.
- Every resource is tagged Project=microduck-train, Run=<run>; `stop` and `sweep` work from those tags only.
"""
from __future__ import annotations

import argparse
import base64
import fnmatch
import glob
import hashlib
import io
import json
import shlex
import subprocess
import sys
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent                       # extensions/flight-20261110/train
SIM = HERE.parents[2]                                         # microduck-sim
LOCAL = HERE / "aws"                                          # ignored: out/<run>/, staging/<run>/, launches.jsonl
REGION = "us-east-1"
PROJECT = "microduck-train"
KEY_NAME = "microduck-train"
SG_NAME = "microduck-train-ssh"
MINI = "mac-mini"
MINI_ROOT = "code/microduck-train-aws"                        # under the Mac mini home
MINI_KEY = "~/.ssh/microduck-train"
MINI_ENV = "PATH=/opt/homebrew/bin:/usr/bin:/bin"
AMI_NAME = "Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 22.04) *"
ROOT_GB = 75                                                  # the AMI's own root size
GRACE_S = 480                                                 # wait for the final pull after the command ends
# price basis (us-east-1, checked 2026-11-12): gp3 $0.08/GB-month, public IPv4 $0.005/h; on-demand Linux $/h
EBS_H = ROOT_GB * 0.08 / 730
IPV4_H = 0.005
ON_DEMAND_H = {"g5.xlarge": 1.006, "g5.2xlarge": 1.212, "g4dn.xlarge": 0.526, "g4dn.2xlarge": 0.752}
VCPU = {"g5.xlarge": 4, "g5.2xlarge": 8, "g4dn.xlarge": 4, "g4dn.2xlarge": 8}
DEFAULT_TYPES = "g5.xlarge,g5.2xlarge,g4dn.xlarge,g4dn.2xlarge"
CAPACITY_ERRORS = ("InsufficientInstanceCapacity", "SpotMaxPriceTooLow", "InsufficientCapacity", "capacity-not-available",
                   "Unsupported", "InsufficientHostCapacity")
# the same exclusions flight_modal.py applies to the code it ships
IGNORE = ["**/.venv/**", "**/logs/**", "**/wandb/**", "**/__pycache__/**", "**/.git/**", "**/*.pt", "**/*.onnx", "**/outputs/**",
          "**/runs/**", "**/cmu/real-logs/**", "**/cmu/whole/runtime-overlay/models-ft*/**", "**/kaggle/out/**", "**/*.gz",
          "**/cmu/simulator/**", "**/cmu/hardware/**", "**/cmu/model/scans/**", "**/.last_call_*"]


# ---------------------------------------------------------------- helpers
def aws(*args, check=True):
    r = subprocess.run(["aws", "--region", REGION, "--output", "json", *args], capture_output=True, text=True)
    if r.returncode and check:
        raise RuntimeError(r.stderr.strip())
    if r.returncode:
        return {"_error": r.stderr.strip()}
    return json.loads(r.stdout) if r.stdout.strip() else {}


def mini(cmd, check=True, timeout=120):
    r = subprocess.run(["ssh", "-o", "ConnectTimeout=15", MINI, f"export {MINI_ENV}; {cmd}"], capture_output=True, text=True, timeout=timeout)
    if r.returncode and check:
        raise RuntimeError(f"mac-mini: {cmd}: {r.stderr.strip()[-800:]}")
    return r.stdout


def tags(run=None, name=None):
    t = [{"Key": "Project", "Value": PROJECT}]
    if run:
        t.append({"Key": "Run", "Value": run})
    if name:
        t.append({"Key": "Name", "Value": name})
    return t


def tag_spec(kinds, run):
    return json.dumps([{"ResourceType": k, "Tags": tags(run, f"{PROJECT}-{run}")} for k in kinds])


def mini_dir(run):
    return f"{MINI_ROOT}/{run}"


def records():
    p = LOCAL / "launches.jsonl"
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def run_instances(run, states=("pending", "running", "stopping", "stopped", "shutting-down")):
    f = [f"Name=tag:Project,Values={PROJECT}", f"Name=instance-state-name,Values={','.join(states)}"]
    if run:
        f.append(f"Name=tag:Run,Values={run}")
    res = aws("ec2", "describe-instances", "--filters", *f)
    return [i for r in res["Reservations"] for i in r["Instances"]]


def tagval(obj, key):
    return next((t["Value"] for t in obj.get("Tags", []) if t["Key"] == key), None)


# ---------------------------------------------------------------- one-time infrastructure (free resources)
def ensure_key():
    kp = aws("ec2", "describe-key-pairs", "--filters", f"Name=key-name,Values={KEY_NAME}")["KeyPairs"]
    if kp:
        return
    # the private key is generated on the Mac mini and never leaves it; AWS gets only the public half
    mini(f"test -f {MINI_KEY} || ssh-keygen -q -t ed25519 -N '' -C {KEY_NAME} -f {MINI_KEY}")
    pub = mini(f"cat {MINI_KEY}.pub").strip()
    stage = LOCAL / "staging"
    stage.mkdir(parents=True, exist_ok=True)
    (stage / f"{KEY_NAME}.pub").write_text(pub + "\n")
    aws("ec2", "import-key-pair", "--key-name", KEY_NAME, "--public-key-material", f"fileb://{stage / (KEY_NAME + '.pub')}",
        "--tag-specifications", json.dumps([{"ResourceType": "key-pair", "Tags": tags(name=KEY_NAME)}]))
    print(f"[infra] imported key pair {KEY_NAME} (private key only on the Mac mini at {MINI_KEY})")


def ensure_sg():
    vpc = aws("ec2", "describe-vpcs", "--filters", "Name=isDefault,Values=true")["Vpcs"][0]["VpcId"]
    sgs = aws("ec2", "describe-security-groups", "--filters", f"Name=group-name,Values={SG_NAME}", f"Name=vpc-id,Values={vpc}")["SecurityGroups"]
    if sgs:
        sg = sgs[0]
    else:
        gid = aws("ec2", "create-security-group", "--group-name", SG_NAME, "--vpc-id", vpc,
                  "--description", "microduck-train: SSH from the Mac mini only",
                  "--tag-specifications", json.dumps([{"ResourceType": "security-group", "Tags": tags(name=SG_NAME)}]))["GroupId"]
        sg = aws("ec2", "describe-security-groups", "--group-ids", gid)["SecurityGroups"][0]
        print(f"[infra] created security group {SG_NAME} {gid}")
    assert tagval(sg, "Project") == PROJECT, f"{SG_NAME} exists without the Project tag; not touching it"
    ip = mini("curl -s -m 10 https://checkip.amazonaws.com").strip()
    want = f"{ip}/32"
    have = [r["CidrIp"] for p in sg["IpPermissions"] if p.get("FromPort") == 22 for r in p.get("IpRanges", [])]
    if want not in have:
        aws("ec2", "authorize-security-group-ingress", "--group-id", sg["GroupId"], "--ip-permissions", json.dumps(
            [{"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": want, "Description": "mac-mini"}]}]))
    for old in (c for c in have if c != want):  # the Mac mini's address changed: drop the stale rule of this group
        aws("ec2", "revoke-security-group-ingress", "--group-id", sg["GroupId"], "--ip-permissions", json.dumps(
            [{"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": old}]}]))
    return sg["GroupId"], vpc


def newest_ami():
    imgs = aws("ec2", "describe-images", "--owners", "amazon", "--filters", f"Name=name,Values={AMI_NAME}",
               "Name=architecture,Values=x86_64", "Name=state,Values=available")["Images"]
    img = max(imgs, key=lambda i: i["CreationDate"])
    return img["ImageId"], img["Name"]


# ---------------------------------------------------------------- bundle
def asset_map(preset, repo, extra):
    m = {}
    if preset in ("flight", "base"):
        m |= {"walk61.onnx": repo / "cmu/whole/runtime-overlay/models/walk61.onnx",
              "stand61.onnx": repo / "cmu/whole/runtime-overlay/models/stand61.onnx",
              "asbuilt-mass-manifest.json": repo / "cmu/whole/dynamics/asbuilt-20261015/asbuilt-mass-manifest.json",
              "existing-model-mass-audit.json": repo / "cmu/whole/electrical/existing-model-mass-audit.json"}
    if preset == "base":  # cmu/finetune/kaggle/kaggle_job.py: --cmu-config manifests
        m |= {f"manifests/{p.name}": p for p in sorted((repo / "cmu/model/manifests").glob("*.json"))}
    if preset == "flight":  # flight_modal.py ASSETS + the kaggle_flight.py init policies
        m |= {f"manifests/{p.name}": p for p in sorted((HERE / "manifests").glob("flightpack-*.json"))}
        m |= {f"init/{p.name}": p for p in sorted((HERE / "init").glob("*.onnx"))}
        for n, p in {"fq2_1999.onnx": HERE / "ckpt/fq2_1999/walk61.onnx", "groundpick61.onnx": HERE / "ckpt/bend_spec/groundpick61.onnx",
                     "seepick61.onnx": HERE / "ckpt/bend_spec/seepick61.onnx", "uni_a.onnx": HERE / "ckpt/uni_a/walk61.onnx"}.items():
            if p.exists():
                m[f"init/{n}"] = p
    for spec in extra:  # DEST=GLOB; DEST ending in / keeps each matched file's name
        dest, pat = spec.split("=", 1)
        hits = sorted(glob.glob(str(Path(pat).expanduser())))
        if not hits:
            sys.exit(f"--asset {spec}: no file matches")
        for h in hits:
            m[dest + Path(h).name if dest.endswith("/") else dest] = Path(h)
    missing = [str(p) for p in m.values() if not Path(p).is_file()]
    if missing:
        sys.exit(f"missing assets: {missing}")
    return m


def build_bundle(repo, assets, stage):
    files = subprocess.run(["git", "-C", str(repo), "ls-files", "-co", "--exclude-standard", "-z"], capture_output=True,
                           text=True, check=True).stdout.split("\0")
    keep = sorted(f for f in files if f and (repo / f).is_file() and not any(fnmatch.fnmatch("/" + f, p) for p in IGNORE))
    h = hashlib.sha256()
    for f in keep:
        h.update(f.encode() + b"\0" + (repo / f).read_bytes())
    digest = h.hexdigest()[:16]
    stage.mkdir(parents=True, exist_ok=True)
    with tarfile.open(stage / "src.tgz", "w:gz") as t:
        for f in keep:
            t.add(repo / f, arcname=f)
        data = (digest + "\n").encode()
        ti = tarfile.TarInfo("SOURCE_DIGEST")
        ti.size = len(data)
        t.addfile(ti, io.BytesIO(data))
    with tarfile.open(stage / "assets.tgz", "w:gz") as t:
        for name, p in sorted(assets.items()):
            t.add(p, arcname=name)
    return digest, len(keep)


# ---------------------------------------------------------------- launch
def candidates(types):
    hist = aws("ec2", "describe-spot-price-history", "--instance-types", *types, "--product-descriptions", "Linux/UNIX",
               "--start-time", time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()))["SpotPriceHistory"]
    latest = {}
    for e in hist:
        k = (e["InstanceType"], e["AvailabilityZone"])
        if k not in latest or e["Timestamp"] > latest[k]["Timestamp"]:
            latest[k] = e
    return sorted(((t, az, float(e["SpotPrice"])) for (t, az), e in latest.items()), key=lambda x: (types.index(x[0]), x[2]))


def cmd_launch(a):
    run = a.run
    assert run.replace("-", "").replace("_", "").isalnum() and len(run) <= 40, "run name: letters, digits, - and _"
    if run_instances(run):
        sys.exit(f"run {run} already has a live instance; `stop` it or pick another name")
    types = a.types.split(",")
    bad = [t for t in types if VCPU.get(t, 99) > 8]
    if bad:
        sys.exit(f"{bad}: above the 8-vCPU spot quota (or unknown type)")
    repo = Path(a.repo).expanduser().resolve()
    attempt = 1 + sum(r["run"] == run for r in records())
    if a.resume and attempt == 1:
        sys.exit(f"--resume: no earlier launch of {run} in {LOCAL / 'launches.jsonl'}")

    # 1. code bundle, on the Mac mini before any instance exists (nothing bills while it uploads)
    stage = LOCAL / "staging" / run
    assets = asset_map(a.preset, repo, a.asset)
    digest, n = build_bundle(repo, assets, stage)
    print(f"[bundle] {n} files from {repo} (digest {digest}), {len(assets)} assets; "
          f"src {(stage / 'src.tgz').stat().st_size / 1e6:.1f} MB, assets {(stage / 'assets.tgz').stat().st_size / 1e6:.1f} MB")
    md = mini_dir(run)
    mini(f"mkdir -p {md}/bundle {md}/out")
    subprocess.run(["rsync", "-a", str(stage / "src.tgz"), str(stage / "assets.tgz"), f"{MINI}:{md}/bundle/"], check=True)
    subprocess.run(["rsync", "-a", str(HERE / "aws_pull.py"), f"{MINI}:{md}/aws_pull.py"], check=True)
    if a.resume:
        ck = mini(f"for d in {md}/out/runs/*/; do ls $d | grep -E '^model_[0-9]+\\.pt$' | sort -t_ -k2 -n | tail -1 | sed \"s|^|$d|\"; done",
                  check=False).strip()
        print(f"[resume] newest checkpoints in the Mac mini mirror:\n{ck or '(none)'}")

    # 2. infrastructure and price
    ensure_key()
    sg, vpc = ensure_sg()
    ami, ami_name = newest_ami()
    subnets = {s["AvailabilityZone"]: s["SubnetId"] for s in aws("ec2", "describe-subnets", "--filters",
               f"Name=vpc-id,Values={vpc}", "Name=default-for-az,Values=true")["Subnets"]}
    cands = [c for c in candidates(types) if c[1] in subnets]
    if a.az:
        cands = [c for c in cands if c[1] in a.az.split(",")]
    if not cands:
        sys.exit("no spot price for these types in the default subnets")
    print(f"[price] AMI {ami} ({ami_name}); spot now: " + ", ".join(f"{t} {az} ${p:.4f}" for t, az, p in cands))

    def plan(t, price, spot=True):
        maxp = min(round(price * 1.25, 4), ON_DEMAND_H[t]) if spot else ON_DEMAND_H[t]
        hourly = maxp + EBS_H + IPV4_H
        wall = int(a.dollars / hourly * 3600) - 300
        if a.hours:
            wall = min(wall, int(a.hours * 3600))
        return maxp, hourly, wall

    # 3. user-data
    def user_data(wall, hourly):
        src = (HERE / "aws_boot.sh").read_text()
        cmd_b64 = base64.b64encode(a.cmd.encode()).decode()
        for k, v in {"RUN": run, "WALL_S": str(wall), "GRACE_S": str(GRACE_S), "RATE": f"{hourly:.4f}", "CMD_B64": cmd_b64}.items():
            src = src.replace(f"@@{k}@@", v)
        assert "@@" not in src
        p = stage / "user-data.sh"
        p.write_text(src)
        assert p.stat().st_size < 16000, "user-data above 16 KB"
        return p

    common = ["--image-id", ami, "--security-group-ids", sg, "--key-name", KEY_NAME, "--count", "1",
              "--instance-initiated-shutdown-behavior", "terminate",
              "--metadata-options", "HttpTokens=required,HttpEndpoint=enabled",
              "--block-device-mappings", json.dumps([{"DeviceName": "/dev/sda1", "Ebs": {"DeleteOnTermination": True,
                                                       "VolumeType": "gp3", "VolumeSize": ROOT_GB}}])]
    inst, chosen, errors = None, None, []
    t_wait = time.time() + 60 * a.wait_capacity
    hard_error = False
    tries = []
    while inst is None and not hard_error:
        errors = []  # capacity and request errors of this round only
        for t, az, price in cands:
            maxp, hourly, wall = plan(t, price)
            if wall >= 600:
                tries.append((t, az, price))
        for t, az, price in tries:
            maxp, hourly, wall = plan(t, price)
            ud = user_data(wall, hourly)
            mo = {"MarketType": "spot", "SpotOptions": {"MaxPrice": f"{maxp:.4f}", "SpotInstanceType": "one-time",
                                                       "InstanceInterruptionBehavior": "terminate"}}
            r = aws("ec2", "run-instances", *common, "--instance-type", t, "--subnet-id", subnets[az], "--user-data", f"file://{ud}",
                    "--instance-market-options", json.dumps(mo),
                    "--tag-specifications", tag_spec(["instance", "volume", "network-interface", "spot-instances-request"], run),
                    *(["--dry-run"] if a.dry_run else []), check=False)
            if a.dry_run:
                print(f"[dry-run] {t} {az} max ${maxp}/h wall {wall / 60:.0f} min: {r.get('_error', '')[-200:]}; user-data {ud}")
                return
            if "_error" in r:
                errors.append(f"{t} {az}: {r['_error'][-300:]}")
                print(f"[launch] {t} {az} spot refused: {r['_error'].split('operation')[0][-90:]}")
                if not any(e in r["_error"] for e in CAPACITY_ERRORS):
                    hard_error = True  # quota, permission or request errors do not change in the next zone
                    break
                continue
            inst, chosen = r["Instances"][0], dict(type=t, az=az, spot_price=price, max_price=maxp, hourly=round(hourly, 4),
                                                   wall_s=wall, market="spot")
            break
        if not tries:
            sys.exit(f"[launch] cap ${a.dollars} buys under 10 min on every candidate")
        tries = []
        if inst is None and not hard_error:
            if time.time() > t_wait:
                break
            print("[launch] no spot capacity in this round; next round in 60 s")
            time.sleep(60)
            cands = [c for c in candidates(types) if c[1] in subnets and (not a.az or c[1] in a.az.split(","))]
    if inst is None and not hard_error and a.allow_on_demand and errors and all(any(e in x for e in CAPACITY_ERRORS) for x in errors):
        t = "g5.xlarge"
        maxp, hourly, wall = plan(t, ON_DEMAND_H[t], spot=False)
        ud = user_data(wall, hourly)
        for az in sorted(subnets):
            r = aws("ec2", "run-instances", *common, "--instance-type", t, "--subnet-id", subnets[az], "--user-data", f"file://{ud}",
                    "--tag-specifications", tag_spec(["instance", "volume", "network-interface"], run), check=False)
            if "_error" not in r:
                inst, chosen = r["Instances"][0], dict(type=t, az=az, spot_price=None, max_price=maxp, hourly=round(hourly, 4),
                                                       wall_s=wall, market="on-demand")
                print("[launch] WARNING: on-demand g5.xlarge (no spot capacity anywhere); it uses 4 of the 16 on-demand "
                      "G vCPUs the c3-carla instance needs")
                break
            errors.append(f"on-demand {t} {az}: {r['_error'][-300:]}")
    if inst is None:
        sys.exit("[launch] no instance:\n  " + "\n  ".join(errors))

    iid = inst["InstanceId"]
    aws("ec2", "wait", "instance-running", "--instance-ids", iid)
    d = aws("ec2", "describe-instances", "--instance-ids", iid)["Reservations"][0]["Instances"][0]
    ip = d.get("PublicIpAddress")
    sdb = aws("ec2", "describe-instance-attribute", "--instance-id", iid, "--attribute", "instanceInitiatedShutdownBehavior")
    rec = dict(run=run, attempt=attempt, instance=iid, ip=ip, launched=time.strftime("%Y-%m-%dT%H:%M:%S%z"), ami=ami,
               repo=str(repo), digest=digest, cmd=a.cmd, dollars=a.dollars, resume=a.resume,
               shutdown_behavior=sdb["InstanceInitiatedShutdownBehavior"]["Value"],
               delete_on_termination=[b["Ebs"]["DeleteOnTermination"] for b in d.get("BlockDeviceMappings", [])],
               spot_request=d.get("SpotInstanceRequestId"), mini_dir=md) | chosen
    LOCAL.mkdir(parents=True, exist_ok=True)
    with open(LOCAL / "launches.jsonl", "a") as f:
        f.write(json.dumps(rec) + "\n")

    # 4. puller on the Mac mini (code upload, resume state, pulls, final-pull handshake)
    life = chosen["wall_s"] + GRACE_S + 1800
    pull = (f"cd {md} && nohup python3 aws_pull.py --dir $HOME/{md} --host {ip} --key {MINI_KEY} --attempt {attempt} "
            f"--life-s {life}{' --resume' if a.resume else ''} > puller.out 2>&1 < /dev/null &")
    mini(pull)
    print(f"[launch] {iid} {chosen['type']} {chosen['market']} in {chosen['az']} ip {ip}; spot ${chosen['spot_price']}/h, "
          f"max ${chosen['max_price']}/h, all-in worst ${chosen['hourly']}/h; wall limit {chosen['wall_s'] / 60:.0f} min "
          f"=> at most ${chosen['hourly'] * (chosen['wall_s'] + 300) / 3600:.2f}; shutdown behaviour {rec['shutdown_behavior']}, "
          f"root delete-on-termination {rec['delete_on_termination']}")
    print(f"[launch] outputs: {MINI}:~/{md}/out (pulled every minute); `python3 {Path(__file__).name} status --run {run}`")


# ---------------------------------------------------------------- status, logs, fetch, stop, sweep
def cmd_status(a):
    live = run_instances(a.run, states=("pending", "running", "stopping", "stopped", "shutting-down", "terminated"))
    recs = {r["instance"]: r for r in records()}
    if not live:
        print("no instances" + (f" for run {a.run}" if a.run else ""))
    for i in sorted(live, key=lambda i: i["LaunchTime"]):
        r = recs.get(i["InstanceId"], {})
        state = i["State"]["Name"]
        line = f"{tagval(i, 'Run')} #{r.get('attempt', '?')} {i['InstanceId']} {i['InstanceType']} {state}"
        if state in ("pending", "running"):
            up_h = (datetime.now(timezone.utc) - datetime.fromisoformat(i["LaunchTime"].replace("Z", "+00:00"))).total_seconds() / 3600
            line += f" up {up_h * 60:.0f} min, about ${up_h * (r.get('spot_price') or r.get('max_price', 0)):.2f} so far"
        else:
            line += f" ({i.get('StateTransitionReason', '')})"
        print(line)
    runs = [a.run] if a.run else sorted({tagval(i, "Run") for i in live})
    for run in runs:
        md = mini_dir(run)
        txt = mini(f"cd {md} 2>/dev/null && cat out/status.json puller.json 2>/dev/null; tail -n 4 out/events.log puller.log 2>/dev/null; "
                   f"grep -h '\\[cap\\]\\|\\[done\\]\\|Traceback' out/job.log 2>/dev/null | tail -n 3", check=False)
        print(f"--- {run} (Mac mini ~/{md})\n{txt.strip()}")


def cmd_logs(a):
    print(mini(f"tail -n {int(a.n)} {mini_dir(a.run)}/out/{shlex.quote(a.file)}", check=False))


def _once_pull(run):
    for i in run_instances(run, states=("running",)):
        r = next((x for x in records() if x["instance"] == i["InstanceId"]), None)
        if r and i.get("PublicIpAddress"):
            md = mini_dir(run)
            mini(f"cd {md} && python3 aws_pull.py --once --dir $HOME/{md} --host {i['PublicIpAddress']} --key {MINI_KEY} --attempt {r['attempt']}",
                 check=False, timeout=1800)


def cmd_fetch(a):
    if a.now:
        _once_pull(a.run)
    dst = LOCAL / "out" / a.run
    dst.mkdir(parents=True, exist_ok=True)
    subprocess.run(["rsync", "-a", "--exclude", "bundle/", "--exclude", "known_hosts", f"{MINI}:{mini_dir(a.run)}/", f"{dst}/"], check=True)
    n = sum(1 for _ in dst.rglob("*") if _.is_file())
    print(f"[fetch] {n} files in {dst}")
    newest = lambda pat: sorted(dst.rglob(pat), key=lambda p: p.stat().st_mtime)[-3:]  # noqa: E731
    for p in newest("model_*.pt") + newest("*.onnx"):
        print("  ", p.relative_to(dst))


def cmd_stop(a):
    insts = run_instances(a.run, states=("pending", "running", "stopping", "stopped"))
    if not insts:
        print(f"no live instance for run {a.run}")
        return
    for i in insts:
        if tagval(i, "Project") != PROJECT or tagval(i, "Run") != a.run:
            sys.exit(f"refusing {i['InstanceId']}: not tagged Project={PROJECT}, Run={a.run}")
    if not a.no_pull:
        _once_pull(a.run)
        print("[stop] final pull done")
    ids = [i["InstanceId"] for i in insts]
    aws("ec2", "terminate-instances", "--instance-ids", *ids)
    aws("ec2", "wait", "instance-terminated", "--instance-ids", *ids)
    print(f"[stop] terminated {' '.join(ids)}")
    mini(f"pkill -f 'aws_pull.py --dir .*/{mini_dir(a.run)} ' || true", check=False)  # its puller would wait 10 min


def cmd_sweep(a):
    billable = []
    for i in run_instances(None):
        billable.append(f"instance {i['InstanceId']} {i['InstanceType']} {i['State']['Name']} run={tagval(i, 'Run')}")
    for v in aws("ec2", "describe-volumes", "--filters", f"Name=tag:Project,Values={PROJECT}")["Volumes"]:
        billable.append(f"volume {v['VolumeId']} {v['Size']} GB {v['State']} run={tagval(v, 'Run')}")
    for s in aws("ec2", "describe-snapshots", "--owner-ids", "self", "--filters", f"Name=tag:Project,Values={PROJECT}")["Snapshots"]:
        billable.append(f"snapshot {s['SnapshotId']} {s['VolumeSize']} GB")
    for e in aws("ec2", "describe-addresses", "--filters", f"Name=tag:Project,Values={PROJECT}")["Addresses"]:
        billable.append(f"elastic ip {e['PublicIp']}")
    for s in aws("ec2", "describe-spot-instance-requests", "--filters", f"Name=tag:Project,Values={PROJECT}",
                 "Name=state,Values=open,active")["SpotInstanceRequests"]:
        billable.append(f"spot request {s['SpotInstanceRequestId']} {s['State']}")
    for e in aws("ec2", "describe-network-interfaces", "--filters", f"Name=tag:Project,Values={PROJECT}")["NetworkInterfaces"]:
        billable.append(f"network interface {e['NetworkInterfaceId']} {e['Status']}")
    free = [f"key pair {k['KeyName']}" for k in aws("ec2", "describe-key-pairs", "--filters", f"Name=tag:Project,Values={PROJECT}")["KeyPairs"]]
    free += [f"security group {g['GroupId']} {g['GroupName']}" for g in aws("ec2", "describe-security-groups", "--filters",
             f"Name=tag:Project,Values={PROJECT}")["SecurityGroups"]]
    pullers = mini("pgrep -fl aws_pull.py || true", check=False).strip()
    print("billable:\n  " + ("\n  ".join(billable) if billable else "none"))
    print("free (kept for reuse):\n  " + ("\n  ".join(free) if free else "none"))
    print("Mac mini pullers:\n  " + (pullers.replace("\n", "\n  ") if pullers else "none"))
    print("S3: none (this tool stores outputs on the Mac mini)")
    sys.exit(1 if billable else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd_name", required=True)
    p = sp.add_parser("launch")
    p.add_argument("--run", required=True)
    p.add_argument("--repo", required=True, help="repository directory to pack (git-tracked and untracked, not ignored)")
    p.add_argument("--cmd", required=True, help="shell command run in the unpacked repo; env OUT, RUN, RATE_PER_HOUR, GPU_NAME; venv first on PATH")
    p.add_argument("--dollars", type=float, required=True, help="cap for this attempt, converted to the wall-clock limit")
    p.add_argument("--hours", type=float, default=0, help="optional tighter wall-clock limit")
    p.add_argument("--preset", choices=["flight", "base", "none"], default="flight", help="assets copied to /root/assets")
    p.add_argument("--asset", action="append", default=[], help="extra asset DEST=GLOB (DEST ending in / keeps names)")
    p.add_argument("--types", default=DEFAULT_TYPES)
    p.add_argument("--az", default="", help="restrict to these zones (comma list)")
    p.add_argument("--resume", action="store_true", help="upload the Mac mini mirror of this run before the command starts")
    p.add_argument("--allow-on-demand", action="store_true", help="g5.xlarge on demand if no spot capacity in any zone")
    p.add_argument("--wait-capacity", type=float, default=10, help="minutes to keep retrying when no zone has spot capacity")
    p.add_argument("--dry-run", action="store_true", help="bundle, infrastructure and an EC2 DryRun request; no instance")
    p.set_defaults(fn=cmd_launch)
    p = sp.add_parser("status")
    p.add_argument("--run")
    p.set_defaults(fn=cmd_status)
    p = sp.add_parser("logs")
    p.add_argument("--run", required=True)
    p.add_argument("--file", default="job.log")
    p.add_argument("-n", default=60)
    p.set_defaults(fn=cmd_logs)
    p = sp.add_parser("fetch")
    p.add_argument("--run", required=True)
    p.add_argument("--now", action="store_true", help="pull from the live instance first")
    p.set_defaults(fn=cmd_fetch)
    p = sp.add_parser("stop")
    p.add_argument("--run", required=True)
    p.add_argument("--no-pull", action="store_true")
    p.set_defaults(fn=cmd_stop)
    p = sp.add_parser("sweep")
    p.set_defaults(fn=cmd_sweep)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
