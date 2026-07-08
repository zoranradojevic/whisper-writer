' WhisperWriter - tihi start bez konzole (radi samo tray ikonica).
' Za vidljivu konzolu (status, brzina, greske) koristi WhisperWriter.bat.
Set fso = CreateObject("Scripting.FileSystemObject")
appDir = fso.GetParentFolderName(WScript.ScriptFullName)
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = appDir
sh.Run """" & appDir & "\.venv\Scripts\python.exe"" run.py --silent", 0, False
