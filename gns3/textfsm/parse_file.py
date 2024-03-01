# /usr/bin/env python

"""
Author: Nick Russo
Purpose: Test textfsm parsing using Network To Code (NTC) templates
as an introductory example.
See https://github.com/networktocode/ntc-templates for more templates.
"""

from csv import DictWriter
import json
import os
from ntc_templates.parse import parse_output


def to_json_file(out_dir, prefix, records):
    """
    Write the records to the output file named <prefix>.json on disk. The
    resulting JSON structure is always a single-depth list of dictionaries.
    """
    with open(f"{out_dir}/{prefix}.json", "w") as handle:
        json.dump(records, handle, indent=2)


def to_csv_file(out_dir, prefix, records):
    """
    Write the records to the output file named <prefix>.json on disk. The
    resulting JSON structure is always a single-depth list of dictionaries.
    """
    with open(f"{out_dir}/{prefix}.csv", "w") as handle:
        dict_writer = DictWriter(handle, records[0].keys())
        dict_writer.writeheader()
        dict_writer.writerows(records)


def main():
    """
    Execution starts here.
    """

    # Create the outputs/ directory if it doesn't exist
    out_dir = "gns3/textfsm/outputs"
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    # For each desired output in the global list
    in_dir = "gns3/textfsm/inputs"
    for input_file in os.listdir(in_dir):
        # Load the input data from plain-text file
        print(f"\nProcessing input: {input_file}")
        with open(f"{in_dir}/{input_file}", "r") as handle:
            data = handle.read()

        # Extract the platform name and command from the filename for NTC
        show_index, dot_index = input_file.find("show"), input_file.find(".")
        ntc_params = {
            "platform": input_file[: show_index - 1],
            "command": input_file[show_index:dot_index].replace("_", " "),
        }

        # Try to parse using an NTC template. It only raises a generic
        # "Exception", but we can catch it and check the message
        try:
            records = parse_output(data=data, **ntc_params)

            # Loop over each dict in list, then iterate over the keys.
            # Try to parse integers without creating a new dict, ignore failures
            for record in records:
                for key in record:
                    try:
                        record[key] = int(record[key])
                    except ValueError:
                        pass

            # Print the output using a variety of outputs
            for output_function in [to_csv_file, to_json_file]:
                output_function(out_dir, input_file[:dot_index], records)

        except Exception as exc:
            # Don't have a template; print error but don't crash
            if "No template found" in str(exc):
                print(str(exc))

            # Some other error occurred; re-raise
            else:
                raise


if __name__ == "__main__":
    main()
