import json
import textfsm
import csv


def to_csv_file(feature, fsm, records):
    with open(f"{feature}.csv", "w", encoding="utf-8") as handle:
        csv_file = csv.writer(handle)
        csv_file.writerow(fsm.header)
        for record in records:
            csv_file.writerow(record)


def to_json_file(feature, fsm, records):
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


inputs = [
    """
user@host> show ospf interface
Intf                State     Area            DR ID           BDR ID       Nbrs
at-5/1/0.0          PtToPt   0.0.0.0         0.0.0.0         0.0.0.0         1
ge-2/3/0.0          DR       0.0.0.0         192.168.4.16    192.168.4.15    1
lo0.0               DR       0.0.0.0         192.168.4.16    0.0.0.0         0
so-0/0/0.0          Down     0.0.0.0         0.0.0.0         0.0.0.0         0
so-6/0/1.0          PtToPt   0.0.0.0         0.0.0.0         0.0.0.0         1
so-6/0/2.0          Down     0.0.0.0         0.0.0.0         0.0.0.0         0
so-6/0/3.0          PtToPt   0.0.0.0         0.0.0.0         0.0.0.0         1
    """,
    """
    OSPF link state database, Area 0.0.0.1
 Type       ID               Adv Rtr           Seq      Age  Opt  Cksum  Len
Router   10.255.70.103    10.255.70.103    0x80000002   215  0x20 0x4112  48
Router  *10.255.71.242    10.255.71.242    0x80000002   214  0x20 0x11b1  48
Summary *23.1.1.0         10.255.71.242    0x80000002   172  0x20 0x6d72  28
Summary *24.1.1.0         10.255.71.242    0x80000002   177  0x20 0x607e  28
NSSA    *33.1.1.1         10.255.71.242    0x80000002   217  0x20 0x73bd  36

    OSPF link state database, Area 0.0.0.2
 Type       ID               Adv Rtr           Seq      Age  Opt  Cksum  Len
Router   10.255.71.52     10.255.71.52     0x80000004   174  0x20 0xd021  36
Router  *10.255.71.242    10.255.71.242    0x80000003   173  0x20 0xe191  36
Network *23.1.1.1         10.255.71.242    0x80000002   173  0x20 0x9c76  32
Summary *12.1.1.0         10.255.71.242    0x80000001   217  0x20 0xfeec  28
Summary *24.1.1.0         10.255.71.242    0x80000002   177  0x20 0x607e  28
NSSA    *33.1.1.1         10.255.71.242    0x80000001   222  0x28 0xe047  36

    OSPF link state database, Area 0.0.0.3
 Type       ID               Adv Rtr           Seq      Age  Opt  Cksum  Len
Router   10.255.71.238    10.255.71.238    0x80000003   179  0x20 0x3942  36
Router  *10.255.71.242    10.255.71.242    0x80000003   177  0x20 0xf37d  36
Network *24.1.1.1         10.255.71.242    0x80000002   177  0x20 0xc591  32
Summary *12.1.1.0         10.255.71.242    0x80000001   217  0x20 0xfeec  28
Summary *23.1.1.0         10.255.71.242    0x80000002   172  0x20 0x6d72  28
NSSA    *33.1.1.1         10.255.71.242    0x80000001   222  0x20 0xeb3b  36
    """,
]

for feature, data in zip(["junos_ospf_intfs", "junos_ospf_lsdb"], inputs):
    with open(f"{feature}.textfsm", "r", encoding="utf-8") as handle:
        fsm = textfsm.TextFSM(handle)
        records = fsm.ParseText(data.strip())

    assert all([len(fsm.header) == len(record) for record in records])
    for method in [to_csv_file, to_json_file]:
        method(feature, fsm, records)

# test subset
# all(d1.get(key) == val for key, val in d1.items())
