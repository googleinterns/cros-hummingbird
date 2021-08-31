"""HummingBird I2C Eletrical Test Automation.

The project serves as an extension measurement module
run on Saleae Logic2 Software. Supporting main function
would be running I2C electrical test on capture data.

"""
import csv
import math
import os
import sys

from generate_report import OutputReportFile
from generate_report import SVGFile
import numpy as np


class Logic():
  """Logic State.

  Specify the logic state of the analog dataline.
  Transition between state HIGH and state LOW
  would be 30% Vdd and 70% Vdd

  Attributes:
    i_30p: index achieve 30% Vdd
    i_70p: index achieve 70% Vdd
    high_start: index where state HIGH begin
    high_end: index where state HIGH end
    low_start: index where state LOW begin
    low_end: index where state LOW end
    state: current logic state of the dataline. (three states: 1 / 0 / None)
    last_low_start: index where last time state LOW start
    last_high_start: index where last time state HIGH start
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


class HummingBird():
  """Main measurement module.

  This is the main module called by Saleae measurement API.

  Attributes:
    stop_flag: STOP pattern detected,
               raise to 1 until START pattern
    start_flag: START pattern detected,
                remain 1 until STOP or RESTART pattern
    restart_flag: RESTART pattern detected,
                  remain 1 until STOP pattern
    data_start_flag: from the first SCL clock cycle after START
                     or RESTART pattern, remain 1 for one packet
                     (9 SCL clock cycles)
    first_packet: the first packet after START or RESTART pattern
    csv_data_path: data csv file to measure
    save_folder: report save folder

    sampling_period: SCL data sampling period
    f_clk: SCL clock frequency
    vs: working voltage
    mode: operation mode
    data_list: data load from csv file
    scl_data: SCL data
    sda_data: SDA data
    v_30p: threshold reference point for state LOW
    v_70p: threshold reference point for state HIGH

    scl_rising_edge: number of SCL rising edge
    scl_falling_edge: number of SCL falling edge
    sda_rising_edge: number of SDA rising edge
    sda_falling_edge: number of SDA falling edge
    start_num: number of START pattern
    restart_num: number of RESTART pattern
    stop_num: number of STOP pattern
  """

  def __init__(self, csv_data_path, save_folder=None, vs=None, mode=None):
    """Initialization.

    Initialize your measurement extension here
    Each measurement object will only be used once,
    all pre-measurement initialization are here

    Args:
      csv_data_path: csv file to measure
      save_folder: output report path
      vs: working voltage
      mode: operation mode
    """
    super().__init__()

    self.stop_flag = 1
    self.start_flag = 0
    self.restart_flag = 0
    self.data_start_flag = None
    self.first_packet = 0

    # Calculate number of edges, start, stop

    self.scl_rising_edge = 0
    self.scl_falling_edge = 0
    self.sda_rising_edge = 0
    self.sda_falling_edge = 0
    self.start_num = 0
    self.restart_num = 0
    self.stop_num = 0

    self.csv_data_path = csv_data_path
    self.save_folder = save_folder
    self.vs = vs
    self.mode = mode
    self.data_list = None
    if os.path.isfile(self.csv_data_path):
      with open(self.csv_data_path, "r") as f:
        data_iter = csv.reader(f, delimiter=",")
        next(data_iter)  # skip header
        self.data_list = np.array(list(data_iter), dtype=np.float64)

    if vs is not None:
      self.v_30p = vs * 0.3
      self.v_70p = vs * 0.7
    else:
      self.v_30p = None
      self.v_70p = None
    self.sampling_period = self.data_list[1, 0] - self.data_list[0, 0]

  def max_of_filtered_arr(self, data, threshold=1):
    """Return the maximum value of the filtered array.

    Remove glitch or spike (voltage difference between
    two sample points larger than 1V) per 0.1us segment
    Return the maximum value of the filtered array

    Args:
      data: raw voltage data
      threshold: difference larger than threshold would be removed
                 (default: 1V)

    Returns:
      maxx: the maxium voltage of the filtered data
    """
    length = round(1e-7 / self.sampling_period)
    segments = min(len(data) // length, 2000)
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

  def determine_datatype(self, data1, data2):
    """Determine Data Type.

    Read the first five cycles to determine data type
    Consider different sampling rate use direct time info
    SCL should has larger frequency than SDA

    Constrain: should capture at least five SCL clk cycles

    Args:
      data1: numpy array of voltages values, unknown type
      data2: numpy array of voltages values, unknown type
    """
    dataline1 = Logic()
    dataline2 = Logic()
    clk_dataline1 = []
    clk_dataline2 = []
    v1 = data1[0]
    v2 = data2[0]
    first_data_start = None
    for i in range(1, len(data1)):
      n1 = data1[i]
      n2 = data2[i]
      if ((v1 >= self.v_30p and n1 < self.v_30p) or
          (v1 <= self.v_30p and n1 > self.v_30p)):
        dataline1.i_30p = i
        if dataline1.i_70p is not None:  # falling edge
          dataline1.low_start = dataline1.i_30p
          dataline1.i_30p = dataline1.i_70p = None

          if dataline1.last_low_start is not None:
            clk_dataline1.append(dataline1.low_start - dataline1.last_low_start)
          elif first_data_start is None:
            first_data_start = i
          dataline1.last_low_start = dataline1.low_start

      if ((v1 >= self.v_70p and n1 < self.v_70p) or
          (v1 <= self.v_70p and n1 > self.v_70p)):
        dataline1.i_70p = i
        if dataline1.i_30p is not None:  # rising edge
          dataline1.high_start = dataline1.i_70p
          dataline1.i_30p = dataline1.i_70p = None

          if dataline1.last_high_start is not None:
            clk_dataline1.append(
                dataline1.high_start - dataline1.last_high_start
            )
          dataline1.last_high_start = dataline1.high_start

      if ((v2 >= self.v_30p and n2 < self.v_30p) or
          (v2 <= self.v_30p and n2 > self.v_30p)):
        dataline2.i_30p = i
        if dataline2.i_70p is not None:  # falling edge
          dataline2.low_start = dataline2.i_30p
          dataline2.i_30p = dataline2.i_70p = None

          if dataline2.last_low_start is not None:
            clk_dataline2.append(
                dataline2.low_start - dataline2.last_low_start
            )
          elif first_data_start is None:
            first_data_start = i
          dataline2.last_low_start = dataline2.low_start

      if ((v2 >= self.v_70p and n2 < self.v_70p) or
          (v2 <= self.v_70p and n2 > self.v_70p)):
        dataline2.i_70p = i
        if dataline2.i_30p is not None:  # rising edge
          dataline2.high_start = dataline2.i_70p
          dataline2.i_30p = dataline2.i_70p = None

          if dataline2.last_high_start is not None:
            clk_dataline2.append(
                dataline2.high_start - dataline2.last_high_start
            )
          dataline2.last_high_start = dataline2.high_start
      v1 = n1
      v2 = n2
      if len(clk_dataline1) >= 8 or len(clk_dataline2) >= 8:
        break

    # Trim from the first edge to the last edge
    # first_data_start: the first edge of data
    # first_data_end: the last edge of data

    first_data_end = None
    dataline1 = Logic()
    dataline2 = Logic()
    v1 = data1[-1]
    v2 = data2[-1]
    for i in range(len(data1)-2, 0, -1):
      n1 = data1[i]
      n2 = data2[i]
      if ((v1 >= self.v_30p and n1 < self.v_30p) or
          (v1 <= self.v_30p and n1 > self.v_30p)):
        dataline1.i_30p = i
        if dataline1.i_70p is not None:  # falling edge
          dataline1.i_30p = dataline1.i_70p = None

          if dataline1.last_low_start is None and first_data_end is None:
            first_data_end = i
            break

      if ((v1 >= self.v_70p and n1 < self.v_70p) or
          (v1 <= self.v_70p and n1 > self.v_70p)):
        dataline1.i_70p = i
        if dataline1.i_30p is not None:  # rising edge
          dataline1.i_30p = dataline1.i_70p = None

      if ((v2 >= self.v_30p and n2 < self.v_30p) or
          (v2 <= self.v_30p and n2 > self.v_30p)):
        dataline2.i_30p = i
        if dataline2.i_70p is not None:  # falling edge
          dataline2.i_30p = dataline2.i_70p = None

          if dataline2.last_low_start is None and first_data_end is None:
            first_data_end = i
            break

      if ((v2 >= self.v_70p and n2 < self.v_70p) or
          (v2 <= self.v_70p and n2 > self.v_70p)):
        dataline2.i_70p = i
        if dataline2.i_30p is not None:  # rising edge
          dataline2.i_30p = dataline2.i_70p = None
      v1 = n1
      v2 = n2

    if first_data_start is None and first_data_end is None:
      print("\nError! No edge detected! "
            "Please check the working voltage and the captured waveform.")
      sys.exit(0)
    first_data_start = int(first_data_start * 0.8)
    first_data_end = int(first_data_end * 0.8 + len(data1) * 0.2)
    if len(clk_dataline1) > len(clk_dataline2):
      # data1 = SCL, data2 = SDA
      self.f_clk = 1 / (np.min(clk_dataline1) * self.sampling_period)
      self.scl_data = data1[first_data_start:first_data_end]
      self.sda_data = data2[first_data_start:first_data_end]
      print("Detect column order:\tSCL, SDA")
    else:
      # data1 = SDA, data2 = SCL
      self.f_clk = 1 / (np.min(clk_dataline2) * self.sampling_period)
      self.scl_data = data2[first_data_start:first_data_end]
      self.sda_data = data1[first_data_start:first_data_end]
      print("Detect column order:\tSDA, SCL")

  def determine_operation_mode(self):
    """Determine Operation Mode.

    Using maximum f_clk from first five cycles to predict
    operation mode

    Returns:
      mode: operation mode (Standard mode / Fast Mode / Fast Mode Plus)
    """
    if self.f_clk < 1.1e5:
      mode = "Standard Mode"
    elif self.f_clk < 4.4e5:
      mode = "Fast Mode"
    elif self.f_clk < 1.1e6:
      mode = "Fast Mode Plus"

    return mode

  def add_measurement(self, measure_field, field, new_result):
    """Compare with exist measurement.

    Args:
      measure_field: measure value for each SPEC parameter
      field: the name of the parameter field
      new_result: new measurement to compare

    Returns:
      measure_field: measure value for each SPEC parameter
    """
    if "runt" in field:
      measure_max = measure_field.get(field)
      if measure_max:
        measure_field[field].append(new_result)
      else:
        measure_field[field] = [new_result]
    else:
      measure_max = measure_field.get(field + "_max")
      if measure_max:
        measure_min = measure_field.get(field + "_min")
        if measure_max[1] < new_result[1]:
          measure_max[:] = new_result.copy()
        elif measure_min[1] > new_result[1]:
          measure_min[:] = new_result.copy()
      else:
        measure_field[field + "_max"] = new_result.copy()
        measure_field[field + "_min"] = new_result.copy()

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
      if v_scl >= self.v_30p and n_scl < self.v_30p:  # falling edge
        interpolation = (self.v_30p - n_scl) / (v_scl - n_scl)
        scl.i_30p = i - interpolation
        if scl.i_70p is not None:
          measure_field = self.add_measurement(
              measure_field, "t_fall_scl",
              [i - interpolation, scl.i_30p - scl.i_70p]
          )
          self.scl_falling_edge += 1
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
        else:
          if (scl.i_30p - scl.low_end) * self.sampling_period > 1e-7:
            measure_field = self.add_measurement(
                measure_field, "runt_scl",
                [i - interpolation, scl.i_30p - scl.low_end]
            )

      elif v_scl <= self.v_30p and n_scl > self.v_30p:  # rising edge
        interpolation = (self.v_30p - n_scl) / (v_scl - n_scl)
        scl.i_30p = i - interpolation
        if scl.i_70p is None:
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

      if v_scl <= self.v_70p and n_scl > self.v_70p:  # rising edge
        interpolation = (self.v_70p - n_scl) / (v_scl - n_scl)
        scl.i_70p = i - interpolation
        if scl.i_30p is not None:
          measure_field = self.add_measurement(
              measure_field, "t_rise_scl",
              [i - interpolation, scl.i_70p - scl.i_30p]
          )
          self.scl_rising_edge += 1
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
        else:
          if (scl.i_70p - scl.high_end) * self.sampling_period > 1e-7:
            measure_field = self.add_measurement(
                measure_field, "runt_scl",
                [i - interpolation, scl.i_70p - scl.high_end]
            )

      elif v_scl >= self.v_70p and n_scl < self.v_70p:  # falling edge
        interpolation = (self.v_70p - n_scl) / (v_scl - n_scl)
        scl.i_70p = i - interpolation
        if scl.i_30p is None:
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

      if v_sda >= self.v_30p and n_sda < self.v_30p:  # falling edge
        interpolation = (self.v_30p - n_sda) / (v_sda - n_sda)
        sda.i_30p = i - interpolation
        if sda.i_70p is not None:
          measure_field = self.add_measurement(
              measure_field, "t_fall_sda",
              [i - interpolation, sda.i_30p - sda.i_70p]
          )
          self.sda_falling_edge += 1
          sda.low_start = sda.i_30p
          sda.state = 0
          sda.i_30p = sda.i_70p = None
        else:
          if (sda.i_30p - sda.low_end) * self.sampling_period > 1e-7:
            measure_field = self.add_measurement(
                measure_field, "runt_sda",
                [i - interpolation, sda.i_30p - sda.low_end]
            )

      elif v_sda <= self.v_30p and n_sda > self.v_30p:  # rising edge
        interpolation = (self.v_30p - n_sda) / (v_sda - n_sda)
        sda.i_30p = i - interpolation
        if sda.i_70p is None:
          sda.low_end = sda.i_30p
          if v_low_sda and sda.low_start:
            if sda.low_start < scl.low_start:
              measure_field = self.add_measurement(
                  measure_field, "v_low_sda",
                  [i - interpolation, np.median(v_low_sda),
                   sda.low_end - sda.low_start]
              )
            v_low_sda = []
          sda.state = None

      if v_sda <= self.v_70p and n_sda > self.v_70p:  # rising edge
        interpolation = (self.v_70p - n_sda) / (v_sda - n_sda)
        sda.i_70p = i - interpolation
        if sda.i_30p is not None:
          measure_field = self.add_measurement(
              measure_field, "t_rise_sda",
              [i - interpolation, sda.i_70p - sda.i_30p]
          )
          self.sda_rising_edge += 1
          sda.high_start = sda.i_70p
          sda.state = 1
          sda.i_30p = sda.i_70p = None
        else:
          if (sda.i_70p - sda.high_end) * self.sampling_period > 1e-7:
            measure_field = self.add_measurement(
                measure_field, "runt_sda",
                [i - interpolation, sda.i_70p - sda.high_end]
            )

      elif v_sda >= self.v_70p and n_sda < self.v_70p:  # falling edge
        interpolation = (self.v_70p - n_sda) / (v_sda - n_sda)
        sda.i_70p = i - interpolation
        if sda.i_30p is None:
          sda.high_end = sda.i_70p
          if v_high_sda and sda.high_start:

            # ignore spike occur during SCL low

            if sda.high_start < scl.low_start:
              measure_field = self.add_measurement(
                  measure_field, "v_high_sda",
                  [i - interpolation, np.median(v_high_sda),
                   sda.high_end - sda.high_start]
              )
            v_high_sda = []
          sda.state = None

      if ((scl.state == 0) and sda.high_end is not None and
          (math.ceil(sda.high_end) == i) and self.data_start_flag and
          (sda.high_start is None or sda.high_start < scl.low_start)):
        if ((self.first_packet and self.data_start_flag == 9) or
            (not self.first_packet and read_flag and
             self.data_start_flag != 9) or
            (not self.first_packet and not read_flag and
             self.data_start_flag == 9)):
          measure_field = self.add_measurement(
              measure_field, "t_HD_DAT_dev_falling",
              [i - interpolation, sda.high_end - scl.low_start]
          )
        else:
          measure_field = self.add_measurement(
              measure_field, "t_HD_DAT_host_falling",
              [i - interpolation, sda.high_end - scl.low_start]
          )

      if ((scl.state == 0) and sda.low_end is not None and
          (math.ceil(sda.low_end) == i) and self.data_start_flag and
          (sda.low_start is None or sda.low_start < scl.low_start)):
        if ((self.first_packet and self.data_start_flag == 9) or
            (not self.first_packet and read_flag and
             self.data_start_flag != 9) or
            (not self.first_packet and not read_flag and
             self.data_start_flag == 9)):
          measure_field = self.add_measurement(
              measure_field, "t_HD_DAT_dev_rising",
              [i - interpolation, sda.low_end - scl.low_start]
          )
        else:
          measure_field = self.add_measurement(
              measure_field, "t_HD_DAT_host_rising",
              [i - interpolation, sda.low_end - scl.low_start]
          )

      # Check at 8 for setup time since data_start_flag increment at high

      if ((sda.state == 0) and scl.low_end is not None and
          (math.ceil(scl.low_end) == i) and self.data_start_flag and
          (scl.low_start is None or scl.low_start < sda.low_start)):
        if ((self.first_packet and self.data_start_flag == 8) or
            (not self.first_packet and read_flag and
             self.data_start_flag != 8) or
            (not self.first_packet and not read_flag and
             self.data_start_flag == 8)):
          measure_field = self.add_measurement(
              measure_field, "t_SU_DAT_dev_falling",
              [i - interpolation, scl.low_end - sda.low_start]
          )
        else:
          measure_field = self.add_measurement(
              measure_field, "t_SU_DAT_host_falling",
              [i - interpolation, scl.low_end - sda.low_start]
          )
      if ((sda.state == 1) and scl.low_end is not None and
          (math.ceil(scl.low_end) == i) and self.data_start_flag is not None and
          (scl.low_start is None or scl.low_start < sda.high_start)):
        if ((self.first_packet and self.data_start_flag == 8) or
            (not self.first_packet and read_flag and
             self.data_start_flag != 8) or
            (not self.first_packet and not read_flag and
             self.data_start_flag == 8)):
          measure_field = self.add_measurement(
              measure_field, "t_SU_DAT_dev_rising",
              [i - interpolation, scl.low_end - sda.high_start]
          )
        else:
          measure_field = self.add_measurement(
              measure_field, "t_SU_DAT_host_rising",
              [i - interpolation, scl.low_end - sda.high_start]
          )

      if ((scl.state == 1) and sda.high_end is not None and
          (math.ceil(sda.high_end) == i)):
        if (not self.stop_flag and
            (sda.high_start is None or sda.high_start < scl.high_start)):  # Sr
          self.restart_flag = 1
          self.first_packet = 1
          self.start_flag = 0
          self.data_start_flag = 0
          self.restart_num += 1
          addr = ""
          measure_field = self.add_measurement(
              measure_field, "t_SU_STA",
              [i - interpolation, sda.high_end - scl.high_start]
          )
        elif (self.stop_flag and
              (sda.high_start is None or scl.high_start < sda.high_start)):  # S
          self.start_flag = 1
          self.first_packet = 1
          self.stop_flag = 0
          self.data_start_flag = 0
          self.start_num += 1
          addr = ""
          if sda.high_start is not None:
            measure_field = self.add_measurement(
                measure_field, "t_BUF",
                [i - interpolation, sda.high_end - sda.high_start]
            )

      if ((sda.state == 0) and scl.high_end is not None and
          (math.ceil(scl.high_end) == i) and
          (scl.high_start is None or scl.high_start < sda.low_start)):
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
          (sda.low_start is None or sda.low_start < scl.high_start)):
        self.stop_flag = 1
        read_flag = 0
        self.restart_flag = self.start_flag = 0
        self.stop_num += 1
        self.data_start_flag = None
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
    """Get SPEC limitation according to operation mode.

    Args:
      mode: operation mode (Standard mode / Fast Mode / Fast Mode Plus)
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

    # Check only voltage SPEC constrain if unknown operation mode

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
      result: pass/fail, margin, start_idx, margin_percentage of each parameter
      svgwidth: worst case width for SVG plot
    """
    values = {}
    result = {}
    svgwidth = {}

    fields1 = ["v_high_scl", "v_low_scl", "v_high_sda", "v_low_sda"]
    for f in fields1:
      ff = "_".join(f.split("_")[:-1])
      measure_max = measure_field.get(f + "_max")
      measure_min = measure_field.get(f + "_min")
      if measure_max and measure_min:
        values[f + "_max"] = measure_max[1]
        values[f + "_min"] = measure_min[1]
        limit = spec_limit[ff]
        if "high" in f:
          values[f + "_worst"] = measure_min[1]
          result[f + "_idx"] = measure_min[0]
          result[f + "_margin"] = measure_min[1] - limit
          svgwidth[f] = measure_min[2]
        elif "low" in f:
          values[f + "_worst"] = measure_max[1]
          result[f + "_idx"] = measure_max[0]
          result[f + "_margin"] = limit - measure_max[1]
          svgwidth[f] = measure_max[2]
        result[f + "_percent"] = result[f + "_margin"] / limit * 100

    fields2 = ["v_nh_scl", "v_nl_scl", "v_nh_sda", "v_nl_sda"]
    for f in fields2:
      ff = f.replace("nh", "high").replace("nl", "low")
      ff2 = f[:4]
      value_max = values.get(ff + "_max")
      value_min = values.get(ff + "_min")
      if value_max and value_min:
        if "nh" in f:
          maxx = (value_max - self.v_70p) / vs
          minn = (value_min - self.v_70p) / vs
        elif "nl" in f:
          maxx = (self.v_30p - value_min) / vs
          minn = (self.v_30p - value_max) / vs
        values[f + "_min"] = minn
        values[f + "_max"] = maxx
        values[f + "_worst"] = minn
        result[f + "_idx"] = result[ff + "_idx"]
        svgwidth[f] = svgwidth[ff]
        limit = spec_limit[ff2]
        if minn >= limit:
          result[f] = 0
        else:
          result[f] = 1
        result[f + "_margin"] = minn - limit
        result[f + "_percent"] = (minn - limit) / limit * 100

    measure_max = measure_field.get("T_clk_max")
    measure_min = measure_field.get("T_clk_min")
    if measure_max and measure_min:
      t_clk_min = measure_min[1] * self.sampling_period
      maxx = int(1 / t_clk_min)
      t_clk_max = measure_max[1] * self.sampling_period
      minn = int(1 / t_clk_max)
      values["f_clk_max"] = maxx
      values["f_clk_min"] = minn
      values["f_clk_worst"] = maxx
      result["f_clk_idx"] = measure_min[0]
      svgwidth["f_clk"] = measure_min[1]
      limit = spec_limit["f_clk"]
      if maxx <= limit:
        result["f_clk"] = 0
      else:
        result["f_clk"] = 1
      result["f_clk_margin"] = limit - maxx
      result["f_clk_percent"] = (limit - maxx) / limit * 100

    fields3 = [
        "t_rise_sda", "t_rise_scl", "t_fall_sda", "t_fall_scl",
        "t_HD_DAT_host_rising", "t_HD_DAT_host_falling",
        "t_HD_DAT_dev_rising", "t_HD_DAT_dev_falling"
    ]
    for f in fields3:
      measure_max = measure_field.get(f + "_max")
      measure_min = measure_field.get(f + "_min")
      if measure_max and measure_min:
        maxx = measure_max[1] * self.sampling_period
        minn = measure_min[1] * self.sampling_period
        values[f + "_max"] = maxx
        values[f + "_min"] = minn
        if "HD" in f:
          ff = f[:8]
          limit_max = spec_limit.get(ff)
          if not limit_max:
            limit_max = np.inf
          limit_min = 0
        else:
          ff = f[:6]
          limit_max = spec_limit.get(ff + "_max")
          limit_min = spec_limit.get(ff + "_min")
          if not limit_min:
            limit_min = np.NINF
        if maxx <= limit_max and minn >= limit_min:
          result[f] = 0
        else:
          result[f] = 1
        if limit_max - maxx < minn - limit_min:
          values[f + "_worst"] = maxx
          result[f + "_idx"] = measure_max[0]
          svgwidth[f] = measure_max[1]
          result[f + "_margin"] = limit_max - maxx
          result[f + "_percent"] = (limit_max - maxx) / limit_max * 100
        else:
          values[f + "_worst"] = minn
          result[f + "_idx"] = measure_min[0]
          svgwidth[f] = measure_min[1]
          result[f + "_margin"] = minn - limit_min
          if "HD" in f and limit_max != np.inf:
            result[f + "_percent"] = (minn - limit_min) / limit_max * 100
          elif limit_min != 0:
            result[f + "_percent"] = (minn - limit_min) / limit_min * 100
          else:
            result[f + "_percent"] = np.inf

    fields4 = [
        "t_low", "t_high", "t_SU_STA", "t_SU_STO", "t_BUF", "t_HD_STA_S",
        "t_HD_STA_Sr", "t_SU_DAT_host_rising", "t_SU_DAT_host_falling",
        "t_SU_DAT_dev_rising", "t_SU_DAT_dev_falling"
    ]
    for f in fields4:
      measure_max = measure_field.get(f + "_max")
      measure_min = measure_field.get(f + "_min")
      if measure_max and measure_min:
        if f in ["t_low", "t_high", "t_SU_STA", "t_SU_STO", "t_BUF"]:
          ff = f
        else:
          ff = f[:8]
        maxx = measure_max[1] * self.sampling_period
        minn = measure_min[1] * self.sampling_period
        values[f + "_max"] = maxx
        values[f + "_min"] = minn
        values[f + "_worst"] = minn
        result[f + "_idx"] = measure_min[0]
        svgwidth[f] = measure_min[1]
        limit = spec_limit[ff]
        if minn >= limit:
          result[f] = 0
        else:
          result[f] = 1
        result[f + "_margin"] = minn - limit
        result[f + "_percent"] = (minn - limit) / limit * 100

    fields6 = ["runt_scl", "runt_sda"]
    for f in fields6:
      if measure_field.get(f):
        result[f] = measure_field[f]

    return values, result, svgwidth

  def get_svg_fields(self, result, svgwidth, vs):
    """Save SVG Plot for Each parameter.

    Calculate Max/Min Value for Plot Boundary
    Then generate SVG plot for each parameter

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
    resolution = min(max(len(self.scl_data) // 2000, 1), 150)
    upscale_x = 3000 / len(self.scl_data) * resolution
    upscale_y = 40 * 5 // (scl_v_max - scl_v_min)
    part = max(int(2e-5 // self.sampling_period), 500)

    fields1 = [
        "v_low_scl", "v_high_scl", "t_rise_scl", "t_fall_scl", "t_low",
        "t_high", "f_clk", "v_nl_scl", "v_nh_scl"
    ]
    for f in fields1:
      if result.get(f + "_idx"):
        idx = result[f + "_idx"]
        start_idx = math.floor(
            max(0, min(idx - part, len(self.scl_data) - part * 2))
        )
        end_idx = math.ceil(min(len(self.scl_data), max(idx + part, part * 2)))
        svg_fields[f] = SVGFile(
            self.scl_data[start_idx:end_idx], scl_v_max, scl_v_min,
            idx - start_idx, svgwidth[f], f, vs
        )
        rect_width = max(svgwidth[f] // resolution * upscale_x, 40)
        rect_x = idx // resolution * upscale_x - rect_width
        mid_x = rect_x + rect_width // 2
        svg_fields["scl"] += (
            f"\n\t\t\t\t<rect id='{f}_rect' x={rect_x} y=50 width={rect_width} height=90% class='rect hide'/>"
            f"\n\t\t\t\t<line id='{f}_line' x1={mid_x} y1=0 x2={mid_x} y2=60 class='arrowline'/>"
            f"\n\t\t\t\t<polygon id='{f}_poly' points='{mid_x - 50} 50, {mid_x} 110, {mid_x + 50} 50' class='arrow'/>"
        )

    y30p = (scl_v_max - 0.3 * vs) * upscale_y + 120
    y70p = (scl_v_max - 0.7 * vs) * upscale_y + 120
    svg_fields["scl"] += (
        f"\n\t\t\t\t<text x=0 y={y30p} class='text2 runt_scl hide'>30 %</text>"
        f"\n\t\t\t\t<text x=0 y={y70p} class='text2 runt_scl hide'>70 %</text>"
        f"\n\t\t\t\t<line x1=0 y1={y30p} x2=100% y2={y30p} class='line2 runt_scl hide'/>"
        f"\n\t\t\t\t<line x1=0 y1={y70p} x2=100% y2={y70p} class='line2 runt_scl hide'/>"
    )
    if result.get("runt_scl"):
      for runt in result["runt_scl"]:
        idx = runt[0]
        rect_width = max(runt[1] // resolution * upscale_x, 40)
        rect_x = idx // resolution * upscale_x - rect_width
        mid_x = rect_x + rect_width // 2
        svg_fields["scl"] += (
            f"\n\t\t\t\t<rect class='runt_scl rect hide' x={rect_x} y=50 width={rect_width} height=90% />"
        )

    fields2 = [
        "v_low_sda", "v_high_sda", "t_rise_sda", "t_fall_sda", "v_nl_sda",
        "v_nh_sda"
    ]
    for f in fields2:
      if result.get(f + "_idx"):
        idx = result[f + "_idx"]
        start_idx = math.floor(
            max(0, min(idx - part, len(self.sda_data) - part * 2))
        )
        end_idx = math.ceil(min(len(self.sda_data), max(idx + part, part * 2)))
        svg_fields[f] = SVGFile(
            self.sda_data[start_idx:end_idx], sda_v_max, sda_v_min,
            idx - start_idx, svgwidth[f], f, vs
        )
        rect_width = max(svgwidth[f] // resolution * upscale_x, 40)
        rect_x = idx // resolution * upscale_x - rect_width
        mid_x = rect_x + rect_width // 2
        svg_fields["sda"] += (
            f"\n\t\t\t\t<rect id='{f}_rect' x={rect_x} y=50 width={rect_width} height=90% class='rect hide'/>"
            f"\n\t\t\t\t<line id='{f}_line' x1={mid_x} y1=0 x2={mid_x} y2=60 class='arrowline'/>"
            f"\n\t\t\t\t<polygon id='{f}_poly' points='{mid_x - 50} 50, {mid_x} 110, {mid_x + 50} 50' class='arrow'/>"
        )

    fields3 = [
        "t_SU_DAT_host_rising", "t_SU_DAT_host_falling",
        "t_HD_DAT_host_rising", "t_HD_DAT_host_falling",
        "t_SU_DAT_dev_rising", "t_SU_DAT_dev_falling",
        "t_HD_DAT_dev_rising", "t_HD_DAT_dev_falling",
        "t_HD_STA_S", "t_HD_STA_Sr", "t_SU_STA", "t_SU_STO", "t_BUF"
    ]
    for f in fields3:
      if result.get(f + "_idx"):
        idx = result[f + "_idx"]
        start_idx = math.floor(
            max(0, min(idx - part, len(self.scl_data) - part * 2))
        )
        end_idx = math.ceil(min(len(self.scl_data), max(idx + part, part * 2)))
        svg_fields[f + "_scl"] = SVGFile(
            self.scl_data[start_idx:end_idx], scl_v_max, scl_v_min,
            idx - start_idx, svgwidth[f], f + "_scl", vs
        )
        svg_fields[f + "_sda"] = SVGFile(
            self.sda_data[start_idx:end_idx], sda_v_max, sda_v_min,
            idx - start_idx, svgwidth[f], f + "_sda", vs
        )
        rect_width = max(svgwidth[f] // resolution * upscale_x, 40)
        rect_x = idx // resolution * upscale_x - rect_width
        mid_x = rect_x + rect_width // 2
        svg_fields["scl"] += (
            f"\n\t\t\t\t<rect id='{f}_scl_rect' x={rect_x} y='0' width={rect_width} height=100% class='rect hide'/>"
            f"\n\t\t\t\t<line id='{f}_line' x1={mid_x} y1=0 x2={mid_x} y2=60 class='arrowline'/>"
            f"\n\t\t\t\t<polygon id='{f}_poly' points='{mid_x - 50} 50, {mid_x} 110, {mid_x + 50} 50' class='arrow'/>"
        )
        svg_fields["sda"] += (
            f"\n\t\t\t\t<rect id='{f}_sda_rect' x={rect_x} y='0' width={rect_width} height=100%"
            f" class='rect hide'/>"
        )

    y30p = (sda_v_max - 0.3 * vs) * upscale_y + 120
    y70p = (sda_v_max - 0.7 * vs) * upscale_y + 120
    svg_fields["sda"] += (
        f"\n\t\t\t\t<text x=0 y={y30p} class='text2 hide runt_sda'>30 %</text>"
        f"\n\t\t\t\t<text x=0 y={y70p} class='text2 hide runt_sda'>70 %</text>"
        f"\n\t\t\t\t<line x1=0 y1={y30p} x2=100% y2={y30p} class='line2 runt_sda hide'/>"
        f"\n\t\t\t\t<line x1=0 y1={y70p} x2=100% y2={y70p} class='line2 runt_sda hide'/>"
    )
    if result.get("runt_sda"):
      for runt in result["runt_sda"]:
        idx = runt[0]
        rect_width = max(runt[1] // resolution * upscale_x, 40)
        rect_x = idx // resolution * upscale_x - rect_width
        mid_x = rect_x + rect_width // 2
        svg_fields["sda"] += (
            f"\n\t\t\t\t<rect class='runt_sda rect hide' x={rect_x} y=50 width={rect_width} height=90% />"
        )
    svg_fields["scl"] += "\n\t\t\t</svg>\n\t\t</div>\n\t</div>"
    svg_fields["sda"] += "\n\t\t\t</svg>\n\t\t</div>\n\t</div>"

    return svg_fields

  def measure(self):
    """Measure.

    This method is called after all the relevant data has been passed
    to process_data function. It returns a dictionary of the required
    measurement values.

    Returns:
      report_path: output testing report
    """
    data1 = self.data_list[:, 1]
    data2 = self.data_list[:, 2]

    print("------------------------------------")
    if self.vs is None:
      vs = self.determine_working_voltage(data1)
    else:
      vs = self.vs
    print("Working Voltage: ", vs, "V")
    self.determine_datatype(data1, data2)
    if self.mode is None:
      mode = self.determine_operation_mode()
    else:
      mode = self.mode.replace("_", " ")
    print("Operation Mode: ", mode)
    print("------------------------------------")

    ################### Measure Each Parameter ############################

    measure_field, addr_list = self.measure_both_scl_sda()
    print("Complete measurement")
    print("Total captured SCL rising edges: ", self.scl_rising_edge)
    print("Total captured SCL falling edges: ", self.scl_falling_edge)
    print("Total captured SDA rising edges: ", self.sda_rising_edge)
    print("Total captured SDA falling edges: ", self.sda_falling_edge)
    print("Total captured START pattern: ", self.start_num)
    print("Total captured RESTART pattern: ", self.restart_num)
    print("Total captured STOP pattern: ", self.stop_num)
    scl_runt_num = 0
    if measure_field.get("runt_scl"):
      scl_runt_num = len(measure_field["runt_scl"])
    sda_runt_num = 0
    if measure_field.get("runt_sda"):
      sda_runt_num = len(measure_field["runt_sda"])
    print("Total captured RUNT pattern on SCL dataline: ", scl_runt_num)
    print("Total captured RUNT pattern on SDA dataline: ", sda_runt_num)
    print("------------------------------------")

    ################### Check SPEC Limitation ##############################

    spec_limit = self.get_spec_limitation(mode, vs)
    values, result, svgwidth = self.check_spec(spec_limit, measure_field, vs)
    print("Complete check spec")

    fail = {}
    fail = {param: result for (param, result) in result.items()
            if ((result == 1) and ("_margin" not in param) and
                ("_percent" not in param) and ("_idx" not in param))}
    passes = {param: result for (param, result) in result.items()
              if ((result == 0) and ("_margin" not in param) and
                  ("_percent" not in param) and ("_idx" not in param))}
    num_pass = len(passes)
    values["spec"] = len(fail)
    print("Pass: ", num_pass)
    print("Fail: ", len(fail))

    ############### Generate and Show Report ##############

    uni_addr = list(set(addr_list))
    uni_addr = [f"0x{int(addr, 2):02X}" for addr in uni_addr]
    print("Detect Addr: ", uni_addr)

    sampling_rate = round(1 / self.sampling_period * 1e-6)
    print("Sampling_rate: ", sampling_rate, "MS/s")
    print("------------------------------------")

    svg_fields = self.get_svg_fields(result, svgwidth, vs)
    waveform_info = [
        self.scl_rising_edge, self.scl_falling_edge, self.sda_rising_edge,
        self.sda_falling_edge, self.start_num, self.restart_num, self.stop_num
    ]
    report_path = OutputReportFile(
        mode, spec_limit.copy(), vs, values.copy(), result.copy(),
        fail.copy(), num_pass, svg_fields, uni_addr, sampling_rate,
        waveform_info, self.save_folder
    )

    test_item = [
        mode, vs, values.copy(), result.copy(), fail.copy(),
        num_pass, uni_addr, sampling_rate, waveform_info
    ]

    return report_path, test_item

