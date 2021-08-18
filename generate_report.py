"""HummingBird Report methods.

The file contain methods related to output report.

"""
import datetime
import math
import os
import typing

import numpy as np


LOCAL_PATH = os.path.join(os.path.dirname(__file__), "output_reports")
if not os.path.exists(LOCAL_PATH):
  os.makedirs(LOCAL_PATH)


def SVGFile(data: np.ndarray, data_max: np.float64, data_min: np.float64,
            rect_idx: int, rect_width: int, field: str, vs: float):
  """Generate SVG plot.

  Args:
    data:  numpy array of voltages
    data_max:  data maximum value
    data_min:  data minimum value
    rect_idx:  index where the worst pattern occurs
    rect_width:  the index width where the worst pattern last
    field:  the SPEC field of this SVG plot
    vs: working voltage, for 30p and 70p marker on plot

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
        f"<svg viewBox='0 0 {width} {height * 1.2 + 120}'>"
    )

  elif field == "sda_show":
    svgfile += (
        f"<div id='{field}'><div class='column_left margin'>SDA capture</div>"
        "<div class='column_right margin'>"
        f"<svg viewBox='0 0 {width} {height * 1.2 + 120}'>"
    )

  else:
    svgfile += f"<div id='{field}_hide' class='hide'>"
    if "sda" in field:
      svgfile += (
          "<div class='column_left margin'>SDA<br>zoom in</div>"
          "<div class='column_right margin'>"
      )
    elif "SU" not in field and "HD" not in field and "BUF" not in field:
      svgfile += (
          "<div class='column_left margin'>SCL<br>zoom in</div>"
          "<div class='column_right margin'>"
      )
    else:
      svgfile += (
          "<div class='column_left'>SCL<br>zoom in</div>"
          "<div class='column_right'>"
      )
    svgfile += f"<svg viewBox='0 0 {width} {height * 1.2 + 120}'>"

    # Red Rect to Mark the Measure Area

    xx1 = max(rect_idx - rect_width, 0)
    yy1 = ((xx1 - math.floor(xx1)) *
           (data[math.ceil(xx1)] - data[math.floor(xx1)]) +
           data[math.floor(xx1)])
    yy1 = (data_max - int(yy1 * 50)) * 2 + 160
    xx1 = xx1 // rate * 5

    xx2 = rect_idx
    yy2 = ((xx2 - math.floor(xx2)) *
           (data[math.ceil(xx2)] - data[math.floor(xx2)]) +
           data[math.floor(xx2)])
    yy2 = (data_max - int(yy2 * 50)) * 2 + 160
    xx2 = xx2 // rate * 5

    y30p = (data_max - int(vs * 0.3 * 50)) * 2 + 160
    y70p = (data_max - int(vs * 0.7 * 50)) * 2 + 160

    rect_width = max(rect_width // rate * 5, 7)
    rect_x = rect_idx // rate * 5 - rect_width
    svgfile += (
        f"<rect x={rect_x} y=100 width={rect_width} height=90% class='rect'/>"
    )
    if ((("SU_STA" in field or "SU_STO" in field) and "scl" in field) or
        ("HD_STA" in field and "sda" in field)):
      svgfile += (
          f"<line x1={xx1 - 20} y1={yy1} x2={xx1 + 20} y2={yy1} class='line'/>"
      )
      if abs(yy1 - y30p) < abs(yy1 - y70p):
        svgfile += f"<text x={xx1 - 140} y={yy1} class='text'>30 %</text>"
      else:
        svgfile += f"<text x={xx1 - 140} y={yy1} class='text'>70 %</text>"
    elif ((("SU_STA" in field or "SU_STO" in field) and "sda" in field) or
          ("HD_STA" in field and "scl" in field)):
      svgfile += (
          f"<line x1={xx2 - 20} y1={yy2} x2={xx2 + 20} y2={yy2} class='line'/>"
      )
      if abs(yy2 - y30p) < abs(yy2 - y70p):
        svgfile += f"<text x={xx2 + 30} y={yy2} class='text'>30 %</text>"
      else:
        svgfile += f"<text x={xx2 + 30} y={yy2} class='text'>70 %</text>"
    elif (("SU" in field and "sda" in field) or
          ("HD" in field and "scl" in field)):
      svgfile += (
          f"<line x1={xx1 - 20} y1={yy1} x2={xx1 + 20} y2={yy1} class='line'/>"
      )
      if abs(yy1 - y30p) < abs(yy1 - y70p):
        svgfile += f"<text x={xx1 - 140} y={yy1} class='text'>30 %</text>"
      else:
        svgfile += f"<text x={xx1 - 140} y={yy1} class='text'>70 %</text>"
    elif (("SU" in field and "scl" in field) or
          ("HD" in field and "sda" in field)):
      svgfile += (
          f"<line x1={xx2 - 20} y1={yy2} x2={xx2 + 20} y2={yy2} class='line'/>"
      )
      if abs(yy2 - y30p) < abs(yy2 - y70p):
        svgfile += f"<text x={xx2 + 30} y={yy2} class='text'>30 %</text>"
      else:
        svgfile += f"<text x={xx2 + 30} y={yy2} class='text'>70 %</text>"
    elif not ("BUF" in field and "scl" in field):
      svgfile += (
          f"<line x1={xx1 - 20} y1={yy1} x2={xx1 + 20} y2={yy1} class='line'/>"
          f"<line x1={xx2 - 20} y1={yy2} x2={xx2 + 20} y2={yy2} class='line'/>"
      )
      if abs(yy1 - y30p) < abs(yy1 - y70p):
        svgfile += f"<text x={xx1 - 140} y={yy1} class='text'>30 %</text>"
      else:
        svgfile += f"<text x={xx1 - 140} y={yy1} class='text'>70 %</text>"
      if abs(yy2 - y30p) < abs(yy2 - y70p):
        svgfile += f"<text x={xx2 + 30} y={yy2} class='text'>30 %</text>"
      else:
        svgfile += f"<text x={xx2 + 30} y={yy2} class='text'>70 %</text>"

  # Data Polyline

  points = ""
  for i in range(0, len(data), rate):
    points += f"{i // rate * 5},{(data_max - int(data[i] * 50)) * 2 + 160} "
  svgfile += f"<polyline points='{points}' class='plotline'/>"
  if field != "scl_show" and field != "sda_show":
    svgfile += "</svg></div></div>"

  return svgfile


def OutputReportFile(mode: str, spec: typing.Dict[str, float], vs: float,
                     values: typing.Dict[str, np.float64],
                     result: typing.Dict[str, np.float64],
                     fail: typing.Dict[str, int], num_pass: int,
                     svg_fields: typing.Dict[str, str],
                     addr: typing.List[str], sampling_rate: int):
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
    sampling_rate: sampling rate of the analog data

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
      padding: 1% 3% 4% 3%;
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
    svg {
      height: 100%;
      width: 100%;
    }
    div {
      margin: 1% auto;
      width: 100%;
    }
    .left {
      float: left;
      width: 50%;
    }
    .right {
      float: left;
      width: 50%;
    }
    .column_left {
      float: left;
      width: 10%;
      padding: 30px 0;
      text-align: center;
      font-weight: 600;
      font-size: 21px;
      margin: 0;
    }
    .column_right {
      float: left;
      width: 90%;
      padding: 0;
      margin: 0;
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
      color: #111;
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
    }
    .margin {
      margin-bottom: 5%;
    }
    .rect {
      fill: red;
      opacity: 0.3;
    }
    .line {
      stroke: black;
      stroke-width: 5;
    }
    .plotline {
      fill: none;
      stroke: black;
      stroke-width: 6;
    }
    .arrowline {
      stroke: #555;
      stroke-width: 50;
      display: none;
    }
    .arrow {
      fill: #555;
      display: none;
    }
    .text {
      fill: black;
      font-size: 50px;
    }"""

    script = """<script>
    function ShowSVG(x){
      console.log(x);
      ele_self = document.getElementById(x);
      selector1 = `#${x}_hide, #${x}_scl_hide, #${x}_sda_hide, `;
      selector2 = `#${x}_rect, #${x}_scl_rect, #${x}_sda_rect, #${x}_line, #${x}_poly`;
      elems = document.querySelectorAll(selector1 + selector2);
      elems.forEach(function(itm, idx, arr) {
          itm.style.display = "inline";
      })
      if (elems.length != 0){
          ele_self.style.background = "#F5B7B1";
      }
      let fields = [
          "v_low_scl", "v_high_scl", , "v_nl_scl", "v_nh_scl", "v_nl_sda",
          "v_nh_sda","t_rise_scl", "t_fall_scl", "t_low", "t_high", "f_clk",
          "v_low_sda", "v_high_sda", "t_rise_sda", "t_fall_sda",
          "t_SU_DAT_rising_host", "t_SU_DAT_falling_host", "t_HD_DAT_rising_host",
          "t_HD_DAT_falling_host", "t_SU_DAT_rising_dev", "t_SU_DAT_falling_dev",
          "t_HD_DAT_rising_dev", "t_HD_DAT_falling_dev","t_HD_STA_S", "t_HD_STA_Sr",
          "t_SU_STA", "t_SU_STO", "t_BUF"
      ];
      fields.forEach(function(item, index, array) {
          if (item != x){
            ele1 = document.getElementById(item);
            if(ele1 != null){ele1.style.background = "white";}
            selector1 = `#${item}_hide, #${item}_scl_hide, #${item}_sda_hide, `;
            selector2 = `#${item}_rect, #${item}_scl_rect, #${item}_sda_rect, #${item}_line, #${item}_poly`;
            elems = document.querySelectorAll(selector1 + selector2);
            elems.forEach(function(itm, idx, arr) {
                itm.style.display = "none";
            })
          }
       })
     }
    </script>"""
    report.write(style)
    report.write("</style></head><body>")
    report.write(script)

    report.write(
        "<h1>HummingBird I2C Electrical Testing Report</h1><div class='left'>"
        "<p><b>Report Time:</b>&nbsp;&nbsp;&nbsp;&nbsp;"
    )
    report.write(time_now.strftime("%Y-%m-%d %H:%M:%S"))
    report.write(
        f"</p><p><b>File Save Path:</b>&nbsp;{report_path}</p>"
        f"<p><b>Operation Mode:</b>&nbsp;&nbsp;{mode}</p>"
        f"<p><b>Operation Voltage:</b>&nbsp;&nbsp;{vs}V</p>"
        f"<p><b>Sampling Rate:</b>&nbsp;&nbsp;{sampling_rate}MS/s</p>"
        "<p><b>Reference SPEC Link:</b>&nbsp;&nbsp;"
        "<a href='https://www.nxp.com/docs/en/user-guide/UM10204.pdf'>"
        "NXP UM10204</a></p>"
    )
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
        "</table><div><b>[1]</b> (V<sub>H</sub>-0.7V<sub>DD</sub>) / V<sub>DD</sub></div>"
        "<div><b>[2]</b> (0.3V<sub>DD</sub>-V<sub>L</sub>) / V<sub>DD</sub></div>"
        "<div><b>[3]</b> t<sub>VD;DAT</sub> and t<sub>VD;ACK</sub> are included in t<sub>HD;DAT</sub></div>"
    )

    for plot in svg_fields.values():
      report.write(plot)

    report.write("</body>\n</html>")

  return report_path

