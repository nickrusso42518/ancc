import json
import textfsm
import csv

def to_csv_file(feature, fsm, records):
    with open(f"{feature}.csv", "w", encoding="utf-8") as handle:
        csv_file = csv.writer(handle)
        csv_file.writerow(fsm.header)
        for record in records:
            csv_file.writerow(records)

def to_json_file(feature, fsm, result):

    def _try_ints(record):
        new_record = []
        for value in record:
            try:
                new_record.append(int(value))
            except ValueError:
                new_record.append(value)
        return new_record

    data = [dict(zip(fsm.header, _try_ints(record))) for record in records]
    with open(f"{feature}.json", "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
"""
rid,dr_pri,state,role,dead_time,ip_addr,intf
10.0.0.2,1,FULL,DR,00:00:37,10.0.99.2,Ethernet0/2
10.0.0.14,0,2WAY,DROTHER,00:00:35,10.0.99.14,Ethernet0/2
10.0.0.12,0,FULL,-,00:00:34,10.1.12.12,Vlan3
10.0.0.13,255,FULL,BDR,00:00:34,10.1.13.13,Serial6.101

intf,pid,area,ip_addr,ip_mask,cost,state,nbr_full,nbr_seen
Lo0,1,0,10.0.0.1,32,1,LOOP,0,0
Et0/2,1,0,10.0.99.1,24,5,DROTH,1,2
Vl3,1,3,10.1.12.1,24,7,P2P,1,1
Se6.101,1,3,10.1.13.1,24,7,P2P,1,1

[
  {
    "Interface": {
      "hostname": "r01",
      "interface": "Ethernet0/2"
    },
    "IP": "10.0.99.1",
    "Area": 0,
    "Remote_Interface": {
      "hostname": "r14",
      "interface": "Ethernet0/2"
    },
    "Remote_IP": "10.0.99.14",
    "Remote_Area": 0,
    "Session_Status": "ESTABLISHED"
  },

  {
    "Interface": {
      "hostname": "r13",
      "interface": "Loopback0"
    },
    "VRF": "default",
    "Process_ID": "1",
    "OSPF_Area_Name": 3,
    "OSPF_Enabled": true,
    "OSPF_Passive": true,
    "OSPF_Cost": 1,
    "OSPF_Network_Type": "BROADCAST",
    "OSPF_Hello_Interval": 10,
    "OSPF_Dead_Interval": 40
  },
"""

inputs = [
    """
Neighbor ID  Pri   State           Dead Time   Address      Interface
10.0.0.2       1   FULL/DR         00:00:37    10.0.99.2    Ethernet0/2
10.0.0.14      0   2WAY/DROTHER    00:00:35    10.0.99.14   Ethernet0/2
10.0.0.12      0   FULL/  -        00:00:34    10.1.12.12   Vlan3
10.0.0.13    255   FULL/BDR        00:00:34    10.1.13.13   Serial6.101
""",
    """
Interface    PID   Area            IP Address/Mask    Cost  State Nbrs F/C
Lo0          1     0               10.0.0.1/32        1     LOOP  0/0
Et0/2        1     0               10.0.99.1/24       5     DROTH 1/2
Vl3          1     3               10.1.12.1/24       7     P2P   1/1
Se6.101      1     3               10.1.13.1/24       7     P2P   1/1
""",
]

for feature, data in zip(["ospf_nbrs", "ospf_intfs"], inputs):
    with open(f"{feature}.textfsm", "r", encoding="utf-8") as handle:
        fsm = textfsm.TextFSM(handle)
        records = fsm.ParseText(data)

    assert all([len(fsm.header) == len(record) for record in records])
    for method in [to_csv_file, to_json_file]:
        method(feature, fsm, records)

# test subset
# all(d1.get(key) == val for key, val in d1.items())
