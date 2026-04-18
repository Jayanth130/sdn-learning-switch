[# SDN Learning Switch Controller

## Problem Statement

In a traditional network, the switch itself contains the logic for 
forwarding packets. This makes the network rigid — you cannot 
programmatically control how packets are forwarded, blocked, or 
redirected.

This project implements an SDN-based Learning Switch using Mininet 
and Ryu OpenFlow controller. The switch logic is moved out of the 
hardware and into a Python controller that:

- Dynamically learns MAC addresses by observing incoming packets
- Installs flow rules into the switch so future packets are handled 
  in hardware without involving the controller
- Blocks specific hosts by installing DROP rules

## Topology

H1 (10.0.0.1) ──┐
H2 (10.0.0.2) ──┼── Switch S1 ──── Ryu Controller
H3 (10.0.0.3) ──┘      (BLOCKED)
- H1 and H2 can communicate freely
- H3 is blocked — all packets from H3 are dropped at the switch level

## How It Works

1. When the switch connects to the controller, one rule is installed:
   "If no rule matches this packet, send it to the controller" 
   (table-miss rule, priority 0)

2. When the first packet arrives:
   - Switch has no rule for it → sends to controller (Packet-In)
   - Controller learns: src_mac → in_port
   - dst_mac unknown → controller tells switch to FLOOD

3. The destination host replies:
   - Controller learns the second MAC → in_port
   - Both endpoints now known → install flow rule:
     "dst_mac X on port Y → always output port Z"

4. All future packets for that flow are handled by the switch 
   directly. Controller is never involved again.

5. If H3 sends any packet:
   - Controller sees H3's MAC → installs DROP rule (priority 10)
   - All future H3 packets are silently dropped at the switch

## Project Structure

sdn_project/
├── controller.py    # Ryu controller — MAC learning + flow rules
└── topology.py      # Mininet topology — 3 hosts, 1 switch
## Setup

### Requirements

- Ubuntu (VM or WSL2)
- Python 3.10
- Mininet
- Ryu SDN Framework

### Installation

**Install Mininet:**
```bash
sudo apt-get install mininet -y
```

**Set up Python virtual environment:**
```bash
python3.10 -m venv sdn-env
source sdn-env/bin/activate
pip install wheel setuptools
pip install eventlet==0.33.3
pip install ryu
```

**Fix Ryu compatibility with Python 3.10:**

Patch `wsgi.py`:
```bash
nano ~/sdn-env/lib/python3.10/site-packages/ryu/app/wsgi.py
```
Find line:
```python
from eventlet.wsgi import ALREADY_HANDLED
```
Replace with:
```python
try:
    from eventlet.wsgi import ALREADY_HANDLED
except ImportError:
    ALREADY_HANDLED = object()
```

Patch `timeout.py`:
```bash
nano ~/sdn-env/lib/python3.10/site-packages/eventlet/timeout.py
```
Find inside `wrap_is_timeout`:
```python
if inspect.isclass(base):
    base.is_timeout = property(lambda _: True)
    return base
```
Replace with:
```python
if inspect.isclass(base):
    try:
        base.is_timeout = property(lambda _: True)
    except TypeError:
        pass
    return base
```

## Execution

**Terminal 1 — Start the controller:**
```bash
source ~/sdn-env/bin/activate
ryu-manager controller.py
```

**Terminal 2 — Start the network:**
```bash
sudo ~/sdn-env/bin/python3 topology.py
```

## Test Scenarios

### Scenario 1 — Normal Traffic (H1 ↔ H2)
mininet> h1 ping h2 -c 4

Expected output:
4 packets transmitted, 4 received, 0% packet loss

Controller log shows:
PacketIn sw=1 in_port=1 src=00:00:00:00:00:01 dst=ff:ff:ff:ff:ff:ff
FLOOD — ff:ff:ff:ff:ff:ff unknown
PacketIn sw=1 in_port=2 src=00:00:00:00:00:02 dst=00:00:00:00:00:01
UNICAST 00:00:00:00:00:01 → port 1  (flow installed)


First packet floods (MAC unknown), subsequent packets unicast 
directly via installed flow rule.

### Scenario 2 — Blocked Host (H3)
mininet> h3 ping h1 -c 4

Expected output:
4 packets transmitted, 0 received, 100% packet loss
### Flow Table Inspection
mininet> sh ovs-ofctl dump-flows s1

Expected output:
priority=10, dl_src=00:00:00:00:00:03          actions=drop
priority=1,  dl_dst=00:00:00:00:00:01          actions=output:s1-eth1
priority=1,  dl_dst=00:00:00:00:00:02          actions=output:s1-eth2
priority=0                                      actions=CONTROLLER:65535
### Bandwidth Test (iperf)
mininet> h2 iperf -s &
mininet> h1 iperf -c 10.0.0.2 -t 5

## Proof of Execution

### Flow Table
![flow_table](screenshots/flow_table.png)

### Scenario 1 — H1 ping H2
![ping_h1_h2](screenshots/ping_h1_h2.png)

### Scenario 2 — H3 blocked
![ping_h3_blocked](screenshots/ping_h3_blocked.png)

### iperf Bandwidth Test
![iperf](screenshots/iperf.png)

### Wireshark Capture
![wireshark](screenshots/wireshark.png)

## Key Concepts

| Term | Meaning |
|---|---|
| Packet-In | Switch sends unknown packet to controller |
| Flow Rule | match + action installed in switch hardware |
| Table-miss | Rule that fires when no other rule matches |
| OFPPacketOut | Controller tells switch to forward current packet |
| OFPFlowMod | Controller installs a new flow rule into switch |
| OFPP_FLOOD | Send out all ports except the one it came in on |

## References

1. Ryu SDN Framework — https://ryu.readthedocs.io
2. OpenFlow Specification 1.3 — https://opennetworking.org
3. Mininet Documentation — http://mininet.org
4. Open vSwitch — https://www.openvswitch.org

](https://github.com/Jayanth130/sdn-learning-switch.git)
