# HummingBird: Automated Electrical Test for I2C Signal
  
HummingBird is an extension that check whether the captured analog measurements meet 
I2C SPEC limitation.

SPEC reference:	[NXP UM10204](https://www.nxp.com/docs/en/user-guide/UM10204.pdf)

A report html file would be generated at under tmp folder,
for example, /tmp/output_reports/report_20210824150025.html

Capture <b>both SCL and SDA data</b> so that all SPEC limitation could be tested. 
Either order would be fine. The test would only run after both SCL and SDA data are 
provided. Note that only the overlapped region of the two datalines would be analyzed. 


Support SPEC | definition
----------------- | ------------------
v_nl | noise margin at the LOW level
v_nh | noise margin at the HIGH level
t_rise | signal rise time
t_fall | signal rise time
t_low | LOW period of the SCL clock
t_high | HIGH period of the SCL clock
f_clk | SCL clock frequency
t_SU_DAT | data set-up time
t_HD_DAT | data hold time, from the falling edge of SCL
t_HD_STA | hold time (repeated) START condition
t_SU_STA | set-up time for a repeated START condition
t_SU_STO | set-up time for STOP condition
t_BUF | bus free time between a STOP and START condition


## Requirements
- Supporting working voltage: 1.8V / 3.3V / 5V
- Supporting operation mode: Standard Mode / Fast Mode / Fast Mode Plus
- Both SCL and SDA datas should be provided and overlapped for at least 5 SCL clk cycles
- The captured should include START or RESTART pattern


## Instructions
1. Install this extension by clicking "Install"
2. Collect SDA and SCL analog data by Saleae Logic2 software
3. Capture the desired data range of both SCL and SDA datalines to go under test by clicking 
on the "Timing Markers & Measurements" on the right, then the Measurements "+" icon, or 
keyboard shortcut "Ctrl + G".

	![Adding a Measurement](figures/add_measurement.png)

4. Drag the measurement selection window over your recorded data in the desired range. Note that 
the more data captured, the more computation time is needed.
5. Both SDA and SCL data should be captured (both order would be fine) to check all SPEC 
limitation. Only the overlapped region of the two datalines would be analyzed. 
6. Test report would be generated and shown after both SCL and SDA data is captured. Each operation 
parameters predicted would be specified on the report. 
7. Go further to run tests on a different range of dataline!

## Command line to load CSV file
1. prepare csv file containing both SDA and SCL analog data.
2. In command line under Hummingbird local folder: 
```python3 main.py [-h] CSV_FILE_PATH
  [--output_folder OUTPUT_FOLDER]
  [--working_voltage WORKING_VOLTAGE]
  [--operation_mode OPERATION_MODE]
```
3. Test report would be generated and shown when both SCL and SDA data is captured. Each operation parameters predicted would be specified on the report. 
4. Go further to run tests on different data files!


