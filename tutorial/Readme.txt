< HummingBird Tutorial >

Introduction:
	Automated Electrical Test for I2C Signal 


Requirement:
	Saleae software
	I2C analog signal measurement from SCL and SDA signal line.
	Recommend to use on Linux platform


Usage:
	Step1. 
	Use Saleae to capture the desire ANALOG signal or open the provided Saleae capture example
	following the video tutorial.

	Step2. 
	Load HummingBird extension module to Saleae from local directory following the video tutorial.

	Step3.
	Capture the desire measurement from SCL and SDA signal.
	The capture should start from the START pattern, and cover at least 5 SCL clk cycle,
	or the result might run into some error since there isn't enough data to analysis.
	Both capturing order would be fine, please make sure the two captures are overlapped.

	Step4. 
	A report would be generated and shown when both SCL and SDA data is captured. 
	
	Step5.
	In the report file, the user can click on each row and scroll down to check the waveform
	of the worst measurement margin, which would be shown at the bottom of the report.
	
	Step6. 
	Go further to run test on a different range of dataline!


Other Information:
	SPEC reference:		NXP UM10204
	https://www.nxp.com/docs/en/user-guide/UM10204.pdf
	
	Report File Path:	./HummingBird/output_reports/report.html
	The report file would be in the "./output_reports/" directory under your local HummingBird
	directory. 
	
	
	
 


