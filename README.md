# DAVE - Nautilus-UG Fork

This is the Nautilus-UG fork of DAVE (Aquatic Robotic Simulator) containing custom configurations for the Glider Nautilus robot.

**Upstream DAVE Documentation**: [http://dave-ros2.notion.site](http://dave-ros2.notion.site)

## Setup

Requires the [Control Stack](https://github.com/Nautilus-UUV/nautilus-ros) setup to be completed first (`~/nautilus_ws` with its `.venv`).

### Steps

1. Install Gazebo Harmonic following the [official guide](https://gazebosim.org/docs/harmonic/install_ubuntu/), then:
```bash
sudo apt install ros-jazzy-ros-gz protobuf-compiler libprotobuf-dev
```
2. Clone repository:
```bash
cd ~/nautilus_ws/src
git clone -b dev git@github.com:Nautilus-UUV/nautilus-dave.git
```
3. Resolve dependencies and build:
```bash
cd ~/nautilus_ws
source .venv/bin/activate
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -y --skip-keys "protobuf"
python -m colcon build --symlink-install
source install/setup.bash
```
4. Verify the setup (sawtooth dive with the full control stack):
```bash
ros2 launch nautilus_hal sawtooth_sim.launch.py \
    headless:=false \
    mission_autostart:=true \
    target_pressure_pa:=147150.0 \
    shallow_pressure_pa:=49050.0 \
    angle_rad:=0.6109 \
    n_oscillations:=3
```

## Usage

### Data Collection

```bash
ros2 launch nautilus_hal sawtooth_sim.launch.py \
    headless:=true \
    mission_autostart:=true \
    target_pressure_pa:=147150.0 \
    shallow_pressure_pa:=49050.0 \
    angle_rad:=0.6109 \
    n_oscillations:=3 \
    record:=true
```

**args:**
- `record:=true` to enable databag generation
- `run_id:={ID}` to give a predefined run_id that is concatenated together with the timestamp
- `bag_path:={PATH}` if you want to override the default data collection path
- `scenario:={PATH}` selects the scenario YAML driving gains, plant, bridge publish rates, and fault injection. Defaults to the installed `library/nominal.yaml` (fault injection off, lake-fitted sensor noise on). For a persistent BCU pump fault (60% pump effectiveness for the whole run), pick `baseline.yaml`:

  ```bash
  scenario:=$(ros2 pkg prefix py_pkg)/share/py_pkg/scenarios/library/baseline.yaml
  ```

  Same flag works for `trim_sim.launch.py`, `sawtooth_sim.launch.py`, `surface_sim.launch.py`, `bridge.launch.py`, and `control_stack.launch.py`.


### UI Connection

#### Mission Laptop

```bash
mosquitto -c ./mosquitto/mosquitto.conf -v
```

```bash
npm run dev
```

#### Pi

Start the HAL:
```bash
ros2 launch nautilus_hal bridge.launch.py
```

Start the simulation:
```bash
ros2 launch dave_demos dave_robot.launch.py \
    namespace:=glider_nautilus world_name:=dave_ocean_waves \
    z:=-5 roll:=3.141592653589793 yaw:=1.5707963267948966 \
    paused:=false headless:=false
```

Start control:
```bash
ros2 launch py_pkg control_stack.launch.py
```

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
cd ~/nautilus_ws
python -m colcon build --symlink-install

# Source the workspace
source install/setup.bash

# Test your changes (launch files, simulations, etc.)
ros2 launch <your_test_commands>
```

