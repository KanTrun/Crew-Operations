"""AG-TWIN — Digital Twin: mô phỏng "nếu... thì..." bằng math_layer + nhân viên ảo."""

from ca_agents.ag_twin.simulator import simulate_scenario
from ca_agents.ag_twin.virtual_staff import simulate_virtual_staff

__all__ = ["simulate_scenario", "simulate_virtual_staff"]