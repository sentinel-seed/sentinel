#!/bin/bash
# ROS2 Installation Script for WSL2 (Ubuntu 24.04 / 22.04)
# Run this script inside WSL: bash install_ros2_wsl.sh

set -e

echo "=============================================="
echo "Sentinel ROS2 - Installation Script for WSL2"
echo "=============================================="

# Detect Ubuntu version
UBUNTU_VERSION=$(lsb_release -rs)
echo "Detected Ubuntu version: $UBUNTU_VERSION"

# Set ROS2 distro based on Ubuntu version
if [[ "$UBUNTU_VERSION" == "24.04" ]]; then
    ROS_DISTRO="jazzy"
elif [[ "$UBUNTU_VERSION" == "22.04" ]]; then
    ROS_DISTRO="humble"
else
    echo "Warning: Ubuntu $UBUNTU_VERSION not officially supported."
    echo "Attempting to use humble (may not work)..."
    ROS_DISTRO="humble"
fi

echo "Using ROS2 distro: $ROS_DISTRO"
echo ""

# Step 1: Setup locale
echo "[1/6] Setting up locale..."
sudo apt update && sudo apt install -y locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# Step 2: Setup sources
echo "[2/6] Setting up ROS2 sources..."
sudo apt install -y software-properties-common curl
sudo add-apt-repository universe -y

# Add ROS2 GPG key
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg

# Add repository to sources list
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# Step 3: Install ROS2
echo "[3/6] Installing ROS2 $ROS_DISTRO..."
sudo apt update
sudo apt install -y ros-${ROS_DISTRO}-ros-base

# Step 4: Install additional packages
echo "[4/6] Installing ROS2 packages..."
sudo apt install -y \
    ros-${ROS_DISTRO}-geometry-msgs \
    ros-${ROS_DISTRO}-std-msgs \
    python3-pip \
    python3-colcon-common-extensions

# Step 5: Install sentinelseed
echo "[5/6] Installing sentinelseed..."
pip3 install --upgrade sentinelseed

# Step 6: Setup environment
echo "[6/6] Setting up environment..."

# Add ROS2 setup to bashrc if not already present
if ! grep -q "source /opt/ros/${ROS_DISTRO}/setup.bash" ~/.bashrc; then
    echo "" >> ~/.bashrc
    echo "# ROS2 ${ROS_DISTRO}" >> ~/.bashrc
    echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> ~/.bashrc
fi

# Source for current session
source /opt/ros/${ROS_DISTRO}/setup.bash

echo ""
echo "=============================================="
echo "Installation complete!"
echo "=============================================="
echo ""
echo "ROS2 $ROS_DISTRO installed successfully."
echo ""
echo "To use ROS2 in a new terminal, run:"
echo "  source /opt/ros/${ROS_DISTRO}/setup.bash"
echo ""
echo "Or restart your terminal (bashrc was updated)."
echo ""
echo "To test the Sentinel ROS2 integration, run:"
echo "  python3 -m sentinelseed.integrations.ros2.scripts.test_ros2_real"
echo ""
