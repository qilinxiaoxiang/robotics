# AWS training launcher (`aws_train.py`)

Runs one MicroDuck training command on one AWS spot GPU instance in us-east-1, then terminates the instance. It works
for any worker: you give it the repository to pack, the shell command, a run name, a dollar cap and optionally a
tighter wall-clock limit. Measured on 2026-11-12 (RUNLOG.md): g5.xlarge spot (A10G 24 GB) at $0.506/h, setup 125 s
and 476 s on two boots (uv sync 57 s and 409 s: the PyPI download speed varies), 2.4 s per PPO iteration at 4096 envs
for the flight worker, so 1000 iterations cost about $0.40. Spot capacity comes and goes: of five launch commands, two found
no g5/g4dn spot capacity in any zone (one of them for 10 min of retries), and one took a g4dn.xlarge (T4).

## Commands

Run from `extensions/flight-20261110/train` on the MacBook. The Mac mini must be reachable as `mac-mini`.

Launch a flight fine-tune (example: 1000 iterations, about 45 min, cap $0.60):

    W='python cmu/finetune/flight/flight_worker.py --root $OUT/runs --gpu $GPU_NAME --rate-per-hour $RATE_PER_HOUR'
    python3 aws_train.py launch --run fa1 --repo ../../../microduck_rl --preset flight --dollars 0.60 \
      --cmd "$W --run-name fa1 --delta packwalk --manifest /root/assets/manifests/flightpack-nominal.json \
             --num-envs 4096 --max-iters 1000 --max-hours 0.8 --max-dollars 0.55 --track-guard 2.0"

Continue the same run after a spot interruption or a cap stop (the worker resumes from its newest `model_<it>.pt`):

    python3 aws_train.py launch --resume --run fa1 ... (same --cmd, a fresh --dollars for this attempt)

Watch, read, fetch, stop, check for leftovers:

    python3 aws_train.py status --run fa1
    python3 aws_train.py logs --run fa1 [--file setup.log|events.log] [-n 100]
    python3 aws_train.py fetch --run fa1 [--now]       # -> train/aws/out/fa1/ (ignored by git)
    python3 aws_train.py stop --run fa1                # final pull, then terminate
    python3 aws_train.py sweep                         # exit 1 if anything billable is left

The grasp worker (`microduck_rl-grasp`, branch cmu/grasp) uses the same launcher: `--repo ../../../microduck_rl-grasp
--preset base` plus `--asset policies/=<glob>` for its policies, and its own worker command with `--root $OUT/runs`.

Inside the command: the unpacked repository is the working directory, the project venv is first on `PATH`, assets are
under `/root/assets/<name>` (the Modal and Kaggle layout), and `OUT`, `RUN`, `RATE_PER_HOUR` (worst-case all-in $/h)
and `GPU_NAME` are set. Everything the command writes under `$OUT` is kept.

## What happens

1. `launch` packs the repository's tracked and untracked, non-ignored files with the exclusions `flight_modal.py`
   uses, plus the preset assets (`flight`: the `flight_modal.py` assets and the `kaggle_flight.py` init policies), and
   copies both to `~/code/microduck-train-aws/<run>/bundle/` on the Mac mini before any instance exists.
2. It reads the current spot price per zone and type (g5.xlarge first, then g5.2xlarge, g4dn.xlarge, g4dn.2xlarge),
   sets the spot max price to 1.25 x the current price, and turns the dollar cap into the wall-clock limit:
   `limit = dollars / (max price + 75 GB gp3 root + public IPv4) - 5 min`. With no capacity anywhere it retries for
   `--wait-capacity` minutes (default 10).
3. The instance (Deep Learning Base OSS Nvidia Driver AMI, Ubuntu 22.04) boots `aws_boot.sh` as user-data. It arms a
   systemd timer that powers off at the limit and a hard `poweroff -f` 60 s later, waits for the code, installs uv
   0.8.22, runs `uv sync --frozen --no-dev` and the Kaggle import check, then runs the command.
4. `aws_pull.py` on the Mac mini uploads the bundle over SSH (and with `--resume` the earlier attempts' outputs), then
   pulls `/opt/mdt/out` every 60 s, and every 10 s once the instance reports a spot interruption notice.
5. When the command ends, the instance writes `DONE`, waits up to 8 min for the puller's final pull, and powers off.
   Shutdown behaviour is terminate, the root volume is deleted on termination, there is no Elastic IP or snapshot.

## Permissions (why there is no S3 bucket or instance role)

The CLI user `claude-cli` has AmazonEC2FullAccess, ReadOnlyAccess, AWSSupportAccess, ServiceQuotasFullAccess and
AWSBillingReadOnlyAccess. `aws iam simulate-principal-policy` on 2026-11-12 gives implicitDeny for `s3:CreateBucket`,
`s3:PutObject`, `s3:DeleteObject`, `iam:CreateRole`, `iam:CreateInstanceProfile`, `iam:PutRolePolicy` and
`iam:PassRole`. So the tool can neither create a bucket nor give an instance a role limited to one prefix. The
least-privilege route that needs no new permission: the instance gets no credentials at all, and outputs live on the
Mac mini, pulled over SSH. If S3 is wanted later, the user needs those S3 actions on `arn:aws:s3:::microduck-train-*`
and the IAM actions on `role/microduck-train-*` and `instance-profile/microduck-train-*`, plus `iam:PassRole` for that
role.

Consequences: the Mac mini must be on while a run is alive (the outputs are lost with the instance otherwise), and the
security group `microduck-train-ssh` admits SSH only from the Mac mini's public address (refreshed at each launch).
The private key `~/.ssh/microduck-train` exists only on the Mac mini. User-data holds the command and limits only.

## Leftovers and limits

- `sweep` lists instances, volumes, snapshots, Elastic IPs, open spot requests and network interfaces tagged
  `Project=microduck-train`, the free key pair and security group (kept for reuse), and pullers on the Mac mini.
- `stop` terminates only instances tagged `Project=microduck-train` and the given `Run`.
- Spot only, within the 8-vCPU spot quota. The 16 on-demand G vCPUs belong to the c3-carla instance (another
  project); `--allow-on-demand` uses g5.xlarge on demand only after every spot candidate failed for capacity.
- The T4 types are a capacity fallback and run slower; `--types g5.xlarge,g5.2xlarge` keeps a run on A10G.
- Local record of every launch: `train/aws/launches.jsonl`.
