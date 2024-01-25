import json
import textfsm
import csv
import os

outputs = [
    {"platform": "cisco_ios", "command": "show ip ospf neighbor"},
    {"platform": "cisco_ios", "command": "show ip ospf interface brief"},
    {"platform": "cisco_ios", "command": "show ip ospf database"},
    {"platform": "juniper_junos", "command": "show ospf neighbor"},
    #{"platform": "juniper_junos", "command": "show ospf interface summary"},
    #{"platform": "juniper_junos", "command": "show ospf database"},
]

from ntc_templates.parse import parse_output

def to_csv_file(feature, fsm, records):
    with open(f"outputs/{feature}.csv", "w", encoding="utf-8") as handle:
        csv_file = csv.writer(handle)
        csv_file.writerow(fsm.header)
        for record in records:
            csv_file.writerow(record)

def to_json_file(prefix, records, fsm=None):

    # If fsm is defined, it's a custom template. Need to map variable names
    # (fsm.headers) with the tabular values, which isn't automatic
    new_records = []
    if fsm:
        #data = [dict(zip(fsm.header, _try_ints(record))) for record in records]

        # Loop over each row in matrix, then try to convert each value to
        # an integer without creating a new list. Ignore failure; retain value.
        for record in records:
            for i in range(len(record)):
                try:
                    record[i] = int(record[i])
                except ValueError:
                    pass

            # Add a new dict to the list with the headers (keys) and values
            new_records.append(dict(zip(fsm.header, record)))

    # Else, it's an NTC template, records is a list of dicts, not a matrix
    else:

        # Loop over each dict in list, then iterate over the keys. Try to parse
        # integers without creating a new dict. Ignore failure; retain value.
        for record in records:
            for key in record.keys():
                try:
                    record[key] = int(record[key])
                except ValueError:
                    pass

            # Basic reference so generic write operation can succeed
            new_records = records

    with open(f"outputs/{prefix}.json", "w", encoding="utf-8") as handle:
        json.dump(new_records, handle, indent=2)


def main():
    #features = ["junos_ospf_intfs", "junos_ospf_lsdb"]
    #output_functions = [to_csv_file, to_json_file]
    output_functions = [to_json_file]

    if not os.path.exists("outputs"):
        os.makedirs("outputs")

    # For each feature
    for output in outputs:

        # Assemble the file prefix for each desired output
        prefix = f"{output['platform']}_{output['command'].replace(' ', '_')}"

        # Load the input data
        with open(f"input/{prefix}.txt", "r", encoding="utf-8") as handle:
            data = handle.read()

        # Try to parse using an NTC template
        records = parse_output(data=data, **output)

        # Print the output using a variety of outputs
        for output_function in output_functions:
            output_function(prefix=prefix, records=records)
        

def test():
    if False:
        with open(f"custom/{feature}.textfsm", "r", encoding="utf-8") as handle:
            fsm = textfsm.TextFSM(handle)
            records = fsm.ParseText(data.strip())

        # Ensure that the number of column headers equals the number
        # of fields in each record, or else tabular format is ruined
        assert all([len(fsm.header) == len(record) for record in records])

        # Print the output using a variety of outputs
        for output_function in output_functions:
            output_function(feature, fsm, records)

if __name__ == "__main__":
    main()
