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
    apt-get install -y /tmp/ros2-apt-source.deb && \
    rm -f /tmp/ros2-apt-source.deb

sudo curl https://packages.osrfoundation.org/gazebo.gpg --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null

echo
echo -e "\033[96m(4/4) ------------     Install ROS-Gazebo    ---------------\033[0m"
DIST=jazzy
GAZEBO=gz-harmonic

echo -e "\033[34mInstalling ROS Gazebo framework...\033[0m"
sudo apt update && apt install -y \
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
echo -e "\033[32m============================================================\033[0m"
echo -e "\033[32mROS-Gazebo Framework Installation completed. Awesome! 🤘🚀 \033[0m"
echo -e "Following command will set-up ROS environment variables to run it"
echo -e "\033[95msource /opt/ros/jazzy/setup.bash\033[0m"
echo -e "You may check ROS, and Gazebo version installed with \033[33mprintenv ROS_DISTRO\033[0m and \033[33mecho \$GZ_VERSION\033[0m"
echo
