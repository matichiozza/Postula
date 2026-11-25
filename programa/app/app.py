"""
Postulá: app de escritorio para los postuladores (ventana propia con pywebview; la interfaz
está hecha en HTML en ui/). Por ahora tiene Computrabajo; las demás plataformas siguen con su
script de consola.

    pythonw app.py      -> abre la app sin consola
    python app.py       -> igual, pero con consola (sirve para ver errores)
"""
import json
import subprocess
import sys

sys.dont_write_bytecode = True   # sin carpetas __pycache__ entre el código
import threading
import traceback
import webbrowser
from pathlib import Path

import webview

APP = Path(__file__).resolve().parent
sys.path.insert(0, str(APP))
sys.path.insert(0, str(APP.parent / "comun"))   # módulos compartidos
from motor_computrabajo import MotorComputrabajo  # noqa: E402
from motor_jobint import MotorBumeran, MotorZonaJobs  # noqa: E402
from motor_empleosit import MotorEmpleosIT  # noqa: E402
import perfil  # noqa: E402
import sueldo_neto  # noqa: E402
import busquedas  # noqa: E402
import rutas  # noqa: E402
import datos_usuario  # noqa: E402
import descartes  # noqa: E402
import cuenta  # noqa: E402
import actualizar  # noqa: E402

MOTORES = {"computrabajo": MotorComputrabajo, "bumeran": MotorBumeran, "zonajobs": MotorZonaJobs,
           "empleosit": MotorEmpleosIT}
LOG = rutas.registros() / "errores.log"
ICONO = APP / "recursos" / "logo.ico"


def historial_formularios(plataforma):
    """De datos/<plataforma>/historial.json, los "postulado" que guardaron preguntas y respuestas
    (los que mandaste desde el formulario). Más nuevos primero."""
    archivo = rutas.datos_bolsa(plataforma) / "historial.json"
    if not archivo.exists():
        return []
    historial = json.loads(archivo.read_text(encoding="utf-8"))
    items = []
    for oid, h in historial.items():
        det = h.get("detalle") or {}
        if h.get("estado") != "postulado" or not isinstance(det, dict) or not det.get("preguntas"):
            continue
        preguntas = det.get("preguntas") or []
        respuestas = det.get("respuestas") or {}
        pares = [{"pregunta": (q or "").strip(), "respuesta": str(respuestas.get(str(i), ""))}
                 for i, q in enumerate(preguntas)]
        items.append({"id": oid, "titulo": h.get("titulo"), "empresa": h.get("empresa"), "url": h.get("url"),
                      "fecha": h.get("fecha") or "", "respuestas": pares})
    items.sort(key=lambda x: x["fecha"], reverse=True)
    return items


def redirigir_salida():
    """Sin consola (pythonw), los print de los scripts (con emojis) fallan o se pierden: todo lo
    que se imprime va a datos/registros/app.log, en UTF-8. Se pisa en cada corrida."""
    salida = open(rutas.registros() / "app.log", "w", encoding="utf-8", errors="replace", buffering=1)
    sys.stdout = sys.stderr = salida


class Api:
    """Lo que la interfaz puede llamar con window.pywebview.api.<método>(...).
    Los atributos con _ no se exponen a la interfaz."""

    def __init__(self):
        self._ventana = None
        self._motor = None
        self._hilo = None

    def iniciar(self, plataforma):
        if self._motor and getattr(self._motor, "solo_cuenta", False) and self._hilo:
            self._hilo.join(timeout=15)          # recién se vinculó la cuenta: Edge se está cerrando
        if self._motor:
            return {"ok": False, "error": "Ya hay una plataforma en curso."}
        motor = MOTORES.get(plataforma)
        if not motor:
            return {"ok": False, "error": "Esa plataforma todavía no está en la app."}
        datos = perfil.cargar()
        faltan = [n for n, k in (("tu nombre", "nombre"), ("tu sueldo bruto", "sueldo"), ("tu zona", "zona")) if not datos.get(k)]
        if faltan:
            return {"ok": False, "error": f"Antes de empezar, completá {', '.join(faltan)} en Ajustes."}
        if not cuenta.leer(plataforma)["vinculada"]:
            return {"ok": False, "error": f"Primero vinculá tu cuenta de {motor.nombre} (botón de cuenta, al lado de Empezar)."}
        self._motor = motor(self._emitir)
        self._hilo = threading.Thread(target=self._motor.correr, daemon=True)
        self._hilo.start()
        return {"ok": True, "nombre": motor.nombre}

    # ------------------------------------------------------------ cuentas
    def cuentas(self):
        """Estado de la cuenta de cada bolsa: {plataforma: {vinculada, mail, fecha}}."""
        return {p: cuenta.leer(p) for p in MOTORES}

    def vincular(self, plataforma, reconectar=False):
        """Abre Edge para iniciar sesión en la bolsa y anota la cuenta. Con reconectar, antes borra la
        sesión guardada (para cuando no entra o querés usar otra cuenta). Termina con el evento
        cuenta_ok o cuenta_error."""
        if self._motor:
            return {"ok": False, "error": "Ya hay una plataforma en curso."}
        motor = MOTORES.get(plataforma)
        if not motor:
            return {"ok": False, "error": "Esa plataforma todavía no está en la app."}
        if reconectar and not cuenta.desvincular(plataforma):
            return {"ok": False, "error": "No pude borrar la sesión anterior: cerrá las ventanas de Edge de la app y probá de nuevo."}
        m = self._motor = motor(self._emitir, solo_cuenta=True)

        def correr():
            try:
                m.correr()
            finally:
                if self._motor is m:
                    self._motor = None
                    self._hilo = None
        self._hilo = threading.Thread(target=correr, daemon=True)
        self._hilo.start()
        return {"ok": True, "nombre": motor.nombre}

    def cerrar_sesion(self, plataforma):
        """Borra la sesión guardada de la bolsa (perfil de Edge). Historial, descartes y búsquedas quedan."""
        if self._motor:
            return {"ok": False, "error": "Volvé al menú antes de cerrar la sesión."}
        if plataforma not in MOTORES:
            return {"ok": False, "error": "Esa plataforma todavía no está en la app."}
        if not cuenta.desvincular(plataforma):
            return {"ok": False, "error": "No pude borrar la sesión: cerrá las ventanas de Edge de la app y probá de nuevo."}
        return {"ok": True}

    def detener(self):
        """Corta la plataforma en curso (cierra su Edge) para volver al menú."""
        if self._motor:
            self._motor.cancelado = True
            self._hilo.join(timeout=25)
            self._motor = None
            self._hilo = None
        return {"ok": True}

    def comando(self, nombre, datos=None):
        if self._motor:
            self._motor.enviar_comando(nombre, datos)

    def perfil(self):
        return perfil.cargar()

    def busqueda(self, plataforma):
        try:
            # también cuántos avisos descartaste (el menú dice "Los N avisos que descartaste se saltean solos")
            return {"ok": True, **busquedas.leer(plataforma), "descartados": len(descartes.Descartes(plataforma))}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def guardar_busqueda(self, plataforma, urls, inactivas=None):
        if self._motor:
            return {"ok": False, "error": "Volvé al menú antes de cambiar las búsquedas."}
        try:
            return busquedas.guardar(plataforma, urls, inactivas)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def filtros(self, plataforma):
        """Categorías, provincias y ciudades para armar la búsqueda desde listas (None si no hay)."""
        try:
            f = busquedas.filtros(plataforma)
            return f and {**f, "remoto": busquedas.REMOTO}
        except Exception:
            return None

    def armar_busqueda(self, plataforma, datos):
        try:
            return busquedas.armar(plataforma, datos or {})
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def verificar_busqueda(self, plataforma, url):
        """Prueba en la web un link pegado a mano (Búsquedas > Guardar): tiene que traer avisos."""
        if self._motor:
            return {"ok": False, "error": "Volvé al menú antes de cambiar las búsquedas."}
        try:
            return busquedas.probar(plataforma, url)
        except Exception as e:
            return {"ok": False, "error": f"No pude probar el link: {e}"}

    def postulaciones_con_respuestas(self, plataforma):
        """Historial (tecla H): avisos con formulario a los que te postulaste respondiendo las preguntas."""
        try:
            return {"ok": True, "items": historial_formularios(plataforma)}
        except Exception as e:
            return {"ok": False, "error": str(e), "items": []}

    def neto(self, bruto):
        return sueldo_neto.calcular(bruto)

    def guardar_perfil(self, datos):
        try:
            # El nombre se cambia desde Ajustes (además de Setup.exe y de importar).
            return {"ok": True, **perfil.guardar(datos.get("sueldo"), datos.get("zona"), datos.get("nombre"))}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ---- exportar / importar tus datos (nombre, sueldo, zona y avisos descartados)
    def _dialogo(self, tipo, **extra):
        r = self._ventana.create_file_dialog(tipo, file_types=("Datos de Postulá (*.json)", "Todos los archivos (*.*)"), **extra)
        if not r:
            return None
        return r if isinstance(r, str) else r[0]

    def exportar(self):
        try:
            nombre = perfil.cargar()["nombre"]
            sugerido = f"Postulá - datos de {nombre}.json" if nombre else "Postulá - mis datos.json"
            ruta = self._dialogo(webview.FileDialog.SAVE, save_filename=sugerido)
            if not ruta:
                return {"ok": False, "cancelado": True}
            if not ruta.lower().endswith(".json"):
                ruta += ".json"
            return datos_usuario.exportar(ruta)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def importar(self):
        if self._motor:
            return {"ok": False, "error": "Volvé al menú antes de importar."}
        try:
            ruta = self._dialogo(webview.FileDialog.OPEN)
            if not ruta:
                return {"ok": False, "cancelado": True}
            return datos_usuario.importar(ruta)
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            return {"ok": False, "error": f"No se pudo importar: {e}"}

    def descartados(self):
        """Ajustes > Avisos descartados: {plataforma: [avisos]} de las bolsas que tienen alguno."""
        try:
            return {"ok": True, "bolsas": {p: descartes.listar(p) for p in rutas.PLATAFORMAS if len(descartes.Descartes(p))}}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def recuperar_descartados(self, plataforma, ids):
        if self._motor:
            return {"ok": False, "error": "Volvé al menú antes de recuperar avisos."}
        try:
            return {"ok": True, "recuperados": descartes.recuperar(plataforma, ids)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def borrar_datos(self):
        """"Empezar de cero" (Ajustes). Solo desde el menú: con una plataforma corriendo, su Edge
        tiene abierta la sesión y no se podría borrar."""
        if self._motor:
            return {"ok": False, "error": "Volvé al menú antes de borrar los datos."}
        try:
            r = datos_usuario.borrar_todo()
            print(f"[borrar datos] borrados: {r['borrados']} | fallaron: {r['fallaron']}")
            return {**r, **perfil.cargar()}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ---- actualizaciones desde GitHub
    def buscar_actualizacion(self):
        try:
            return {"ok": True, **actualizar.buscar()}
        except Exception as e:
            print(f"[actualizar] {e}")
            return {"ok": False, "error": str(e)}

    def actualizar(self):
        if self._motor:
            return {"ok": False, "error": "Volvé al menú antes de actualizar."}
        try:
            return {"ok": True, **actualizar.actualizar()}
        except Exception as e:
            print(f"[actualizar] {e}")
            return {"ok": False, "error": str(e)}

    def reiniciar(self):
        """Abre la app de nuevo (ya actualizada) y cierra esta."""
        exe = actualizar.RAIZ / "Postulá.exe"
        orden = [str(exe)] if exe.exists() else [sys.executable, str(APP / "app.py")]
        subprocess.Popen(orden, cwd=str(APP), close_fds=True)
        self._ventana.destroy()

    def abrir_url(self, url):
        if str(url).startswith("https://"):
            webbrowser.open(url)

    def _emitir(self, tipo, datos=None):
        if tipo == "fatal":
            LOG.write_text((datos or {}).get("texto", ""), encoding="utf-8")
        try:
            self._ventana.evaluate_js(
                f"window.app && window.app.evento({json.dumps(tipo)}, {json.dumps(datos or {}, ensure_ascii=False)})")
        except Exception:
            pass

    def _cerrar(self):
        if self._motor:
            self._motor.cancelado = True
            self._hilo.join(timeout=20)


def identidad_windows():
    """Que Windows muestre la app como "Postulá" (con su logo) y no como Python: con un
    AppUserModelID propio, la barra de tareas no la agrupa con python/pythonw y usa el ícono
    de la ventana."""
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Postula.App")
    except Exception:
        pass


def main():
    redirigir_salida()
    identidad_windows()
    api = Api()
    ventana = webview.create_window(
        "Postulá", str(APP / "ui" / "index.html"), js_api=api,
        width=1280, height=820, min_size=(900, 600), background_color="#0e1116", maximized=True)
    api._ventana = ventana
    webview.start(icon=str(ICONO))   # ícono de la ventana y de la barra de tareas
    api._cerrar()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        LOG.write_text(traceback.format_exc(), encoding="utf-8")
        raise
