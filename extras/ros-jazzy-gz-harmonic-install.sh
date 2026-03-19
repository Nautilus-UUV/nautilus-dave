#!/bin/bash
# Script to install development tools and libraries for robotics and simulation
echo
echo -e "\033[94m============================================================\033[0m"
echo -e "\033[94m== One-liner Installation Script for ROS-Gazebo Framework ==\033[0m"
echo -e "\033[94m============================================================\033[0m"
echo -e "Requirements: Ubuntu 24.04 LTS Noble"
echo -e "\033[94m============================================================\033[0m"

echo
echo -e "\033[96m(1/4) -------------    Updating the System  ----------------\033[0m"
echo "Performing full system upgrade (this might take a while)..."
sudo sudo apt update && apt full-upgrade -y

echo
echo -e "\033[96m(2/4) ------------    Install Dependencies   ---------------\033[0m"
echo -e "\033[34mInstalling essential tools and libraries...\033[0m"
sudo apt install -y \
    build-essential \
    cmake \
    cppcheck \
    curl \
    git \
    gnupg \
    libeigen3-dev \
    libgles2-mesa-dev \
    lsb-release \
    pkg-config \
    protobuf-compiler \
    python3-dbg \
    python3-pip \
    python3-venv \
    qtbase5-dev \
    ruby \
    software-properties-common \
    sudo \
    cppzmq-dev \
    wget

echo
echo -e "\033[96m(3/4) ------------    Install Package Keys   ---------------\033[0m"
echo -e "\033[34mInstalling Signing Keys for ROS and Gazebo...\033[0m"
# Remove keyring if exists to avoid conflicts
sudo rm -f /usr/share/keyrings/ros2-latest-archive-keyring.gpg && \
    sudo rm -rf /etc/apt/sources.list.d/ros2-latest.list
# Get Keys
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
    -o /usr/share/keyrings/ros-archive-keyring.gpg
sudo wget https://packages.osrfoundation.org/gazebo.gpg \
    -O /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg

sudo apt update && sudo apt install -y jq
UBUNTU_CODENAME=noble && \
    ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | jq -r '.tag_name') && \
    curl -L -o /tmp/ros2-apt-source.deb \
    "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.${UBUNTU_CODENAME}_all.deb" && \
    sudo apt-get install -y /tmp/ros2-apt-source.deb && \
    rm -f /tmp/ros2-apt-source.deb

sudo curl https://packages.osrfoundation.org/gazebo.gpg --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null

echo
echo -e "\033[96m(4/4) ------------     Install ROS-Gazebo    ---------------\033[0m"
DIST=jazzy
GAZEBO=gz-harmonic

echo -e "\033[34mInstalling ROS Gazebo framework...\033[0m"
sudo apt update && sudo apt install -y \
    python3-rosdep \
    python3-rosinstall-generator \
    python3-colcon-core \
    python3-colcon-common-extensions \
    python3-vcstool \
    $GAZEBO \
    ros-$DIST-desktop-full \
    ros-$DIST-ros-gz \
    ros-$DIST-gz-ros2-control \
    ros-$DIST-effort-controllers \
    ros-$DIST-geographic-info \
    ros-$DIST-joint-state-publisher \
    ros-$DIST-joy-teleop \
    ros-$DIST-key-teleop \
    ros-$DIST-moveit-planners \
    ros-$DIST-moveit-simple-controller-manager \
    ros-$DIST-moveit-ros-visualization \
    ros-$DIST-robot-localization \
    ros-$DIST-ros2-controllers \
    ros-$DIST-teleop-tools \
    ros-$DIST-urdfdom-py \
    ros-$DIST-marine-acoustic-msgs \
    ros-dev-tools

echo
echo -e "\033[96m(4/4) ------------     Install Ardusub    ---------------\033[0m"
sudo apt update && sudo apt install -y \
    libgz-sim8-dev rapidjson-dev libopencv-dev \
    libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
    gstreamer1.0-plugins-bad gstreamer1.0-libav gstreamer1.0-gl \
    ffmpeg python3-venv python3-websockets \
    ros-${DIST}-joy-linux gstreamer1.0-tools gstreamer1.0-plugins-good gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-ugly python3-gi python3-gst-1.0 \
    libfuse2 libxcb-xinerama0 libxkbcommon-x11-0 libxcb-cursor-dev

# Install ardusub(local)
sudo mkdir -p /opt/ardusub_ws && cd /opt/ardusub_ws || exit
sudo wget https://raw.githubusercontent.com/IOES-Lab/dave/ros2/extras/ardusub-ubuntu-install.sh
sudo chmod +x ardusub-ubuntu-install.sh && sudo bash ./ardusub-ubuntu-install.sh

# Mavros install
sudo apt-get -y install ros-jazzy-mavros*
sudo mkdir -p /opt/mavros_ws && cd /opt/mavros_ws || exit
sudo wget https://raw.githubusercontent.com/mavlink/mavros/master/mavros/scripts/install_geographiclib_datasets.sh
sudo chmod +x install_geographiclib_datasets.sh && sudo bash ./install_geographiclib_datasets.sh

# Environment variables setup (add to the user's shell rc file)
RC_FILE="$HOME/.bashrc"
if [ -n "$ZSH_VERSION" ] || [ "$(basename -- "${SHELL:-}")" = "zsh" ]; then
    RC_FILE="$HOME/.zshrc"
fi
echo "source /opt/ros/jazzy/setup.bash" >> "$RC_FILE" && \
echo "export PATH=/opt/ardusub_ws/ardupilot/Tools/autotest:\$PATH" >> "$RC_FILE" && \
echo "export PATH=/opt/ardusub_ws/ardupilot/build/sitl/bin:\$PATH" >> "$RC_FILE" && \
echo "export GEOGRAPHICLIB_GEOID_PATH=/usr/share/GeographicLib/geoids" >> "$RC_FILE" && \
echo "export GZ_SIM_SYSTEM_PLUGIN_PATH=/opt/ardusub_ws/ardupilot_gazebo/build:\$GZ_SIM_SYSTEM_PLUGIN_PATH" >> "$RC_FILE" && \
echo "export GZ_SIM_RESOURCE_PATH=/opt/ardusub_ws/ardupilot_gazebo/models:/opt/ardusub_ws/ardupilot_gazebo/worlds:\$GZ_SIM_RESOURCE_PATH" >> "$RC_FILE"

echo
echo -e "\033[32m============================================================\033[0m"
echo -e "\033[32mROS-Gazebo Framework (w mavros and Ardusub) Installation completed. Awesome! 🤘🚀 \033[0m"
echo -e "You may check ROS, and Gazebo version installed with \033[33mprintenv ROS_DISTRO\033[0m and \033[33mecho \$GZ_VERSION\033[0m"
echo
