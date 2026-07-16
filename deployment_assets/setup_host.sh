#!/bin/bash
# ==============================================================================
# SRVS V4 Host VM Initialization & Docker GPU Setup Script (Ubuntu 24.04 LTS)
# ==============================================================================
# This script automates the installation of:
# 1. Docker Engine & Docker Compose
# 2. NVIDIA Container Toolkit (for GPU pass-through)
# ==============================================================================

# Exit immediately if a command exits with a non-zero status
set -e

echo "[SYSTEM] Starting Host VM initialization..."

# 1. Update and Upgrade System Packages
echo "[SYSTEM] Updating system repositories..."
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install Essential Tools
echo "[SYSTEM] Installing utility packages..."
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release git

# 3. Install Docker Engine
echo "[SYSTEM] Installing Docker and Docker-Compose..."
sudo apt-get install -y docker.io docker-compose

# Start and enable Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add ubuntu user to the docker group so you don't need 'sudo' for docker commands
sudo usermod -aG docker ubuntu

# 4. Install NVIDIA Container Toolkit (Enables GPU pass-through inside Docker)
echo "[SYSTEM] Adding NVIDIA Container Toolkit repository..."
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

echo "[SYSTEM] Installing nvidia-container-toolkit..."
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure Docker daemon to support the nvidia runtime
echo "[SYSTEM] Configuring Docker with NVIDIA runtime..."
sudo nvidia-container-toolkit-toolkit-setup
sudo systemctl restart docker

echo "=============================================================================="
echo "[SUCCESS] Host environment setup completed successfully!"
echo "[INFO] IMPORTANT: Please log out of your SSH session and log back in (or run "
echo "       'newgrp docker') to apply the docker group permissions without sudo."
echo "=============================================================================="
