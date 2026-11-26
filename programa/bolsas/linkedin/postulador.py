"""
LinkedIn (solo avisos con "Solicitud sencilla"). No tiene script de consola: lo usa la app (app/motor_linkedin.py).

- Búsqueda: con JobSpy (python-jobspy), que lee la búsqueda pública de empleos de LinkedIn, SIN sesión,
  siempre con el filtro de Solicitud sencilla (f_AL). Trae título, empresa, lugar, fecha y link.
- Postulación: con tu sesión, en el Edge de la app (datos/linkedin/perfil_edge), abriendo la Solicitud
  sencilla del aviso. Ver motor_linkedin.py.

El link de una búsqueda guardada es el de la web de LinkedIn (sirve para abrirla en el navegador):
    https://www.linkedin.com/jobs/search/?keywords=<palabra>&location=<lugar>&f_AL=true[&f_WT=2]
f_WT=2 = remoto. Ver comun/busquedas.py (_armar_linkedin) y CONTEXTO.md.
"""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE.parent.parent / "comun"))   # módulos compartidos
sys.dont_write_bytecode = True
import rutas  # noqa: E402

DATOS = rutas.datos_bolsa("linkedin")
CONFIG_FILE = DATOS / "config.json"
HISTORIAL_FILE = DATOS / "historial.json"
PERFIL_DIR = DATOS / "perfil_edge"
SITIO = "https://www.linkedin.com"

DEFAULT_CONFIG = {
    "salario_pretendido": None,
    "pausa_min_seg": 4,
    "pausa_max_seg": 9,
    "max_postulaciones_por_corrida": 40,
    "max_resultados_busqueda": 300,     # avisos que se piden a JobSpy por lugar
    "max_paginas_listado": 1,           # no se usa (JobSpy pagina solo); está por compatibilidad
    "palabras_excluidas_titulo": [],
    "omitir_repetidos": True,
    "umbral_repetidos": 0.85,
}
ESTADOS_POSTULADO = ("postulado", "ya_postulado")


def cargar_json(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def guardar_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def url_aviso(jid):
    return f"{SITIO}/jobs/view/{jid}/"


def leer_busqueda(url):
    """Link guardado -> {"palabra", "lugar", "remoto"}."""
    q = dict(parse_qsl(urlsplit(url).query))
    return {"palabra": q.get("keywords", ""), "lugar": q.get("location", ""), "remoto": q.get("f_WT") == "2"}


class _Contador429(logging.Handler):
    """JobSpy no avisa por excepción cuando LinkedIn lo frena: lo escribe en su log."""
    def __init__(self):
        super().__init__()
        self.frenado = False

    def emit(self, record):
        if "429" in record.getMessage():
            self.frenado = True


POR_PAGINA = 10      # avisos por página de la búsqueda pública de LinkedIn (jobspy.linkedin.constant)


def buscar_pagina(url, inicio):
    """UNA página de resultados (10 avisos) desde la posición `inicio`, sin la pausa de JobSpy entre
    páginas (la pausa la hace quien llama). -> (avisos, frenado). Sirve para ir mostrando los avisos a
    medida que llegan en vez de esperar a tener todos (JobSpy espera 3-7 s entre página y página)."""
    return buscar(url, POR_PAGINA, inicio)


def buscar(url, maximo=300, inicio=0):
    """Busca con JobSpy (solo Solicitud sencilla). -> (avisos, frenado). Cada aviso:
    {id, titulo, empresa, url, fecha ('dd-mm-aaaa'), ubicacion}. frenado=True si LinkedIn respondió 429."""
    from jobspy import scrape_jobs          # se importa acá: si falta, la app avisa al recorrer
    b = leer_busqueda(url)
    escucha = _Contador429()
    log = logging.getLogger("jobspy.linkedin")
    log_raiz = logging.getLogger("jobspy")
    for lg in (log, log_raiz):
        lg.addHandler(escucha)
    try:
        df = scrape_jobs(site_name=["linkedin"], search_term=b["palabra"] or None,
                         location=b["lugar"] or "Argentina", is_remote=b["remoto"],
                         easy_apply=True, results_wanted=maximo, offset=inicio, verbose=1)
    finally:
        for lg in (log, log_raiz):
            lg.removeHandler(escucha)
    avisos = []
    for _, r in df.iterrows():
        jid = str(r.get("id") or "").split("-")[-1]
        if not jid.isdigit():
            continue
        fecha = r.get("date_posted")
        try:
            fecha = datetime.strptime(str(fecha)[:10], "%Y-%m-%d").strftime("%d-%m-%Y")
        except Exception:
            fecha = ""
        texto = lambda k: "" if r.get(k) is None or str(r.get(k)) == "nan" else str(r.get(k)).strip()
        avisos.append({"id": jid, "titulo": texto("title"), "empresa": texto("company"), "url": url_aviso(jid),
                       "fecha": fecha, "ubicacion": texto("location")})
    return avisos, escucha.frenado
