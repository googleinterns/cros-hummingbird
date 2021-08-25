"""HummingBird execution file.

This is a python excution file to run I2C eletrical test on
data from csv file.

"""
import argparse
import os
import subprocess

from hummingbird_cmd import HummingBird


LOCAL_PATH = os.path.join(os.path.dirname(__file__), "output_reports")
if not os.path.exists(LOCAL_PATH):
  os.makedirs(LOCAL_PATH)

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("csv", help="csv data path")
  parser.add_argument("--out", default=LOCAL_PATH, help="output report folder")
  args = parser.parse_args()

  print("\nLoading data from ", args.csv)
  hum1 = HummingBird(csv_data_path=args.csv, save_folder=args.out)
  report_path = hum1.measure()
  print("Generate report at ", report_path)
  subprocess.run(["open", report_path], check=True)
