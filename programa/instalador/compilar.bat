@echo off
rem Compila Setup.exe (en la carpeta de arriba de "programa") con el compilador de C# que viene con
rem Windows (.NET Framework 4). No hace falta instalar nada.
rem "Laburo IA.exe" (el lanzador) NO queda suelto en la raíz: va empaquetado DENTRO de Setup.exe
rem (recurso LaburoIA.exe) y Setup lo desempaqueta en la raíz al instalar. Así, antes de instalar
rem solo se ve Setup.exe y no hay confusión.
cd /d "%~dp0"
set CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe
if not exist "%CSC%" set CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe
set ICO=..\app\recursos\logo.ico
set PNG=..\app\recursos\logo.png
set LANZADOR=%TEMP%\LaburoIA-lanzador.exe
"%CSC%" /nologo /target:winexe /optimize+ /win32icon:%ICO% /out:"%LANZADOR%" Lanzador.cs || goto error
"%CSC%" /nologo /target:winexe /optimize+ /win32icon:setup.ico /resource:%PNG%,logo.png /resource:"%LANZADOR%",LaburoIA.exe /r:System.Windows.Forms.dll /r:System.Drawing.dll /r:Microsoft.CSharp.dll /out:..\..\Setup.exe Setup.cs || goto error
del "%LANZADOR%"
echo Listo: Setup.exe en la carpeta de arriba de "programa" (trae adentro a Laburo IA.exe).
exit /b 0
:error
echo Fallo la compilacion.
exit /b 1
