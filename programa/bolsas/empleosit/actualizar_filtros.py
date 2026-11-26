"""
Arma filtros.json (listas del editor de búsquedas) leyendo páginas públicas de EmpleosIT:
categorías del buscador, las provincias del lateral "refinar" (Location_State; solo aparecen las que tienen
avisos, con su número) y las ciudades que tienen avisos publicados, cada una dentro de su provincia.
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
        # provincias del lateral: links con Location_State[multi_like][]=<número> (el lateral carga después)
        try:
            page.wait_for_selector('a[href*="Location_State"]', timeout=20000)
        except Exception:
            pass
        estados = page.evaluate(r"""() => [...document.querySelectorAll('a[href*="Location_State"]')].map(a => {
            const m = decodeURIComponent(a.getAttribute('href')).match(/Location_State\[multi_like\]\[\]=(\d+)/);
            return m ? {sem: m[1], nombre: a.textContent.replace(/\s+/g, ' ').replace(/\(\d+\)\s*$/, '').trim()} : null;
        }).filter(Boolean)""")
        ctx.close()
    ciudades = {}
    for lugar in lugares:
        ciudad = lugar.rsplit(",", 1)[0].strip()
        if ciudad and ciudad != "Remoto":
            ciudades[ciudad] = lugar
    if not categorias or not ciudades:
        raise SystemExit("No pude leer las listas: no se cambia filtros.json.")
    # "Remoto" del lateral no se usa como provincia: remoto va por JobType (ver comun/busquedas.py)
    provincias = {e["nombre"]: {"sem": e["sem"], "nombre": e["nombre"], "ciudades": []}
                  for e in estados if e["nombre"].lower() != "remoto"}
    sueltas = []
    for ciudad, lugar in sorted(ciudades.items()):
        prov = lugar.rsplit(",", 1)[1].strip() if "," in lugar else ""
        if prov in provincias:
            provincias[prov]["ciudades"].append({"sem": ciudad, "nombre": ciudad})
        else:                                          # su provincia no está en el lateral: queda suelta
            sueltas.append({"sem": ciudad, "nombre": lugar, "ciudades": []})
    datos = {"relevado": datetime.now().strftime("%d-%m-%Y"), "varias_categorias": True, "categorias": categorias,
             "provincias": sorted(provincias.values(), key=lambda x: x["nombre"]) + sueltas}
    DESTINO.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(categorias)} categorías, {len(provincias)} provincias y {len(ciudades)} ciudades -> {DESTINO}")


if __name__ == "__main__":
    main()
