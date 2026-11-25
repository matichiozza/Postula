"""
Links de búsqueda de cada plataforma (los listados que recorre el postulador). Se guardan en el
config.json de la plataforma: "urls_busqueda" (la lista) y "url_busqueda" (el primero, por
compatibilidad con los scripts que todavía leen uno solo).
"""
import json
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

import rutas

PLATAFORMAS = {
    # hosts válidos para el link; "quitar" = parámetros que el script maneja solo (la página ?p=N)
    "computrabajo": {"nombre": "Computrabajo", "hosts": ("ar.computrabajo.com",), "quitar": ("p",),
                     "ejemplo": "https://ar.computrabajo.com/empleos-de-informatica-y-telecom-en-capital-federal"},
    "bumeran": {"nombre": "Bumeran", "hosts": ("www.bumeran.com.ar", "bumeran.com.ar"), "quitar": ("page",),
                "ejemplo": "https://www.bumeran.com.ar/empleos.html"},
    "zonajobs": {"nombre": "ZonaJobs", "hosts": ("www.zonajobs.com.ar", "zonajobs.com.ar"), "quitar": ("page",),
                 "ejemplo": "https://www.zonajobs.com.ar/empleos.html"},
    "empleosit": {"nombre": "EmpleosIT", "hosts": ("www.empleosit.com.ar", "empleosit.com.ar"), "quitar": ("page",),
                  "ejemplo": "https://www.empleosit.com.ar/search-results-jobs/"},
}


def _config(plataforma):
    return rutas.datos_bolsa(plataforma) / "config.json"


# ------------------------------------------------------------------ armar búsquedas desde listas
# Por ahora solo Computrabajo. filtros.json lo arma bolsas/computrabajo/actualizar_filtros.py con las
# categorías, provincias y ciudades que ofrece la web. Formato de los links (verificado el 24-11-2026):
#   /empleos-de-<categoría><lugar>                      ej.: /empleos-de-informatica-y-telecom-en-capital-federal
#   /trabajo-de-<puesto>[-de-<categoría>]<lugar>        ej.: /trabajo-de-desarrollador-de-informatica-y-telecom-en-remoto
#   /empleos<lugar>                                     ej.: /empleos-en-cordoba-en-rio-cuarto
# <lugar> = "" (todo el país) | "-en-remoto" | "-en-<provincia>" | "-en-<provincia>-en-<ciudad>"
# Ojo: un slug inventado no da error (la web lo toma como palabra clave), por eso se eligen de listas.
REMOTO = {"sem": "-en-remoto", "nombre": "Remoto (todo el país)"}
_filtros_cache = {}


def filtros(plataforma):
    """Categorías y lugares para elegir, o None si la plataforma no los tiene."""
    archivo = rutas.codigo_bolsa(plataforma) / "filtros.json"
    if not archivo.exists():
        return None
    clave = archivo.stat().st_mtime
    if _filtros_cache.get(plataforma, (None,))[0] != clave:
        _filtros_cache[plataforma] = (clave, json.loads(archivo.read_text(encoding="utf-8")))
    return _filtros_cache[plataforma][1]


def slug(texto):
    """'Diseñador gráfico' -> 'disenador-grafico' (como lo arma la web)."""
    import unicodedata
    t = unicodedata.normalize("NFKD", (texto or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return "-".join("".join(c if c.isalnum() else " " for c in t).split())


def armar(plataforma, datos):
    """datos: {puesto, categoria (slug), provincia (sem), ciudad (sem)} -> {ok, url, resumen} o {ok: False, error}."""
    f = filtros(plataforma)
    if not f:
        return {"ok": False, "error": "Esta plataforma no tiene listas para armar la búsqueda."}
    if plataforma in JOBINT:
        return _armar_jobint(plataforma, f, datos)
    puesto = slug(datos.get("puesto"))
    cat = datos.get("categoria") or ""
    prov = datos.get("provincia") or ""
    ciudad = datos.get("ciudad") or ""
    if cat and cat not in {c["slug"] for c in f["categorias"]}:
        return {"ok": False, "error": "Categoría desconocida."}
    lugar = ""
    if prov == REMOTO["sem"]:
        lugar = prov
    elif prov:
        p = next((x for x in f["provincias"] if x["sem"] == prov), None)
        if not p:
            return {"ok": False, "error": "Provincia desconocida."}
        lugar = prov
        if ciudad:
            if ciudad not in {c["sem"] for c in p["ciudades"]}:
                return {"ok": False, "error": "Ciudad desconocida."}
            lugar = ciudad
    if puesto:
        camino = f"/trabajo-de-{puesto}" + (f"-de-{cat}" if cat else "") + lugar
    elif cat:
        camino = f"/empleos-de-{cat}{lugar}"
    elif lugar:
        camino = f"/empleos{lugar}"
    else:
        return {"ok": False, "error": "Elegí al menos una categoría, un puesto o un lugar."}
    url = "https://ar.computrabajo.com" + camino
    return {"ok": True, "url": url, "resumen": resumen(url)}


# ------------------------------------------------------------------ Bumeran y ZonaJobs (plataforma Jobint)
# Formato de los links (verificado el 24-11-2026, igual en los dos sitios):
#   /[en-<provincia>/[<localidad>/]]empleos[-area-<área>][-modalidad-remoto][-busqueda-<palabras>].html
# - el orden importa: "-modalidad-remoto" después de "-busqueda-..." se toma como parte de las palabras;
# - las palabras van sin tildes ni ñ ("disenador-grafico"): con ñ la web no encuentra nada;
# - un área inventada no da error, trae 0 avisos; un link roto termina en /404.
# A diferencia de Computrabajo, "remoto" se puede combinar con un lugar (aquí se usa sin lugar).
JOBINT = ("bumeran", "zonajobs")
SITIOS = {"bumeran": "https://www.bumeran.com.ar", "zonajobs": "https://www.zonajobs.com.ar"}
RE_JOBINT = None


def _armar_jobint(plataforma, f, datos):
    puesto = slug(datos.get("puesto"))
    cat = datos.get("categoria") or ""
    prov = datos.get("provincia") or ""
    ciudad = datos.get("ciudad") or ""
    if cat and cat not in {c["slug"] for c in f["categorias"]}:
        return {"ok": False, "error": "Categoría desconocida."}
    lugar, remoto = "", prov == REMOTO["sem"]
    if prov and not remoto:
        p = next((x for x in f["provincias"] if x["sem"] == prov), None)
        if not p:
            return {"ok": False, "error": "Provincia desconocida."}
        lugar = f"en-{prov}/"                                   # "buenos-aires/capital-federal" ya trae la localidad
        if ciudad:
            if ciudad not in {c["sem"] for c in p["ciudades"]}:
                return {"ok": False, "error": "Localidad desconocida."}
            lugar = f"en-{prov}/{ciudad}/"
    if not (puesto or cat or lugar or remoto):
        return {"ok": False, "error": "Elegí al menos una categoría, un puesto o un lugar."}
    nombre = "empleos" + (f"-area-{cat}" if cat else "") + ("-modalidad-remoto" if remoto else "") + \
             (f"-busqueda-{puesto}" if puesto else "") + ".html"
    url = f"{SITIOS[plataforma]}/{lugar}{nombre}"
    return {"ok": True, "url": url, "resumen": resumen(url)}


def _leer_jobint(plataforma, camino):
    """Inverso de _armar_jobint: el camino del link -> (puesto, categoría, lugar) legibles, o None."""
    import re
    f = filtros(plataforma)
    if not f:
        return None
    partes = [p for p in unquote(camino).strip("/").split("/") if p]
    if not partes or not partes[-1].endswith(".html"):
        return None
    m = re.fullmatch(r"empleos(?:-area-(?P<area>.+?))?(?P<remoto>-modalidad-remoto)?(?:-busqueda-(?P<kw>.+))?\.html", partes[-1])
    if not m:
        return None
    lugar_partes = partes[:-1]
    lugar = ""
    if lugar_partes:
        if not lugar_partes[0].startswith("en-") or len(lugar_partes) > 2:
            return None
        prov = lugar_partes[0][3:]
        p = next((x for x in f["provincias"] if x["sem"] == prov), None)
        nombre_prov = p["nombre"] if p else prov.replace("-", " ").title()
        if len(lugar_partes) == 2:
            loc = lugar_partes[1]
            if prov == "buenos-aires" and loc == "capital-federal":
                lugar = "Capital Federal"
            else:
                c = next((x for x in (p or {}).get("ciudades", []) if x["sem"] == loc), None)
                lugar = f"{c['nombre'] if c else loc.replace('-', ' ').title()}, {nombre_prov}"
        else:
            lugar = nombre_prov
    if m.group("remoto"):
        lugar = (lugar + " · " if lugar else "") + "Remoto"
    cat = ""
    if m.group("area"):
        cat = {c["slug"]: c["nombre"] for c in f["categorias"]}.get(m.group("area"))
        if not cat:
            return None
    puesto = (m.group("kw") or "").replace("-", " ")
    return puesto, cat, lugar


def _leer_computrabajo(camino):
    """Inverso de armar(): '/trabajo-de-x-de-cat-en-prov' -> (puesto, categoría, lugar) legibles, o None."""
    f = filtros("computrabajo")
    if not f:
        return None
    camino = unquote(camino.strip("/"))
    lugares = [(REMOTO["sem"], REMOTO["nombre"])]
    for p in f["provincias"]:
        lugares.append((p["sem"], p["nombre"]))
        lugares += [(c["sem"], f"{c['nombre']}, {p['nombre']}") for c in p["ciudades"]]
    lugar = ""
    for sem, nombre in sorted(lugares, key=lambda x: -len(x[0])):
        if camino.endswith(sem):
            camino, lugar = camino[: -len(sem)], nombre
            break
    cats = {c["slug"]: c["nombre"] for c in f["categorias"]}
    puesto = cat = ""
    if camino.startswith("empleos-de-"):
        cat = cats.get(camino[len("empleos-de-"):])
        if not cat:
            return None
    elif camino.startswith("trabajo-de-"):
        resto = camino[len("trabajo-de-"):]
        for s, nombre in cats.items():
            if resto.endswith("-de-" + s):
                resto, cat = resto[: -len("-de-" + s)], nombre
                break
        puesto = resto.replace("-", " ")
    elif camino != "empleos" or not lugar:
        return None
    return puesto, cat, lugar


def resumen(url):
    """Texto legible de la búsqueda, sacado del link (ej.: 'Empleos de informatica y telecom en capital federal')."""
    partes = urlsplit(url)
    host = partes.netloc.lower()
    leido = None
    if host == "ar.computrabajo.com" and not partes.query:
        try:
            leido = _leer_computrabajo(partes.path)
        except Exception:
            leido = None
    for plat in JOBINT:
        if host in PLATAFORMAS[plat]["hosts"]:
            try:
                leido = _leer_jobint(plat, partes.path)
            except Exception:
                leido = None
    if leido:
        puesto, cat, lugar = leido
        que = " · ".join(x for x in (f"“{puesto}”" if puesto else "", cat) if x) or "Todos los empleos"
        return f"{que} — {lugar or 'Todo el país'}"
    tramo = unquote(partes.path.rstrip("/").split("/")[-1] or "")
    for fin in (".html", ".htm"):
        tramo = tramo.removesuffix(fin)
    texto = " ".join(tramo.replace("-", " ").replace("_", " ").split())
    consulta = dict(parse_qsl(partes.query))
    q = consulta.get("q") or consulta.get("query") or consulta.get("keywords")
    if q:
        texto = f"{texto} · “{q}”" if texto else f"“{q}”"
    return (texto[:1].upper() + texto[1:]) if texto else partes.netloc


def lista(cfg):
    """Los links de un config ya cargado (sirve tanto si tiene la lista como si tiene uno solo)."""
    urls = cfg.get("urls_busqueda")
    if not isinstance(urls, list) or not urls:
        urls = [cfg.get("url_busqueda")]
    return [u for u in urls if isinstance(u, str) and u.strip()]


def leer(plataforma):
    cfg = json.loads(_config(plataforma).read_text(encoding="utf-8")) if _config(plataforma).exists() else {}
    return {"busquedas": [{"url": u, "resumen": resumen(u), "campos": desarmar(plataforma, u)} for u in lista(cfg)],
            "ejemplo": PLATAFORMAS[plataforma]["ejemplo"]}


def desarmar(plataforma, url):
    """Inverso de armar(): link -> {"categoria", "provincia", "ciudad", "puesto"} con los mismos
    valores que usan las listas del editor, o None si el link no se puede editar con las listas
    (por ejemplo, uno pegado a mano con otros filtros). Lo usa el editor de búsquedas para abrir
    una búsqueda guardada y cambiarla."""
    try:
        partes = urlsplit(url)
        if partes.query:
            return None
        if plataforma == "computrabajo":
            return _desarmar_computrabajo(partes.path)
        if plataforma in JOBINT:
            return _desarmar_jobint(plataforma, partes.path)
    except Exception:
        return None
    return None


def _desarmar_computrabajo(camino):
    f = filtros("computrabajo")
    if not f:
        return None
    camino = unquote(camino.strip("/"))
    # lugar: el sem más largo con el que termina el camino (ciudad antes que provincia)
    lugares = [(REMOTO["sem"], REMOTO["sem"], "")]
    for p in f["provincias"]:
        lugares.append((p["sem"], p["sem"], ""))
        lugares += [(c["sem"], p["sem"], c["sem"]) for c in p["ciudades"]]
    prov = ciudad = ""
    for sem, p_sem, c_sem in sorted(lugares, key=lambda x: -len(x[0])):
        if camino.endswith(sem):
            camino, prov, ciudad = camino[: -len(sem)], p_sem, c_sem
            break
    cats = {c["slug"] for c in f["categorias"]}
    cat = puesto = ""
    if camino.startswith("empleos-de-"):
        cat = camino[len("empleos-de-"):]
        if cat not in cats:
            return None
    elif camino.startswith("trabajo-de-"):
        resto = camino[len("trabajo-de-"):]
        for s in cats:
            if resto.endswith("-de-" + s):
                resto, cat = resto[: -len("-de-" + s)], s
                break
        puesto = resto.replace("-", " ")
    elif camino != "empleos" or not prov:
        return None
    return {"categoria": cat, "provincia": prov, "ciudad": ciudad, "puesto": puesto}


def _desarmar_jobint(plataforma, camino):
    import re
    f = filtros(plataforma)
    if not f:
        return None
    partes = [p for p in unquote(camino).strip("/").split("/") if p]
    if not partes:
        return None
    m = re.fullmatch(r"empleos(?:-area-(?P<area>.+?))?(?P<remoto>-modalidad-remoto)?(?:-busqueda-(?P<kw>.+))?\.html", partes[-1])
    if not m:
        return None
    cat = m.group("area") or ""
    if cat and cat not in {c["slug"] for c in f["categorias"]}:
        return None
    lugar = partes[:-1]
    prov = ciudad = ""
    if lugar:
        if not lugar[0].startswith("en-") or len(lugar) > 2 or m.group("remoto"):
            return None                                       # remoto + lugar no se arma con las listas
        prov = lugar[0][3:]
        if len(lugar) == 2:
            if prov == "buenos-aires" and lugar[1] == "capital-federal":
                prov = "buenos-aires/capital-federal"            # la entrada propia "Capital Federal (CABA)"
            else:
                ciudad = lugar[1]
        p = next((x for x in f["provincias"] if x["sem"] == prov), None)
        if not p or (ciudad and ciudad not in {c["sem"] for c in p["ciudades"]}):
            return None
    elif m.group("remoto"):
        prov = REMOTO["sem"]
    return {"categoria": cat, "provincia": prov, "ciudad": ciudad, "puesto": (m.group("kw") or "").replace("-", " ")}


def validar(plataforma, url):
    """-> (url normalizada, None) o (None, mensaje de error)."""
    info = PLATAFORMAS.get(plataforma)
    if not info:
        return None, "Plataforma desconocida."
    url = (url or "").strip()
    if not url:
        return None, "Pegá el link de la búsqueda."
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    partes = urlsplit(url)
    if partes.netloc.lower() not in info["hosts"]:
        return None, f"El link tiene que ser de {info['hosts'][0]} (el de la página con la lista de avisos)."
    if "/candidate/" in partes.path or "/ofertas-de-trabajo/" in partes.path or (
            plataforma in JOBINT and ("/empleos/" in partes.path or "/postulantes/" in partes.path)):
        return None, "Ese es el link de un aviso o de tu cuenta. Pegá el de la lista de resultados de la búsqueda."
    if plataforma in JOBINT and not partes.path.endswith(".html"):
        return None, "Pegá el link de una lista de avisos (termina en .html, por ejemplo …/empleos-area-…html)."
    consulta = [(k, v) for k, v in parse_qsl(partes.query, keep_blank_values=True) if k not in info["quitar"]]
    host = partes.netloc.lower()
    if plataforma in JOBINT and not host.startswith("www."):
        host = "www." + host                       # bumeran.com.ar -> www.bumeran.com.ar (el sitio redirige igual)
    return urlunsplit(("https", host, partes.path, urlencode(consulta), "")), None


def guardar(plataforma, urls):
    """urls: lista de links (los vacíos se ignoran, los repetidos se guardan una vez)."""
    if isinstance(urls, str):
        urls = [urls]
    limpias = []
    for i, u in enumerate(urls or []):
        if not (u or "").strip():
            continue
        url, error = validar(plataforma, u)
        if error:
            return {"ok": False, "error": f"Link {i + 1}: {error}", "fila": i}
        if url not in limpias:
            limpias.append(url)
    # sin búsquedas también se puede guardar (el usuario quitó todas): el menú pide "Elegir qué buscar"
    archivo = _config(plataforma)
    cfg = json.loads(archivo.read_text(encoding="utf-8")) if archivo.exists() else {}
    cfg["urls_busqueda"] = limpias
    cfg["url_busqueda"] = limpias[0]
    archivo.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, **leer(plataforma)}


# ------------------------------------------------------------------ probar un link pegado a mano
def probar(plataforma, url):
    """Abre el link en la web y cuenta los avisos. Sirve para los links pegados a mano: uno mal
    copiado no da error, la web simplemente no trae avisos (o redirige a la portada).
    Usa un Edge temporal fuera de la pantalla (headless no sirve: las bolsas lo bloquean), sin la
    sesión del usuario. -> {"ok", "avisos", "resumen", "error"}"""
    url, error = validar(plataforma, url)
    if error:
        return {"ok": False, "error": error}
    import shutil
    import tempfile
    from playwright.sync_api import sync_playwright
    perfil = tempfile.mkdtemp(prefix="laburo-probar-")
    try:
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(perfil, channel="msedge", headless=False,
                                                       args=["--window-position=-2400,0"])
            try:
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                avisos = _contar_avisos(plataforma, page, url)
            finally:
                ctx.close()
    except Exception as e:
        return {"ok": False, "error": f"No pude abrir el link para probarlo ({str(e).splitlines()[0][:120]})."}
    finally:
        shutil.rmtree(perfil, ignore_errors=True)
    if not avisos:
        return {"ok": False, "avisos": 0, "error": "Ese link no trae ningún aviso. ¿Está bien copiado?"}
    return {"ok": True, "avisos": avisos, "resumen": resumen(url)}


def _contar_avisos(plataforma, page, url):
    """Cantidad de avisos que muestra el listado (el total del título si está, si no los de la página)."""
    import re
    if plataforma == "computrabajo":
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1500)
        if urlsplit(page.url).path.strip("/") == "":          # redirigió a la portada: link inválido
            return 0
        en_pagina = page.locator("article.box_offer").count()
        titulo = page.evaluate("() => (document.querySelector('h1') || {}).textContent || ''")
        m = re.search(r"\d[\d.]*", titulo)
        total = int(m.group(0).replace(".", "")) if m else 0
        return total if (total and en_pagina) else en_pagina
    if plataforma in JOBINT:
        # El listado lo arma la web pidiéndole a su API (searchV2): se lee el total de esa respuesta.
        try:
            with page.expect_response(lambda r: "api/avisos/searchV2" in r.url, timeout=45000) as resp:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception:
            return 0                                      # nunca pidió avisos: el link no es un listado
        if page.url.rstrip("/").endswith("/404"):
            return 0
        try:
            return int(resp.value.json().get("total") or 0)
        except Exception:
            return 0
    raise ValueError("Todavía no sé probar links de esta plataforma.")
