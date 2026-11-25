"""
Datos personales: el nombre (para saludar en el menú) y lo que se usa para autocompletar las
preguntas de los formularios (sueldo bruto pretendido y zona de residencia).

Se guardan en datos/perfil.json ({"nombre": "...", "sueldo": N o null, "zona": "..."}). El nombre
lo pide Setup.exe; sueldo y zona se completan desde la app ("Tus datos para los formularios"),
y en una instalación nueva arrancan vacíos. Los scripts de consola también toman el sueldo de acá.
"""
import json

import rutas

ARCHIVO = rutas.PERFIL

PALABRAS_SALARIO = ("salari", "remuneraci", "sueldo", "pretensi", "pretendid")
PALABRAS_ZONA = ("zona", "reside", "residencia", "vivís", "vivis", "vives", "barrio", "localidad",
                 "domicilio", "dónde viv", "donde viv", "ubicad", "ubicación", "ubicacion")
# Preguntas que nombran una zona pero no preguntan dónde vivís ("¿podés ir a zona norte?").
NO_ZONA = ("disponib", "traslad", "viajar", "movilizar", "oficina", "presencial", "podés ir", "podrías ir")


def _texto(v, maximo=120):
    return " ".join(str(v or "").split())[:maximo]


def _sueldo(v):
    digitos = "".join(c for c in str(v or "") if c.isdigit())[:12]
    return int(digitos) if digitos else None


def cargar():
    """-> {"nombre": str, "sueldo": int | None, "zona": str}"""
    try:
        guardado = json.loads(ARCHIVO.read_text(encoding="utf-8"))
        if not isinstance(guardado, dict):
            guardado = {}
    except (OSError, ValueError):
        guardado = {}           # no existe todavía (o está roto): vacío
    return {"nombre": _texto(guardado.get("nombre"), 60), "sueldo": _sueldo(guardado.get("sueldo")),
            "zona": _texto(guardado.get("zona"))}


def guardar(sueldo=None, zona=None, nombre=None):
    """Guarda lo que se pasa; lo que viene en None queda como estaba."""
    datos = cargar()
    if sueldo is not None:
        datos["sueldo"] = _sueldo(sueldo)
    if zona is not None:
        datos["zona"] = _texto(zona)
    if nombre is not None:
        datos["nombre"] = _texto(nombre, 60)
    ARCHIVO.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVO.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    return cargar()


def precarga(titulo, datos=None):
    """Qué precargar en una pregunta abierta del formulario. -> (valor, tipo) o ("", None).
    tipo: "sueldo" (bruto pretendido), "sueldo_neto" (si la pregunta dice "neto/neta": el neto
    estimado de sueldo_neto.py, redondeado a miles) o "zona"."""
    datos = datos or cargar()
    tipo = tipo_pregunta(titulo)
    if tipo == "sueldo" and datos.get("sueldo"):
        t = (titulo or "").lower()
        if "neto" in t or "neta" in t or "en mano" in t or "de bolsillo" in t:
            import sueldo_neto
            neto = int(round(sueldo_neto.calcular(datos["sueldo"])["neto"], -3))
            return str(neto), "sueldo_neto"
        return str(datos["sueldo"]), "sueldo"
    if tipo == "zona" and datos.get("zona"):
        return datos["zona"], "zona"
    return "", None


def tipo_pregunta(titulo):
    """'sueldo', 'zona' o None según de qué trate la pregunta."""
    t = (titulo or "").lower()
    if any(w in t for w in PALABRAS_SALARIO):
        return "sueldo"
    if any(w in t for w in PALABRAS_ZONA) and not any(w in t for w in NO_ZONA):
        return "zona"
    return None
