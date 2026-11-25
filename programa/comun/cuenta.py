"""
Cuenta vinculada de cada bolsa (datos/<bolsa>/cuenta.json).

"Vinculada" = alguna vez se inició sesión en el Edge de la app (datos/<bolsa>/perfil_edge/, donde quedan
las cookies) y se anotó con qué mail. Sirve para que el menú muestre el estado sin abrir Edge. Si la sesión
vence igual, al empezar el recorrido la app lo detecta y vuelve a pedir el login.

Reconectar (o usar otra cuenta) borra el perfil de Edge de esa bolsa: el historial, los descartes y la
configuración están en otros archivos y no se tocan.
"""
import json
import shutil
from datetime import datetime

import rutas


def _archivo(bolsa):
    return rutas.datos_bolsa(bolsa) / "cuenta.json"


def leer(bolsa):
    """-> {"vinculada": bool, "mail": str, "fecha": str}"""
    f = _archivo(bolsa)
    perfil = rutas.datos_bolsa(bolsa) / "perfil_edge"
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        d = None
    if not d or not perfil.exists():
        return {"vinculada": False, "mail": "", "fecha": ""}
    return {"vinculada": True, "mail": d.get("mail") or "", "fecha": d.get("fecha") or ""}


def guardar(bolsa, mail):
    _archivo(bolsa).write_text(json.dumps({"mail": mail or "", "fecha": datetime.now().isoformat(timespec="seconds")},
                                          ensure_ascii=False, indent=2), encoding="utf-8")


def desvincular(bolsa):
    """Borra la sesión guardada (perfil de Edge) y el registro de la cuenta. Edge tiene que estar cerrado."""
    d = rutas.datos_bolsa(bolsa)
    try:
        _archivo(bolsa).unlink()
    except FileNotFoundError:
        pass
    shutil.rmtree(d / "perfil_edge", ignore_errors=True)
    return not (d / "perfil_edge").exists()
