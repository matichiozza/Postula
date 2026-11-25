"""
Exportar, importar y borrar los datos del usuario (Ajustes de la app).

Exportar/importar sirve para pasarlos a una instalación nueva (o a otra PC).

El archivo es un JSON legible:
    {"app": "Postulá", "tipo": "datos-de-usuario", "version": 1, "exportado": "2026-11-24 18:30",
     "nombre": "...", "sueldo": N o null, "zona": "...",
     "descartes": {"computrabajo": {"<id>": {titulo, empresa, url, motivo, fecha}}, "bumeran": {...}, ...},
     "busquedas": {"computrabajo": ["<link>", ...], "bumeran": [...], ...}}

Importar reemplaza nombre, sueldo y zona (solo los que vienen completos) y SUMA los avisos
descartados y las búsquedas a los que ya haya (no borra ninguno; las repetidas no se duplican).
Las sesiones de Edge y los historiales no viajan: las sesiones no sirven en otra PC y los
historiales se rearman solos.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

import busquedas
import descartes
import perfil
import rutas

TIPO = "datos-de-usuario"


def exportar(destino):
    """Escribe el archivo y devuelve un resumen."""
    p = perfil.cargar()
    desc = descartes.todos()
    busq = {}
    for plataforma in rutas.PLATAFORMAS:
        try:
            urls = [b["url"] for b in busquedas.leer(plataforma)["busquedas"]]
        except Exception:
            urls = []
        if urls:
            busq[plataforma] = urls
    datos = {"app": "Postulá", "tipo": TIPO, "version": 1, "exportado": datetime.now().strftime("%Y-%m-%d %H:%M"),
             **p, "descartes": desc, "busquedas": busq}
    destino = Path(destino)
    destino.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"ok": True, "archivo": str(destino), **p, "descartes": sum(len(v) for v in desc.values()),
            "busquedas": sum(len(v) for v in busq.values())}


def leer(origen):
    """Lee y valida un archivo exportado. -> dict o ValueError con un mensaje claro."""
    try:
        datos = json.loads(Path(origen).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ValueError("No pude leer ese archivo. ¿Es el que exportaste desde Postulá?")
    if not isinstance(datos, dict) or datos.get("tipo") != TIPO:
        raise ValueError("Ese archivo no es una exportación de datos de Postulá.")
    if not isinstance(datos.get("descartes", {}), dict):
        raise ValueError("El archivo está incompleto (los descartes no tienen el formato esperado).")
    if not isinstance(datos.get("busquedas", {}), dict):            # los exportados antes del 24-11-2026 no la traen
        raise ValueError("El archivo está incompleto (las búsquedas no tienen el formato esperado).")
    return datos


def importar(origen):
    """Aplica un archivo exportado. Devuelve un resumen de lo que cambió."""
    datos = leer(origen)
    nuevo = perfil.guardar(
        sueldo=datos.get("sueldo") if datos.get("sueldo") else None,
        zona=datos.get("zona") if datos.get("zona") else None,
        nombre=datos.get("nombre") if datos.get("nombre") else None)
    sumados, total = 0, 0
    for plataforma, avisos in datos.get("descartes", {}).items():
        if plataforma in rutas.PLATAFORMAS and isinstance(avisos, dict):
            sumados += descartes.sumar(plataforma, avisos)
            total += len(avisos)
    busq_nuevas = sumar_busquedas(datos.get("busquedas") or {})
    return {"ok": True, **nuevo, "descartes_archivo": total, "descartes_nuevos": sumados, "busquedas_nuevas": busq_nuevas}


def sumar_busquedas(por_plataforma):
    """Agrega las búsquedas importadas a las que ya hay (sin duplicar). Las que no son válidas para
    su plataforma se ignoran. -> cuántas sumó en total."""
    sumadas = 0
    for plataforma, urls in por_plataforma.items():
        if plataforma not in rutas.PLATAFORMAS or not isinstance(urls, list):
            continue
        actuales = [b["url"] for b in busquedas.leer(plataforma)["busquedas"]]
        nuevas = []
        for u in urls:
            url, error = busquedas.validar(plataforma, u if isinstance(u, str) else "")
            if url and not error and url not in actuales and url not in nuevas:
                nuevas.append(url)
        if nuevas:
            busquedas.guardar(plataforma, actuales + nuevas)
            sumadas += len(nuevas)
    return sumadas


# Lo que NO se borra al empezar de cero: no son datos del usuario sino de la instalación.
CONSERVAR = {"python.txt"}            # qué Python abre la app (lo escribe Setup.exe)
CONSERVAR_REGISTROS = {"app.log"}     # lo tiene abierto la app mientras corre


def borrar_todo():
    """"Empezar de cero": borra perfil.json (nombre, sueldo, zona) y, de cada bolsa, config.json
    (búsquedas), historial.json, descartes.json y la sesión de Edge (perfil_edge/). También los
    registros viejos. Devuelve {"ok", "borrados": [...], "fallaron": [...]}."""
    borrados, fallaron = [], []
    if not rutas.DATOS.exists():
        return {"ok": True, "borrados": [], "fallaron": []}
    for item in sorted(rutas.DATOS.iterdir()):
        if item.name in CONSERVAR:
            continue
        objetivos = ([r for r in item.iterdir() if r.name not in CONSERVAR_REGISTROS]
                     if item == rutas.REGISTROS else [item])
        for obj in objetivos:
            nombre = obj.relative_to(rutas.DATOS).as_posix()
            try:
                if obj.is_dir():
                    shutil.rmtree(obj)
                else:
                    obj.unlink()
                borrados.append(nombre)
            except OSError:
                fallaron.append(nombre)
    return {"ok": not fallaron, "borrados": borrados, "fallaron": fallaron}
