Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

repoRoot = fso.GetParentFolderName(WScript.ScriptFullName)
script = fso.BuildPath(repoRoot, "Launch-Hermes.ps1")

If Not fso.FileExists(script) Then
  MsgBox "Cannot find launcher script: " & script, vbCritical, "Hermes Launcher"
  WScript.Quit 1
End If

cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & script & """"
shell.Run cmd, 0, False
