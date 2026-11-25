"""
Dónde está cada cosa. El código y los datos del usuario van separados:

    programa/
    ├─ app/          la app de escritorio
    ├─ bolsas/       el código de cada bolsa (<bolsa>/postulador.py)
    ├─ comun/        módulos compartidos (este, busquedas, descartes, perfil, sueldo_neto)
    ├─ datos/        TODO lo personal (un solo usuario): perfil.json (nombre, sueldo, zona),
    │                <bolsa>/{config.json, historial.json, descartes.json, perfil_edge/},
    │                python.txt y registros/ (logs)
    └─ instalador/   fuentes de Setup.exe y Laburo IA.exe

Para empezar de cero con otra cuenta alcanza con borrar datos/ (o usar la opción de Setup.exe).
"""
from pathlib import Path

PROGRAMA = Path(__file__).resolve().parent.parent
APP = PROGRAMA / "app"
BOLSAS = PROGRAMA / "bolsas"
DATOS = PROGRAMA / "datos"
PLATAFORMAS = ("computrabajo", "bumeran", "zonajobs", "empleosit")
PERFIL = DATOS / "perfil.json"         # nombre, sueldo pretendido y zona de residencia
REGISTROS = DATOS / "registros"        # app.log, errores.log, setup.log


def codigo_bolsa(bolsa):
    """Carpeta con el código de una bolsa (postulador.py, y en Computrabajo filtros.json)."""
    return BOLSAS / bolsa


def datos_bolsa(bolsa):
    """Carpeta con los datos de una bolsa (config.json, historial.json, perfil_edge/). Se crea si falta."""
    d = DATOS / bolsa
    d.mkdir(parents=True, exist_ok=True)
    return d


def registros():
    REGISTROS.mkdir(parents=True, exist_ok=True)
    return REGISTROS
