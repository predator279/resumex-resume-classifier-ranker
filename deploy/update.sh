#!/usr/bin/env bash
# deploy/update.sh
# ─────────────────────────────────────────────────────────────────────────────
# ResumeX — Zero-downtime update script
#
# Run this on your EC2 instance whenever you push new code to GitHub.
#
# Usage (from EC2 terminal):
#   cd ~/resumex-resume-classifier-ranker
#   bash deploy/update.sh
#
# Or from your local machine (one-liner):
#   ssh -i resumex-key.pem ec2-user@<ec2-ip> "cd resumex-resume-classifier-ranker && bash deploy/update.sh"
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

CONTAINER_NAME="resumex"
IMAGE_NAME="resumex"

echo ""
echo "========================================================"
echo "  ResumeX Update"
echo "  $(date)"
echo "========================================================"

# ── 1. Pull latest code ───────────────────────────────────────────────────────
echo ""
echo ">>> Pulling latest code from GitHub …"
git pull origin main

# ── 2. Run with Docker Compose ───────────────────────────────────────────────
echo ""
echo ">>> Replacing containers (Zero-downtime recreation if needed) …"
sudo docker compose up -d --build

# ── 4. Verify ─────────────────────────────────────────────────────────────────
echo ""
echo ">>> Waiting 15 seconds for startup …"
sleep 15

echo ">>> Health check …"
for i in $(seq 1 6); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health || echo "000")
  if [ "$STATUS" = "200" ]; then
    echo "    ✅ Health check passed!"
    curl -s http://localhost/health
    break
  else
    echo "    Attempt $i: HTTP $STATUS — waiting 10s …"
    sleep 10
  fi
done

echo ""
echo ">>> Update complete. Container logs (last 20 lines):"
sudo docker logs --tail 20 "$CONTAINER_NAME"
echo ""
echo "========================================================"
echo "  Done!"
echo "========================================================"
