#!/usr/bin/env bash
# deploy/setup_ec2.sh
# ─────────────────────────────────────────────────────────────────────────────
# ResumeX — EC2 Bootstrap Script
#
# Run this ONCE on a fresh Amazon Linux 2023 t2.micro instance.
# It will:
#   1. Create 2 GB swap space  (prevents OOM on 1 GB RAM instance)
#   2. Install Docker + Git
#   3. Clone the repo
#   4. Build the Docker image
#   5. Run the container (port 80 → 8000, models volume mounted)
#
# Usage:
#   ssh -i resumex-key.pem ec2-user@<your-ec2-public-ip>
#   bash setup_ec2.sh
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

REPO_URL="https://github.com/predator279/resumex-resume-classifier-ranker.git"
REPO_DIR="resumex-resume-classifier-ranker"
CONTAINER_NAME="resumex"
IMAGE_NAME="resumex"

echo ""
echo "========================================================"
echo "  ResumeX EC2 Setup"
echo "========================================================"
echo ""

# ── 1. Swap space (2 GB) ──────────────────────────────────────────────────────
echo ">>> Creating 2 GB swap space on /swapfile …"
if [ ! -f /swapfile ]; then
  sudo dd if=/dev/zero of=/swapfile bs=128M count=16   # 128M × 16 = 2048 MB
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab
  echo "    Swap created and enabled."
else
  echo "    /swapfile already exists — skipping."
fi

free -h

# ── 2. Install Docker + Git ───────────────────────────────────────────────────
echo ""
echo ">>> Installing Docker and Git …"
sudo yum update -y
sudo yum install -y docker git

echo ">>> Starting Docker service …"
sudo systemctl start docker
sudo systemctl enable docker

# Add ec2-user to the docker group so we don't need sudo for docker commands
sudo usermod -aG docker ec2-user
echo "    NOTE: You may need to log out and back in for group changes to take effect."
echo "    For this script, we will use 'sudo' for docker commands."

# ── 3. Clone repo ────────────────────────────────────────────────────────────
echo ""
echo ">>> Cloning repository …"
if [ -d "$REPO_DIR" ]; then
  echo "    Repo already cloned — pulling latest …"
  cd "$REPO_DIR"
  git pull origin main
  cd ..
else
  git clone "$REPO_URL"
fi

cd "$REPO_DIR"

# ── 4. Build Docker image ────────────────────────────────────────────────────
echo ""
echo ">>> Building Docker image (this may take 5-10 minutes on first run) …"
sudo docker build -t "$IMAGE_NAME" .

# ── 5. Stop any existing container ───────────────────────────────────────────
echo ""
echo ">>> Stopping existing container (if any) …"
sudo docker stop "$CONTAINER_NAME" 2>/dev/null || true
sudo docker rm   "$CONTAINER_NAME" 2>/dev/null || true

# ── 6. Run the container ─────────────────────────────────────────────────────
echo ""
echo ">>> Starting ResumeX container …"
sudo docker run -d \
  --name "$CONTAINER_NAME" \
  -p 80:8000 \
  -v resumex-models:/root/.cache/huggingface \
  --restart unless-stopped \
  "$IMAGE_NAME"

# ── 7. Wait and verify ───────────────────────────────────────────────────────
echo ""
echo ">>> Waiting for container to start (models may download for ~90 seconds) …"
sleep 15

echo ">>> Container status:"
sudo docker ps --filter "name=$CONTAINER_NAME"

echo ""
echo ">>> Health check (retrying up to 12 times with 10s intervals) …"
for i in $(seq 1 12); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health || echo "000")
  if [ "$STATUS" = "200" ]; then
    echo "    ✅ Health check passed! (attempt $i)"
    curl -s http://localhost/health | python3 -m json.tool
    break
  else
    echo "    Attempt $i: HTTP $STATUS — waiting 10s …"
    sleep 10
  fi
done

echo ""
echo "========================================================"
echo "  Setup complete!"
echo "  Your app is live at: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
echo "  Health endpoint:     http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)/health"
echo "========================================================"
