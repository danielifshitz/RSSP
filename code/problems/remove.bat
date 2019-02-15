@echo off

setlocal enabledelayedexpansion

for /F "tokens=*" %%A in (%1) do (
	set line=%%A
	echo !line:~3! >> newfile.txt
)

del %1
ren newfile.txt %1