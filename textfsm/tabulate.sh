#!/bin/bash
# Quickly print the CSV files in tabular form

for file in textfsm/outputs/*.csv
do
  echo ""
  echo $file
  column -s, -t $file
done
