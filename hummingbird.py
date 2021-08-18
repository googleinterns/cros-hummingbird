"""HummingBird I2C Eletrical Test Automation.

The project serves as an extension measurement module
run on Saleae Logic2 Software. Supporting main function
would be running I2C electrical test on capture data.

"""
import datetime
import math
import os
import subprocess

from generate_report import OutputReportFile
from generate_report import SVGFile
import numpy as np
from saleae.data import GraphTime
from saleae.range_measurements import AnalogMeasurer

LOCAL_PATH = os.path.join(os.path.dirname(__file__), "output_reports")
if not os.path.exists(LOCAL_PATH):
  os.makedirs(LOCAL_PATH)


class Logic():
  """Logic State.

  Specify the logic state of the analog dataline.
  Transition between state HIGH and state LOW would be 30%Vdd and 70%Vdd

  Attributes:
    i_30p:  index achieve 30%Vdd
    i_70p:  index achieve 70%Vdd
    high_start: index where state HIGH begin
    high_end:   index where state HIGH end
    low_start:   index where state LOW begin
    low_end:   index where state LOW end
    state:   current logic state of the dataline. (three states: 1/0/None)
    last_low_start:   index where last time state LOW start
    last_high_start:   index where last time state HIGH start
  """

  def __init__(self):
    self.i_30p = None
    self.i_70p = None
    self.high_start = None
    self.high_end = None
    self.low_start = None
    self.low_end = None
    self.state = None
    self.last_low_start = None
    self.last_high_start = None


class HummingBird(AnalogMeasurer):
  """Main measurement module.

  This is the main module called by Saleae measurement API.

  Attributes:
    samples:  analog data samples, in the format of (time index, voltage value)
    start_time:  captured analog data start time
    sampling_period: time between two samples
    stop_flag:  STOP pattern detected, raise to 1 until START pattern
    start_flag:  START pattern detected, remain 1 for one package
                 (would last 9 SCL clock cycle)
    restart_flag:  RESTART pattern detected, remain 1 for one package
                 (would last 9 SCL clock cycle)
    data_start_flag:  from first SCL clock cycle after START or RESTART pattern,
                      remain 1 for one package (9 SCL clock cycle)

    scl_data_path:  SCL data save path
    scl_data:  SCL data
    scl_start_time:  SCL data start time
    scl_sampling_period:  SCL data sampling period
    f_clk:  SCL clock frequency
    sda_data_path:  SDA data save path
    sda_data:  SDA data
    sda_start_time:  SDA data start time
    sda_sampling_period:  SDA data sampling period

    requested_measurements: measurement required in extension.json
  """

  def __init__(self, requested_measurements):
    """Initialization.

    Initialize your measurement extension here
    Each measurement object will only be used once,
    all per-measurement initialization are here

    Args:
      requested_measurements:  measurement required in from extension.json
    """
    supported_measurements = [
        "v_low_scl", "v_low_sda", "v_high_scl", "v_high_sda", "v_nl_scl",
        "v_nh_scl", "v_nl_sda", "v_nh_sda", "t_rise_sda", "t_rise_scl",
        "t_fall_sda", "t_fall_scl", "t_low", "t_high", "f_clk",
        "t_SU_DAT_rising_host", "t_SU_DAT_falling_host", "t_HD_DAT_rising_host",
        "t_HD_DAT_falling_host", "t_SU_DAT_rising_dev", "t_SU_DAT_falling_dev",
        "t_HD_DAT_rising_dev", "t_HD_DAT_falling_dev", "t_HD_STA_S",
        "t_HD_STA_Sr", "t_SU_STA", "t_SU_STO", "t_BUF"
    ]
    super().__init__(requested_measurements)
    self.samples = []
    self.start_time = None
    self.sampling_period = None

    self.stop_flag = 1
    self.start_flag = 0
    self.restart_flag = 0
    self.data_start_flag = 0  # 1 when first scl high
    self.first_packet = 0

    self.scl_data_path = os.path.join(LOCAL_PATH, "SCL.txt")
    self.scl_data = None
    self.scl_start_time = None
    self.scl_sampling_period = None
    self.f_clk = None
    if os.path.isfile(self.scl_data_path):
      with open(self.scl_data_path, "r") as f:
        head = [next(f) for x in range(3)]
        scl_start_time = head[0].split("\n")[0]
        [dt, subms] = scl_start_time.split("\t")
        dt = datetime.datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
        ms, us = int(subms[0:3]), int(subms[3:6])
        ns, ps = int(subms[6:9]), int(subms[9:12])
        self.scl_start_time = GraphTime(dt, millisecond=ms, microsecond=us,
                                        nanosecond=ns, picosecond=ps)
        self.scl_sampling_period = float(head[1].split("\n")[0])
        self.f_clk = float(head[2].split("\n")[0])
        self.scl_data = np.loadtxt(self.scl_data_path, delimiter=",",
                                   skiprows=3)
      os.remove(self.scl_data_path)

    self.sda_data_path = os.path.join(LOCAL_PATH, "SDA.txt")
    self.sda_data = None
    self.sda_start_time = None
    self.sda_sampling_period = None
    if os.path.isfile(self.sda_data_path):
      with open(self.sda_data_path, "r") as f:
        head = [next(f) for x in range(2)]
        sda_start_time = head[0].split("\n")[0]
        [dt, subms] = sda_start_time.split("\t")
        dt = datetime.datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
        ms, us = int(subms[0:3]), int(subms[3:6])
        ns, ps = int(subms[6:9]), int(subms[9:12])
        self.sda_start_time = GraphTime(dt, millisecond=ms, microsecond=us,
                                        nanosecond=ns, picosecond=ps)
        self.sda_sampling_period = float(head[1].split("\n")[0])
        self.sda_data = np.loadtxt(self.sda_data_path, delimiter=",",
                                   skiprows=2)

      os.remove(self.sda_data_path)

    self.v_30p = None
    self.v_70p = None

    self.requested_measurements = {}
    for m in supported_measurements:
      if m + "_worst" in requested_measurements:
        self.requested_measurements[m + "_worst"] = True
      else:
        self.requested_measurements[m + "_worst"] = False
    if "spec" in requested_measurements:
      self.requested_measurements["spec"] = True

  def process_data(self, data):
    """Process data.

    This method will be called one or more times per measurement
    Iterate over data to get Voltage values, one per sample

    Args:
      data:
        data.samples is a numpy array of float32 voltages, one for each sample
        data.sample_count is the number of samples
    """
    self.samples.append(data.samples)
    if self.sampling_period is None:
      self.sampling_period = (
          ((data.end_time - data.start_time) / data.sample_count).__float__())

    if self.start_time is None:
      self.start_time = data.start_time

  def max_of_filtered_arr(self, data, threshold=1):
    """Return the maximum value of the filtered array.

    Remove glitch from per 0.1us segment
    Remove voltage difference between two sample points
    larger than 1V
    Return the maximum value of the filtered array

    Args:
      data: raw voltage data
      threshold: difference larger than threshold would be removed
                 (default: 1V)

    Returns:
      maxx: the maxium voltage of the filtered data
    """
    length = round(1e-7 / self.sampling_period)
    segments = len(data) // length
    maxx = 0
    for i in range(segments):
      arr = data[i * length:(i + 1) * length]
      median = np.median(arr)
      maxx = max(np.max(arr[arr < median + threshold]), maxx)
    return maxx

  def determine_working_voltage(self, data):
    """Determine Working Voltage.

    Perform de-glitch on data and using the maximum 
    voltage value to predict the working voltage.

    Args:
      data: numpy array of voltages values

    Returns:
      vs: working voltage
    """
    v_max = self.max_of_filtered_arr(data)

    vs_list = [1.8, 3.3, 5]
    pos = np.argmax(vs_list > v_max)
    if pos:
      if vs_list[pos] - v_max <= v_max - vs_list[pos - 1]:
        vs = vs_list[pos]
      else:
        vs = vs_list[pos-1]
    else:
      vs = v_max
    self.v_30p = vs * 0.3
    self.v_70p = vs * 0.7

    return vs

  def determine_datatype(self, data):
    """Determine Data Type.

    Read the first four cycle to determine data type
    Consider different sampling rate by multiply sampling_period
    Avoid extreme value which might cause by clk stretching
    Calculate the difference percentage of f_max and f_avg
    SCL should be stable and the difference should be small

    Constrain: should capture at least five SCL clk cycles

    Args:
      data: numpy array of voltages values

    Returns:
      datatype:  SCL or SDA
    """
    datatype = None
    dataline = Logic()
    clk_dataline = []
    v = data[0]
    for i in range(1, len(data)):
      n = data[i]
      if ((v >= self.v_30p and n < self.v_30p) or
          (v <= self.v_30p and n > self.v_30p)):
        dataline.i_30p = i
        if dataline.i_70p is not None:  # falling edge
          dataline.low_start = dataline.i_30p
          dataline.i_30p = dataline.i_70p = None

          if dataline.last_low_start is not None:
            clk_dataline.append(dataline.low_start - dataline.last_low_start)
          dataline.last_low_start = dataline.low_start

      if ((v >= self.v_70p and n < self.v_70p) or
          (v <= self.v_70p and n > self.v_70p)):
        dataline.i_70p = i
        if dataline.i_30p is not None:  # rising edge
          dataline.high_start = dataline.i_70p
          dataline.i_30p = dataline.i_70p = None

          if dataline.last_high_start is not None:
            clk_dataline.append(dataline.high_start - dataline.last_high_start)
          dataline.last_high_start = dataline.high_start
      v = n
      if len(clk_dataline) >= 8:
        break

    if len(clk_dataline) > 7:
      clk_dataline = np.sort(clk_dataline)[:-2]
      t_clk = clk_dataline[-1]  # max period time
      t_clk2 = clk_dataline[0]  # min period time
      stable = (t_clk - t_clk2) / t_clk2 * 100

      if stable < 20:
        datatype = "SCL"
        self.f_clk = 1 / (t_clk2 * self.sampling_period)

    if datatype is None:
      datatype = "SDA"

    return datatype

  def determine_operation_mode(self):
    """Determine Operation Mode.

    Using average f_clk from first five cycles to predict operation mode

    Returns:
      mode: operation mode (Standard mode/Fast Mode/Fast Mode Plus)
    """
    if self.f_clk < 1.1e5:
      mode = "Standard Mode"
    elif self.f_clk < 4.4e5:
      mode = "Fast Mode"
    elif self.f_clk < 1.1e6:
      mode = "Fast Mode Plus"

    return mode

  def process_1st_2nd_capture(self, datatype, data):
    """Process 1st or 2nd Capture.

    If 1st, write data.
    If 2nd, solve datatime time zone when convert datatime to graphtime

    Args:
      datatype: SCL or SDA
      data: numpy array of voltages values
    """
    if datatype == "SCL":
      self.scl_data = data
      self.scl_sampling_period = self.sampling_period
      if self.sda_data is None:
        with open(self.scl_data_path, "w") as f:
          f.write(self.start_time.as_datetime().__str__().split(".")[0] + "\t" +
                  self.start_time.__str__().split(".")[1] + "\n")
          f.write(self.sampling_period.__str__() + "\n")
          f.write(self.f_clk.__str__() + "\n")
          np.savetxt(f, data)
        self.scl_start_time = self.start_time
      else:
        dt = self.start_time.as_datetime().__str__().split(".")[0]
        dt = datetime.datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
        subms = self.start_time.__str__().split(".")[1]
        ms, us = int(subms[0:3]), int(subms[3:6])
        ns, ps = int(subms[6:9]), int(subms[9:12])
        self.scl_start_time = GraphTime(dt, millisecond=ms, microsecond=us,
                                        nanosecond=ns, picosecond=ps)

    elif datatype == "SDA":
      self.sda_data = data
      self.sda_sampling_period = self.sampling_period
      if self.scl_data is None:
        with open(self.sda_data_path, "w") as f:
          f.write(self.start_time.as_datetime().__str__().split(".")[0] + "\t" +
                  self.start_time.__str__().split(".")[1] + "\n")
          f.write(self.sampling_period.__str__() + "\n")
          np.savetxt(f, data)
        self.sda_start_time = self.start_time
      else:
        dt = self.start_time.as_datetime().__str__().split(".")[0]
        dt = datetime.datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
        subms = self.start_time.__str__().split(".")[1]
        ms, us = int(subms[0:3]), int(subms[3:6])
        ns, ps = int(subms[6:9]), int(subms[9:12])
        self.sda_start_time = GraphTime(dt, millisecond=ms, microsecond=us,
                                        nanosecond=ns, picosecond=ps)

  def match_start_end_time(self):
    """Match start time and end time of SDA and SCL.

    Find overlap region of the two captures

    Raises:
      Exception:  SDA and SCL data time range is not overlapped
    """
    if self.scl_start_time > self.sda_start_time:
      delta_s = (self.scl_start_time - self.sda_start_time).__float__()
      delta_s = round(delta_s / self.sda_sampling_period)
      self.sda_data = self.sda_data[delta_s:]
    else:
      delta_s = (self.sda_start_time - self.scl_start_time).__float__()
      delta_s = round(delta_s / self.scl_sampling_period)
      self.scl_data = self.scl_data[delta_s:]

    if len(self.scl_data) < len(self.sda_data):
      delta_e = len(self.sda_data) - len(self.scl_data)
      if delta_e != 0:
        self.sda_data = self.sda_data[:-delta_e]
    else:
      delta_e = len(self.scl_data) - len(self.sda_data)
      if delta_e != 0:
        self.scl_data = self.scl_data[:-delta_e]

    if (not self.sda_data.any()) or (not self.scl_data.any()):
      raise Exception(
          "SDA data range and SCL data range needs to be overlapped!"
          "Please capture again.")

  def add_measurement(self, measure_field, field, new_result):
    """Compare with exist measurement.

    Args:
      measure_field: measure value for each SPEC parameter
      field: specific parameter field
      new_result: new measurement to compare

    Returns:
      measure_field: measure value for each SPEC parameter
    """
    if measure_field.get(field + "_max"):
      if measure_field[field + "_max"][1] < new_result[1]:
        measure_field[field + "_max"] = new_result
      elif measure_field[field + "_min"][1] > new_result[1]:
        measure_field[field + "_min"] = new_result
    else:
      measure_field[field + "_max"] = new_result
      measure_field[field + "_min"] = new_result

    return measure_field

  def measure_both_scl_sda(self):
    """When both SCL and SDA data is provided.

    Returns:
      measure_field: measure value for each SPEC parameter
      addr_list: device address included in the capture
    """
    measure_field = {}
    addr_list = []
    sda = Logic()
    scl = Logic()
    scl.state = 1  # assume SCL initial state is HIGH
    read_flag = 0

    v_sda = self.sda_data[0]
    v_scl = self.scl_data[0]
    v_low_scl = []
    v_high_scl = []
    v_low_sda = []
    v_high_sda = []
    addr = ""
    for i in range(1, len(self.sda_data)):
      n_sda = self.sda_data[i]
      n_scl = self.scl_data[i]
      if ((v_scl >= self.v_30p and n_scl < self.v_30p) or
          (v_scl <= self.v_30p and n_scl > self.v_30p)):
        interpolation = (self.v_30p - n_scl) / (v_scl - n_scl)
        scl.i_30p = i - interpolation
        if scl.i_70p is not None:  # falling edge
          measure_field = self.add_measurement(
              measure_field, "t_fall_scl",
              [i - interpolation, scl.i_30p - scl.i_70p]
          )
          scl.low_start = scl.i_30p
          scl.state = 0
          scl.i_30p = scl.i_70p = None

          ## Don't take t_buf into T_clk consideration

          if scl.last_low_start is not None and self.data_start_flag:
            measure_field = self.add_measurement(
                measure_field, "T_clk",
                [i - interpolation, scl.low_start - scl.last_low_start]
            )
          scl.last_low_start = scl.low_start

          ## Finish one package in 9 SCL clk cycles, check finish at clk LOW

          if self.data_start_flag == 9:
            self.data_start_flag = 0
            if self.first_packet:
              addr_list.append(addr)
              self.first_packet = 0

        else:  # rising edge
          scl.low_end = scl.i_30p
          if scl.low_start is not None:
            if v_low_scl:
              measure_field = self.add_measurement(
                  measure_field, "v_low_scl",
                  [i - interpolation, np.median(v_low_scl),
                   scl.low_end - scl.low_start]
              )
              v_low_scl = []
            measure_field = self.add_measurement(
                measure_field, "t_low",
                [i - interpolation, scl.low_end - scl.low_start]
            )
          scl.state = None

      if ((v_scl >= self.v_70p and n_scl < self.v_70p) or
          (v_scl <= self.v_70p and n_scl > self.v_70p)):
        interpolation = (self.v_70p - n_scl) / (v_scl - n_scl)
        scl.i_70p = i - interpolation
        if scl.i_30p is not None:  # rising edge
          measure_field = self.add_measurement(
              measure_field, "t_rise_scl",
              [i - interpolation, scl.i_70p - scl.i_30p]
          )
          scl.high_start = scl.i_70p
          scl.state = 1
          scl.i_30p = scl.i_70p = None

          ## Don't take t_buf into T_clk consideration

          if scl.last_high_start is not None and self.data_start_flag:
            measure_field = self.add_measurement(
                measure_field, "T_clk",
                [i - interpolation, scl.high_start - scl.last_high_start]
            )
          scl.last_high_start = scl.high_start
          if ((self.restart_flag or self.start_flag) and
              not self.data_start_flag):
            self.data_start_flag = 1
          elif self.data_start_flag:
            self.data_start_flag += 1  # count SCL clk cycle at HIGH

        else:  # falling edge
          scl.high_end = scl.i_70p
          if scl.high_start is not None:
            if v_high_scl:
              measure_field = self.add_measurement(
                  measure_field, "v_high_scl",
                  [i - interpolation, np.median(v_high_scl),
                   scl.high_end - scl.high_start]
              )
              v_high_scl = []
            measure_field = self.add_measurement(
                measure_field, "t_high",
                [i - interpolation, scl.high_end - scl.high_start]
            )

          ## check Read/Write at 8th SCL clk cycle

          if (self.first_packet and
              (self.data_start_flag == 8 and sda.state == 1)):
            read_flag = 1

          if self.first_packet and (0 < self.data_start_flag < 8):
            if sda.state:
              addr += "1"
            else:
              addr += "0"
          scl.state = None

      if ((v_sda >= self.v_30p and n_sda < self.v_30p) or
          (v_sda <= self.v_30p and n_sda > self.v_30p)):
        interpolation = (self.v_30p - n_sda) / (v_sda - n_sda)
        sda.i_30p = i - interpolation
        if sda.i_70p is not None:  # falling edge
          measure_field = self.add_measurement(
              measure_field, "t_fall_sda",
              [i - interpolation, sda.i_30p - sda.i_70p]
          )
          sda.low_start = sda.i_30p
          sda.state = 0
          sda.i_30p = sda.i_70p = None

        else:  # rising edge
          sda.low_end = sda.i_30p
          if v_low_sda and sda.low_start:
            measure_field = self.add_measurement(
                measure_field, "v_low_sda",
                [i - interpolation, np.median(v_low_sda),
                 sda.low_end - sda.low_start]
            )
            v_low_sda = []
          sda.state = None

      if ((v_sda >= self.v_70p and n_sda < self.v_70p) or
          (v_sda <= self.v_70p and n_sda > self.v_70p)):
        interpolation = (self.v_70p - n_sda) / (v_sda - n_sda)
        sda.i_70p = i - interpolation
        if sda.i_30p is not None:  # rising edge
          measure_field = self.add_measurement(
              measure_field, "t_rise_sda",
              [i - interpolation, sda.i_70p - sda.i_30p]
          )
          sda.high_start = sda.i_70p
          sda.state = 1
          sda.i_30p = sda.i_70p = None

        else:  # falling edge
          sda.high_end = sda.i_70p
          if v_high_sda and sda.high_start:
            measure_field = self.add_measurement(
                measure_field, "v_high_sda",
                [i - interpolation, np.median(v_high_sda),
                 sda.high_end - sda.high_start]
            )
            v_high_sda = []
          sda.state = None

      if ((scl.state == 0) and sda.high_end is not None and
          (math.ceil(sda.high_end) == i) and self.data_start_flag):
        if ((self.first_packet and self.data_start_flag == 9) or
            (not self.first_packet and read_flag and
             self.data_start_flag != 9)):
          measure_field = self.add_measurement(
              measure_field, "t_HD_DAT_falling_dev",
              [i - interpolation, sda.high_end - scl.low_start]
          )
        else:
          measure_field = self.add_measurement(
              measure_field, "t_HD_DAT_falling_host",
              [i - interpolation, sda.high_end - scl.low_start]
          )

      if ((scl.state == 0) and sda.low_end is not None and
          (math.ceil(sda.low_end) == i) and self.data_start_flag):
        if ((self.first_packet and self.data_start_flag == 9) or
            (not self.first_packet and read_flag and
             self.data_start_flag != 9)):
          measure_field = self.add_measurement(
              measure_field, "t_HD_DAT_rising_dev",
              [i - interpolation, sda.low_end - scl.low_start]
          )
        else:
          measure_field = self.add_measurement(
              measure_field, "t_HD_DAT_rising_host",
              [i - interpolation, sda.low_end - scl.low_start]
          )

      if ((sda.state == 0) and scl.low_end is not None and
          (math.ceil(scl.low_end) == i) and
          ((scl.low_start is None) or (scl.low_start < sda.low_start)) and
          self.data_start_flag):
        if ((self.first_packet and self.data_start_flag == 8) or
            (not self.first_packet and read_flag and
             self.data_start_flag != 8)):
          measure_field = self.add_measurement(
              measure_field, "t_SU_DAT_falling_dev",
              [i - interpolation, scl.low_end - sda.low_start]
          )
        else:
          measure_field = self.add_measurement(
              measure_field, "t_SU_DAT_falling_host",
              [i - interpolation, scl.low_end - sda.low_start]
          )
      if ((sda.state == 1) and scl.low_end is not None and
          (math.ceil(scl.low_end) == i) and
          ((scl.low_start is None) or (scl.low_start < sda.high_start)) and
          self.data_start_flag):
        if ((self.first_packet and self.data_start_flag == 8) or
            (not self.first_packet and read_flag and
             self.data_start_flag != 8)):
          measure_field = self.add_measurement(
              measure_field, "t_SU_DAT_rising_dev",
              [i - interpolation, scl.low_end - sda.high_start]
          )
        else:
          measure_field = self.add_measurement(
              measure_field, "t_SU_DAT_rising_host",
              [i - interpolation, scl.low_end - sda.high_start]
          )

      if ((scl.state == 1) and sda.high_end is not None and
          (math.ceil(sda.high_end) == i)):
        if not self.stop_flag:  # Sr
          self.restart_flag = 1
          self.first_packet = 1
          self.start_flag = 0
          self.data_start_flag = 0
          addr = ""
          measure_field = self.add_measurement(
              measure_field, "t_SU_STA",
              [i - interpolation, sda.high_end-scl.high_start]
          )
        else:  # S
          self.start_flag = 1
          self.first_packet = 1
          self.stop_flag = 0
          self.data_start_flag = 0
          addr = ""
          if sda.high_start is not None:
            measure_field = self.add_measurement(
                measure_field, "t_BUF",
                [i - interpolation, sda.high_end-sda.high_start]
            )

      if ((sda.state == 0) and scl.high_end is not None and
          (math.ceil(scl.high_end) == i) and
          ((scl.high_start is None) or (scl.high_start < sda.low_start))):
        if self.restart_flag:
          measure_field = self.add_measurement(
              measure_field, "t_HD_STA_Sr",
              [i - interpolation, scl.high_end - sda.low_start]
          )
        elif self.start_flag:
          measure_field = self.add_measurement(
              measure_field, "t_HD_STA_S",
              [i - interpolation, scl.high_end - sda.low_start]
          )

      if ((scl.state == 1) and sda.low_end is not None and
          (math.ceil(sda.low_end) == i) and
          scl.high_start is not None):
        self.stop_flag = 1
        read_flag = 0
        self.restart_flag = self.start_flag = 0
        measure_field = self.add_measurement(
            measure_field, "t_SU_STO",
            [i - interpolation, sda.low_end - scl.high_start]
        )

      # Constrain: captured data should include START or RESTART pattern

      if (scl.state == 0) and not self.stop_flag:
        v_low_scl.append(n_scl)
      elif (scl.state == 1) and not self.stop_flag:
        v_high_scl.append(n_scl)
      if (sda.state == 0) and self.data_start_flag:
        v_low_sda.append(n_sda)
      elif (sda.state == 1) and self.data_start_flag:
        v_high_sda.append(n_sda)

      v_sda = n_sda
      v_scl = n_scl

    return measure_field, addr_list

  def get_spec_limitation(self, mode, vs):
    """Get SPEC limitation according to mode.

    Args:
      mode: operation mode (Standard mode/Fast Mode/Fast Mode Plus)
      vs: working voltage

    Returns:
      spec_limit: limitation for each parameter
    """
    spec_limit_sm = {
        "v_low": 0.3 * vs, "v_high": 0.7 * vs, "v_nh": 0.2, "v_nl": 0.1,
        "t_rise_max": 1e-6, "t_fall_max": 3e-7, "t_low": 4.7e-6, "t_high": 4e-6,
        "f_clk": 1e5, "t_SU_DAT": 2.5e-7, "t_HD_DAT": 3.45e-6, "t_HD_STA": 4e-6,
        "t_SU_STA": 4.7e-6, "t_SU_STO": 4e-6, "t_BUF": 4.7e-6
    }
    spec_limit_fm = {
        "v_low": 0.3 * vs, "v_high": 0.7 * vs, "v_nh": 0.2, "v_nl": 0.1,
        "t_rise_max": 3e-7, "t_rise_min": 2e-8, "t_fall_max": 3e-7,
        "t_fall_min": 20 * vs / 5.5 * 1e-9, "t_low": 1.3e-6, "t_high": 6e-7,
        "f_clk": 4e5, "t_SU_DAT": 1e-7, "t_HD_DAT": 9e-7, "t_HD_STA": 6e-7,
        "t_SU_STA": 6e-7, "t_SU_STO": 6e-7, "t_BUF": 1.3e-6
    }
    spec_limit_fmp = {
        "v_low": 0.3 * vs, "v_high": 0.7 * vs, "v_nh": 0.2, "v_nl": 0.1,
        "t_rise_max": 1.2e-7, "t_fall_max": 1.2e-7,
        "t_fall_min": 20 * vs / 5.5 * 1e-9, "t_low": 5e-7, "t_high": 2.6e-7,
        "f_clk": 1e6, "t_SU_DAT": 5e-8, "t_HD_STA": 2.6e-7, "t_SU_STA": 2.6e-7,
        "t_SU_STO": 2.6e-7, "t_BUF": 5e-7
    }

    # Check Only Voltage SPEC Constrain If Can't Determine SPEC Mode yet

    spec_limit = {
        "v_nh": 0.2, "v_nl": 0.1, "v_low": 0.3 * vs, "v_high": 0.7 * vs
    }

    if mode == "Standard Mode":
      spec_limit = spec_limit_sm
    elif mode == "Fast Mode":
      spec_limit = spec_limit_fm
    elif mode == "Fast Mode Plus":
      spec_limit = spec_limit_fmp

    return spec_limit

  def check_spec(self, spec_limit, measure_field, vs):
    """Check SPEC with each parameters.

    Args:
      spec_limit: spec limitation of each parameter
      measure_field: all measurement of each parameter
      vs: working voltage

    Returns:
      values: max, min, worst measurement of each parameter
      result: pass/fail, margin of each parameter
      svgwidth: worst case width for SVG plot
    """
    values = {}
    result = {}
    svgwidth = {}

    fields1 = ["v_high_scl", "v_low_scl", "v_high_sda", "v_low_sda"]
    for f in fields1:
      ff = "_".join(f.split("_")[:-1])
      if (self.requested_measurements[f + "_worst"] and
          measure_field.get(f + "_max") and measure_field.get(f + "_min")):

        values[f + "_max"] = measure_field[f + "_max"][1]
        values[f + "_min"] = measure_field[f + "_min"][1]
        if "high" in f:
          values[f + "_worst"] = values[f + "_min"]
          result[f + "_idx"] = measure_field[f + "_min"][0]
          result[f + "_margin"] = values[f + "_worst"] - spec_limit[ff]
          svgwidth[f] = measure_field[f + "_min"][2]
        elif "low" in f:
          values[f + "_worst"] = values[f + "_max"]
          result[f + "_idx"] = measure_field[f + "_max"][0]
          result[f + "_margin"] = spec_limit[ff] - values[f + "_worst"]
          svgwidth[f] = measure_field[f + "_max"][2]
        result[f + "_percent"] = result[f + "_margin"] / spec_limit[ff] * 100

    fields2 = ["v_nh_scl", "v_nl_scl", "v_nh_sda", "v_nl_sda"]
    for f in fields2:
      ff = f.replace("nh", "high").replace("nl", "low")
      ff2 = "_".join(f.split("_")[:-1])
      if (self.requested_measurements[f + "_worst"] and
          measure_field[ff + "_max"] and measure_field[ff + "_min"]):
        if "nh" in f:
          values[f + "_max"] = (values[ff + "_max"] - self.v_70p) / vs
          values[f + "_min"] = (values[ff + "_min"] - self.v_70p) / vs
        elif "nl" in f:
          values[f + "_max"] = (self.v_30p - values[ff + "_min"]) / vs
          values[f + "_min"] = (self.v_30p - values[ff + "_max"]) / vs
        values[f + "_worst"] = values[f + "_min"]
        result[f + "_idx"] = result[ff + "_idx"]
        svgwidth[f] = svgwidth[ff]
        if values[f + "_worst"] >= spec_limit[ff2]:
          result[f] = 0
        else:
          result[f] = 1
        result[f + "_margin"] = values[f + "_worst"] - spec_limit[ff2]
        result[f + "_percent"] = result[f + "_margin"] / spec_limit[ff2] * 100

    if (self.requested_measurements["f_clk_worst"] and
        measure_field.get("T_clk_max") and measure_field.get("T_clk_min")):
      t_clk_min = measure_field["T_clk_min"][1] * self.scl_sampling_period
      values["f_clk_max"] = 1 / t_clk_min
      t_clk_max = measure_field["T_clk_max"][1] * self.scl_sampling_period
      values["f_clk_min"] = 1 / t_clk_max
      values["f_clk_worst"] = values["f_clk_max"]
      result["f_clk_idx"] = measure_field["T_clk_min"][0]
      svgwidth["f_clk"] = measure_field["T_clk_min"][1]
      if int(values["f_clk_worst"]) <= spec_limit["f_clk"]:
        result["f_clk"] = 0
      else:
        result["f_clk"] = 1
      result["f_clk_margin"] = int(spec_limit["f_clk"] - values["f_clk_worst"])
      result["f_clk_percent"] = (
          result["f_clk_margin"] / spec_limit["f_clk"] * 100
      )

    fields3 = ["t_rise_sda", "t_rise_scl", "t_fall_sda", "t_fall_scl"]
    for f in fields3:
      if(self.requested_measurements[f + "_worst"] and
         measure_field.get(f + "_max") and measure_field.get(f + "_min")):
        values[f + "_max"] = (
            measure_field[f + "_max"][1] * self.sampling_period)
        values[f + "_min"] = (
            measure_field[f + "_min"][1] * self.sampling_period)
        ff = "_".join(f.split("_")[:-1])
        if spec_limit.get(ff + "_max") is not None:
          if spec_limit.get(ff + "_min") is None:
            limit_min = np.NINF
          else:
            limit_min = spec_limit[ff + "_min"]
          if (values[f + "_max"] <= spec_limit[ff + "_max"] and
              values[f + "_min"] >= limit_min):
            result[f] = 0
          else:
            result[f] = 1
          if (spec_limit[ff + "_max"] - values[f + "_max"] <
              values[f + "_min"] - limit_min):
            values[f + "_worst"] = values[f + "_max"]
            result[f + "_idx"] = measure_field[f + "_max"][0]
            svgwidth[f] = measure_field[f + "_max"][1]
            result[f + "_margin"] = spec_limit[ff + "_max"] - values[f + "_max"]
            result[f + "_percent"] = (
                result[f + "_margin"] / spec_limit[ff + "_max"] * 100)
          else:
            values[f + "_worst"] = values[f + "_min"]
            result[f + "_idx"] = measure_field[f + "_min"][0]
            svgwidth[f] = measure_field[f + "_min"][1]
            result[f + "_margin"] = values[f + "_min"] - limit_min
            result[f + "_percent"] = result[f + "_margin"] / limit_min * 100
        else:  # to show rise/fall time value when only SDA is captured
          values[f + "_worst"] = values[f + "_max"]

    fields4 = [
        "t_low", "t_high", "t_SU_STA", "t_SU_STO", "t_BUF", "t_HD_STA_S",
        "t_HD_STA_Sr", "t_SU_DAT_rising_host", "t_SU_DAT_falling_host",
        "t_SU_DAT_rising_dev", "t_SU_DAT_falling_dev"
    ]
    for f in fields4:
      if(self.requested_measurements[f + "_worst"] and
         measure_field.get(f + "_max") and measure_field.get(f + "_min")):
        if f in ["t_low", "t_high", "t_SU_STA", "t_SU_STO", "t_BUF"]:
          ff = f
        elif f in ["t_HD_STA_S", "t_HD_STA_Sr"]:
          ff = "_".join(f.split("_")[:-1])
        else:
          ff = "_".join(f.split("_")[:-2])
        values[f + "_max"] = (
            measure_field[f + "_max"][1] * self.scl_sampling_period)
        values[f + "_min"] = (
            measure_field[f + "_min"][1] * self.scl_sampling_period)
        values[f + "_worst"] = values[f + "_min"]
        result[f + "_idx"] = measure_field[f + "_min"][0]
        svgwidth[f] = measure_field[f + "_min"][1]
        if values[f + "_worst"] >= spec_limit[ff]:
          result[f] = 0
        else:
          result[f] = 1
        result[f + "_margin"] = values[f + "_worst"] - spec_limit[ff]
        result[f + "_percent"] = result[f + "_margin"] / spec_limit[ff] * 100

    fields5 = [
        "t_HD_DAT_rising_host", "t_HD_DAT_falling_host", "t_HD_DAT_rising_dev",
        "t_HD_DAT_falling_dev"
    ]
    for f in fields5:
      if(self.requested_measurements[f + "_worst"] and
         measure_field.get(f + "_max") and measure_field.get(f + "_min")):
        ff = "_".join(f.split("_")[:-2])
        values[f + "_max"] = (
            measure_field[f + "_max"][1] * self.scl_sampling_period)
        values[f + "_min"] = (
            measure_field[f + "_min"][1] * self.scl_sampling_period)
        if spec_limit.get(ff) is None:
          limit_max = np.inf
        else:
          limit_max = spec_limit[ff]
        if values[f + "_min"] >= 0 and values[f + "_max"] <= limit_max:
          result[f] = 0
        else:
          result[f] = 1
        if values[f + "_min"] - 0 < limit_max - values[f + "_max"]:
          values[f + "_worst"] = values[f + "_min"]
          result[f + "_idx"] = measure_field[f + "_min"][0]
          svgwidth[f] = measure_field[f + "_min"][1]
          result[f + "_margin"] = values[f + "_min"] - 0
        else:
          values[f + "_worst"] = values[f + "_max"]
          result[f + "_idx"] = measure_field[f + "_max"][0]
          svgwidth[f] = measure_field[f + "_max"][1]
          result[f + "_margin"] = limit_max - values[f + "_max"]
        result[f + "_percent"] = result[f + "_margin"]/limit_max * 100

    return values, result, svgwidth

  def get_svg_fields(self, result, svgwidth, vs):
    """Save SVG Data for Each parameter.

    Calculate Max/Min Value for Plot Boundary
    Then generate svg plot for each parameter

    Args:
      result: get start idx of worst waveform
      svgwidth: get width of worst waveform
      vs: working voltage, for 30p and 70p marker on plot

    Returns:
      svg_fields: svg plots to draw on html report
    """
    if self.scl_data is not None:
      scl_v_max = np.max(self.scl_data)
      scl_v_min = np.min(self.scl_data)
    if self.sda_data is not None:
      sda_v_max = np.max(self.sda_data)
      sda_v_min = np.min(self.sda_data)

    svg_fields = {}
    svg_fields["scl"] = SVGFile(
        self.scl_data, scl_v_max, scl_v_min, None, None, "scl_show", vs
    )
    svg_fields["sda"] = SVGFile(
        self.sda_data, sda_v_max, sda_v_min, None, None, "sda_show", vs
    )
    rate = min(max(len(self.scl_data) // 1000, 1), 180)

    fields1 = [
        "v_low_scl", "v_high_scl", "t_rise_scl", "t_fall_scl", "t_low",
        "t_high", "f_clk", "v_nl_scl", "v_nh_scl"
    ]
    for f in fields1:
      if result.get(f + "_idx"):
        idx = result[f + "_idx"]
        start_idx = math.floor(
            max(0, min(idx - 1000, len(self.scl_data) - 2000))
        )
        end_idx = math.ceil(min(len(self.scl_data), max(idx + 1000, 2000)))
        svg_fields[f] = SVGFile(
            self.scl_data[start_idx:end_idx], scl_v_max, scl_v_min,
            idx - start_idx, svgwidth[f], f, vs
        )
        rect_width = max(svgwidth[f] // rate * 5, 40)
        rect_x = idx // rate * 5 - rect_width
        mid_x = rect_x + rect_width // 2
        svg_fields["scl"] += (
            f"<rect id='{f}_rect' x={rect_x} y='0' width={rect_width} height=100% class='rect hide'/>"
            f"<line id='{f}_line' x1={mid_x} y1=0 x2={mid_x} y2=60 class='arrowline'/>"
            f"<polygon id='{f}_poly' points='{mid_x - 50} 50, {mid_x} 110, {mid_x + 50} 50' class='arrow'/>"
        )

    fields2 = [
        "v_low_sda", "v_high_sda", "t_rise_sda", "t_fall_sda", "v_nl_sda",
        "v_nh_sda"
    ]
    for f in fields2:
      if result.get(f + "_idx"):
        idx = result[f + "_idx"]
        start_idx = math.floor(
            max(0, min(idx - 1000, len(self.sda_data) - 2000))
        )
        end_idx = math.ceil(min(len(self.sda_data), max(idx + 1000, 2000)))
        svg_fields[f] = SVGFile(
            self.sda_data[start_idx:end_idx], sda_v_max, sda_v_min,
            idx - start_idx, svgwidth[f], f, vs
        )
        rect_width = max(svgwidth[f] // rate * 5, 40)
        rect_x = idx // rate * 5 - rect_width
        mid_x = rect_x + rect_width // 2
        svg_fields["sda"] += (
            f"<rect id='{f}_rect' x={rect_x} y='0' width={rect_width} height=100% class='rect hide'/>"
            f"<line id='{f}_line' x1={mid_x} y1=0 x2={mid_x} y2=60 class='arrowline'/>"
            f"<polygon id='{f}_poly' points='{mid_x - 50} 50, {mid_x} 110, {mid_x + 50} 50' class='arrow'/>"
        )

    fields3 = [
        "t_SU_DAT_rising_host", "t_SU_DAT_falling_host",
        "t_HD_DAT_rising_host", "t_HD_DAT_falling_host",
        "t_SU_DAT_rising_dev", "t_SU_DAT_falling_dev",
        "t_HD_DAT_rising_dev", "t_HD_DAT_falling_dev",
        "t_HD_STA_S", "t_HD_STA_Sr", "t_SU_STA", "t_SU_STO", "t_BUF"
    ]
    for f in fields3:
      if result.get(f + "_idx"):
        idx = result[f + "_idx"]
        start_idx = math.floor(
            max(0, min(idx - 1000, len(self.scl_data) - 2000))
        )
        end_idx = math.ceil(min(len(self.scl_data), max(idx + 1000, 2000)))
        svg_fields[f + "_scl"] = SVGFile(
            self.scl_data[start_idx:end_idx], scl_v_max, scl_v_min,
            idx - start_idx, svgwidth[f], f + "_scl", vs
        )
        svg_fields[f + "_sda"] = SVGFile(
            self.sda_data[start_idx:end_idx], sda_v_max, sda_v_min,
            idx - start_idx, svgwidth[f], f + "_sda", vs
        )
        rect_width = max(svgwidth[f] // rate * 5, 40)
        rect_x = idx // rate * 5 - rect_width
        mid_x = rect_x + rect_width // 2
        svg_fields["scl"] += (
            f"<rect id='{f}_scl_rect' x={rect_x} y='0' width={rect_width} height=100% class='rect hide'/>"
            f"<line id='{f}_line' x1={mid_x} y1=0 x2={mid_x} y2=60 class='arrowline'/>"
            f"<polygon id='{f}_poly' points='{mid_x - 50} 50, {mid_x} 110, {mid_x + 50} 50' class='arrow'/>"
        )
        svg_fields["sda"] += (
            f"<rect id='{f}_sda_rect' x={rect_x} y='0' width={rect_width} height=100%"
            f" class='rect hide''/>"
        )
    svg_fields["scl"] += "</svg></div></div>"
    svg_fields["sda"] += "</svg></div></div>"

    return svg_fields

  def measure(self):
    """Measure.

    This method is called after all the relevant data has been passed
    to process_data function. It returns a dictionary of the required
    measurements values.

    Returns:
      values: dictionary of request_measurements values
    """
    data = np.concatenate(self.samples)

    vs = self.determine_working_voltage(data)
    datatype = self.determine_datatype(data)
    mode = None
    if self.f_clk is not None:  # Read from 1st SCL capture
      mode = self.determine_operation_mode()

    self.process_1st_2nd_capture(datatype, data)
    if self.sda_data is not None and self.scl_data is not None:
      self.match_start_end_time()
    else:
      return {"spec": 0}

    ################### find SPEC value ##############################
    # Constrain: should capture from START pattern

    supported_measurements = [
        "t_rise_sda", "t_rise_scl", "t_fall_sda", "t_fall_scl", "t_low",
        "t_high", "t_SU_DAT_rising_host", "t_SU_DAT_falling_host",
        "t_HD_DAT_rising_host", "t_HD_DAT_falling_host",
        "t_SU_DAT_rising_dev", "t_SU_DAT_falling_dev", "t_HD_DAT_rising_dev",
        "t_HD_DAT_falling_dev", "t_HD_STA_Sr", "t_HD_STA_S", "t_SU_STA",
        "t_SU_STO", "t_BUF"
    ]
    if any(k.split("_worst")[0] in supported_measurements
           for k in self.requested_measurements):
      measure_field, addr_list = self.measure_both_scl_sda()

    ################### check SPEC limitation ##############################

    spec_limit = self.get_spec_limitation(mode, vs)
    values, result, svgwidth = self.check_spec(spec_limit, measure_field, vs)

    fail = {}
    if self.requested_measurements["spec"]:
      fail = {param: result for (param, result) in result.items()
              if ((result == 1) and ("_margin" not in param) and
                  ("_percent" not in param) and ("_idx" not in param))}
      passes = {param: result for (param, result) in result.items()
                if ((result == 0) and ("_margin" not in param) and
                    ("_percent" not in param) and ("_idx" not in param))}
      num_pass = len(passes)
      values["spec"] = len(fail)

    ############### Generate and Show Report ##############

    uni_addr = list(set(addr_list))
    uni_addr = [f"0x{int(addr, 2):02X}" for addr in uni_addr]

    sampling_rate = round(1 / self.sampling_period * 1e-6)
    svg_fields = self.get_svg_fields(result, svgwidth, vs)
    report_path = OutputReportFile(
        mode, spec_limit.copy(), vs, values.copy(), result.copy(),
        fail.copy(), num_pass, svg_fields, uni_addr, sampling_rate)
    subprocess.run(["open", report_path], check=True)

    return values
