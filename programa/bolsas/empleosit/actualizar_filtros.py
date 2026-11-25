"""
Arma filtros.json (listas del editor de búsquedas) leyendo páginas públicas de EmpleosIT:
categorías del buscador y las ciudades que tienen avisos publicados (la web no filtra por provincia).
    python actualizar_filtros.py
"""
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True
SITIO = "https://www.empleosit.com.ar"
DESTINO = Path(__file__).resolve().parent / "filtros.json"


def main():
    with sync_playwright() as p, tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as perfil:
        ctx = p.chromium.launch_persistent_context(perfil, channel="msedge", headless=False,
                                                   args=["--window-position=-2400,0"])
        page = ctx.pages[0]
        page.set_default_timeout(90000)
        page.goto(SITIO + "/find-jobs/", wait_until="domcontentloaded")
        categorias = page.eval_on_selector_all(
            'select[name="JobCategory[multi_like][]"] option',
            "ops => ops.filter(o => o.value).map(o => ({slug: o.value, nombre: o.textContent.trim()}))")
        page.goto(SITIO + "/search-results-jobs/?action=search&listing_type%5Bequal%5D=Job&view=list&listings_per_page=100",
                  wait_until="domcontentloaded")
        lugares = page.eval_on_selector_all(".location-ico", "e => e.map(x => x.textContent.trim())")
        ctx.close()
    ciudades = {}
    for lugar in lugares:
        ciudad = lugar.rsplit(",", 1)[0].strip()
        if ciudad and ciudad != "Remoto":
            ciudades[ciudad] = lugar
    if not categorias or not ciudades:
        raise SystemExit("No pude leer las listas: no se cambia filtros.json.")
    datos = {"relevado": datetime.now().strftime("%d-%m-%Y"), "varias_categorias": True, "categorias": categorias,
             "provincias": [{"sem": c, "nombre": n, "ciudades": []} for c, n in sorted(ciudades.items())]}
    DESTINO.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(categorias)} categorías y {len(ciudades)} ciudades -> {DESTINO}")


if __name__ == "__main__":
    main()
