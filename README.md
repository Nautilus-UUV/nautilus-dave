# DAVE - Nautilus-UUV Fork

[![Publish a Docker image (AMD64; Common X86_64 Linux Machine)](https://github.com/IOES-Lab/dave/actions/workflows/docker-amd64.yml/badge.svg)](https://github.com/IOES-Lab/dave/actions/workflows/docker-amd64.yml)
[![Publish a Docker image (ARM64; Apple Silicon)](https://github.com/IOES-Lab/dave/actions/workflows/docker-arm64v8.yml/badge.svg?branch=ros2)](https://github.com/IOES-Lab/dave/actions/workflows/docker-arm64v8.yml)

This is the Nautilus-UUV fork of DAVE (Aquatic Robotic Simulator) containing custom configurations for the Glider Nautilus robot.

**Upstream DAVE Documentation**: [http://dave-ros2.notion.site](http://dave-ros2.notion.site)

## Installation

### Prerequisites

1. **Install DAVE** following the official installation tutorial:
   - [DAVE Native Installation Guide](https://dave-ros2.notion.site/Native-Local-Installation-Manual-7c6d7be83a4947d28ae3e3eb6b7de5ee)
   - Complete all steps through building the base DAVE workspace

### Installing Nautilus Custom Models

After completing the official DAVE installation:

```bash
# Navigate to the DAVE workspace
cd ~/dave_ws/src

# Remove the default DAVE repository
rm -rf dave

# Clone the Nautilus fork with the dev branch
git clone -b dev https://github.com/Nautilus-UUV/dave.git
```

Source your ros2 and correspondic gazebo versions:

```bash
# Source ros2 jazzy and gazebo harmonic
source /opt/ros/jazzy/setup.bash
source /opt/gazebo/install/setup.bash && export PYTHONPATH=$PYTHONPATH:/opt/gazebo/install/lib/python
```



Build custom dave:

```bash
# Navigate back to workspace root
cd ~/dave_ws

# Remove any existing build artifacts
rm -rf build/ install/ log/

# Rebuild the workspace with Nautilus customizations
# NOTE: we skip the Hardware Abstraction Layer (HAL) of the actual control
colcon build --package-skip nautilus_hal --symlink-install

# Source the workspace
source install/setup.bash
```

**Optional:**
Add to .bashrc_aliases to source dave by running `dave`:
```bash
alias jazzy='source /opt/ros/jazzy/setup.bash'
alias harmonic='source /opt/gazebo/install/setup.bash && export PYTHONPATH=$PYTHONPATH:/opt/gazebo/install/lib/python'
alias dave='jazzy && harmonic && source ~/dave_ws/install/setup.bash'
```

> [!NOTE]
> That's right, we don't technically need to follow the DAVE installation since we are deleting it and rebuilding it. All that is needed is a working ros2 and corresponding gazebo version.


## Running the [nautilus-ros Repository](https://github.com/Nautilus-UUV/nautilus-ros) with the Digital Twin

```bash
cd ~/dave_ws/src
git clone -b dev ... # [INSERT ROS2 REPO]

cd ~/dave_ws
rm -rf build/ install/ log/

colcon build --symlink-install # this time not skipping the nautilus_hal

source install/setup.bash
```

### Testing Setup

We need to start 3 components: 
1. The Hardware Abstraction layer 
```bash
ros2 launch nautilus_hal bridge_launch.py 
````
2. The control logic (for this there is a mocked integration test)
```bash
ros2 run py_pkg bcu_oscillator 
``` 
3. The DAVE simulation with Nautilus
```bash
ros2 launch nautilus_hal bridge_launch.py # launches all the interfaces
```

Now, if everything is working correctly, you should see the Nautilus Glider reach for the surface and dive back down in an oscillary motion.


## Branch Structure

Our fork uses a structured branching model:

```
polaris-ros2 (stable - tracks upstream + Nautilus customizations)
    └── dev (active development - merge feature branches here)
        └── github_username/feature_name
```

> [!NOTE]
> `dev` contains a [fork sync](.github/workflows/fork-sync.yml) workflow to automatically sync changes from upstream

## Contributing Workflow

### Create a Feature Branch

```bash
# Make sure you're on the dev branch
git checkout dev

# Pull the latest changes
git pull origin dev

# Create your feature branch
git checkout -b github_username/feature_name
```

### Make Your Changes

Edit files in the appropriate locations:

- **Robot models**: `models/dave_robot_models/description/glider_nautilus/`
- **Configurations**: `models/dave_robot_models/config/glider_nautilus/`
- **Meshes**: `models/dave_robot_models/meshes/glider_nautilus/`
- **Launch files**: Add to appropriate package directories

```
dave/
├── models/
│   └── dave_robot_models/
│       ├── description/
│       │   └── glider_nautilus/    # Robot SDF files
│       ├── config/
│       │   └── glider_nautilus/    # Launch configuration ros_gz_bridge
│       └── meshes/
│           └── glider_nautilus/    # 3D mesh files
├── README.md                       # This file
└── ...                             # Other DAVE packages
```

### Test Your Changes

```bash
# Rebuild the workspace
cd ~/dave_ws
colcon build --symlink-install

# Source the workspace
source install/setup.bash

# Test your changes (launch files, simulations, etc.)
ros2 launch <your_test_commands>
```
