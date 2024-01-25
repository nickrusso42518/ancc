#!/bin/bash
# Quickly print the CSV files in tabular form

for file in outputs/*.csv
do
  echo ""
  echo $file
  column --separator "," --table $file
done
