import textfsm
import csv


def tabulate(feature, fsm, result):
    with open(f"{feature}.csv", "w", encoding="utf-8") as handle:
        csv_file = csv.writer(handle)
        csv_file.writerow(fsm.header)
        for row in result:
            csv_file.writerow(row)


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
        result = fsm.ParseText(data)

    tabulate(feature, fsm, result)
