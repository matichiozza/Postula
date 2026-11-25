"""
Arma filtros.json de Bumeran y de ZonaJobs: las áreas (categorías), provincias y localidades, para que
la app deje armar las búsquedas desde listas.

    python actualizar_filtros.py

Las dos bolsas son la misma plataforma (Jobint/Navent) y comparten el listado, así que se pide una
sola vez a la API de búsqueda de Bumeran y se guarda en bolsas/bumeran/filtros.json y en
bolsas/zonajobs/filtros.json. Solo lee datos públicos (sin sesión), con un Edge temporal fuera de la
pantalla (headless no sirve: Cloudflare lo bloquea). Tarda alrededor de un minuto.

Cómo se arman los links (verificado el 24-11-2026, igual en los dos sitios):
    /[en-<provincia>/[<localidad>/]]empleos[-area-<área>][-modalidad-remoto][-busqueda-<palabras>].html
La API devuelve, con cada búsqueda, las "facetas" (filtros posibles con cuántos avisos tiene cada uno).
Ojo: como en Computrabajo, solo aparecen las localidades que tienen avisos en ese momento.
"""
import json
import sys
import tempfile
import time
import unicodedata
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parent
SALIDAS = [BASE / "filtros.json", BASE.parent / "zonajobs" / "filtros.json"]
SITIO = "https://www.bumeran.com.ar"

FETCH = """async (body) => {
  const r = await fetch('/api/avisos/searchV2?pageSize=1&page=0&sort=RELEVANTES', {method: 'POST', credentials: 'include',
     headers: {'x-site-id': 'BMAR', 'Content-Type': 'application/json'}, body: JSON.stringify(body)});
  return [r.status, await r.text()];
}"""

# La API trae los nombres sin tildes: se corrigen para mostrarlos.
TILDES = {"Cordoba": "Córdoba", "Neuquen": "Neuquén", "Rio Negro": "Río Negro", "Entre Rios": "Entre Ríos",
          "Tucuman": "Tucumán"}


def sin_tildes(t):
    return "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c)).lower()


def main():
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(tempfile.mkdtemp(), channel="msedge", headless=False,
                                                   args=["--window-position=-2400,0"])
        page = ctx.pages[0]
        page.goto(SITIO + "/empleos.html", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        def buscar(filtros):
            st, txt = page.evaluate(FETCH, {"filtros": filtros})
            if st != 200:
                raise RuntimeError(f"La API de búsqueda respondió HTTP {st}")
            d = json.loads(txt)
            return {f["type"]: f["facets"] for f in d.get("filters", [])}

        facetas = buscar([])
        categorias = [{"slug": a["idSemantico"], "nombre": a["name"]} for a in facetas.get("area", []) if a.get("idSemantico")]
        provincias = []
        for prov in facetas.get("provincia", []):
            time.sleep(1.2)
            slug = prov["idSemantico"].split("|")[-1]                     # "argentina|buenos-aires" -> "buenos-aires"
            locs = buscar([{"id": "provincia", "value": prov["idSemantico"]}]).get("localidad", [])
            ciudades = []
            for l in locs:
                partes = (l.get("idSemantico") or "").split("|")          # "argentina|buenos-aires|capital-federal"
                if len(partes) == 3 and partes[1] == slug:
                    ciudades.append({"sem": partes[2], "nombre": TILDES.get(l["name"], l["name"])})
            ciudades.sort(key=lambda c: sin_tildes(c["nombre"]))
            provincias.append({"sem": slug, "nombre": TILDES.get(prov["name"], prov["name"]), "ciudades": ciudades})
            print(f"  {prov['name']}: {len(ciudades)} localidades")
        ctx.close()

    if len(categorias) < 15 or len(provincias) < 15:
        sys.exit(f"Trajo muy pocas áreas ({len(categorias)}) o provincias ({len(provincias)}): ¿cambió la API? No guardo nada.")
    # Capital Federal: para la plataforma es una localidad de Buenos Aires, pero la gente la busca como
    # provincia. Se agrega también como entrada propia (sem "buenos-aires/capital-federal").
    if any(c["sem"] == "capital-federal" for p in provincias if p["sem"] == "buenos-aires" for c in p["ciudades"]):
        provincias.append({"sem": "buenos-aires/capital-federal", "nombre": "Capital Federal (CABA)", "ciudades": []})
    provincias.sort(key=lambda x: sin_tildes(x["nombre"]))
    categorias.sort(key=lambda x: sin_tildes(x["nombre"]))
    datos = {"relevado": date.today().isoformat(), "categorias": categorias, "provincias": provincias}
    for salida in SALIDAS:
        salida.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"Guardado en {salida}")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
