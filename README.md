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
colcon build --symlink-install

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

## Branch Structure

Our fork uses a structured branching model:

```
polaris-ros2 (stable - tracks upstream + Nautilus customizations)
    └── dev (active development - merge feature branches here)
        ├── feature/new-sensor-integration
        ├── feature/improved-controller
        └── feature/your-feature-name
```

### Branch Descriptions

- **`polaris-ros2`**: Stable branch with tested Nautilus customizations
  - Tracks upstream `IOES-Lab/dave:ros2`
  - Contains production-ready Glider Nautilus models
  - Protected branch - requires PR approval

- **`dev`**: Active development branch
  - Base branch for all new feature development
  - Integration testing happens here
  - Periodically merged into `polaris-ros2` after testing

- **`feature/*`**: Individual feature branches
  - Created from `dev`
  - One feature per branch
  - Merged back to `dev` via PR

## Contributing Workflow

### 1. Set Up Your Development Environment

```bash
cd ~/dave_ws/src/dave

# Add the upstream IOES-Lab repository (for pulling updates)
git remote add upstream https://github.com/IOES-Lab/dave.git

# Verify remotes
git remote -v
# Should show:
#   origin    https://github.com/Nautilus-UUV/dave.git
```

### 2. Create a Feature Branch

```bash
# Make sure you're on the dev branch
git checkout dev

# Pull the latest changes
git pull origin dev

# Create your feature branch
git checkout -b feature/your-feature-name
```

### 3. Make Your Changes

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

### 4. Test Your Changes

```bash
# Rebuild the workspace
cd ~/dave_ws
colcon build --symlink-install

# Source the workspace
source install/setup.bash

# Test your changes (launch files, simulations, etc.)
ros2 launch <your_test_commands>
```

### 5. Commit Your Changes

```bash
cd ~/dave_ws/src/dave

# Stage your changes
git add .

# Run pre-commit checks
pre-commit run --all-files

# Commit with a descriptive message
git commit -m "feat: add description of your feature"

# Push to your feature branch
git push origin feature/your-feature-name
```

### 6. Create a Pull Request

1. Go to [https://github.com/Nautilus-UUV/dave](https://github.com/Nautilus-UUV/dave)
2. Click "Pull requests" → "New pull request"
3. Set **base branch** to `dev` (not `polaris-ros2`!)
4. Set **compare branch** to your `feature/your-feature-name`
5. Fill in the PR description:
   - What does this feature add/fix?
   - How did you test it?
   - Any breaking changes?
6. Request review from team members
7. Address review feedback and update your branch as needed

### 7. After PR is Merged

```bash
# Switch back to dev
git checkout dev

# Pull the updated dev branch
git pull origin dev

# Delete your local feature branch
git branch -d feature/your-feature-name

# Delete the remote feature branch
git push origin --delete feature/your-feature-name
```

## Commit Message Conventions

Follow conventional commits format:

- `feat: add new buoyancy model` - New feature
- `fix: correct thruster orientation` - Bug fix
- `docs: update installation instructions` - Documentation
- `refactor: simplify sensor configuration` - Code refactoring
- `test: add integration test for controller` - Tests
- `chore: update dependencies` - Maintenance tasks

## Syncing with Upstream DAVE

Periodically pull updates from the upstream IOES-Lab/dave repository:

```bash
# Checkout polaris-ros2
git checkout polaris-ros2

# Fetch upstream changes
git fetch upstream

# Merge upstream ros2 into polaris-ros2
git merge upstream/ros2

# Resolve any conflicts if they occur

# Push updated polaris-ros2
git push origin polaris-ros2

# Update dev branch with the new changes
git checkout dev
git merge polaris-ros2
git push origin dev
```
