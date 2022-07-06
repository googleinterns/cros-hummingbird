"""HummingBird Report methods.

methods related to the output report.
"""
import datetime
import math
import os
import typing

import numpy as np


def SVGFile(data: np.ndarray, data_max: np.float64, data_min: np.float64,
            rect_idx: int, rect_width: int, field: str, vs: float):
  """Generate SVG plot.

  Args:
    data: numpy array of voltages
    data_max: data maximum value
    data_min: data minimum value
    rect_idx: index where the worst pattern occurs
    rect_width: the index width of the worst pattern
    field: the name of the parameter field
    vs: working voltage, for 30p and 70p marker on plot

  Returns:
    SVG plot to write in the html report.
  """
  svgfile = ""
  upscale_y = 40 * 5 // (data_max - data_min)
  resolution = min(max(len(data) // 2000, 1), 150)
  upscale_x = 3000 / len(data) * resolution
  width = len(data) * upscale_x / resolution
  height = (data_max - data_min) * upscale_y + 120

  if field == "scl_show":
    svgfile += (
        f"\n\t<div id='{field}'>\n\t\t<div class='column_left'>SCL capture</div>"
        "\n\t\t<div class='column_right'>"
        f"\n\t\t\t<svg viewBox='0 0 {width} {height}'>"
    )

  elif field == "sda_show":
    svgfile += (
        f"\n\t<div id='{field}'>\n\t\t<div class='column_left'>SDA capture</div>"
        "\n\t\t<div class='column_right margin'>"
        f"\n\t\t\t<svg viewBox='0 0 {width} {height}'>"
    )

  else:
    svgfile += f"\n\t<div id='{field}_hide' class='hide'>"
    if "sda" in field:
      svgfile += (
          "\n\t\t<div class='column_left margin'>SDA<br>zoom in</div>"
          "\n\t\t<div class='column_right margin'>"
      )
    elif "SU" not in field and "HD" not in field and "BUF" not in field:
      svgfile += (
          "\n\t\t<div class='column_left margin'>SCL<br>zoom in</div>"
          "\n\t\t<div class='column_right margin'>"
      )
    else:
      svgfile += (
          "\n\t\t<div class='column_left'>SCL<br>zoom in</div>"
          "\n\t\t<div class='column_right'>"
      )
    svgfile += f"\n\t\t\t<svg viewBox='0 0 {width} {height}'>"

    # Red Rect to Mark the Measure Area

    xx1 = max(rect_idx - rect_width, 0)
    yy1 = ((xx1 - math.floor(xx1)) *
           (data[math.ceil(xx1)] - data[math.floor(xx1)]) +
           data[math.floor(xx1)])
    yy1 = (data_max - yy1) * upscale_y + 60
    xx1 = xx1 // resolution * upscale_x

    xx2 = rect_idx
    yy2 = ((xx2 - math.floor(xx2)) *
           (data[math.ceil(xx2)] - data[math.floor(xx2)]) +
           data[math.floor(xx2)])
    yy2 = (data_max - yy2) * upscale_y + 60
    xx2 = xx2 // resolution * upscale_x

    y30p = (data_max - vs * 0.3) * upscale_y + 60
    y70p = (data_max - vs * 0.7) * upscale_y + 60

    rect_width = max(rect_width // resolution * upscale_x, 7)
    rect_x = rect_idx // resolution * upscale_x - rect_width
    svgfile += (
        f"\n\t\t\t\t<rect x={rect_x} y=1% width={rect_width} height=95% class='rect'/>"
    )
    if ((("SU_STA" in field or "SU_STO" in field) and "scl" in field) or
        ("HD_STA" in field and "sda" in field)):
      svgfile += (
          f"\n\t\t\t\t<line x1={xx1 - 15} y1={yy1} x2={xx1 + 15} y2={yy1} class='line'/>"
      )
      if abs(yy1 - y30p) < abs(yy1 - y70p):
        svgfile += f"\n\t\t\t\t<text x={xx1 - 110} y={yy1} class='text'>30 %</text>"
      else:
        svgfile += f"\n\t\t\t\t<text x={xx1 - 110} y={yy1} class='text'>70 %</text>"
    elif ((("SU_STA" in field or "SU_STO" in field) and "sda" in field) or
          ("HD_STA" in field and "scl" in field)):
      svgfile += (
          f"\n\t\t\t\t<line x1={xx2 - 15} y1={yy2} x2={xx2 + 15} y2={yy2} class='line'/>"
      )
      if abs(yy2 - y30p) < abs(yy2 - y70p):
        svgfile += f"\n\t\t\t\t<text x={xx2 + 30} y={yy2} class='text'>30 %</text>"
      else:
        svgfile += f"\n\t\t\t\t<text x={xx2 + 30} y={yy2} class='text'>70 %</text>"
    elif (("SU" in field and "sda" in field) or
          ("HD" in field and "scl" in field)):
      svgfile += (
          f"\n\t\t\t\t<line x1={xx1 - 15} y1={yy1} x2={xx1 + 15} y2={yy1} class='line'/>"
      )
      if abs(yy1 - y30p) < abs(yy1 - y70p):
        svgfile += f"\n\t\t\t\t<text x={xx1 - 110} y={yy1} class='text'>30 %</text>"
      else:
        svgfile += f"\n\t\t\t\t<text x={xx1 - 110} y={yy1} class='text'>70 %</text>"
    elif (("SU" in field and "scl" in field) or
          ("HD" in field and "sda" in field)):
      svgfile += (
          f"\n\t\t\t\t<line x1={xx2 - 15} y1={yy2} x2={xx2 + 15} y2={yy2} class='line'/>"
      )
      if abs(yy2 - y30p) < abs(yy2 - y70p):
        svgfile += f"\n\t\t\t\t<text x={xx2 + 30} y={yy2} class='text'>30 %</text>"
      else:
        svgfile += f"\n\t\t\t\t<text x={xx2 + 30} y={yy2} class='text'>70 %</text>"
    elif not ("BUF" in field and "scl" in field):
      svgfile += (
          f"\n\t\t\t\t<line x1={xx1 - 15} y1={yy1} x2={xx1 + 15} y2={yy1} class='line'/>"
          f"\n\t\t\t\t<line x1={xx2 - 15} y1={yy2} x2={xx2 + 15} y2={yy2} class='line'/>"
      )
      if abs(yy1 - y30p) < abs(yy1 - y70p):
        svgfile += f"\n\t\t\t\t<text x={xx1 - 110} y={yy1} class='text'>30 %</text>"
      else:
        svgfile += f"\n\t\t\t\t<text x={xx1 - 110} y={yy1} class='text'>70 %</text>"
      if abs(yy2 - y30p) < abs(yy2 - y70p):
        svgfile += f"\n\t\t\t\t<text x={xx2 + 30} y={yy2} class='text'>30 %</text>"
      else:
        svgfile += f"\n\t\t\t\t<text x={xx2 + 30} y={yy2} class='text'>70 %</text>"

  # Data Polyline

  points = ""
  if field == "scl_show" or field == "sda_show":
    for i in range(0, len(data), resolution):
      points += f"{i // resolution * upscale_x},{int((data_max - data[i]) * upscale_y + 120)} "
    svgfile += f"\n\t\t\t\t<polyline points='{points}' class='plotline'/>"
  else:
    for i in range(0, len(data), resolution):
      points += f"{i // resolution * upscale_x},{int((data_max - data[i]) * upscale_y + 60)} "
    svgfile += (
        f"\n\t\t\t\t<polyline points='{points}' class='plotline'/>\n\t\t\t</svg>\n\t\t</div>\n\t</div>"
    )

  return svgfile


def OutputReportFile(mode: str, spec: typing.Dict[str, float], vs: float, clk_stretch: bool,
                     values: typing.Dict[str, np.float64],
                     result: typing.Dict[str, np.float64],
                     fail: typing.Dict[str, int], num_pass: int,
                     svg_fields: typing.Dict[str, str],
                     addr: typing.List[str], sampling_rate: int,
                     waveform_info: typing.List[int],
                     save_folder: str):
  """Write HTML report.

  Args:
    mode: operation mode
    spec: dictionary of SPEC limitation for each field (max / min)
    vs: working voltge
    clk_stretch: has clock stretching or not
    values: dictionary of measurement for each field
            include max / min / worst for each field
    result: dictionary of electrical test result
            include Pass or Fail / margin / margin percentage for each field
    fail: dictionary of the failed SPEC fields
    num_pass: number of pass of the test
    svg_fields: SVG plot dictionary for each SPEC field
    addr: device address included in the capture
    sampling_rate: sampling rate of the analog data
    waveform_info: edge count and pattern count info list
    save_folder: optional input when using CMD

  Returns:
    report_path: save path for current report.
  """
  result_num = len(fail) + num_pass
  fails = ", ".join(list(fail.keys()))

  runt_num = 0
  if result.get("runt_scl"):
    runt_num += len(result["runt_scl"])
  if result.get("runt_sda"):
    runt_num += len(result["runt_sda"])

  field = [
      "v_low_sda", "v_low_scl", "v_high_sda", "v_high_scl", "v_nl_sda",
      "v_nl_scl", "v_nh_sda", "v_nh_scl", "f_clk", "t_low", "t_high",
      "t_SU_STA", "t_HD_STA_S", "t_HD_STA_Sr", "t_SU_DAT_host_rising",
      "t_SU_DAT_host_falling", "t_HD_DAT_host_rising", "t_HD_DAT_host_falling",
      "t_SU_DAT_dev_rising", "t_SU_DAT_dev_falling", "t_HD_DAT_dev_rising",
      "t_HD_DAT_dev_falling", "t_rise_sda", "t_rise_scl", "t_fall_sda",
      "t_fall_scl", "t_SU_STO", "t_BUF"
  ]
  spec_field = [
      "v_low", "v_high", "v_nh", "v_nl", "t_rise_max", "t_rise_min",
      "t_fall_max", "t_fall_min", "t_low", "t_high", "f_clk", "t_SU_DAT",
      "t_HD_DAT", "t_HD_STA", "t_SU_STA", "t_SU_STO", "t_BUF"
  ]
  time_now = datetime.datetime.now()
  report_path = os.path.join(
      save_folder, f"report_{time_now.strftime('%Y%m%d%H%M%S')}.html"
  )
  with open(report_path, "w") as report:
    report.write(
        "<!DOCTYPE html><html lang='en'>\n<head>\n\t<meta charset='UTF-8'>"
    )
    report.write("\n\t<title>HummingBird Output Report</title>\n\t<style>")
    style = """\n\t\tbody {
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
    button {
      background-color: #e7e7e7;
      border: none;
      display: inline-block;
      padding: 5px 10px;
      margin-left: 10px;
    }
    button:hover {
      background-color: #aaa;
      color: white;
    }
    .left {
      float: left;
      width: 35%;
    }
    .right {
      float: left;
      width: 65%;
    }
    .column_left {
      float: left;
      width: 9%;
      padding: 30px 0 0 0;
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
    .summary td {
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
      stroke-width: 4;
    }
    .line2 {
      stroke: gray;
      stroke-width: 3;
    }
    .plotline {
      fill: none;
      stroke: black;
      stroke-width: 4;
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
      font-size: 35px;
    }
    .text2 {
      fill: black;
      font-size: 20px;
    }"""

    script = """\n\t<script>
    function ShowSVG(x) {
      console.log(x);
      HideRunt();
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
          "t_SU_DAT_host_rising", "t_SU_DAT_host_falling", "t_HD_DAT_host_rising",
          "t_HD_DAT_host_falling", "t_SU_DAT_dev_rising", "t_SU_DAT_dev_falling",
          "t_HD_DAT_dev_rising", "t_HD_DAT_dev_falling","t_HD_STA_S", "t_HD_STA_Sr",
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
     function ShowRunt(x) {
       console.log(x);
       scl_elems = document.querySelectorAll(".runt_scl");
       sda_elems = document.querySelectorAll(".runt_sda");
       sda_elems.forEach(function(itm, idx, arr) {
          itm.style.display = "inline";
       })
       scl_elems.forEach(function(itm, idx, arr) {
          itm.style.display = "inline";
       })
       let fields = [
            "v_low_scl", "v_high_scl", , "v_nl_scl", "v_nh_scl", "v_nl_sda",
            "v_nh_sda","t_rise_scl", "t_fall_scl", "t_low", "t_high", "f_clk",
            "v_low_sda", "v_high_sda", "t_rise_sda", "t_fall_sda",
            "t_SU_DAT_host_rising", "t_SU_DAT_host_falling", "t_HD_DAT_host_rising",
            "t_HD_DAT_host_falling", "t_SU_DAT_dev_rising", "t_SU_DAT_dev_falling",
            "t_HD_DAT_dev_rising", "t_HD_DAT_dev_falling","t_HD_STA_S", "t_HD_STA_Sr",
            "t_SU_STA", "t_SU_STO", "t_BUF"
        ];
        fields.forEach(function(item, index, array) {
            ele1 = document.getElementById(item);
            if(ele1 != null){ele1.style.background = "white";}
            selector1 = `#${item}_hide, #${item}_scl_hide, #${item}_sda_hide, `;
            selector2 = `#${item}_rect, #${item}_scl_rect, #${item}_sda_rect, #${item}_line, #${item}_poly`;
            elems = document.querySelectorAll(selector1 + selector2);
            elems.forEach(function(itm, idx, arr) {
                itm.style.display = "none";
            })
         })
     }
     function HideRunt() {
       scl_elems = document.querySelectorAll(".runt_scl");
       sda_elems = document.querySelectorAll(".runt_sda");
       sda_elems.forEach(function(itm, idx, arr) {
          itm.style.display = "none";
       })
       scl_elems.forEach(function(itm, idx, arr) {
          itm.style.display = "none";
       })      
     }\n\t</script>"""
    report.write(style)
    report.write("\n\t</style>\n</head>\n<body>")
    report.write(script)

    report.write(
        "\n\t<h1>HummingBird I2C Electrical Testing Report</h1>\n\t<div class='left'>"
        "\n\t\t<p><b>Report Time:</b>&nbsp;&nbsp;&nbsp;&nbsp;"
    )
    report.write(time_now.strftime("%Y-%m-%d %H:%M:%S"))
    report.write(
        f"</p>\n\t\t<p><b>File Save Path:</b>&nbsp;{report_path}</p>"
        f"\n\t\t<p><b>Operation Mode:</b>&nbsp;&nbsp;{mode}</p>"
        f"\n\t\t<p><b>Operation Voltage:</b>&nbsp;&nbsp;{vs}V</p>"
        f"\n\t\t<p><b>Sampling Rate:</b>&nbsp;&nbsp;{sampling_rate}MS/s (Strongly "
        "recommend &geq; 50MS/s for accuracy)</p>"
        "\n\t\t<p><b>Reference SPEC Link:</b>&nbsp;&nbsp;"
        "<a href='https://www.nxp.com/docs/en/user-guide/UM10204.pdf'>"
        "NXP UM10204</a></p>"
    )
    if clk_stretch:
    	report.write("\n\t\t<p><b>Clock Stretching:</b>&nbsp;&nbsp;Yes</p>")
    else:
    	report.write("\n\t\t<p><b>Clock Stretching:</b>&nbsp;&nbsp;No</p>")
    
    if not fails:
      report.write("\n\t\t<p>Pass SPEC test successfully! :)</p>")
    else:
      report.write("\n\t\t<p><b>Fail:</b>&nbsp;&nbsp;" + fails + "</p>")
    report.write("\n\t\t<div class='addr'><b>Include Address (7-bit):</b>&nbsp;&nbsp;")
    report.write(" ".join(addr))
    report.write(
        f"</div>\n\t\t<p>Detect {runt_num} runt pattern<button onclick=ShowRunt()>"
        "Show Runt</button><button onclick=HideRunt()>Hide Runt</button></p>"
        "\n\t</div>\n\t<div class='right'>\n\t\t<table class='summary'>"
        "\n\t\t\t<tr>\n\t\t\t\t<th colspan=2>Margin Threshold</th>\n\t\t\t</tr>"
        "\n\t\t\t<tr>\n\t\t\t\t<td><b>Warning</b></td>\n\t\t\t\t<td class='warning'>"
        "&lt; 5%</td>\n\t\t\t</tr>\n\t\t\t<tr>\n\t\t\t\t<td><b>Critical</b></td>"
        "\n\t\t\t\t<td class='critical'>&lt; 0%</td>\n\t\t\t</tr>\n\t\t</table>"
        "\n\t\t<table class='summary'>\n\t\t\t<tr>\n\t\t\t\t<th colspan=2>SPEC "
        "Test Summary</th>\n\t\t\t</tr>\n\t\t\t<tr>\n\t\t\t\t<td><b>Fail</b></td>"
        f"\n\t\t\t\t<td>{len(fail)}</td>\n\t\t\t</tr>\n\t\t\t<tr>\n\t\t\t\t<td>"
        f"<b>Pass</b></td>\n\t\t\t\t<td>{num_pass}</td>\n\t\t\t</tr>\n\t\t\t<tr>"
        f"\n\t\t\t\t<td><b>Total</b></td>\n\t\t\t\t<td>{result_num}</td>\n\t\t\t</tr>"
        "\n\t\t</table>\n\t\t<table class='summary'>\n\t\t\t<tr>"
        "\n\t\t\t\t<th colspan=2>Waveform Info</th>\n\t\t\t</tr>"
    )

    info_list = [
        "SCL rise edges", "SCL fall edges", "SDA rise edges", "SDA fall edges",
        "START patterns", "RESTART patterns", "STOP patterns"
    ]
    for i in range(len(info_list)):
      report.write(
          f"\n\t\t\t<tr>\n\t\t\t\t<td><b>{info_list[i]}</b></td>"
          f"\n\t\t\t\t<td>{waveform_info[i]}</td>\n\t\t\t</tr>"
      )
    report.write(
        "\n\t\t</table>\n\t\t<h3>Click each row to check the waveform of the worst "
        "mearsurement shown <u>at the end of report</u>.</h3>\n\t</div>"
    )

    for f in field:
      if values.get(f + "_worst") is None:
        values[f + "_max"] = "N/A"
        values[f + "_min"] = "N/A"
        values[f + "_worst"] = "N/A"

      else:
        if "t_rise_" in f or "t_fall_" in f:
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
        spec[k] = "-"

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

    report.write("\n\t<table>\n\t\t<tr>")
    for i in range(len(headers[0])):
      column = headers[0][i]
      if i in [0, 1, 2, 6]:
        report.write(f"\n\t\t\t<th rowspan='2'>{column}</th>")
      elif i in [3, 5]:
        report.write(f"\n\t\t\t<th colspan='2'>{column}</th>")
      else:
        report.write(f"\n\t\t\t<th colspan='3'>{column}</th>")
    report.write("\n\t\t</tr>\n\t\t<tr>")

    for i in range(len(headers[1])):
      column = headers[1][i]
      report.write(f"\n\t\t\t<th>{column}</th>")

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

      report.write(
          f"\n\t\t<tr id='{field[i]}' onclick='ShowSVG(\"{field[i]}\")'>"
      )
      for j in range(len(row)-1):
        column = row[j]
        if i in [0, 2, 4, 6, 12, 14, 16, 18, 20, 22, 24] and j in range(5):
          report.write(f"\n\t\t\t<td rowspan='2'>{column}</td>")
        else:
          report.write(f"\n\t\t\t<td>{column}</td>")

      last_column = row[-1]
      if last_column == "Fail":
        report.write(f"\n\t\t\t<td class='critical'>{last_column}</td>")

      elif last_column == "Pass":
        if float(row[-2]) < 5:
          report.write(f"\n\t\t\t<td class='warning'>{last_column}</td>")
        else:
          report.write(f"\n\t\t\t<td>{last_column}</td>")

      elif last_column == "N/A" and i >= 4:
        report.write(f"\n\t\t\t<td class='NA'>{last_column.strip()}</td>")
      elif i == 0:
        report.write("\n\t\t\t<td rowspan='4'>Only for Informative</td>")
      report.write("\n\t\t</tr>")

    report.write(
        "\n\t</table>\n\t<div><b>[1]</b> (V<sub>H</sub>-0.7V<sub>DD</sub>) / V<sub>DD</sub></div>"
        "\n\t<div><b>[2]</b> (0.3V<sub>DD</sub>-V<sub>L</sub>) / V<sub>DD</sub></div>"
        "\n\t<div><b>[3]</b> t<sub>VD;DAT</sub> and t<sub>VD;ACK</sub> are included in t<sub>HD;DAT</sub></div>"
    )

    for plot in svg_fields.values():
      report.write(plot)

    report.write("\n</body>\n</html>")

  return report_path

