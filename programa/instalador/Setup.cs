// Setup.exe: instalador de Laburo IA con la ventana clásica de Windows (asistente de 4 pasos).
//   Bienvenida -> Opciones -> Instalando -> Listo
// Instala en el lugar (la carpeta donde está Setup.exe): prepara la PC y desempaqueta "Laburo IA.exe"
// (que viaja adentro de Setup.exe) en esa misma carpeta. Antes de instalar, la raíz solo tiene Setup.exe y programa\.
//   1. Python >= 3.9 (si no hay, ofrece instalar 3.12 con winget o con el instalador de python.org)
//   2. pip install playwright pywebview
//   3. Verifica Microsoft Edge
//   4. Anota el Python en programa\datos\python.txt (lo usa Laburo IA.exe)
//   5. Desempaqueta Laburo IA.exe en la raíz y, opcional, acceso directo en el escritorio
//   6. Opcional: borra los datos de un usuario anterior (programa\datos: sesiones, historiales, sueldo y zona)
// NO pregunta el sueldo: se completa en la app ("Tus datos para los formularios").
//
// Línea de comandos (para pruebas):
//   Setup.exe /silencioso [/nombre "Mati"] [/borrar] [/escritorio]   instala sin ventanas; el detalle queda en programa\datos\registros\setup.log
//   Setup.exe /capturas <carpeta>                   guarda una imagen de cada pantalla (no instala nada)
// Se compila con compilar.bat.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Linq;
using System.Net;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Windows.Forms;

[assembly: AssemblyTitle("Instalador de Laburo IA")]
[assembly: AssemblyProduct("Laburo IA")]
[assembly: AssemblyVersion("1.0.0.0")]

// ============================================================================ lógica de instalación
class Instalacion
{
    public readonly string Raiz, Prog, Datos, LogFile;
    public bool CrearEscritorio, BorrarDatos;
    public string Nombre = "";   // para saludar en el menú de la app ("¡Hey Mati, postulate!")
    public Action<string> Log = delegate { };
    public Action<int, string> Paso = delegate { };
    public Func<string, bool> Preguntar = t => true;   // sí/no (con ventana, un MessageBox)
    public const int Pasos = 6;
    static readonly string[][] Bolsas = {
        new[] { "bumeran", "Bumeran" }, new[] { "zonajobs", "ZonaJobs" },
        new[] { "computrabajo", "Computrabajo" }, new[] { "empleosit", "EmpleosIT" } };

    public Instalacion(string raiz)
    {
        Raiz = raiz.TrimEnd('\\');
        Prog = Path.Combine(Raiz, "programa");
        Datos = Path.Combine(Prog, "datos");
        LogFile = Path.Combine(Datos, "registros", "setup.log");
    }

    public bool ProgramaPresente() { return File.Exists(Path.Combine(Prog, "app", "app.py")); }

    /// Datos de un usuario anterior que se pueden borrar (rutas relativas a programa\datos\).
    public List<string> DatosPrevios()
    {
        var l = new List<string>();
        foreach (var b in Bolsas)
        {
            if (Directory.Exists(Path.Combine(Datos, b[0], "perfil_edge"))) l.Add(b[0] + "\\perfil_edge");
            if (File.Exists(Path.Combine(Datos, b[0], "historial.json"))) l.Add(b[0] + "\\historial.json");
            if (File.Exists(Path.Combine(Datos, b[0], "descartes.json"))) l.Add(b[0] + "\\descartes.json");
            if (File.Exists(Path.Combine(Datos, b[0], "config.json"))) l.Add(b[0] + "\\config.json");   // búsquedas (igual que "Empezar de cero" de la app)
        }
        if (File.Exists(Path.Combine(Datos, "perfil.json"))) l.Add("perfil.json");
        return l;
    }

    /// El nombre guardado en datos\perfil.json (para precargar el campo), o "".
    public string NombreGuardado()
    {
        try
        {
            string t = File.ReadAllText(Path.Combine(Datos, "perfil.json"), Encoding.UTF8);
            var m = System.Text.RegularExpressions.Regex.Match(t, "\"nombre\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"");
            return m.Success ? System.Text.RegularExpressions.Regex.Unescape(m.Groups[1].Value) : "";
        }
        catch { return ""; }
    }

    void Escribir(string t)
    {
        try { File.AppendAllText(LogFile, DateTime.Now.ToString("HH:mm:ss ") + t + Environment.NewLine, Encoding.UTF8); } catch { }
        Log(t);
    }

    // ------------------------------------------------------------------ procesos
    int Correr(string exe, string args, int timeoutSeg, List<string> salida = null, bool mostrar = true,
               Dictionary<string, string> entorno = null)
    {
        var psi = new ProcessStartInfo(exe, args)
        {
            UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true,
            StandardOutputEncoding = Encoding.UTF8, StandardErrorEncoding = Encoding.UTF8,
        };
        psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
        psi.EnvironmentVariables["PYTHONDONTWRITEBYTECODE"] = "1";
        if (entorno != null) foreach (var kv in entorno) psi.EnvironmentVariables[kv.Key] = kv.Value;
        using (var p = new Process { StartInfo = psi })
        {
            DataReceivedEventHandler h = (s, e) =>
            {
                if (e.Data == null) return;
                if (salida != null) lock (salida) salida.Add(e.Data);
                if (mostrar && e.Data.Trim().Length > 0) Escribir("   " + e.Data);
            };
            p.OutputDataReceived += h;
            p.ErrorDataReceived += h;
            p.Start();
            p.BeginOutputReadLine();
            p.BeginErrorReadLine();
            if (!p.WaitForExit(timeoutSeg * 1000)) { try { p.Kill(); } catch { } return -1; }
            p.WaitForExit();
            return p.ExitCode;
        }
    }

    /// python.exe >= 3.9 (que no sea el alias de Microsoft Store), o null.
    public string BuscarPython()
    {
        const string codigo = "\"import sys; print(sys.executable); print(sys.version_info[0]*100+sys.version_info[1])\"";
        var candidatos = new List<Tuple<string, string>> { Tuple.Create("py", "-3 "), Tuple.Create("python", "") };
        var dirs = new List<string>();
        foreach (var b in new[] { Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "Python"),
                                  Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles) })
            if (Directory.Exists(b)) dirs.AddRange(Directory.GetDirectories(b, "Python3*"));
        foreach (var d in dirs)
            if (File.Exists(Path.Combine(d, "python.exe"))) candidatos.Add(Tuple.Create(Path.Combine(d, "python.exe"), ""));
        string mejor = null; int mejorV = 0;
        foreach (var c in candidatos)
        {
            var sal = new List<string>();
            int r;
            try { r = Correr(c.Item1, c.Item2 + "-c " + codigo, 20, sal, false); } catch { continue; }
            if (r != 0 || sal.Count < 2) continue;
            int v;
            string ruta = sal[0].Trim();
            if (!int.TryParse(sal[1].Trim(), out v) || v < 309 || ruta.Contains("WindowsApps") || !File.Exists(ruta)) continue;
            if (v > mejorV) { mejor = ruta; mejorV = v; }
        }
        return mejor;
    }

    string InstalarPython()
    {
        if (!Preguntar("No encontré Python 3.9 o superior en esta computadora, y Laburo IA lo necesita.\n\n¿Instalo Python 3.12 ahora? (solo para tu usuario)"))
            return null;
        Escribir("Instalando Python 3.12 con winget...");
        try { Correr("winget", "install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements", 900); }
        catch { Escribir("   (winget no está disponible)"); }
        string py = BuscarPython();
        if (py != null) return py;
        // Plan B (sin winget): el instalador oficial de python.org
        const string url = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe";
        string exe = Path.Combine(Path.GetTempPath(), "python-3.12.10-amd64.exe");
        Escribir("Descargando " + url + " ...");
        ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
        using (var wc = new WebClient()) wc.DownloadFile(url, exe);
        Escribir("Instalando Python (se abre una ventana con la barra de progreso)...");
        using (var p = Process.Start(exe, "/passive InstallAllUsers=0 PrependPath=1 Include_launcher=0 Include_test=0")) p.WaitForExit();
        return BuscarPython();
    }

    // ------------------------------------------------------------------ accesos directos
    static void AccesoDirecto(string lnk, string destino, string args, string carpeta, string icono, string descripcion)
    {
        Type t = Type.GetTypeFromProgID("WScript.Shell");
        dynamic sh = Activator.CreateInstance(t);
        dynamic l = sh.CreateShortcut(lnk);
        l.TargetPath = destino;
        l.Arguments = args;
        l.WorkingDirectory = carpeta;
        l.IconLocation = icono + ",0";
        l.Description = descripcion;
        l.Save();
        Marshal.FinalReleaseComObject(l);
        Marshal.FinalReleaseComObject(sh);
    }

    /// Desempaqueta "Laburo IA.exe" (recurso LaburoIA.exe de este Setup) en la raíz. Si ya estaba,
    /// lo reemplaza (así una versión nueva de Setup también actualiza el lanzador). null = salió bien.
    static string ExtraerLanzador(string destino)
    {
        try
        {
            using (var s = Assembly.GetExecutingAssembly().GetManifestResourceStream("LaburoIA.exe"))
            {
                if (s == null) return "Este Setup.exe está incompleto (no trae Laburo IA.exe adentro). Volvé a compilarlo.";
                string tmp = destino + ".nuevo";
                using (var f = File.Create(tmp)) s.CopyTo(f);
                if (File.Exists(destino)) File.Delete(destino);
                File.Move(tmp, destino);
            }
            return null;
        }
        catch (Exception e)
        {
            return "No pude crear Laburo IA.exe en la carpeta del programa (" + e.Message + "). Si la app está abierta, cerrala y volvé a ejecutar Setup.exe.";
        }
    }

    // ------------------------------------------------------------------ todo junto
    /// Devuelve null si salió bien, o el mensaje de error.
    public string Ejecutar()
    {
        try { Directory.CreateDirectory(Path.GetDirectoryName(LogFile)); File.WriteAllText(LogFile, "", Encoding.UTF8); } catch { }
        Escribir("Instalando Laburo IA en " + Raiz);

        Paso(1, "Buscando Python...");
        string py = BuscarPython() ?? InstalarPython();
        if (py == null)
            return "No hay Python 3.9 o superior. Instalalo desde https://www.python.org/downloads/ " +
                   "(marcá \"Add python.exe to PATH\") y volvé a ejecutar Setup.exe.";
        Escribir("Python: " + py);

        Paso(2, "Instalando las librerías (Playwright y pywebview)...");
        int r = Correr(py, "-m pip install --disable-pip-version-check playwright pywebview", 900);
        if (r != 0) return "Falló la instalación de las librerías (pip). Revisá la conexión a internet y volvé a intentar.";
        if (Correr(py, "-c \"import playwright.sync_api, webview\"", 60) != 0)
            return "Las librerías se instalaron pero Python no las puede abrir.";
        Escribir("Librerías listas.");

        Paso(3, "Buscando Microsoft Edge...");
        string[] edges = {
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), @"Microsoft\Edge\Application\msedge.exe"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), @"Microsoft\Edge\Application\msedge.exe") };
        string edge = edges.FirstOrDefault(File.Exists);
        if (edge == null) Escribir("ATENCIÓN: no encontré Microsoft Edge. Laburo IA lo usa para entrar a las bolsas de trabajo: instalalo desde https://www.microsoft.com/edge");
        else Escribir("Edge: " + edge);

        Paso(4, "Preparando el programa...");
        if (BorrarDatos)   // primero se borra lo del usuario anterior, después se guarda lo nuevo (nombre)
        {
            foreach (var d in DatosPrevios())
            {
                string ruta = Path.Combine(Datos, d);
                if (Directory.Exists(ruta)) Directory.Delete(ruta, true); else File.Delete(ruta);
                Escribir("Borrado: programa\\datos\\" + d);
            }
        }
        Directory.CreateDirectory(Datos);
        File.WriteAllText(Path.Combine(Datos, "python.txt"), py, new UTF8Encoding(false));
        if (!string.IsNullOrWhiteSpace(Nombre))
        {
            // Se guarda con el mismo código de la app (comun\perfil.py), así el formato es uno solo.
            // El nombre viaja en una variable de entorno: así no hay problemas con comillas o tildes.
            var entorno = new Dictionary<string, string> { { "LABURO_NOMBRE", Nombre.Trim() } };
            string codigo = "\"import os, sys; sys.path.insert(0, os.path.join(os.getcwd(), 'comun')); import perfil; " +
                            "perfil.guardar(nombre=os.environ['LABURO_NOMBRE'])\"";
            string cwd = Environment.CurrentDirectory;
            Environment.CurrentDirectory = Prog;
            int rn;
            try { rn = Correr(py, "-c " + codigo, 60, null, true, entorno); }
            finally { Environment.CurrentDirectory = cwd; }
            if (rn != 0) return "No pude guardar tu nombre en programa\\datos\\perfil.json.";
            Escribir("Nombre guardado: " + Nombre.Trim());
        }
        Escribir("Python anotado en programa\\datos\\python.txt (lo usa Laburo IA.exe).");
        // Los accesos "Postular en <Bolsa>" de versiones anteriores ya no se usan: se borran si quedaron.
        foreach (var b in Bolsas)
        {
            string viejo = Path.Combine(Prog, "Postular en " + b[1] + ".lnk");
            if (File.Exists(viejo)) File.Delete(viejo);
        }

        Paso(5, "Creando Laburo IA.exe y los accesos directos...");
        // El lanzador viaja empaquetado dentro de Setup.exe y recién acá aparece en la raíz.
        string exe = Path.Combine(Raiz, "Laburo IA.exe");
        string error = ExtraerLanzador(exe);
        if (error != null) return error;
        Escribir("Laburo IA.exe listo en " + Raiz);
        if (CrearEscritorio)
        {
            AccesoDirecto(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "Laburo IA.lnk"),
                          exe, "", Raiz, exe, "Laburo IA - app de postulaciones");
            Escribir("Acceso directo en el escritorio.");
        }

        Paso(6, "Terminando...");
        Escribir("Instalación terminada.");
        return null;
    }
}

// ============================================================================ ventana (asistente)
class Asistente : Form
{
    readonly Instalacion ins;
    readonly Panel[] paginas = new Panel[4];
    int actual;
    readonly Button bAtras, bSiguiente, bCancelar;
    readonly Panel cabecera, linea;
    readonly Label cabTitulo, cabSub;
    readonly CheckBox chkEscritorio, chkBorrar, chkAbrir;
    readonly ProgressBar barra;
    readonly Label lblEstado, finTitulo, finTexto;
    readonly TextBox txtLog, txtNombre;
    bool instalando, terminado;
    static readonly Color Verde = Color.FromArgb(23, 154, 108), VerdeClaro = Color.FromArgb(63, 214, 160);
    readonly Image logo;
    float k = 1;   // escala de la pantalla (1 = 100 %, 1.25 = 125 %...)
    Point P(int x, int y) { return new Point((int)Math.Round(x * k), (int)Math.Round(y * k)); }
    Size Z(int w, int h) { return new Size((int)Math.Round(w * k), (int)Math.Round(h * k)); }

    public Asistente(Instalacion ins)
    {
        this.ins = ins;
        SuspendLayout();
        AutoScaleMode = AutoScaleMode.None;   // se escala a mano (P/Z): el automático estiraba los textos con pantallas al 125 %
        using (var g = CreateGraphics()) k = g.DpiX / 96F;
        Text = "Instalar Laburo IA";
        Font = new Font("Segoe UI", 9F);
        FormBorderStyle = FormBorderStyle.FixedDialog;
        MaximizeBox = false;
        MinimizeBox = true;
        StartPosition = FormStartPosition.CenterScreen;
        ClientSize = Z(600, 420);
        BackColor = SystemColors.Control;
        try { Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath); } catch { }
        using (var s = Assembly.GetExecutingAssembly().GetManifestResourceStream("logo.png"))
            logo = s != null ? Image.FromStream(s) : null;

        // ---- cabecera (pasos 2 y 3), como en los instaladores clásicos
        cabecera = new Panel { Location = P(0, 0), Size = Z(600, 62), BackColor = Color.White };
        cabTitulo = new Label { Location = P(20, 12), AutoSize = true, Font = new Font("Segoe UI", 9.5F, FontStyle.Bold) };
        cabSub = new Label { Location = P(34, 34), AutoSize = true };
        var cabLogo = new PictureBox { Image = logo, SizeMode = PictureBoxSizeMode.Zoom, Location = P(546, 11), Size = Z(40, 40) };
        cabecera.Controls.AddRange(new Control[] { cabTitulo, cabSub, cabLogo });
        linea = new Panel { Location = P(0, 62), Size = Z(600, 1), BackColor = SystemColors.ControlDark };

        // ---- botones de abajo
        var sep = new Label { Location = P(0, 372), Size = Z(600, 2), BorderStyle = BorderStyle.Fixed3D };
        bAtras = new Button { Text = "< &Atrás", Location = P(325, 385), Size = Z(80, 25) };
        bSiguiente = new Button { Text = "&Siguiente >", Location = P(405, 385), Size = Z(80, 25) };
        bCancelar = new Button { Text = "Cancelar", Location = P(500, 385), Size = Z(80, 25) };
        bAtras.Click += (s, e) => Mostrar(actual - 1);
        bSiguiente.Click += (s, e) => Avanzar();
        bCancelar.Click += (s, e) => Close();
        AcceptButton = bSiguiente;
        CancelButton = bCancelar;

        // ---- 0: bienvenida
        Label tmpTit, tmpTxt;
        paginas[0] = PaginaConBanda("Te damos la bienvenida a Laburo IA",
            "Este asistente prepara la computadora para usar Laburo IA, la app que se postula sola a los avisos de empleo y te deja decidir los que tienen preguntas.\n\n" +
            "Va a instalar lo que haga falta (Python y dos librerías) y dejar listo el programa. Puede tardar unos minutos y necesita internet.\n\n" +
            "Hacé clic en Siguiente para continuar.", out tmpTit, out tmpTxt);

        // ---- 1: opciones
        var p1 = Pagina();
        p1.Controls.Add(new Label { Text = "¿Cómo te llamás?", Location = P(30, 14), AutoSize = true, Font = new Font("Segoe UI", 9F, FontStyle.Bold) });
        txtNombre = new TextBox { Text = ins.NombreGuardado(), Location = P(30, 35), Size = Z(250, 23), MaxLength = 60 };
        p1.Controls.Add(txtNombre);
        p1.Controls.Add(new Label { Text = "Para saludarte en la app (\"¡Hey Mati, postulate!\"). Para cambiarlo, volvé a ejecutar Setup.exe.",
                                    Location = P(290, 38), Size = Z(290, 34), ForeColor = SystemColors.GrayText });
        p1.Controls.Add(new Label { Text = "Laburo IA se va a instalar en esta carpeta:", Location = P(30, 76), AutoSize = true });
        p1.Controls.Add(new TextBox { Text = ins.Raiz, ReadOnly = true, Location = P(30, 96), Size = Z(540, 23), TabStop = false });
        chkEscritorio = new CheckBox { Text = "Crear un acceso directo en el &escritorio", Location = P(30, 130), AutoSize = true };
        p1.Controls.Add(chkEscritorio);
        var previos = ins.DatosPrevios();
        chkBorrar = new CheckBox { Text = "&Borrarlos (para empezar de cero; si querés conservarlos, exportalos antes desde la app)", AutoSize = true, Location = P(14, 0) };
        if (previos.Count > 0)
        {
            var g = new GroupBox { Text = "Datos de un usuario anterior", Location = P(30, 160), Size = Z(540, 140) };
            g.Controls.Add(new Label { Text = "Hay sesiones, historiales, búsquedas, avisos descartados o datos personales guardados:",
                                       Location = P(14, 20), Size = Z(512, 18) });
            var lista = new ListBox { Location = P(14, 40), Size = Z(512, 62), IntegralHeight = false, SelectionMode = SelectionMode.None };
            foreach (var d in previos) lista.Items.Add("programa\\datos\\" + d);
            g.Controls.Add(lista);
            chkBorrar.Location = P(14, 110);
            g.Controls.Add(chkBorrar);
            p1.Controls.Add(g);
        }
        paginas[1] = p1;

        // ---- 2: instalando
        var p2 = Pagina();
        lblEstado = new Label { Text = "Preparando...", Location = P(30, 20), Size = Z(540, 18) };
        barra = new ProgressBar { Location = P(30, 44), Size = Z(540, 20), Maximum = Instalacion.Pasos };
        p2.Controls.Add(new Label { Text = "Detalle:", Location = P(30, 78), AutoSize = true });
        txtLog = new TextBox { HideSelection = true, Multiline = true, ReadOnly = true, ScrollBars = ScrollBars.Vertical, Location = P(30, 98),
                               Size = Z(540, 196), BackColor = SystemColors.Window, Font = new Font("Consolas", 8.5F), WordWrap = false };
        p2.Controls.AddRange(new Control[] { lblEstado, barra, txtLog });
        paginas[2] = p2;

        // ---- 3: listo
        paginas[3] = PaginaConBanda("Laburo IA quedó instalado", "", out finTitulo, out finTexto);
        chkAbrir = new CheckBox { Text = "&Abrir Laburo IA ahora", Checked = true, AutoSize = true, Location = P(186, 300), BackColor = Color.White };
        paginas[3].Controls.Add(chkAbrir);

        Controls.AddRange(new Control[] { cabecera, linea, sep, bAtras, bSiguiente, bCancelar });
        foreach (var p in paginas) Controls.Add(p);
        ResumeLayout(false);
        Mostrar(0);
    }

    Panel Pagina()
    {
        return new Panel { Location = P(0, 63), Size = Z(600, 309), Visible = false };
    }

    Panel PaginaConBanda(string titulo, string texto, out Label lTit, out Label lTxt)
    {
        var p = new Panel { Location = P(0, 0), Size = Z(600, 372), BackColor = Color.White, Visible = false };
        var banda = new Panel { Location = P(0, 0), Size = Z(164, 372) };
        banda.Paint += (s, e) =>
        {
            using (var b = new LinearGradientBrush(banda.ClientRectangle, VerdeClaro, Verde, 60F)) e.Graphics.FillRectangle(b, banda.ClientRectangle);
            if (logo != null)
            {
                int t = (int)(96 * e.Graphics.DpiX / 96F);
                e.Graphics.InterpolationMode = InterpolationMode.HighQualityBicubic;
                e.Graphics.DrawImage(logo, (banda.Width - t) / 2, (int)(banda.Height * 0.30), t, t);
            }
        };
        lTit = new Label { Text = titulo, Location = P(186, 24), Size = Z(396, 56), Font = new Font("Segoe UI", 14F, FontStyle.Bold), ForeColor = Color.FromArgb(24, 33, 45) };
        lTxt = new Label { Text = texto, Location = P(186, 92), Size = Z(396, 200) };
        p.Controls.AddRange(new Control[] { banda, lTit, lTxt });
        return p;
    }

    void Mostrar(int i)
    {
        actual = i;
        for (int k = 0; k < paginas.Length; k++) paginas[k].Visible = k == i;
        bool banda = i == 0 || i == 3;
        cabecera.Visible = linea.Visible = !banda;
        if (i == 1) { cabTitulo.Text = "Opciones de instalación"; cabSub.Text = "Elegí cómo querés dejar instalado Laburo IA."; }
        if (i == 2) { cabTitulo.Text = "Instalando"; cabSub.Text = "Esperá mientras se prepara Laburo IA en esta computadora."; }
        bAtras.Visible = i == 1;
        bSiguiente.Text = i == 1 ? "&Instalar" : i == 3 ? "&Finalizar" : "&Siguiente >";
        bSiguiente.Enabled = i != 2;
        bCancelar.Enabled = i != 2 && i != 3;
        if (i == 3) bCancelar.Enabled = false;
        paginas[i].BringToFront();
        if (bSiguiente.Enabled) bSiguiente.Focus();
        if (i == 1) { txtNombre.Focus(); txtNombre.SelectAll(); }
    }

    void Avanzar()
    {
        if (actual == 0) Mostrar(1);
        else if (actual == 1) Instalar();
        else if (actual == 3)
        {
            terminado = true;
            if (chkAbrir.Visible && chkAbrir.Checked)
            {
                try { Process.Start(new ProcessStartInfo(Path.Combine(ins.Raiz, "Laburo IA.exe")) { WorkingDirectory = ins.Raiz }); }
                catch (Exception e) { MessageBox.Show(this, "No pude abrir Laburo IA: " + e.Message, Text); }
            }
            Close();
        }
    }

    void Instalar()
    {
        if (txtNombre.Text.Trim().Length == 0)
        {
            MessageBox.Show(this, "Escribí tu nombre: la app lo usa para saludarte.", Text, MessageBoxButtons.OK, MessageBoxIcon.Information);
            txtNombre.Focus();
            return;
        }
        ins.Nombre = txtNombre.Text.Trim();
        ins.CrearEscritorio = chkEscritorio.Checked;
        ins.BorrarDatos = chkBorrar.Checked;
        if (ins.BorrarDatos && MessageBox.Show(this, "Se van a borrar las sesiones, los historiales, las búsquedas, los avisos descartados y los datos personales del usuario anterior.\n\nSi querés conservarlos, cancelá, abrí Laburo IA y exportalos primero (Ajustes > Exportar). ¿Borrarlos igual?",
                Text, MessageBoxButtons.YesNo, MessageBoxIcon.Warning, MessageBoxDefaultButton.Button2) != DialogResult.Yes)
            return;
        Mostrar(2);
        instalando = true;
        ins.Log = t => BeginInvoke((Action)(() => txtLog.AppendText(t + Environment.NewLine)));
        ins.Paso = (n, t) => BeginInvoke((Action)(() => { barra.Value = Math.Min(n, barra.Maximum); lblEstado.Text = t; }));
        ins.Preguntar = t => (bool)Invoke((Func<bool>)(() =>
            MessageBox.Show(this, t, Text, MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes));
        new Thread(() =>
        {
            string error;
            try { error = ins.Ejecutar(); }
            catch (Exception e) { error = "Error inesperado: " + e.Message; }
            BeginInvoke((Action)(() => Terminar(error)));
        }) { IsBackground = true }.Start();
    }

    void Terminar(string error)
    {
        instalando = false;
        if (error == null)
        {
            barra.Value = barra.Maximum;
            finTitulo.Text = "Laburo IA quedó instalado";
            finTexto.Text = "Ya podés usar Laburo IA: abrilo con \"Laburo IA\" de la carpeta del programa" +
                            (ins.CrearEscritorio ? " o con el acceso del escritorio." : ".") +
                            "\n\nLa primera vez, completá tu sueldo pretendido y tu zona en \"Tus datos\" (o traé todo de una instalación anterior con Ajustes > Importar), y cuando entres a una bolsa de trabajo iniciá sesión en la ventana que se abre.\n\nHacé clic en Finalizar para cerrar el asistente.";
            chkAbrir.Visible = true;
        }
        else
        {
            finTitulo.Text = "No se pudo completar la instalación";
            finTexto.Text = error + "\n\nEl detalle quedó en programa\\datos\\registros\\setup.log.";
            chkAbrir.Visible = false;
            bSiguiente.Text = "&Cerrar";
        }
        Mostrar(3);
        if (error != null) bSiguiente.Text = "&Cerrar";
    }

    protected override void OnFormClosing(FormClosingEventArgs e)
    {
        if (instalando)
        {
            e.Cancel = true;
            return;
        }
        if (!terminado && actual < 2 &&
            MessageBox.Show(this, "¿Salir del instalador? Laburo IA no va a quedar instalado.", Text,
                            MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes)
            e.Cancel = true;
        base.OnFormClosing(e);
    }

    // --- para revisar el diseño sin instalar: guarda una imagen de cada pantalla
    public void Capturas(string carpeta)
    {
        Directory.CreateDirectory(carpeta);
        StartPosition = FormStartPosition.Manual;
        Location = P(40, 40);
        TopMost = true;
        Show();
        txtLog.Text = "12:00:01 Instalando Laburo IA en " + ins.Raiz + "\r\n12:00:02 Python: C:\\...\\python.exe\r\n12:00:05    Requirement already satisfied: playwright\r\n";
        barra.Value = 2; lblEstado.Text = "Instalando las librerías (Playwright y pywebview)...";
        for (int i = 0; i < 4; i++)
        {
            if (i == 3) { Terminar(null); }
            else Mostrar(i);
            Application.DoEvents();
            Refresh();
            Thread.Sleep(400);
            Application.DoEvents();
            using (var bmp = new Bitmap(Width, Height))
            {
                using (var g = Graphics.FromImage(bmp)) g.CopyFromScreen(Location, Point.Empty, Size);   // píxeles reales de la pantalla
                bmp.Save(Path.Combine(carpeta, "setup_" + i + ".png"));
            }
        }
        terminado = true;
        Close();
    }
}

static class Programa
{
    [DllImport("user32.dll")] static extern bool SetProcessDPIAware();

    [STAThread]
    static int Main(string[] args)
    {
        var a = args.Select(x => x.ToLowerInvariant()).ToList();
        var ins = new Instalacion(AppDomain.CurrentDomain.BaseDirectory);
        if (a.Contains("/silencioso"))
        {
            if (!ins.ProgramaPresente()) return 2;
            ins.CrearEscritorio = a.Contains("/escritorio");
            ins.BorrarDatos = a.Contains("/borrar");
            int n = a.IndexOf("/nombre");
            if (n >= 0 && n + 1 < args.Length) ins.Nombre = args[n + 1];
            ins.Preguntar = t => false;   // sin ventanas no se instala Python solo
            ins.Log = t => Console.WriteLine(t);
            return ins.Ejecutar() == null ? 0 : 1;
        }
        try { SetProcessDPIAware(); } catch { }
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        if (!ins.ProgramaPresente())
        {
            MessageBox.Show("No encuentro la carpeta \"programa\" al lado de Setup.exe.\n\nSetup.exe, Laburo IA.exe y la carpeta programa tienen que estar juntos.",
                            "Instalar Laburo IA", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 2;
        }
        int i = a.IndexOf("/capturas");
        if (i >= 0 && i + 1 < args.Length) { new Asistente(ins).Capturas(args[i + 1]); return 0; }
        Application.Run(new Asistente(ins));
        return 0;
    }
}
