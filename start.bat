@echo off

C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoExit -Command ^
"cd 'C:\Users\adm-T36Physics\Documents\Shift-report-automation-main'; ^
.\venv\Scripts\Activate.ps1; ^
cd 'C:\Users\adm-T36Physics\Documents\Shift-report-automation-main\app'; ^
start python run.py; ^
cd 'C:\Users\adm-T36Physics\Documents\Shift-report-automation-main\Kunal Dose report app'; ^
start python Dose.py; ^
cd 'C:\Users\adm-T36Physics\Documents\Shift-report-automation-main\Task Reminder App'; ^
start python app.py"