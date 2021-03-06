"""HummingBird execution file.

This is a python excution file to run I2C eletrical test on
data from csv file.

"""
import argparse
import os
import subprocess
import time

from hummingbird import HummingBird


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("csv",
                      help="csv data path, column format: [time, CH1, CH2]")
  parser.add_argument("--output_folder", default=None,
                      help="the folder path to save output report, "
                      "ex:\"./output_reports/\"")
  parser.add_argument("--working_voltage", default=None, type=float,
                      choices=[1.8, 3.3, 5],
                      help="supplying voltage (unit: V)")
  parser.add_argument("--operation_mode", default=None,
                      choices=["Standard_Mode", "Fast_Mode", "Fast_Mode_Plus"],
                      help="SPEC operation mode")
  args = parser.parse_args()

  if args.output_folder is None:
    LOCAL_PATH = os.path.join(os.path.dirname(__file__), "output_reports")
    args.output_folder = LOCAL_PATH

  if not os.path.exists(args.output_folder):
    os.makedirs(args.output_folder)

  stt = time.time()
  print("\nLoading data from ", args.csv)
  hum1 = HummingBird(csv_data_path=args.csv,
                     save_folder=args.output_folder,
                     vs=args.working_voltage,
                     mode=args.operation_mode)
  print("=== Data Load time: ", time.time() - stt, "s ===")

  stt = time.time()
  report_path, _ = hum1.measure()
  print("Generate report at ", report_path)
  print("=== Measure Time: ", time.time() - stt, "s ===")

  subprocess.run(["open", report_path], check=True)
