"""HummingBird Report methods.

The file contain methods related to output report.

"""
import datetime
import os
import typing

import numpy as np


LOCAL_PATH = os.path.join(os.path.dirname(__file__), "output_reports")
if not os.path.exists(LOCAL_PATH):
  os.makedirs(LOCAL_PATH)


def SVGFile(data: np.ndarray, data_max: np.float64, data_min: np.float64,
            rect_idx: int, rect_width: int, field: str):
  """Generate SVG plot.

  Args:
    data:  numpy array of voltages
    data_max:  data maximum value
    data_min:  data minimum value
    rect_idx:  index where the worst pattern occurs
    rect_width:  the index width where the worst pattern last
    field:  the SPEC field of this SVG plot

  Returns:
    SVG plot to write in the html report.
  """
  svgfile = ""
  data_max = int(data_max * 50)
  data_min = int(data_min * 50)
  height = (data_max - data_min) * 2
  rate = min(max(len(data) // 1000, 1), 180)
  width = len(data) // rate * 5

  if field == "scl_show":
    svgfile += (
        f"<div id='{field}'><div class='column_left'>SCL capture</div>"
        "<div class='column_right'>"
        f"<svg viewBox='0 0 {width} {height * 1.2}' height={height * 0.7} width=auto>"
    )

  elif field == "sda_show":
    svgfile += (
        f"<div id='{field}'><div class='column_left'>SDA capture</div>"
        "<div class='column_right'>"
        f"<svg viewBox='0 0 {width} {height * 1.2}' height={height * 0.7} width=auto>"
    )

  else:
    if "sda" in field:
      svgfile += (
          f"<div id='{field}_hide' class='hide'>"
          "<div class='column_left'>SDA capture</div><div class='column_right'>"
      )

    else:
      svgfile += (
          f"<div id='{field}_hide' class='hide'>"
          "<div class='column_left'>SCL capture</div><div class='column_right'>"
      )
    svgfile += (
        f"<svg viewBox='0 0 {width} {height * 1.2}' height={height * 0.7} width=auto>"
    )

    # Red Rect to Mark the Measure Area

    rect_width = max(rect_width//rate * 5, 7)
    rect_x = rect_idx//rate * 5 - rect_width
    svgfile += (
        f"<rect x={rect_x} y='0' width={rect_width} height='100%' fill='red' opacity='0.3'/>"
    )

  # Data Polyline

  points = ""
  for i in range(0, len(data), rate):
    points += f"{i//rate * 5},{(data_max - int(data[i] * 50)) * 2 + 40} "
  svgfile += (
      f"<polyline points='{points}' style='fill:none;stroke:black;stroke-width:5;'/>"
      "</svg></div></div>"
  )

  return svgfile


def OutputReportFile(mode: str, spec: typing.Dict[str, float], vs: float,
                     values: typing.Dict[str, np.float64],
                     result: typing.Dict[str, np.float64],
                     fail: typing.Dict[str, int], num_pass: int,
                     svg_fields: typing.Dict[str, str],
                     addr: typing.List[str]):
  """Write HTML report.

  Args:
    mode:  operation mode
    spec:  dictionary of SPEC limitation for each field (max/min)
    vs:    working voltge
    values:  dictionary of measurement for each field
             include max/min/worst for each field
    result:  dictionary of electrical test result
             include Pass or Fail/margin/margin percentage for each field
    fail:  dictionary of the failed SPEC fields
    num_pass:  number of passed SPEC fields
    svg_fields:  SVG plot dictionary for each SPEC field
    addr:  addresses included in the capture

  Returns:
    report_path: report path for current testing result.
  """
  result_num = len(fail) + num_pass
  fails = ", ".join(list(fail.keys()))

  field = [
      "v_low_sda", "v_low_scl", "v_high_sda", "v_high_scl", "v_nl_sda",
      "v_nl_scl", "v_nh_sda", "v_nh_scl", "f_clk", "t_low", "t_high",
      "t_SU_STA", "t_HD_STA_S", "t_HD_STA_Sr", "t_SU_DAT_rising_host",
      "t_SU_DAT_falling_host", "t_HD_DAT_rising_host", "t_HD_DAT_falling_host",
      "t_SU_DAT_rising_dev", "t_SU_DAT_falling_dev", "t_HD_DAT_rising_dev",
      "t_HD_DAT_falling_dev", "t_rise_sda", "t_rise_scl", "t_fall_sda",
      "t_fall_scl", "t_SU_STO", "t_BUF"
  ]
  spec_field = [
      "v_low", "v_high", "v_nh", "v_nl", "t_rise_max", "t_rise_min",
      "t_fall_max", "t_fall_min", "t_low", "t_high", "f_clk", "t_SU_DAT",
      "t_HD_DAT", "t_HD_STA", "t_SU_STA", "t_SU_STO", "t_BUF"
  ]
  time_now = datetime.datetime.now()
  report_path = os.path.join(
      LOCAL_PATH, f"report_{time_now.strftime('%Y%m%d%H%M%S')}.html"
  )
  with open(report_path, "w") as report:
    report.write("<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'>")
    report.write("<title>HummingBird Output Report</title><style>")
    style = """body {
      padding: 1% 3%;
      font-family: arial, sans-serif;
      font-size: 18px;
    }
    h1 {
      text-align: center;
    }
    h3 {
      text-align: right;
      color: #555;
      font-style: italic;
      font-size: 19px;
      clear: right;
      padding: 20px 10px 0 0;
    }
    p {
      margin: 8px auto;
      display: flex;
      align-items: start;
      font-weight: normal;
    }
    table {
      border-collapse: collapse;
      width: 100%;
      margin: 20px auto;
      font-size: 17px;
    }
    td, th {
      border: 1px solid #dddddd;
      text-align: left;
      padding: 8px;
    }
    table th {
      height: 60px;
      background: #555;
      color: #fff;
      line-height: 1.2;
      font-size: 18px;
    }
    table tr:hover {
      color: #555555;
      background-color: #f5f5f5;
      cursor: pointer;
    }
    div {
      margin: 1% auto;
      width: 100%;
    }
    .left {
      float: left;
      width:50%;
    }
    .right {
      float: left;
      width:50%;
    }
    .column_left {
      float: left;
      width: 10%;
      padding: 30px 0;
      text-align: center;
      font-weight: 600;
      margin-bottom: 50px;
      font-size: 21px;
    }
    .column_right{
      float: left;
      width:90%;
      padding: 0;
      margin-bottom: 50px;
    }
    .summary {
      margin: 0 0 20px 10px;
      align-items: end;
      float: right;
      width: 300px;
      height: 30px;
      font-size: 16px; 
    }
    .summary th {
      background-color: #aaa;
      color:  #111;
      height: 40px;
    }
    .summary td{
      width: 50%;
    }
    .warning {
      background: yellow;
    }
    .critical {
      background: red;
    }
    .NA {
      background: #cdcdcd;
    }
    .hide {
      display: none;
    }
    .addr {
      padding-top: 10px;
      color: #882132;
      font-size: 19px;
    }"""

    script = """<script>
    function ShowSVG(x){
      console.log(x);
      ele_self = document.getElementById(x);
      ele_self.style.background = "#F5B7B1";
      ele = document.getElementById(x + "_hide");
      ele_scl = document.getElementById(x + "_scl_hide");
      ele_sda = document.getElementById(x + "_sda_hide");
      let fields = [
          "v_low_scl", "v_high_scl", , "v_nl_scl", "v_nh_scl", "v_nl_sda",
          "v_nh_sda","t_rise_scl", "t_fall_scl", "t_low", "t_high", "f_clk",
          "v_low_sda", "v_high_sda", "t_rise_sda", "t_fall_sda",
          "t_SU_DAT_rising_host", "t_SU_DAT_falling_host", "t_HD_DAT_rising_host",
          "t_HD_DAT_falling_host", "t_SU_DAT_rising_dev", "t_SU_DAT_falling_dev",
          "t_HD_DAT_rising_dev", "t_HD_DAT_falling_dev","t_HD_STA_S", "t_HD_STA_Sr",
          "t_SU_STA", "t_SU_STO", "t_BUF"
      ];
      if(ele != null){
        ele.style.display = "block";
        sda = document.getElementById('sda_show');
        if(sda!=null){sda.style.display = "none";}
         scl = document.getElementById('scl_show');
        if(scl!=null){scl.style.display = "none";}
        fields.forEach(function(item, index, array) {
          if (item != x){
            ele1 = document.getElementById(item);
            if(ele1!=null){ele1.style.background = "white";}
            ele2 = document.getElementById(item + "_hide");
            if(ele2!=null){ele2.style.display = "none";}
            ele3 = document.getElementById(item + "_scl_hide");
            if(ele3!=null){ele3.style.display = "none";}
            ele4 = document.getElementById(item + "_sda_hide");
            if(ele4!=null){ele4.style.display = "none";}
          }
        })
      }else if(ele_scl!=null && ele_sda!=null) {
        ele_scl.style.display = "block";
        ele_sda.style.display = "block";
        sda = document.getElementById('sda_show');
        if(sda!=null){sda.style.display = "none";}
         scl = document.getElementById('scl_show');
        if(scl!=null){scl.style.display = "none";}
        fields.forEach(function(item, index, array) {
          if (item != x){
            ele1 = document.getElementById(item);
            if(ele1!=null){ele1.style.background = "white";}
            ele2 = document.getElementById(item + "_hide");
            if(ele2!=null){ele2.style.display = "none";}
            ele3 = document.getElementById(item + "_scl_hide");
            if(ele3!=null){ele3.style.display = "none";}
            ele4 = document.getElementById(item + "_sda_hide");
            if(ele4!=null){ele4.style.display = "none";}
          }
        })
      }else{
        sda = document.getElementById('sda_show');
        if(sda!=null){sda.style.display = "block";}
        scl = document.getElementById('scl_show');
        if(scl!=null){scl.style.display = "block";}
        fields.forEach(function(item, index, array) {
          ele1 = document.getElementById(item);
          if(ele1!=null){ele1.style.background = "white";}
          ele2 = document.getElementById(item + "_hide");
          if(ele2!=null){ele2.style.display = "none";}
          ele3 = document.getElementById(item + "_scl_hide");
          if(ele3!=null){ele3.style.display = "none";}
          ele4 = document.getElementById(item + "_sda_hide");
          if(ele4!=null){ele4.style.display = "none";}
        })
      }
    }
    </script>"""
    report.write(style)
    report.write("</style></head><body>")
    report.write(script)

    if mode is None:
      mode = "Unknown ( Note: SCL data has not been specified... )"

    report.write(
        "<h1>HummingBird I2C Electrical Testing Report</h1><div class='left'><p>"
        "<b>Report Time:</b>&nbsp;&nbsp;&nbsp;&nbsp;"
    )
    report.write(time_now.strftime("%Y-%m-%d %H:%M:%S"))
    report.write(
        f"</p><p><b>File Save Path:</b>&nbsp;&nbsp;&nbsp;&nbsp;{report_path}"
        f"</p><p><b>Operation Mode:</b>&nbsp;&nbsp;{mode}</p><p><b>Operation "
        f"Voltage:</b>&nbsp;&nbsp;{vs}V</p><p><b>Reference SPEC Link:</b>&nbsp;"
        "&nbsp;<a href='https://www.nxp.com/docs/en/user-guide/UM10204.pdf'>"
        "NXP UM10204</a></p>"
    )
    if mode != "Unknown ( Note: SCL data has not been specified... )":
      if not fails:
        report.write("<p>Pass SPEC test successfully! :)</p>")
      else:
        report.write("<p><b>Fail:</b>&nbsp;&nbsp;" + fails + "</p>")
    report.write("<div class='addr'><b>Include Address:</b>&nbsp;&nbsp;")
    report.write(" ".join(addr))
    report.write(
        "</div></div><div class='right'><table class='summary'><tr>"
        "<th colspan=2>Margin Threshold</th></tr><tr><td><b>Warning</b></td>"
        "<td class='warning'>&lt; 5%</td></tr><tr><td><b>Critical</b></td>"
        "<td class='critical'>&lt; 0%</td></tr></table><table class='summary'>"
        "<tr><th colspan=2>SPEC Test Summary</th></tr><tr><td><b>Fail</b></td>"
        f"<td>{len(fail)}</td></tr><tr><td><b>Pass</b></td><td>{num_pass}</td>"
        f"</tr><tr><td><b>Total</b></td><td>{result_num}</td></tr></table><h3>"
        "Click each row to check the waveform of the worst mearsurement shown "
        "<u>at the end of report</u>. </h3></div>"
    )

    for f in field:
      if values.get(f + "_worst") is None:
        values[f + "_max"] = "N/A"
        values[f + "_min"] = "N/A"
        values[f + "_worst"] = "N/A"

      else:
        if "t_rise" in f or "t_fall" in f:
          values[f + "_max"] *= 1e9
          values[f + "_min"] *= 1e9
          values[f + "_worst"] *= 1e9
          result[f + "_margin"] *= 1e9

        elif "t_" in f:
          values[f + "_max"] *= 1e6
          values[f + "_min"] *= 1e6
          values[f + "_worst"] *= 1e6
          result[f + "_margin"] *= 1e6

        elif "f_" in f:
          values[f + "_max"] /= 1e3
          values[f + "_min"] /= 1e3
          values[f + "_worst"] /= 1e3
          result[f + "_margin"] /= 1e3

        values[f + "_max"] = f"{values[f + '_max']:.3f}"
        values[f + "_min"] = f"{values[f + '_min']:.3f}"
        values[f + "_worst"] = f"{values[f + '_worst']:.3f}"

      if result.get(f + "_margin") is not None:
        result[f + "_percent"] = f"{result[f + '_percent']:.1f}"
        result[f + "_margin"] = f"{result[f + '_margin']:.3f}"
        if "v_high" in f or "v_low" in f:
          values[f + "_result"] = "Only for Informative"
        else:
          if result[f] == 0:
            values[f + "_result"] = "Pass"
          else:
            values[f + "_result"] = "Fail"

      else:
        result[f + "_margin"] = "N/A"
        result[f + "_percent"] = "N/A"
        values[f + "_result"] = "N/A"

    for k in spec_field:
      if spec.get(k) is not None:
        if "t_rise" in k or "t_fall" in k:
          spec[k] *= 1e9
        elif "t_" in k:
          spec[k] *= 1e6
        elif "f_" in k:
          spec[k] /= 1e3
        spec[k] = f"{spec[k]:.2f}"
      else:
        spec[k] = " "

    headers = [
        ["Symbol", "Parameter", "Unit", "SPEC", "Measurement", "Margin",
         "Pass/Fail"],
        ["Min", "Max", "Min", "Max", "Worst", "value", "%"]
    ]
    column0 = [
        "V<sub>L</sub>", "V<sub>H</sub>", "V<sub>nL</sub>", "V<sub>nH</sub>",
        "f<sub>clk</sub>", "t<sub>LOW</sub>", "t<sub>HIGH</sub>",
        "t<sub>SU;STA</sub>", "t<sub>HD;STA</sub>", "t<sub>SU;DAT;wr</sub>",
        "t<sub>HD;DAT;wr</sub>", "t<sub>SU;DAT;rd</sub>",
        "t<sub>HD;DAT;rd</sub>", "t<sub>r</sub>", "t<sub>f</sub>",
        "t<sub>SU;STO</sub>", "t<sub>BUF</sub>"
    ]
    column1 = [
        "voltage at LOW level", "voltage at HIGH level",
        "noise margin at the LOW level <b>[1]</b>",
        "noise margin at the HIGH level <b>[2]</b>",
        "SCL clock frequency", "LOW period of the SCL clock",
        "HIGH period of the SCL clock",
        "set-up time for repeated START condition",
        "hold time START condition",
        "set-up time for data WRITE from host to device",
        "hold time for data WRITE from host to device <b>[3]</b>",
        "set-up time for data READ from device to host",
        "data hold time for data READ from device to host <b>[3]</b>",
        "rise time of both SDA and SCL signals",
        "fall time of both SDA and SCL signals",
        "set-up time for STOP condition",
        "bus free time between a STOP and START condition"
    ]
    column2 = [
        "V", "V", "V<sub>DD</sub>", "V<sub>DD</sub>", "kHz", "us", "us", "us",
        "us", "us", "us", "us", "us", "ns", "ns", "us", "us"
    ]
    column3 = [
        "-", spec["v_high"], spec["v_nl"], spec["v_nh"], "0", spec["t_low"],
        spec["t_high"], spec["t_SU_STA"], spec["t_HD_STA"], spec["t_SU_DAT"],
        "0", spec["t_SU_DAT"], "0", spec["t_rise_min"], spec["t_fall_min"],
        spec["t_SU_STO"], spec["t_BUF"]
    ]
    column4 = [
        spec["v_low"], "-", "-", "-", spec["f_clk"], "-", "-", "-", "-", "-",
        spec["t_HD_DAT"], "-", spec["t_HD_DAT"], spec["t_rise_max"],
        spec["t_fall_max"], "-", "-"
    ]
    column5 = []
    column6, column7, column8, column9, column10 = [], [], [], [], []

    for i in range(len(field)):
      f = field[i]
      column6.append(values[f + "_max"])
      column7.append(values[f + "_worst"])
      column8.append(result[f + "_margin"])
      column9.append(result[f + "_percent"])
      column10.append(values[f + "_result"])
      if "sda" in f:
        column5.append("SDA: " + values[f + "_min"])
      elif "scl" in f:
        column5.append("SCL: " + values[f + "_min"])
      elif f[-1] == "S":
        column5.append("S: " + values[f + "_min"])
      elif f[-2:] == "Sr":
        column5.append("Sr: " + values[f + "_min"])
      elif "rising" in f:
        column5.append("rise: " + values[f + "_min"])
      elif "falling" in f:
        column5.append("fall: " + values[f + "_min"])
      else:
        column5.append(values[f + "_min"])

    report.write("<table><tr>")
    for i in range(len(headers[0])):
      column = headers[0][i]
      if i in [0, 1, 2, 6]:
        report.write(f"<th rowspan='2'>{column}</th>")
      elif i in [3, 5]:
        report.write(f"<th colspan='2'>{column}</th>")
      else:
        report.write(f"<th colspan='3'>{column}</th>")
    report.write("</tr><tr>")

    for i in range(len(headers[1])):
      column = headers[1][i]
      report.write(f"<th>{column}</th>")

    for i in range(len(field)):
      f = field[i]
      if "scl" in f or f[-2:] == "Sr" or "falling" in f:
        row = [
            column5.pop(0), column6.pop(0), column7.pop(0), column8.pop(0),
            column9.pop(0), column10.pop(0)
        ]
      else:
        row = [
            column0.pop(0), column1.pop(0), column2.pop(0), column3.pop(0),
            column4.pop(0), column5.pop(0), column6.pop(0), column7.pop(0),
            column8.pop(0), column9.pop(0), column10.pop(0)
        ]

      report.write(f"<tr id='{field[i]}' onclick='ShowSVG(\"{field[i]}\")'>")
      for j in range(len(row)-1):
        column = row[j]
        if i in [0, 2, 4, 6, 12, 14, 16, 18, 20, 22, 24] and j in range(5):
          report.write(f"<td rowspan='2'>{column}</td>")
        else:
          report.write(f"<td>{column}</td>\n")

      last_column = row[-1]
      if last_column == "Fail":
        report.write(f"<td class='critical'>{last_column}</td>")

      elif last_column == "Pass":
        if float(row[-2]) < 5:
          report.write(f"<td class='warning'>{last_column}</td>")
        else:
          report.write(f"<td>{last_column}</td>")

      elif last_column == "N/A" and i >= 4:
        report.write(f"<td class='NA'>{last_column.strip()}</td>")
      elif i == 0:
        report.write("<td rowspan='4'>Only for Informative</td>")
      report.write("</tr>")

    report.write(
        "</table><div><b>[1]</b> (V<sub>H</sub>-0.7V<sub>DD</sub>) / "
        "V<sub>DD</sub>&nbsp;&nbsp;<b>[2]</b> (0.3V<sub>DD</sub>-V<sub>L</sub>) "
        "/ V<sub>DD</sub></div><div><b>[3]</b> t<sub>VD;DAT</sub> and t"
        "<sub>VD;ACK</sub> are included in t<sub>HD;DAT</sub></div>"
    )

    for plot in svg_fields.values():
      report.write(plot)

    report.write("</body>\n</html>")

  return report_path

