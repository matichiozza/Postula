"""
Arma computrabajo/filtros.json: las categorías, provincias y ciudades que ofrece Computrabajo, para
que la app deje elegirlas desde listas (sin tener que ir a la web a ver qué hay).

    python actualizar_filtros.py

Lee solo páginas públicas (sin sesión), con un perfil de Edge temporal y la ventana fuera de la
pantalla (headless no sirve: Computrabajo da 403). No toca perfil_edge/: se puede correr con la app
abierta. Tarda un par de minutos (una página por provincia, con pausas).

De dónde sale cada cosa:
  - categorías: /empleos-por-categoria/ (links ?q=empleos-de-<slug>);
  - provincias: el filtro "Provincia" del listado;
  - ciudades: el filtro "Ciudad" de /empleos-en-<provincia>. Ojo: la web solo muestra las ciudades
    que tienen avisos en ese momento, por eso conviene volver a correr esto cada tanto.
"""
import json
import random
import re
import sys
import tempfile
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parent
SALIDA = BASE / "filtros.json"
SITIO = "https://ar.computrabajo.com"

# La web escribe algunos nombres sin tilde o con errores: se corrigen para mostrarlos.
NOMBRES_CATEGORIA = {
    "construccion-y-obra": "Construcción y obra",
    "mercadeo-publicidad-comunicacion": "Marketing / Publicidad / Comunicación",
}

CATEGORIAS_JS = r"""() => [...document.querySelectorAll('a[href*="empleos-por-categoria/?q=empleos-de-"]')]
    .map(a => ({slug: a.getAttribute('href').split('q=empleos-de-')[1], nombre: a.textContent.trim()}))"""
PROVINCIAS_JS = r"""() => [...document.querySelectorAll('[id$="_location"]')]
    .map(a => ({sem: a.dataset.sem, nombre: a.textContent.trim()}))"""
CIUDADES_JS = r"""() => [...document.querySelectorAll('ul[data-id="idcity"] a')]
    .map(a => ({sem: a.dataset.sem, nombre: a.textContent.trim()}))"""


def ir(page, url):
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1200)


def nombre_ciudad(c, prov):
    """'Catamarca' (-en-catamarca-en-capital) -> 'Catamarca Capital'; 'La rioja' -> 'La Rioja Capital'."""
    if (c["sem"].endswith("-en-capital") or c["sem"] == prov["sem"] + "-capital"
            or c["nombre"].lower() == prov["nombre"].lower()):
        return f"{prov['nombre']} (capital)"
    n = c["nombre"]
    return n[:1].upper() + n[1:]


def main():
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            tempfile.mkdtemp(), channel="msedge", headless=False, args=["--window-position=-2400,0"])
        page = ctx.pages[0]

        ir(page, SITIO + "/empleos-por-categoria/")
        categorias = []
        for c in page.evaluate(CATEGORIAS_JS):
            if c["slug"] and c["slug"] not in [x["slug"] for x in categorias]:
                categorias.append({"slug": c["slug"], "nombre": NOMBRES_CATEGORIA.get(c["slug"], c["nombre"])})
        print(f"{len(categorias)} categorías")

        ir(page, SITIO + "/empleos-en-capital-federal")   # /empleos a secas no trae el filtro de provincia
        provincias = [x for x in page.evaluate(PROVINCIAS_JS) if x["sem"] and x["sem"] != "-en-extranjero"]
        if len(provincias) < 20:
            sys.exit(f"Solo encontré {len(provincias)} provincias: ¿cambió la página? No guardo nada.")

        for prov in provincias:
            page.wait_for_timeout(random.uniform(1500, 3000))
            ir(page, SITIO + "/empleos" + prov["sem"])
            ciudades = {}
            for c in page.evaluate(CIUDADES_JS):
                if c["sem"] and c["sem"] != prov["sem"]:
                    ciudades[c["sem"]] = nombre_ciudad(c, prov)
            prov["ciudades"] = sorted(({"sem": s, "nombre": n} for s, n in ciudades.items()),
                                      key=lambda x: re.sub(r"[^a-z0-9 ]", "", quitar_tildes(x["nombre"]).lower()))
            print(f"  {prov['nombre']}: {len(prov['ciudades'])} ciudades")
        ctx.close()

    provincias.sort(key=lambda x: quitar_tildes(x["nombre"]).lower())
    categorias.sort(key=lambda x: quitar_tildes(x["nombre"]).lower())
    datos = {"relevado": date.today().isoformat(), "categorias": categorias, "provincias": provincias}
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Guardado en {SALIDA}")


def quitar_tildes(t):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
