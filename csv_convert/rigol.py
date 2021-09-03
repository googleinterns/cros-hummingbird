"""CSV file convert.

This is a python excution file to convert RIGOL csv file
into HummingBird readable format.

"""
import argparse
import csv
import os


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("input_csv", help="input csv data path")
  parser.add_argument("--output_csv", default=None, help="output csv data path")
  args = parser.parse_args()

  if args.output_csv is None:
    name, ext = os.path.splitext(args.input_csv)
    args.output_csv = name + "_converted" + ext

  with open(args.input_csv, "r") as f:
    data_iter = csv.reader(f, delimiter=",")
    channel_info = next(data_iter)[1:3]
    time_info = next(data_iter)[-1]
    with open(args.output_csv, "w", newline="") as f_out:
      writer = csv.writer(f_out, delimiter=",")
      writer.writerow(["Time [s]", channel_info[0], channel_info[1]])
      for data in data_iter:
        data = data[:3]
        data[0] = int(data[0]) * float(time_info)
        writer.writerow(data)
