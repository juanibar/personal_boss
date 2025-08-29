Option Explicit
Dim fso, shell, scriptDir, batPath, cmd
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
batPath = fso.BuildPath(scriptDir, "PersonalBoss.bat")
cmd = Chr(34) & batPath & Chr(34)

' Ejecutar oculto (0), sin esperar (False)
shell.CurrentDirectory = scriptDir
shell.Run cmd, 0, False
