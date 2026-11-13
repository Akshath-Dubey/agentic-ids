# Agentic IDS — Smart Grid Intrusion Detection

A multi-agent intrusion detection system with a Streamlit dashboard. Upload CICIDS-format CSV files and five cooperating agents process them:

| Agent | File | Role |
|---|---|---|
| Monitoring | `agents/monitoring_agent.py` | Ingests and summarises traffic |
| Detection | `agents/detection_agent.py` | Classifies flows (XGBoost, falls back to HistGradientBoosting) |
| Decision | `agents/decision_agent.py` | Applies the sensitivity threshold |
| Response | `agents/response_agent.py` | Chooses mitigation actions |
| Learning | `agents/learning_agent.py` | Retrains on new data ("Auto Learn") |

## Live endpoints (AWS ap-south-1)

| Service | URL | Access |
|---|---|---|
| **Agentic IDS dashboard** | http://13.203.254.194 | Public |
| Grafana | http://15.252.117.69:3000 | `admin` / `ansible/credentials/grafana_admin_password` |
| SonarQube | http://15.252.117.69:9000 | `admin` / `ansible/credentials/sonar_admin_password` + `#Aa1` |
| Prometheus | http://15.252.117.69:9090 | Admin IPs only (`admin_cidrs`) |
| Alertmanager | http://15.252.117.69:9093 | Admin IPs only (`admin_cidrs`) |

## Architecture

```
                 git push (main)
                       │
                       ▼
  GitHub Actions: pytest + coverage ─► SonarQube scan + quality gate ─► docker build + health check
                                         (tools server :9000)              │
                                                                           ▼
                                                              push ghcr.io/<owner>/agentic-ids:<sha>
                                                                           │
                                                                Ansible over SSH (rollout)
                                                                           ▼
 ┌──────────────────────── AWS default VPC, ap-south-1 ─────────────────────────────────────────┐
 │                                                                                              │
 │   K3s cluster (security group "agentic-ids-sg")                                             │
 │   ┌──────────────────────────────┐      private network     ┌─────────────────────────────┐  │
 │   │ agentic-ids  (t3.small)      │◄── 6443 / 8472 / 10250 ─►│ agentic-ids-worker-1        │  │
 │   │ K3s server (control plane)   │                          │ (t3.small) K3s agent        │  │
 │   │ Traefik :80  ─► app pod #1   │                          │ Traefik :80 ─► app pod #2   │  │
 │   │ kube-state-metrics :30080    │                          │                             │  │
 │   │ node_exporter :9100          │                          │ node_exporter :9100         │  │
 │   └──────────────▲───────────────┘                          └──────────────▲──────────────┘  │
 │      Elastic IP  │ 13.203.254.194                                          │                 │
 │                  │                 scrape 9100 / 30080, probe :80          │                 │
 │   ┌──────────────┴─────────────────────────────────────────────────────────┴──────────────┐  │
 │   │ agentic-ids-tools (c7i-flex.large, 4 GiB) — Docker Compose          EIP 15.252.117.69 │  │
 │   │ Prometheus :9090 ─► Alertmanager :9093 ─► email (Gmail SMTP)                          │  │
 │   │ Grafana :3000   Blackbox exporter   SonarQube :9000 + PostgreSQL   node_exporter      │  │
 │   └───────────────────────────────────────────────────────────────────────────────────────┘  │
 └──────────────────────────────────────────────────────────────────────────────────────────────┘
        Browser ─► http://13.203.254.194 ─► Traefik ─► Service (sticky cookie) ─► one of 2 pods
```

## Technology stack

| Layer | Tool | Location |
|---|---|---|
| Cloud | AWS: 3× EC2 (Ubuntu 24.04), 2 security groups, key pair, 2 Elastic IPs, default VPC | `terraform/` |
| Infrastructure as code | Terraform | `terraform/` |
| Configuration management | Ansible: hardening, swap, node_exporter, K3s server + agent, monitoring stack, SonarQube bootstrap, app rollout | `ansible/` |
| Container | Docker: `python:3.12-slim`, non-root, `streamlit run app.py` on :8501 | `Dockerfile` |
| Orchestration | Kubernetes (K3s): 2 nodes, app with 2 replicas | `k8s/` |
| CI/CD | GitHub Actions + GitHub Container Registry | `.github/workflows/deploy.yml` |
| Code quality | SonarQube Community (self-hosted on AWS), quality gate blocks deploys | `sonar-project.properties` |
| Metrics | Prometheus + node_exporter + kube-state-metrics + blackbox exporter | `ansible/monitoring/` |
| Dashboards | Grafana ("Agentic IDS - Overview", "Node Exporter Full") | `ansible/monitoring/grafana/` |
| Alerts | Prometheus rules → Alertmanager → email | `ansible/monitoring/alert-rules.yml` |

### The three instances

| Name | Type | Role | Why it's separate |
|---|---|---|---|
| `agentic-ids` | t3.small (2 vCPU, 2 GiB) | K3s server: control plane, Traefik, one app replica | Holds the public dashboard IP |
| `agentic-ids-worker-1` | t3.small (2 vCPU, 2 GiB) | K3s agent: second app replica | If one node fails, the app keeps running on the other, and load is spread across both |
| `agentic-ids-tools` | c7i-flex.large (2 vCPU, 4 GiB) | Prometheus, Alertmanager, Grafana, SonarQube | Monitoring must stay up when the cluster is down, and SonarQube needs ~2 GiB that would starve the app |

The tools server uses c7i-flex.large because this AWS account is on the Free Tier plan, which blocks t3.medium. On a normal account, `tools_instance_type = "t3.medium"` is cheaper.

## Repository structure

```
app.py                     Streamlit dashboard (the deployed entry point)
main.py                    Offline training script (not used by the deployment)
agents/                    The five agents
utils/preprocess.py        Feature preprocessing
models/model.pkl           Saved model (not loaded by app.py)
tests/test_smoke.py        End-to-end agent pipeline smoke test
Dockerfile, .dockerignore, .streamlit/config.toml
sonar-project.properties   SonarQube analysis settings
terraform/
  main.tf                  K3s server + worker instances, cluster security group, Elastic IP
  tools.tf                 Tools instance, its security group and Elastic IP
  alerts.tf                Optional CloudWatch/SNS alarms (enable_cloudwatch_alerts)
  variables.tf, outputs.tf, providers.tf, terraform.tfvars.example
ansible/
  playbook.yml             Common setup, K3s server, K3s agents, monitoring stack, app deploy
  monitoring/              Compose file, Prometheus config + alert rules, Alertmanager, Grafana
  ansible.cfg, inventory.ini.example
k8s/
  namespace, configmap, deployment (2 replicas), service (sticky), ingress, secret.example
  monitoring/kube-state-metrics.yaml
.github/workflows/deploy.yml
```

## Prerequisites

- An AWS account and an IAM user that can manage EC2, security groups, key pairs and Elastic IPs. It also needs SNS and CloudWatch permissions, but only for the optional CloudWatch alarms.
- AWS CLI configured, Terraform ≥ 1.5, Docker
- Ansible (`pip install ansible-core`). It needs a Linux/macOS control node, so on Windows use WSL or the Docker command below.
- A GitHub repository with Actions enabled, and the `gh` CLI for setting secrets

## 1. Terraform: provision the 3 instances

```bash
ssh-keygen -t ed25519 -N "" -f ~/.ssh/agentic-ids       # deploy key — never commit it
cd terraform
cp terraform.tfvars.example terraform.tfvars               # set alert_email, admin_cidrs = ["<your-ip>/32"]
terraform init
terraform fmt -check && terraform validate
terraform plan -out tfplan
terraform apply tfplan
terraform output                                           # app_url, grafana_url, sonarqube_url, ...
terraform output -raw ansible_inventory > ../ansible/inventory.ini
```

## 2. Ansible: configure everything

```bash
cd ansible
export ALERT_SMTP_PASSWORD='<gmail app password>'          # optional: enables alert emails
ansible-playbook playbook.yml --tags setup                 # all 3 servers, K3s cluster, monitoring, SonarQube
ansible-playbook playbook.yml --tags deploy \
  -e app_image=ghcr.io/<owner>/agentic-ids:latest          # first deploy (CI does this afterwards)
```

What each play does:

1. **All instances**: package updates, key-only SSH, swap (2 GB, or 4 GB on tools), and node_exporter as a systemd service.
2. **K3s server**: installs K3s, sets up kubectl access, and reads the join token and version.
3. **K3s agents**: install the same K3s version and join over the private IP (`https://<server-private-ip>:6443`).
4. **Cluster checks**: wait until every node is Ready, label the workers, check Traefik, and deploy kube-state-metrics.
5. **Deploy** (`--tags deploy`): apply the manifests with the new image and wait for both replicas to roll out.
6. **Tools**: Docker and Compose, the kernel settings SonarQube needs, then Prometheus, Alertmanager, blackbox exporter, Grafana (with provisioned dashboards), SonarQube and PostgreSQL. Finally it sets the SonarQube admin password and creates a CI token.

Passwords are generated on the first run and saved to `ansible/credentials/`, which is git-ignored. The SonarQube CI token is saved to `credentials/sonar_token`.

Windows, via Docker (run from the repo root):

```bash
docker run --rm -v "$PWD:/work" -v ~/.ssh/agentic-ids:/key:ro -w /work/ansible \
  -e ANSIBLE_CONFIG=/work/ansible/ansible.cfg -e ALERT_SMTP_PASSWORD python:3.12-slim sh -c \
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

- **2 replicas**, spread across the two nodes with `topologySpreadConstraints`.
- **Sticky sessions**: Streamlit keeps each user's session in the memory of one pod. The Service's Traefik annotation sets an `ids_affinity` cookie, so a browser's WebSocket and file uploads always reach the same pod.
- **Rolling updates** with `maxUnavailable: 0`, so a deploy never takes the app offline.
- **Probes**: startup, readiness and liveness probes on `/_stcore/health`. The pods run non-root with seccomp and drop all capabilities.
- **Resources**: each pod requests 200m CPU / 384Mi and is limited to 1.5 CPU / 1280Mi.
- **Routing**: Traefik (bundled with K3s) listens on port 80 on both nodes. The Elastic IP points at the server node.

Manual commands, run on the server:

```bash
kubectl get nodes -o wide
kubectl -n agentic-ids get pods -o wide                    # one pod per node
kubectl -n agentic-ids set image deployment/agentic-ids agentic-ids=ghcr.io/<owner>/agentic-ids:<sha>
kubectl -n agentic-ids rollout status deployment/agentic-ids
kubectl -n agentic-ids rollout undo deployment/agentic-ids # rollback
```

## 5. GitHub Actions CI/CD

On every push to `main`:

1. **Validate**: install requirements, byte-compile, and run `pytest` with coverage. Then the **SonarQube scan** runs, and the job fails if the quality gate fails, which blocks the deploy.
2. **Build**: build the Docker image and confirm the container answers `/_stcore/health`.
3. **Publish**: push `ghcr.io/<owner>/agentic-ids:<commit-sha>` and `:latest` to GHCR.
4. **Deploy**: Ansible (`--tags deploy`) on the K3s server rolls the new image out to both nodes.
5. **Verify**: `curl http://$EC2_HOST/_stcore/health` from the runner. The job fails if the check fails.

Pull requests run steps 1 and 2 only.

### Secrets and variables (Settings → Secrets and variables → Actions)

| Name | Type | Value |
|---|---|---|
| `EC2_HOST` | Variable | `terraform output -raw public_ip` |
| `SONAR_HOST_URL` | Variable | `terraform output -raw sonarqube_url` |
| `EC2_SSH_KEY` | Secret | contents of `~/.ssh/agentic-ids` (private key) |
| `SONAR_TOKEN` | Secret | contents of `ansible/credentials/sonar_token` |
| `GHCR_PULL_TOKEN` | Secret (optional) | PAT with `read:packages`. Lets nodes re-pull a private image later. Not needed if the GHCR package is public. |

```bash
gh variable set SONAR_HOST_URL --body "$(terraform -chdir=terraform output -raw sonarqube_url)"
gh secret set SONAR_TOKEN < ansible/credentials/sonar_token
```

## 6. SonarQube

SonarQube Community runs self-hosted on the tools server at http://15.252.117.69:9000, backed by PostgreSQL. Each CI run uploads the code and `coverage.xml` to project `agentic-ids`, then waits for the **Sonar way** quality gate. The dashboard shows bugs, vulnerabilities, security hotspots, code smells, duplication and coverage.

## 7. Monitoring and alerts

**Prometheus** scrapes every 15s:

| Job | Source | What it shows |
|---|---|---|
| `node` | node_exporter on all 3 instances | CPU, memory, disk, network |
| `kube-state-metrics` | NodePort 30080 on the cluster | Deployment replicas, pod restarts, which node each pod is on |
| `app` | Blackbox probe of http://13.203.254.194/_stcore/health | Public uptime and response time |
| `app_nodes` | Blackbox probe of each node's Traefik | Whether each node serves the app |

**Grafana** provisions two dashboards automatically:
- **Agentic IDS - Overview** (the home dashboard): app up/down, instances up, replicas available, firing alerts, CPU per instance with the 80% line, memory, response time, network, pod restarts, and which node each pod is on.
- **Node Exporter Full**: the standard community dashboard, with detailed per-host metrics.

**Alert rules** (`ansible/monitoring/alert-rules.yml`) go to Alertmanager, which sends email:

| Alert | Condition |
|---|---|
| `HighCPUUsage` | CPU > **80%** for 5 minutes on any instance |
| `HighMemoryUsage` | Memory > 90% for 5 minutes |
| `DiskSpaceLow` | Less than 10% free on `/` |
| `InstanceDown` | node_exporter unreachable for 2 minutes |
| `AppEndpointDown` | Public dashboard failing health checks for 2 minutes |
| `AppReplicasUnavailable` | Fewer available replicas than desired for 5 minutes |
| `PodRestartingOften` | More than 3 restarts in 15 minutes |

**Enable email:** create a Gmail [App Password](https://myaccount.google.com/apppasswords) (needs 2-Step Verification) for the `alert_email` account, then:

```bash
printf '%s' '<16-char app password>' > ansible/credentials/smtp_password
ansible-playbook playbook.yml --tags monitoring
```

Alerts also show up in Grafana, Prometheus (`/alerts`) and Alertmanager without email.

**Demo: trigger the CPU alert.** Run this on any instance. The alert goes *pending* after about 1 minute and *firing* (and emails) after 5:

```bash
sudo apt-get install -y stress-ng && stress-ng --cpu 2 --timeout 420s
```

## Troubleshooting

```bash
# K3s server
kubectl get nodes -o wide
kubectl -n agentic-ids get deploy,pods,svc,ingress -o wide
kubectl -n agentic-ids logs -l app=agentic-ids --tail=100
sudo journalctl -u k3s -n 100            # on the worker: sudo journalctl -u k3s-agent -n 100

# Tools server
cd /opt/monitoring && sudo docker compose ps
sudo docker compose logs --tail=100 sonarqube   # or prometheus, grafana, alertmanager

# From your machine
curl -i http://13.203.254.194/_stcore/health
```

| Symptom | Likely cause |
|---|---|
| Worker `NotReady` | Security group self-rule missing, or the token/version is wrong. Check `journalctl -u k3s-agent`. |
| File upload fails or the session resets | Sticky cookie blocked. Check the `ids_affinity` cookie and the Service annotations. |
| `ImagePullBackOff` on a node | Private GHCR package and the pull token expired. Make the package public or set `GHCR_PULL_TOKEN`. |
| SonarQube container exits | Low memory or `vm.max_map_count`. Re-run `--tags monitoring` and check `docker compose logs sonarqube`. |
| CI SonarQube step times out | The tools server is down, or `SONAR_HOST_URL`/`SONAR_TOKEN` is wrong. |
| No alert emails | No SMTP password set, or the Gmail App Password is wrong. Check `docker compose logs alertmanager`. |

## Cleanup

```bash
cd terraform
terraform destroy      # removes all 3 instances, Elastic IPs, security groups and the key pair
```

You can also delete the `agentic-ids` package under GitHub → Packages.

## Security trade-offs and limitations

- **HTTP only.** No domain or TLS, to avoid extra cost. Grafana and SonarQube logins travel unencrypted, so use generated passwords and don't reuse them.
- **SSH (22) is open to 0.0.0.0/0** because GitHub-hosted runners deploy from changing IPs. Access is key-only, with password and root login disabled.
- **SonarQube (9000) is public**, because CI runners must reach it. It requires login, and the default admin password is replaced automatically.
- **Prometheus and Alertmanager** have no login, so they're limited to `admin_cidrs`.
- **Cluster ports stay private.** The K3s API (6443), kubelet, flannel, node_exporter and kube-state-metrics accept traffic only from inside the cluster or tools security groups.
- **Single control plane.** The worker adds app redundancy, but if the server node goes down, the cluster can't be managed until it returns. A highly available control plane would need 3 server nodes.
- **Tests:** `tests/test_smoke.py` checks that the agent pipeline runs end to end on synthetic data. It doesn't measure detection accuracy.
- `main.py` isn't part of the deployment. It calls `utils.preprocess.load_data`, which doesn't exist.
- **Cost:** about US$3.6/day (2× t3.small + c7i-flex.large + 70 GB gp3 + 3 public IPv4). Run `terraform destroy` after the demo.
