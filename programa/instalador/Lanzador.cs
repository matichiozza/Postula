// "Laburo IA.exe": el ejecutable de la raíz. Abre la app (programa\app\app.py) con el pythonw que
// dejó anotado Setup.exe en programa\datos\python.txt. No usa rutas fijas: si se mueve la carpeta, sigue andando.
// Se compila con compilar.bat (csc de .NET Framework, viene con Windows).
using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Windows.Forms;

[assembly: AssemblyTitle("Laburo IA")]
[assembly: AssemblyProduct("Laburo IA")]
[assembly: AssemblyDescription("Laburo IA - app de postulaciones")]
[assembly: AssemblyVersion("1.0.0.0")]

static class Lanzador
{
    [STAThread]
    static void Main()
    {
        string raiz = AppDomain.CurrentDomain.BaseDirectory;
        string prog = Path.Combine(raiz, "programa");
        string appDir = Path.Combine(prog, "app");
        if (!File.Exists(Path.Combine(appDir, "app.py")))
        {
            Avisar("No encuentro la carpeta \"programa\" al lado de Laburo IA.exe.\n\n" +
                   "Laburo IA.exe, Setup.exe y la carpeta programa tienen que estar juntos.");
            return;
        }
        string pythonw = Python.Pythonw(prog);
        if (pythonw == null)
        {
            Avisar("Laburo IA todavía no está instalado en esta computadora.\n\n" +
                   "Ejecutá Setup.exe (está en esta misma carpeta) y después volvé a abrir Laburo IA.");
            return;
        }
        try
        {
            var psi = new ProcessStartInfo(pythonw, "app.py") { WorkingDirectory = appDir, UseShellExecute = false };
            psi.EnvironmentVariables["PYTHONDONTWRITEBYTECODE"] = "1";   // sin carpetas __pycache__ entre el código
            Process.Start(psi);
        }
        catch (Exception e)
        {
            Avisar("No pude abrir Laburo IA:\n" + e.Message + "\n\nProbá ejecutar Setup.exe de nuevo.");
        }
    }

    static void Avisar(string texto)
    {
        MessageBox.Show(texto, "Laburo IA", MessageBoxButtons.OK, MessageBoxIcon.Information);
    }
}

static class Python
{
    /// pythonw.exe anotado por Setup.exe en programa\datos\python.txt (o null si falta o ya no existe).
    public static string Pythonw(string prog)
    {
        try
        {
            string txt = Path.Combine(prog, "datos", "python.txt");
            if (!File.Exists(txt)) return null;
            string py = File.ReadAllText(txt).Trim();
            string w = Path.Combine(Path.GetDirectoryName(py), "pythonw.exe");
            if (File.Exists(w)) return w;
            return File.Exists(py) ? py : null;
        }
        catch { return null; }
    }
}
