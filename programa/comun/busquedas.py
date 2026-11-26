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
    "empleosit": {"nombre": "EmpleosIT", "hosts": ("www.empleosit.com.ar", "empleosit.com.ar"), "quitar": ("page", "searchId"),
                  "ejemplo": "https://www.empleosit.com.ar/search-results-jobs/?action=search&listing_type%5Bequal%5D=Job"},
    "linkedin": {"nombre": "LinkedIn", "hosts": ("www.linkedin.com", "linkedin.com", "ar.linkedin.com"), "quitar": ("start", "currentJobId"),
                 "ejemplo": "https://www.linkedin.com/jobs/search/?keywords=desarrollador&location=Argentina&f_AL=true"},
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


# ------------------------------------------------------------------ varias localidades en una búsqueda
# Ninguna bolsa combina bien varios lugares en un link: se guarda el link del primero más
# "lugares=prov~ciudad;prov~ciudad" (es de la app) y al recorrer se busca cada uno y se unen (expandir).
def _separar(url):
    """-> (link sin "lugares", [{"provincia", "ciudad"}])."""
    partes = urlsplit(url)
    consulta = parse_qsl(partes.query, keep_blank_values=True)
    texto = ";".join(v for k, v in consulta if k == "lugares")
    if not texto:
        return url, []
    lugares = [dict(zip(("provincia", "ciudad"), t.partition("~")[::2])) for t in texto.split(";") if t]
    resto = urlencode([(k, v) for k, v in consulta if k != "lugares"])
    return urlunsplit((partes.scheme, partes.netloc, partes.path, resto, "")), lugares


def armar(plataforma, datos):
    """Como _armar_uno, y además admite datos["lugares"] = [{"provincia", "ciudad"}] (vacío = todo el país)."""
    if datos.get("lugares") is None:
        return _armar_uno(plataforma, datos)
    lugares = list({(x.get("provincia") or "", x.get("ciudad") or ""): None for x in datos["lugares"] if x.get("provincia")})
    armados = [_armar_uno(plataforma, {**datos, "provincia": p, "ciudad": c}) for p, c in lugares or [("", "")]]
    malo = next((a for a in armados if not a["ok"]), None)
    if malo:
        return malo
    url = armados[0]["url"]
    if len(lugares) > 1:
        url += ("&" if "?" in url else "?") + urlencode({"lugares": ";".join(f"{p}~{c}" for p, c in lugares)})
    return {"ok": True, "url": url, "resumen": resumen(url)}


def expandir(plataforma, url):
    """Los links que hay que recorrer para una búsqueda guardada (uno por lugar)."""
    base, lugares = _separar(url)
    if not lugares:
        return [url]
    campos = _desarmar_uno(plataforma, base)
    if not campos:
        return [base]
    armados = [_armar_uno(plataforma, {**campos, **lugar}) for lugar in lugares]
    return [a["url"] for a in armados if a["ok"]] or [base]


def _nombre_lugar(plataforma, lugar):
    if lugar["provincia"] == REMOTO["sem"]:
        return "Remoto"
    p = next((x for x in (filtros(plataforma) or {}).get("provincias", []) if x["sem"] == lugar["provincia"]), None)
    if not p:
        return lugar["provincia"]
    c = next((x for x in p["ciudades"] if x["sem"] == lugar["ciudad"]), None)
    return (c or p)["nombre"].replace(" (CABA)", "")


def resumen(url):
    """Texto legible de la búsqueda: "qué — dónde"."""
    base, lugares = _separar(url)
    texto = _resumen_uno(base)
    if not lugares:
        return texto
    host = urlsplit(url).netloc.lower()
    plataforma = next((k for k, v in PLATAFORMAS.items() if host in v["hosts"]), None)
    if not plataforma:
        return texto
    nombres = [_nombre_lugar(plataforma, x) for x in lugares]
    donde = " + ".join(nombres) if len(nombres) <= 2 else f"{len(nombres)} lugares"
    return f"{texto.split(' — ')[0]} — {donde}"


def _armar_uno(plataforma, datos):
    """datos: {puesto, categoria (slug), provincia (sem), ciudad (sem)} -> {ok, url, resumen} o {ok: False, error}."""
    f = filtros(plataforma)
    if not f:
        return {"ok": False, "error": "Esta plataforma no tiene listas para armar la búsqueda."}
    if plataforma in JOBINT:
        return _armar_jobint(plataforma, f, datos)
    if plataforma == "empleosit":
        return _armar_empleosit(f, datos)
    if plataforma == "linkedin":
        return _armar_linkedin(f, datos)
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
    subareas = list(dict.fromkeys(datos.get("subareas") or []))
    if subareas and not set(subareas) <= {s["slug"] for s in _subareas_de(f, cat)}:
        return {"ok": False, "error": "Subárea desconocida."}
    nombre = "empleos" + (f"-area-{cat}" if cat else "") + ("-modalidad-remoto" if remoto else "") + \
             (f"-busqueda-{puesto}" if puesto else "") + ".html"
    url = f"{SITIOS[plataforma]}/{lugar}{nombre}" + ("?" + urlencode({"subareas": ",".join(subareas)}) if subareas else "")
    return {"ok": True, "url": url, "resumen": resumen(url)}


def _subareas_de(f, categoria):
    return next((c.get("subareas") or [] for c in f["categorias"] if c["slug"] == categoria), [])


def _subareas_en_link(consulta):
    """"subareas=a,b" -> ["a", "b"]; None si el link trae otros parámetros (no se arma con las listas)."""
    q = parse_qsl(consulta)
    if any(k != "subareas" for k, _ in q):
        return None
    return [s for _, v in q for s in v.split(",") if s]


def _nombres_subareas(f, categoria, subareas):
    nombres = {s["slug"]: s["nombre"] for s in _subareas_de(f, categoria)}
    elegidas = [nombres.get(s, s.replace("-", " ").title()) for s in subareas]
    return ", ".join(elegidas) if len(elegidas) <= 2 else f"{len(elegidas)} subáreas"


def _leer_jobint(plataforma, camino, consulta=""):
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
    subareas = _subareas_en_link(consulta)
    if subareas and m.group("area"):
        cat = f"{cat}: {_nombres_subareas(f, m.group('area'), subareas)}"
    return puesto, cat, lugar


# ------------------------------------------------------------------ EmpleosIT (SmartJobBoard)
# El buscador es un GET a /search-results-jobs/ (verificado 25-11-2026): keywords[all_words],
# JobCategory[multi_like][]=<id>, JobType[multi_like][]=1242 (remoto) y Location_City[multi_like_and][].
# Lugar: Location_State[multi_like][]=<número de provincia> (la web solo lista las provincias con avisos)
# o Location_City[multi_like_and][]=<ciudad>; en "Dónde" las ciudades van dentro de su provincia.
EIT_BASE = "https://www.empleosit.com.ar/search-results-jobs/"
EIT_FIJOS = [("action", "search"), ("listing_type[equal]", "Job"), ("view", "list"), ("listings_per_page", "100")]
EIT_PALABRA, EIT_CATEGORIA = "keywords[all_words]", "JobCategory[multi_like][]"
EIT_TIPO, EIT_REMOTO, EIT_CIUDAD = "JobType[multi_like][]", "1242", "Location_City[multi_like_and][]"
EIT_PROVINCIA = "Location_State[multi_like][]"            # número de provincia (61 = Buenos Aires)


def _lugar_empleosit(f, prov, ciudad):
    """(provincia, ciudad) del editor -> (clave, valor) del link, o None si no está en las listas.
    Provincia = número de Location_State (25-11-2026: la web sí filtra por provincia; solo lista las que
    tienen avisos). Ciudad = Location_City. Una ciudad "suelta" (su provincia no está) va como provincia."""
    if prov == REMOTO["sem"]:
        return EIT_TIPO, EIT_REMOTO
    p = next((x for x in f["provincias"] if x["sem"] == prov), None)
    if not p:
        return None
    if ciudad:
        return (EIT_CIUDAD, ciudad) if ciudad in {c["sem"] for c in p["ciudades"]} else None
    return (EIT_PROVINCIA, prov) if prov.isdigit() else (EIT_CIUDAD, prov)


def _armar_empleosit(f, datos):
    puesto = " ".join((datos.get("puesto") or "").split())
    cats = list(dict.fromkeys(datos.get("subareas") or ([datos["categoria"]] if datos.get("categoria") else [])))
    todas = {c["slug"] for c in f["categorias"]}
    if not set(cats) <= todas:
        return {"ok": False, "error": "Categoría desconocida."}
    consulta = list(EIT_FIJOS)
    if puesto:
        consulta.append((EIT_PALABRA, puesto))
    if set(cats) != todas:                                   # todas marcadas = sin filtro de categoría
        consulta += [(EIT_CATEGORIA, c) for c in cats]       # la web suma los avisos de todas
    prov = datos.get("provincia") or ""
    if prov:
        par = _lugar_empleosit(f, prov, datos.get("ciudad") or "")
        if not par:
            return {"ok": False, "error": "Lugar desconocido."}
        consulta.append(par)
    if not (puesto or cats or prov):
        return {"ok": False, "error": "Elegí al menos una categoría, un puesto o un lugar."}
    url = EIT_BASE + "?" + urlencode(consulta)
    return {"ok": True, "url": url, "resumen": resumen(url)}


def _desarmar_empleosit(consulta):
    f = filtros("empleosit")
    q = dict(parse_qsl(consulta))
    if not f or set(q) - {k for k, _ in EIT_FIJOS} - {EIT_PALABRA, EIT_CATEGORIA, EIT_TIPO, EIT_CIUDAD, EIT_PROVINCIA}:
        return None
    todas = [c["slug"] for c in f["categorias"]]
    cats = [v for k, v in parse_qsl(consulta) if k == EIT_CATEGORIA] or todas     # sin filtro = todas
    if not set(cats) <= set(todas) or (q.get(EIT_TIPO) and q.get(EIT_TIPO) != EIT_REMOTO):
        return None
    prov = ciudad = ""
    if q.get(EIT_TIPO) == EIT_REMOTO:
        prov = REMOTO["sem"]
    elif q.get(EIT_PROVINCIA):
        prov = q[EIT_PROVINCIA]
        if prov not in {p["sem"] for p in f["provincias"]}:
            return None
    elif q.get(EIT_CIUDAD):
        c = q[EIT_CIUDAD]
        dentro = next((p for p in f["provincias"] if c in {x["sem"] for x in p["ciudades"]}), None)
        if dentro:
            prov, ciudad = dentro["sem"], c
        elif c in {p["sem"] for p in f["provincias"]}:
            prov = c                                           # ciudad suelta
        else:
            return None
    return {"categoria": "", "subareas": cats, "provincia": prov, "ciudad": ciudad, "puesto": q.get(EIT_PALABRA, "")}


def _leer_empleosit(consulta):
    c = _desarmar_empleosit(consulta)
    if c is None:
        return None
    f = filtros("empleosit")
    nombres = {x["slug"]: x["nombre"] for x in f["categorias"]}
    elegidas = [nombres[s] for s in c["subareas"]]
    cat = "Todas las categorías" if len(elegidas) == len(nombres) else \
        ", ".join(elegidas) if len(elegidas) <= 2 else f"{len(elegidas)} categorías"
    if c["provincia"] == REMOTO["sem"]:
        lugar = "Remoto"
    else:
        p = next((x for x in f["provincias"] if x["sem"] == c["provincia"]), {"nombre": "", "ciudades": []})
        lugar = next((x["nombre"] for x in p["ciudades"] if x["sem"] == c["ciudad"]), p["nombre"])
        lugar = lugar.replace("Ciudad Autónoma de Buenos Aires (CABA)", "CABA")
    return c["puesto"], cat, lugar


# ------------------------------------------------------------------ LinkedIn (búsqueda con JobSpy)
# Se guarda el link de la web de LinkedIn (se puede abrir en el navegador), siempre con f_AL=true
# (Solicitud sencilla). No tiene categorías: palabra clave + lugar (texto que LinkedIn entiende,
# de bolsas/linkedin/filtros.json) o remoto (f_WT=2, en todo el país).
LI_BASE = "https://www.linkedin.com/jobs/search/"


def _armar_linkedin(f, datos):
    puesto = " ".join((datos.get("puesto") or "").split())
    if not puesto:
        return {"ok": False, "error": "Escribí la palabra clave."}
    prov, ciudad = datos.get("provincia") or "", datos.get("ciudad") or ""
    consulta = [("keywords", puesto)]
    if prov == REMOTO["sem"]:
        consulta += [("location", "Argentina"), ("f_WT", "2")]
    elif prov:
        p = next((x for x in f["provincias"] if x["sem"] == prov), None)
        if not p or (ciudad and ciudad not in {c["sem"] for c in p["ciudades"]}):
            return {"ok": False, "error": "Lugar desconocido."}
        consulta.append(("location", ciudad or prov))
    else:
        consulta.append(("location", "Argentina"))
    consulta.append(("f_AL", "true"))
    url = LI_BASE + "?" + urlencode(consulta)
    return {"ok": True, "url": url, "resumen": resumen(url)}


def _desarmar_linkedin(consulta):
    f = filtros("linkedin")
    q = dict(parse_qsl(consulta))
    if not f or set(q) - {"keywords", "location", "f_AL", "f_WT"} or not q.get("keywords"):
        return None
    lugar, prov, ciudad = q.get("location", ""), "", ""
    if q.get("f_WT") == "2":
        prov = REMOTO["sem"]
    elif lugar and lugar != "Argentina":
        for p in f["provincias"]:
            if p["sem"] == lugar:
                prov = lugar
            for c in p["ciudades"]:
                if c["sem"] == lugar:
                    prov, ciudad = p["sem"], lugar
        if not prov:
            return None
    return {"categoria": "", "subareas": [], "provincia": prov, "ciudad": ciudad, "puesto": q["keywords"]}


def _leer_linkedin(consulta):
    q = dict(parse_qsl(consulta))
    if not q.get("keywords"):
        return None
    lugar = "Remoto" if q.get("f_WT") == "2" else q.get("location", "")
    f = filtros("linkedin") or {"provincias": []}
    for p in f["provincias"]:
        if p["sem"] == lugar:
            lugar = p["nombre"].replace(" (CABA)", "")
        for c in p["ciudades"]:
            if c["sem"] == lugar:
                lugar = c["nombre"]
    return q["keywords"], "", "" if lugar == "Argentina" else lugar


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


def _resumen_uno(url):
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
                leido = _leer_jobint(plat, partes.path, partes.query)
            except Exception:
                leido = None
    if host in PLATAFORMAS["linkedin"]["hosts"]:
        try:
            leido = _leer_linkedin(partes.query)
        except Exception:
            leido = None
    if host in PLATAFORMAS["empleosit"]["hosts"]:
        try:
            leido = _leer_empleosit(partes.query)
        except Exception:
            leido = None
        if not leido:
            return "Búsqueda de EmpleosIT"
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
    """Las búsquedas ACTIVAS de un config (las que se recorren)."""
    apagadas = set(cfg.get("urls_inactivas") or [])
    return [u for u in todas(cfg) if u not in apagadas]


def todas(cfg):
    """Los links de un config ya cargado (sirve tanto si tiene la lista como si tiene uno solo)."""
    urls = cfg.get("urls_busqueda")
    if not isinstance(urls, list) or not urls:
        urls = [cfg.get("url_busqueda")]
    return [u for u in urls if isinstance(u, str) and u.strip()]


def leer(plataforma):
    cfg = json.loads(_config(plataforma).read_text(encoding="utf-8")) if _config(plataforma).exists() else {}
    activas = set(lista(cfg))
    return {"busquedas": [{"url": u, "resumen": resumen(u), "campos": desarmar(plataforma, u), "activa": u in activas}
                          for u in todas(cfg)],
            "ejemplo": PLATAFORMAS[plataforma]["ejemplo"]}


def desarmar(plataforma, url):
    """Link guardado -> campos del editor (con "lugares"), o None si no se puede editar con las listas."""
    base, lugares = _separar(url)
    campos = _desarmar_uno(plataforma, base)
    if campos:
        campos["lugares"] = lugares or ([{"provincia": campos["provincia"], "ciudad": campos["ciudad"]}] if campos["provincia"] else [])
    return campos


def _desarmar_uno(plataforma, url):
    """Inverso de armar(): link -> {"categoria", "provincia", "ciudad", "puesto"} con los mismos
    valores que usan las listas del editor, o None si el link no se puede editar con las listas
    (por ejemplo, uno pegado a mano con otros filtros). Lo usa el editor de búsquedas para abrir
    una búsqueda guardada y cambiarla."""
    try:
        partes = urlsplit(url)
        if plataforma == "empleosit":
            return _desarmar_empleosit(partes.query)
        if plataforma == "linkedin":
            return _desarmar_linkedin(partes.query)
        if plataforma in JOBINT:
            return _desarmar_jobint(plataforma, partes.path, partes.query)
        if partes.query:
            return None
        if plataforma == "computrabajo":
            return _desarmar_computrabajo(partes.path)
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


def _desarmar_jobint(plataforma, camino, consulta=""):
    import re
    f = filtros(plataforma)
    if not f:
        return None
    partes = [p for p in unquote(camino).strip("/").split("/") if p]
    subareas = _subareas_en_link(consulta)
    if not partes or subareas is None:
        return None
    m = re.fullmatch(r"empleos(?:-area-(?P<area>.+?))?(?P<remoto>-modalidad-remoto)?(?:-busqueda-(?P<kw>.+))?\.html", partes[-1])
    if not m:
        return None
    cat = m.group("area") or ""
    if cat and cat not in {c["slug"] for c in f["categorias"]}:
        return None
    if subareas and not set(subareas) <= {s["slug"] for s in _subareas_de(f, cat)}:
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
    return {"categoria": cat, "subareas": subareas, "provincia": prov, "ciudad": ciudad,
            "puesto": (m.group("kw") or "").replace("-", " ")}


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
    if plataforma == "linkedin":
        if not partes.path.startswith("/jobs/search"):
            return None, "Pegá el link de una búsqueda de empleos de LinkedIn (…/jobs/search/?keywords=…)."
        q = dict(consulta)
        if not q.get("keywords"):
            return None, "El link tiene que tener una palabra clave (keywords=…)."
        # solo se usan palabra, lugar y remoto; siempre Solicitud sencilla
        consulta = [(k, q[k]) for k in ("keywords", "location") if q.get(k)] +                    ([("f_WT", "2")] if "2" in q.get("f_WT", "").split(",") else []) + [("f_AL", "true")] +                    ([("lugares", q["lugares"])] if q.get("lugares") else [])        # varios lugares (es de la app)
        return urlunsplit(("https", "www.linkedin.com", "/jobs/search/", urlencode(consulta), "")), None
    if plataforma == "empleosit":
        if "/search-results-jobs" not in partes.path:
            return None, "Pegá el link de una lista de resultados de EmpleosIT (…/search-results-jobs/?…)."
        # "searchId" es una búsqueda guardada en tu sesión del navegador: sin los filtros no sirve
        if any(k == "searchId" for k, _ in parse_qsl(partes.query)) and not any(
                k.startswith(("keywords", "JobCategory", "Job", "Location", "Posted", "Employment")) for k, _ in consulta):
            return None, "Ese link no trae los filtros. Hacé la búsqueda con el botón «Buscar» y copiá el link de la primera página."
        propios = {k for k, _ in consulta}
        consulta += [(k, v) for k, v in EIT_FIJOS if k not in propios]
    host = partes.netloc.lower()
    if plataforma in ("empleosit",) + JOBINT and not host.startswith("www."):
        host = "www." + host                       # bumeran.com.ar -> www.bumeran.com.ar (el sitio redirige igual)
    return urlunsplit(("https", host, partes.path, urlencode(consulta), "")), None


def guardar(plataforma, urls, inactivas=None):
    """urls: lista de links (los vacíos se ignoran, los repetidos se guardan una vez). inactivas: los
    que quedan guardados pero no se recorren (None = no cambiar cuáles están apagados)."""
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
    if inactivas is None:
        apagadas = set(cfg.get("urls_inactivas") or [])
    else:
        apagadas = {validar(plataforma, u)[0] for u in inactivas}
    cfg["urls_busqueda"] = limpias
    cfg["urls_inactivas"] = [u for u in limpias if u in apagadas]
    # None (y no borrar la clave) si no queda ninguna: así no vuelve la búsqueda de fábrica del script
    cfg["url_busqueda"] = next((u for u in limpias if u not in apagadas), None)
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
    perfil = tempfile.mkdtemp(prefix="postula-probar-")
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
    if plataforma == "empleosit":
        page.goto(url, wait_until="domcontentloaded", timeout=90000)
        return page.locator('.listing-title a[href*="/display-job/"]').count()
    if plataforma == "linkedin":
        import importlib.util
        spec = importlib.util.spec_from_file_location("postulador_linkedin", rutas.codigo_bolsa("linkedin") / "postulador.py")
        li = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(li)
        avisos, frenado = li.buscar(url, 25)
        if frenado and not avisos:
            raise RuntimeError("LinkedIn está limitando las búsquedas; probá en unos minutos")
        return len(avisos)
    raise ValueError("Todavía no sé probar links de esta plataforma.")
