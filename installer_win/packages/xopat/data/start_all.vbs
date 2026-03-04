Dim oShell, sBase
Set oShell = CreateObject("WScript.Shell")
sBase = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
oShell.Run """" & sBase & "start_all.bat""", 0, False