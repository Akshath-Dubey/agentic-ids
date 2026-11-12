# Agentic IDS — AWS Deployment

```
GitHub push (main) ─► GitHub Actions: validate ─► docker build + startup check ─► push to GHCR
                                                                                     │
                     http://<EC2_IP> ◄── Traefik ingress ◄── K3s on EC2 ◄── Ansible deploy (SSH)
```

| Layer | Tool | Location |
|---|---|---|
| Infrastructure (1× EC2, SG, key pair, Elastic IP in default VPC) | Terraform | `terraform/` |
| Server config (packages, SSH hardening, K3s, kubectl) + app rollout | Ansible | `ansible/playbook.yml` |
| Container image (`streamlit run app.py` on :8501) | Docker | `Dockerfile` |
| Namespace, ConfigMap, Deployment, Service, Ingress | Kubernetes (K3s) | `k8s/` |
| Test → build → push → deploy | GitHub Actions | `.github/workflows/deploy.yml` |

Exposed ports: **22** (SSH, key-only) and **80** (dashboard). The K3s API (6443) is not reachable from the internet.

## 1. Provision (one time)

```bash
ssh-keygen -t ed25519 -N "" -f ~/.ssh/agentic-ids      # deploy key (never commit it)
cd terraform
cp terraform.tfvars.example terraform.tfvars              # adjust if needed
terraform init && terraform plan -out tfplan
terraform apply tfplan
terraform output -raw ansible_inventory > ../ansible/inventory.ini
```

## 2. Configure the server (one time)

Ansible needs a Linux/macOS control node (on Windows use WSL or the Docker one-liner below).

```bash
cd ansible
ansible-playbook playbook.yml --tags setup
# Windows via Docker:
# docker run --rm -it -v "$PWD/..:/work" -v ~/.ssh:/root/.ssh:ro -w /work/ansible \
#   -e ANSIBLE_CONFIG=/work/ansible/ansible.cfg python:3.12-slim \
#   sh -c "pip install -q ansible-core && ansible-playbook playbook.yml --tags setup"
```

## 3. CI/CD settings (GitHub repo → Settings → Secrets and variables → Actions)

| Name | Type | Value |
|---|---|---|
| `EC2_HOST` | Variable | `terraform output -raw public_ip` |
| `EC2_SSH_KEY` | Secret | contents of `~/.ssh/agentic-ids` (private key) |
| `GHCR_PULL_TOKEN` | Secret (optional) | PAT with `read:packages`, lets the node re-pull a private image later. Not needed if the GHCR package is public. |

Every push to `main` then runs: tests → image build → container health check → push `ghcr.io/<owner>/agentic-ids:<sha>` and `:latest` → Ansible deploy → public health check. Pull requests run validation and build only.

Rollback: re-run an earlier successful workflow run, or on the server
`kubectl -n agentic-ids rollout undo deployment/agentic-ids`.

## Notes and limitations

- **HTTP only.** No domain or TLS, to keep the demo free of extra cost and services. Don't upload sensitive data.
- **SSH is open to 0.0.0.0/0** because GitHub-hosted runners deploy from changing IPs. Password and root login are disabled; access is key-only. For manual-only deploys set `ssh_allowed_cidrs = ["<your-ip>/32"]`.
- **Tests:** the repo had none. `tests/test_smoke.py` checks that the agent pipeline runs end to end on synthetic data. It doesn't measure detection accuracy.
- `main.py` (CLI training script) isn't part of the deployment. It calls `utils.preprocess.load_data`, which doesn't exist, and expects a local `data/` folder.
- `models/model.pkl` is copied into the image but isn't loaded by any code: the dashboard trains its agents on the uploaded CSVs.
- **Cost:** t3.small plus 20 GB gp3 plus a public IPv4 costs roughly US$0.7/day in ap-south-1. Run `terraform destroy` after the demo.
