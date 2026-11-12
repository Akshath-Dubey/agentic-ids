# Agentic IDS — Smart Grid Intrusion Detection

A multi-agent intrusion detection system with a Streamlit dashboard. Upload CICIDS-format CSV files and five cooperating agents process them:

| Agent | File | Role |
|---|---|---|
| Monitoring | `agents/monitoring_agent.py` | Ingests and summarises traffic |
| Detection | `agents/detection_agent.py` | Classifies flows (XGBoost, falls back to HistGradientBoosting) |
| Decision | `agents/decision_agent.py` | Applies the sensitivity threshold |
| Response | `agents/response_agent.py` | Chooses mitigation actions |
| Learning | `agents/learning_agent.py` | Retrains on new data ("Auto Learn") |

It's deployed on AWS: **http://13.203.254.194**

## Architecture

```
git push (main)
   │
   ▼
GitHub Actions ── validate (compile + pytest) ── docker build + container health check ── push to GHCR
                                                                                            │
                                                                     Ansible over SSH ◄─────┘
                                                                            │
                                                                            ▼
                 Browser ──► http://<EC2_IP>:80 ──► Traefik ingress ──► Service ──► Pod (Streamlit :8501)
                                                   └──────────── K3s on one EC2 instance ────────────┘
```

## Technology stack

| Layer | Tool | Location |
|---|---|---|
| Cloud | AWS: 1× EC2 (t3.small, Ubuntu 24.04), security group, key pair, Elastic IP, default VPC | `terraform/` |
| Infrastructure as code | Terraform | `terraform/` |
| Server configuration | Ansible: packages, swap, SSH hardening, K3s, kubectl, app rollout | `ansible/playbook.yml` |
| Container | Docker: `python:3.12-slim`, non-root, `streamlit run app.py` on :8501 | `Dockerfile` |
| Orchestration | Kubernetes (K3s, single node) | `k8s/` |
| CI/CD | GitHub Actions + GitHub Container Registry | `.github/workflows/deploy.yml` |
| Code quality | SonarQube Cloud (scan + quality gate in CI) | `sonar-project.properties` |
| Alerts | CloudWatch alarms → SNS → email (CPU > 80%, status check failed) | `terraform/alerts.tf` |

## Repository structure

```
app.py                  Streamlit dashboard (the deployed entry point)
main.py                 Offline training script (not used by the deployment)
agents/                 The five agents
utils/preprocess.py     Feature preprocessing
models/model.pkl        Saved model (not loaded by app.py)
tests/test_smoke.py     End-to-end agent pipeline smoke test
Dockerfile, .dockerignore, .streamlit/config.toml
sonar-project.properties  SonarQube Cloud analysis settings
terraform/              main.tf, alerts.tf, variables.tf, outputs.tf, providers.tf, terraform.tfvars.example
ansible/                playbook.yml, ansible.cfg, inventory.ini.example
k8s/                    namespace, configmap, deployment, service, ingress, secret.example
.github/workflows/deploy.yml
```

## Prerequisites

- AWS account and an IAM user/role that can manage EC2, security groups, key pairs, Elastic IPs, SNS topics and CloudWatch alarms
- AWS CLI configured (`aws configure`), Terraform ≥ 1.5, Docker
- Ansible (`pip install ansible-core`). It needs a Linux/macOS control node, so on Windows use WSL or the Docker command below.
- A GitHub repository with Actions enabled

## 1. AWS and Terraform (one time)

```bash
ssh-keygen -t ed25519 -N "" -f ~/.ssh/agentic-ids       # deploy key — never commit it
cd terraform
cp terraform.tfvars.example terraform.tfvars               # region, instance type, allowed CIDRs
terraform init
terraform fmt -check && terraform validate
terraform plan -out tfplan
terraform apply tfplan
terraform output                                           # public_ip, public_dns, app_url, ssh_command
terraform output -raw ansible_inventory > ../ansible/inventory.ini
```

Defaults: `ap-south-1`, `t3.small`, 20 GB gp3, latest Ubuntu 24.04 AMI. AWS credentials come from your AWS CLI profile or environment and are never stored in the repo.

## 2. Ansible: configure the server and install K3s (one time)

```bash
cd ansible
ansible-playbook playbook.yml --tags setup                 # packages, swap, SSH hardening, K3s, kubectl
ansible-playbook playbook.yml --tags deploy \
  -e app_image=ghcr.io/<owner>/agentic-ids:latest          # optional first deploy (CI normally does this)
```

Windows, via Docker:

```bash
docker run --rm -v "$PWD/..:/work:ro" -v ~/.ssh/agentic-ids:/key:ro -w /work/ansible \
  -e ANSIBLE_CONFIG=/work/ansible/ansible.cfg python:3.12-slim sh -c \
  "apt-get update -qq && apt-get install -y -qq openssh-client && pip install -q ansible-core && \
   mkdir -p /root/.ssh && cp /key /root/.ssh/agentic-ids && chmod 600 /root/.ssh/agentic-ids && \
   ansible-playbook playbook.yml --tags setup"
```

The playbook is idempotent, so re-running it is safe.

## 3. Docker (local build and run)

```bash
docker build -t agentic-ids .
docker run --rm -p 8501:8501 agentic-ids                   # http://localhost:8501
```

## 4. Kubernetes

Ansible copies `k8s/` to the server, substitutes the image, and applies the manifests. To do it by hand on the server:

```bash
kubectl apply -f k8s/namespace.yaml -f k8s/configmap.yaml -f k8s/deployment.yaml \
              -f k8s/service.yaml -f k8s/ingress.yaml
kubectl -n agentic-ids set image deployment/agentic-ids agentic-ids=ghcr.io/<owner>/agentic-ids:<sha>
kubectl -n agentic-ids rollout status deployment/agentic-ids
```

The Deployment runs 1 replica as a non-root user, with readiness and liveness probes on `/_stcore/health`, a 200m/384Mi CPU/memory request and 1.5 CPU/1280Mi limit (sized for t3.small). Traefik, which ships with K3s, routes port 80 to the Service.

## 5. GitHub Actions CI/CD

On every push to `main`:

1. **Validate**: install requirements, byte-compile, run `pytest` with coverage, then a SonarQube Cloud scan. The job fails if the quality gate fails, which blocks the deploy.
2. **Build**: build the Docker image and confirm the container answers `/_stcore/health`
3. **Publish**: push `ghcr.io/<owner>/agentic-ids:<commit-sha>` and `:latest` to GHCR
4. **Deploy**: Ansible (`--tags deploy`) sets the new image and waits for the rollout to finish
5. **Verify**: `curl http://$EC2_HOST/_stcore/health` from the runner. The job fails if the check fails.

Pull requests run steps 1 and 2 only. To roll back, re-run an earlier successful workflow, or run `kubectl -n agentic-ids rollout undo deployment/agentic-ids`.

### Required secrets and variables (Settings → Secrets and variables → Actions)

| Name | Type | Value |
|---|---|---|
| `EC2_HOST` | Variable | `terraform output -raw public_ip` |
| `EC2_SSH_KEY` | Secret | contents of `~/.ssh/agentic-ids` (private key) |
| `GHCR_PULL_TOKEN` | Secret (optional) | PAT with `read:packages`, so the node can re-pull a private image after the job token expires. Not needed if the GHCR package is public. |

| `SONAR_TOKEN` | Secret | SonarQube Cloud token. Until it's set, the scan is skipped with a warning. |

`GITHUB_TOKEN` (built in) is used to push to GHCR, so no AWS keys are needed in GitHub.

## 6. SonarQube Cloud (code quality)

1. Sign in at https://sonarcloud.io with GitHub, then choose **+ → Analyze new project** and import `agentic-ids`.
2. In the project, go to **Administration → Analysis Method** and turn **off Automatic Analysis**, since CI does the analysis.
3. Go to **My Account → Security** and generate a token. Add it as the `SONAR_TOKEN` repository secret.
4. If the organization or project keys differ from the ones in `sonar-project.properties`, update them.

Each push then sends bugs, vulnerabilities, code smells, duplication and test coverage (from `pytest --cov`) to the SonarQube dashboard. The pipeline waits for the quality gate.

## 7. Email alerts (CloudWatch → SNS)

`terraform/alerts.tf` creates:

| Alarm | Fires when | Email |
|---|---|---|
| `agentic-ids-cpu-above-80pct` | Average EC2 CPU > 80% over 5 minutes | ALARM, then OK when it recovers |
| `agentic-ids-status-check-failed` | EC2 instance/system status check fails for 2 minutes | ALARM, then OK |

Set `alert_email` in `terraform.tfvars` and run `terraform apply`. **AWS then emails a confirmation link, and you must click it before any alerts arrive.** It uses free basic EC2 metrics, so there's no agent on the server.

To test without loading the CPU:

```bash
aws cloudwatch set-alarm-state --region ap-south-1 --alarm-name agentic-ids-cpu-above-80pct \
  --state-value ALARM --state-reason "Manual test"
```

To test with real load, run this on the server (high CPU for 6 minutes; the alarm fires within about 10 minutes):

```bash
sudo apt-get install -y stress-ng && stress-ng --cpu 2 --timeout 360s
```

## Public application URL

| | |
|---|---|
| URL | http://13.203.254.194 |
| Health | http://13.203.254.194/_stcore/health → `ok` |
| SSH | `ssh -i ~/.ssh/agentic-ids ubuntu@13.203.254.194` |

## Troubleshooting

```bash
# On the server
kubectl get nodes
kubectl -n agentic-ids get deploy,pods,svc,ingress
kubectl -n agentic-ids describe pod -l app=agentic-ids
kubectl -n agentic-ids logs deploy/agentic-ids --tail=100
kubectl -n kube-system get pods                   # traefik, coredns
sudo systemctl status k3s; sudo journalctl -u k3s -n 100

# From your machine
curl -i http://<EC2_IP>/_stcore/health
```

| Symptom | Likely cause |
|---|---|
| `ImagePullBackOff` | The GHCR package is private and the pull token expired. Make the package public or set `GHCR_PULL_TOKEN`. |
| `OOMKilled` / pod restarts | A very large CSV upload. Use `instance_type = "t3.medium"` and raise the memory limit. |
| 404 from Traefik | The Ingress or Service is missing. Re-run the deploy job. |
| CI deploy step can't SSH | `EC2_HOST`/`EC2_SSH_KEY` is wrong, or `ssh_allowed_cidrs` excludes GitHub runners. |

## Cleanup

```bash
cd terraform
terraform destroy          # removes the EC2 instance, Elastic IP, security group, key pair, alarms and SNS topic
```

You can also delete the `agentic-ids` package under GitHub → Packages.

## Security trade-offs and limitations

- **HTTP only.** There's no domain or TLS, to avoid extra cost and services. Don't upload sensitive data.
- **SSH (22) is open to 0.0.0.0/0** because GitHub-hosted runners deploy from changing IPs. Password and root login are disabled, and access is key-only. For manual-only deploys, set `ssh_allowed_cidrs = ["<your-ip>/32"]`.
- Only ports **22** and **80** are open. The Kubernetes API (6443) isn't reachable from the internet.
- **Tests:** the repo had none originally. `tests/test_smoke.py` checks that the agent pipeline runs end to end on synthetic data. It doesn't measure detection accuracy.
- `main.py` isn't part of the deployment. It calls `utils.preprocess.load_data`, which doesn't exist, and expects a local `data/` folder.
- **Cost:** about US$0.7/day (t3.small + 20 GB gp3 + public IPv4 in ap-south-1). Run `terraform destroy` after the demo.
