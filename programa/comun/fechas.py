"""
Cuándo se publicó un aviso, en palabras: "Publicado hoy", "Publicado ayer", "Publicado hace 3 días".
Computrabajo lo da como texto ("Hace 4 días"); Bumeran y ZonaJobs como fecha ("24-11-2026").
"" si no se reconoce (la lista muestra solo la empresa).
"""
import re
import unicodedata
from datetime import date, datetime, timedelta

MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre")


def _hace(dias):
    if dias <= 0:
        return "Publicado hoy"
    if dias == 1:
        return "Publicado ayer"
    return f"Publicado hace {dias} días"


def desde_fecha(texto, hoy=None):
    """'24-11-2026' (o con hora, o con /) -> texto."""
    try:
        fecha = datetime.strptime(str(texto)[:10].replace("/", "-"), "%d-%m-%Y").date()
    except ValueError:
        return ""
    return _hace(((hoy or date.today()) - fecha).days)


def antiguedad(texto="", fecha_hora=None, ahora=None):
    """Minutos desde la publicación (para ordenar), o None. Con fecha_hora ('24-11-2026 18:57:18',
    Bumeran/ZonaJobs) es exacto; con el texto de Computrabajo, tan preciso como lo que dice."""
    ahora = ahora or datetime.now()
    if fecha_hora:
        fecha_hora = str(fecha_hora).replace("/", "-")
        for formato, largo in (("%d-%m-%Y %H:%M:%S", 19), ("%d-%m-%Y", 10)):
            try:
                return max(0, int((ahora - datetime.strptime(str(fecha_hora)[:largo], formato)).total_seconds() // 60))
            except ValueError:
                pass
        return None
    m = re.search(r"hace\s+(\d+)\s+(minuto|hora)", (texto or "").lower())
    if m:
        return int(m.group(1)) * (60 if m.group(2) == "hora" else 1)
    palabras = desde_texto(texto, ahora.date())
    if not palabras:
        return None
    if "más de 30" in palabras:
        return 31 * 1440
    dias = re.search(r"\d+", palabras)
    return 1440 * (int(dias.group()) if dias else 1 if "ayer" in palabras else 0)


def desde_texto(texto, hoy=None):
    """El texto del listado de Computrabajo -> texto."""
    t = unicodedata.normalize("NFKD", (texto or "").lower())
    t = " ".join("".join(c for c in t if not unicodedata.combining(c)).split())
    hoy = hoy or date.today()
    if re.search(r"mas de 30 dias", t):
        return "Publicado hace más de 30 días"
    if re.search(r"\b(minutos?|horas?|segundos?|hoy)\b", t):
        return "Publicado hoy"
    if re.search(r"\bayer\b", t):
        return _hace(1)
    m = re.search(r"hace (\d+) dias?", t)
    if m:
        return _hace(int(m.group(1)))
    m = re.search(r"\b(\d{1,2}) de (\w+)", t)           # avisos más viejos: "30 de octubre"
    if m and m.group(2) in MESES:
        try:
            fecha = date(hoy.year, MESES.index(m.group(2)) + 1, int(m.group(1)))
        except ValueError:
            return ""
        if fecha > hoy + timedelta(days=1):
            fecha = fecha.replace(year=hoy.year - 1)
        return _hace((hoy - fecha).days)
    return ""
