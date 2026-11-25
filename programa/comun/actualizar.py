"""
Actualizar la app desde su repositorio de GitHub.

  buscar()     compara la versión instalada (const VERSION de app/ui/app.js) con la publicada en main.
  actualizar() descarga el proyecto, y su Setup.exe lo instala encima de esta carpeta.

Los datos del usuario (programa/datos/) no se tocan: el instalador copia programa/ sin esa carpeta y
solo trae datos si el destino no tiene ninguno (la descarga nunca trae).

La descarga la hace Windows (PowerShell/.NET) y no urllib: así usa el proxy del sistema con la sesión
del usuario (en redes de empresa, urllib recibe un 407).
"""
import os
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

REPO = "matichiozza/Postula"
URL_VERSION = f"https://raw.githubusercontent.com/{REPO}/main/programa/app/ui/app.js"
URL_ZIP = f"https://codeload.github.com/{REPO}/zip/refs/heads/main"
RAIZ = Path(__file__).resolve().parent.parent.parent        # la carpeta de la app (Setup.exe y programa/)
SIN_VENTANA = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# La URL y el destino viajan en variables de entorno: nada se arma dentro del comando.
DESCARGAR_PS = (
    "$ErrorActionPreference = 'Stop';"
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;"
    "$p = [Net.WebRequest]::GetSystemWebProxy(); $p.Credentials = [Net.CredentialCache]::DefaultNetworkCredentials;"
    "$w = New-Object Net.WebClient; $w.Proxy = $p; $w.Headers.Add('User-Agent', 'Postula');"
    "$w.Headers.Add('Cache-Control', 'no-cache');"
    "$w.DownloadFile($env:DESCARGA_URL, $env:DESCARGA_DESTINO)"
)


def descargar(url, destino, segundos=300):
    r = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", DESCARGAR_PS],
                       env={**os.environ, "DESCARGA_URL": url, "DESCARGA_DESTINO": str(destino)},
                       capture_output=True, timeout=segundos, creationflags=SIN_VENTANA)
    if r.returncode or not Path(destino).exists():
        print("[actualizar]", r.stderr.decode("cp850", errors="replace")[:600])
        raise RuntimeError("No pude conectarme con GitHub. Revisá tu conexión y probá de nuevo.")


def version_de(app_js):
    m = re.search(r"const VERSION = '(\d+(?:\.\d+)*)'", Path(app_js).read_text(encoding="utf-8", errors="replace"))
    if not m:
        raise RuntimeError("No encontré el número de versión.")
    return m.group(1)


def mas_nueva(a, b):
    """¿La versión a es más nueva que la b? ("1.2.10" > "1.2.9")."""
    partes = lambda v: [int(x) for x in v.split(".")]
    x, y = partes(a), partes(b)
    largo = max(len(x), len(y))
    return x + [0] * (largo - len(x)) > y + [0] * (largo - len(y))


def instalada():
    return version_de(RAIZ / "programa" / "app" / "ui" / "app.js")


def buscar():
    """-> {"actual", "publicada", "hay"}"""
    with tempfile.TemporaryDirectory(prefix="postula-version-") as tmp:
        archivo = Path(tmp) / "app.js"
        descargar(URL_VERSION, archivo, 90)
        publicada = version_de(archivo)
    actual = instalada()
    return {"actual": actual, "publicada": publicada, "hay": mas_nueva(publicada, actual)}


def actualizar():
    """Descarga e instala la versión publicada. -> {"version"}. Después hay que reiniciar la app."""
    actual = instalada()
    with tempfile.TemporaryDirectory(prefix="postula-actualizar-", ignore_cleanup_errors=True) as tmp:
        paquete = Path(tmp) / "postula.zip"
        descargar(URL_ZIP, paquete)
        with zipfile.ZipFile(paquete) as z:
            z.extractall(Path(tmp) / "nuevo")               # extractall no deja salir de la carpeta
        carpetas = [d for d in (Path(tmp) / "nuevo").iterdir() if d.is_dir()]
        origen = carpetas[0] if len(carpetas) == 1 else Path(tmp) / "nuevo"
        setup = origen / "Setup.exe"
        if not setup.exists() or not (origen / "programa" / "app" / "app.py").exists():
            raise RuntimeError("La descarga está incompleta: no se cambió nada.")
        if (origen / "programa" / "datos").exists():
            raise RuntimeError("La descarga trae una carpeta de datos que no debería: no se cambió nada.")
        nueva = version_de(origen / "programa" / "app" / "ui" / "app.js")
        if not mas_nueva(nueva, actual):
            raise RuntimeError(f"Lo publicado ({nueva}) no es más nuevo que lo que tenés ({actual}).")
        try:
            r = subprocess.run([str(setup), "/silencioso", "/destino", str(RAIZ), "/sinmenu"],
                               capture_output=True, timeout=1200, creationflags=SIN_VENTANA)
        except OSError as e:
            raise RuntimeError(f"Windows no dejó ejecutar el instalador descargado ({e}).")
        if r.returncode:
            raise RuntimeError("El instalador no pudo terminar. El detalle está en programa\\datos\\registros\\setup.log.")
    return {"version": nueva}
