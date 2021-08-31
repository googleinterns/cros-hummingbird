"""HummingBird I2C Eletrical Test Automation.

The project serves as an extension measurement module
run on Saleae Logic2 Software. Supporting main function
would be running I2C electrical test on capture data.

"""
import datetime
import os
import subprocess
import tempfile

from generate_report import OutputReportFile
import hummingbird
import numpy as np
from saleae.data import GraphTime
from saleae.range_measurements import AnalogMeasurer


LOCAL_PATH = os.path.join(tempfile.gettempdir(), "output_reports")
if not os.path.exists(LOCAL_PATH):
  os.makedirs(LOCAL_PATH)


class HummingBird(AnalogMeasurer, hummingbird.HummingBird):
  """Main measurement module.

  This is the main module called by Saleae measurement API.

  Attributes:
    samples: analog data samples,
             in the format of (time_index, voltage_value)
    start_time: captured data start time
    sampling_period: time between two samples
    stop_flag: STOP pattern detected,
               raise to 1 until START pattern
    start_flag: START pattern detected,
                remain 1 until STOP or RESTART pattern
    restart_flag: RESTART pattern detected,
                  remain 1 until STOP pattern
    data_start_flag: from the first SCL clock cycle after START
                     or RESTART pattern, remain 1 for one package
                     (9 SCL clock cycles)

    scl_data_path: SCL data save path
    scl_data: SCL data
    scl_start_time: SCL data start time
    scl_sampling_period: SCL data sampling period
    f_clk: SCL clock frequency
    sda_data_path: SDA data save path
    sda_data: SDA data
    sda_start_time: SDA data start time
    sda_sampling_period: SDA data sampling period

    requested_measurements: measurement required by extension.json
  """

  def __init__(self, requested_measurements):
    """Initialization.

    Initialize your measurement extension here
    Each measurement object will only be used once,
    all pre-measurement initialization are here

    Args:
      requested_measurements: measurement required by extension.json
    """
    super(HummingBird, self).__init__(requested_measurements)
    supported_measurements = [
        "v_low_scl", "v_low_sda", "v_high_scl", "v_high_sda", "v_nl_scl",
        "v_nh_scl", "v_nl_sda", "v_nh_sda", "t_rise_sda", "t_rise_scl",
        "t_fall_sda", "t_fall_scl", "t_low", "t_high", "f_clk",
        "t_SU_DAT_host_rising", "t_SU_DAT_host_falling", "t_HD_DAT_host_rising",
        "t_HD_DAT_host_falling", "t_SU_DAT_dev_rising", "t_SU_DAT_dev_falling",
        "t_HD_DAT_dev_rising", "t_HD_DAT_dev_falling", "t_HD_STA_S",
        "t_HD_STA_Sr", "t_SU_STA", "t_SU_STO", "t_BUF"
    ]
    self.samples = []
    self.start_time = None
    self.sampling_period = None

    self.scl_rising_edge = 0
    self.scl_falling_edge = 0
    self.sda_rising_edge = 0
    self.sda_falling_edge = 0
    self.start_num = 0
    self.restart_num = 0
    self.stop_num = 0

    self.stop_flag = 1
    self.start_flag = 0
    self.restart_flag = 0
    self.data_start_flag = 0
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
        data.samples is a numpy array of float32 voltages
        data.sample_count is the number of samples
    """
    self.samples.append(data.samples)
    if self.sampling_period is None:
      self.sampling_period = (
          ((data.end_time - data.start_time) / data.sample_count).__float__())

    if self.start_time is None:
      self.start_time = data.start_time

  def determine_datatype(self, data):
    """Determine Data Type.

    Read the first five cycles to determine data type
    Consider different sampling rate by multiply sampling_period
    Avoid extreme value which might cause by clk stretching
    Calculate the difference percentage of t_max and t_min
    SCL should be stable and the difference should be small

    Constrain: should capture at least five SCL clk cycles

    Args:
      data: numpy array of voltages values

    Returns:
      datatype: current capture is SCL or SDA
    """
    datatype = None
    dataline = hummingbird.Logic()
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

  def process_1st_2nd_capture(self, datatype, data):
    """Process 1st or 2nd Capture.

    If 1st, write data.
    If 2nd, solve datatime time zone when convert datatime
    to graphtime

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
      Exception: SDA and SCL data time range is not overlapped
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

  def measure(self):
    """Measure.

    This method is called after all the relevant data has been passed
    to process_data function. It returns a dictionary of the required
    measurement values.

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

    ################### Measure Each Parameter ############################

    supported_measurements = [
        "t_rise_sda", "t_rise_scl", "t_fall_sda", "t_fall_scl", "t_low",
        "t_high", "t_SU_DAT_host_rising", "t_SU_DAT_host_falling",
        "t_HD_DAT_host_rising", "t_HD_DAT_host_falling",
        "t_SU_DAT_dev_rising", "t_SU_DAT_dev_falling", "t_HD_DAT_dev_rising",
        "t_HD_DAT_dev_falling", "t_HD_STA_Sr", "t_HD_STA_S", "t_SU_STA",
        "t_SU_STO", "t_BUF"
    ]
    if any(k.split("_worst")[0] in supported_measurements
           for k in self.requested_measurements):
      measure_field, addr_list = self.measure_both_scl_sda()

    ################### Check SPEC Limitation ##############################

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
    waveform_info = [
        self.scl_rising_edge, self.scl_falling_edge, self.sda_rising_edge,
        self.sda_falling_edge, self.start_num, self.restart_num, self.stop_num
    ]
    report_path = OutputReportFile(
        mode, spec_limit.copy(), vs, values.copy(), result.copy(),
        fail.copy(), num_pass, svg_fields, uni_addr, sampling_rate,
        waveform_info, LOCAL_PATH
    )
    subprocess.run(["open", report_path], check=True)

    return values
