"""
Postulador automático para empleosit.com.ar (plataforma SmartJobBoard).

Uso:
    python postulador.py              -> corre normal
    python postulador.py --simular    -> lista los avisos, sin postularse
    python postulador.py --limite 5   -> como máximo 5 postulaciones sin preguntas

Flujo:
 1. Abre Edge con un perfil propio (perfil_edge). Si no hay sesión, iniciás sesión vos.
 2. Trae el listado (búsqueda de config.json, 100 por página).
 3. Fase 1: para cada aviso abre el formulario de postulación. Si NO tiene preguntas, lo envía.
    Si tiene preguntas, lo deja para el final.
 4. Fase 2: te pregunta si querés seguir con los que tienen preguntas; te las hace por consola,
    completa el formulario y lo envía.
Todo queda en historial.json. Ver CONTEXTO.md.
"""
import argparse
import json
import random
import re
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE.parent.parent / "comun"))   # módulos compartidos
sys.dont_write_bytecode = True
import descartes  # noqa: E402
import perfil  # noqa: E402
import rutas  # noqa: E402
DATOS = rutas.datos_bolsa("empleosit")   # datos/empleosit/: lo personal va separado del código
CONFIG_FILE = DATOS / "config.json"
HISTORIAL_FILE = DATOS / "historial.json"
PERFIL_DIR = DATOS / "perfil_edge"
SITIO = "https://www.empleosit.com.ar"
URL_FORM = SITIO + "/apply-now/?listing_id={lid}&ajaxRelocate=1"

DEFAULT_CONFIG = {
    "url_busqueda": SITIO + "/search-results-jobs/?action=search&view=list&listings_per_page=100"
                    "&Location_City%5Bmulti_like_and%5D%5B%5D=Ciudad%20Aut%C3%B3noma%20de%20Buenos%20Aires%20%28CABA%29",
    "salario_pretendido": 1800000,
    "pausa_min_seg": 4,
    "pausa_max_seg": 9,
    "max_postulaciones_por_corrida": 150,
    "max_paginas_listado": 30,
    "palabras_excluidas_titulo": [],
    "omitir_repetidos": True,
    "umbral_repetidos": 0.85,
}

PALABRAS_SALARIO = ("salari", "remuneraci", "sueldo", "pretensi", "pretendid")
ESTADOS_FINALES = ("postulado", "ya_postulado", "postulado_externo", "descartado", "repetido")
ESTADOS_POSTULADO = ("postulado", "ya_postulado", "postulado_externo")

# Envía el formulario igual que el botón "Enviar" de la web (que hace un POST AJAX y recibe JSON).
SUBMIT_JS = """async () => {
  const f = document.querySelector('#applyForm');
  const r = await fetch(f.action, {method: 'POST', body: new FormData(f), credentials: 'include'});
  return [r.status, await r.text()];
}"""

LEER_PREGUNTAS_JS = """() => {
  const ins = [...document.querySelectorAll('#applyForm input[name="QuestionAnswer[]"]')];
  return ins.map(i => {
    let t = '';
    const fld = i.closest('.inputField');
    let prev = fld ? fld.previousElementSibling : null;
    if (prev && prev.classList.contains('inputName')) t = prev.innerText.trim().replace(/:$/, '');
    return t;
  });
}"""


# ----------------------------------------------------------------- utilidades
def cargar_json(path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def guardar_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def pausa(cfg):
    time.sleep(random.uniform(cfg["pausa_min_seg"], cfg["pausa_max_seg"]))


def preguntar(texto, opciones_validas=None):
    while True:
        r = input(texto).strip()
        if opciones_validas is None or r.lower() in opciones_validas:
            return r
        print("  Respuesta no válida.")


# ----------------------------------------------------------------- repetidos (igual que Computrabajo)
def normalizar(t):
    t = unicodedata.normalize("NFKD", (t or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"\b(\w+)\s*/\s*(a|as|o|os)\b", r"\1", t)
    t = re.sub(r"\((a|as|o|os)\)", "", t)
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return " ".join(t.split())


def codigo_ref(titulo):
    m = re.search(r"\bref\.?\s*:?\s*(\d{3,})", (titulo or "").lower())
    return m.group(1) if m else None


def es_repetido(a, b, umbral):
    if normalizar(a.get("empresa")) != normalizar(b.get("empresa")):
        return False
    ra, rb = codigo_ref(a.get("titulo")), codigo_ref(b.get("titulo"))
    if ra and rb:
        return ra == rb
    ta, tb = set(normalizar(a.get("titulo")).split()), set(normalizar(b.get("titulo")).split())
    if not ta or not tb:
        return False
    return len(ta & tb) / len(ta | tb) >= umbral


def agrupar_repetidos(avisos, umbral):
    grupos = []
    for a in avisos:
        for g in grupos:
            if es_repetido(g[0], a, umbral):
                g.append(a)
                break
        else:
            grupos.append([a])
    return grupos


# ----------------------------------------------------------------- sitio
class EmpleosIT:
    def __init__(self, page):
        self.page = page

    def logueado(self):
        try:
            return self.page.locator("a[href*='logout']").count() > 0
        except Exception:
            return False

    def asegurar_login(self):
        self.page.goto(SITIO + "/my-account/", wait_until="domcontentloaded")
        if self.logueado():
            print("✅ Ya hay una sesión iniciada.")
            return
        # Sin sesión, /my-account/ ya redirige solo al login: si esa redirección pisa este goto,
        # Playwright tira ERR_ABORTED, pero la página igual termina en el login.
        if "/login" not in self.page.url:
            try:
                self.page.goto(SITIO + "/login/", wait_until="domcontentloaded")
            except Exception:
                pass
        print("👉 Iniciá sesión en la ventana de Edge que se abrió. Espero...")
        while not self.logueado():
            time.sleep(2)
        print("✅ Sesión detectada.")

    def mail(self):
        """Mail de la cuenta logueada: el campo email[original] de "Editar perfil". None si no aparece."""
        try:
            self.page.goto(SITIO + "/edit-profile/", wait_until="domcontentloaded")
            campo = self.page.locator('input[name="email[original]"]')
            return descartes.buscar_mail(campo.input_value() if campo.count() else "")
        except Exception:
            return None

    def listar(self, url, max_paginas):
        avisos, vistos = [], set()
        sep = "&" if "?" in url else "?"
        for n in range(1, max_paginas + 1):
            self.page.goto(f"{url}{sep}page={n}", wait_until="domcontentloaded")
            items = self.page.evaluate("""() => [...document.querySelectorAll('.listing-title a[href*="/display-job/"]')].map(a => {
                const box = a.closest('.listing-right') || a.closest('div');
                const emp = box ? box.querySelector('.company-ico a, .company-ico') : null;
                const loc = box ? box.querySelector('.location-ico') : null;
                const m = a.href.match(/display-job\\/(\\d+)/);
                return {id: m ? m[1] : null, titulo: a.innerText.trim(), url: a.href.split('?')[0],
                        empresa: emp ? emp.innerText.trim() : '', ubicacion: loc ? loc.innerText.trim() : ''};
            })""")
            nuevos = [i for i in items if i["id"] and i["id"] not in vistos]
            if not nuevos:
                break
            for i in nuevos:
                vistos.add(i["id"])
                avisos.append(i)
            print(f"   página {n}: {len(nuevos)} avisos")
            time.sleep(random.uniform(1.5, 3))
        return avisos

    def abrir_form(self, lid):
        """Abre el formulario. Devuelve la lista de preguntas ([] si no tiene) o None si no hay formulario."""
        self.page.goto(URL_FORM.format(lid=lid), wait_until="domcontentloaded", timeout=60000)
        if not self.page.locator("#applyForm").count():
            return None
        return self.page.evaluate(LEER_PREGUNTAS_JS)

    def enviar(self, respuestas=None):
        """Completa las respuestas (en orden) y envía. Devuelve (estado, detalle)."""
        if respuestas:
            campos = self.page.locator('#applyForm input[name="QuestionAnswer[]"]')
            for i, r in enumerate(respuestas):
                campos.nth(i).fill(r)
        status, texto = self.page.evaluate(SUBMIT_JS)
        try:
            d = json.loads(texto)
        except Exception:
            return "error", f"HTTP {status}: {texto[:200]}"
        if d.get("status") == "jobapplysuccess":
            if d.get("check_redirect_url"):
                return "postulado_externo", d["check_redirect_url"]
            return "postulado", None
        errores = d.get("errors") or {}
        if "APPLY_APPLIED_ERROR" in errores:
            return "ya_postulado", None
        return "error", errores or texto[:200]


# ----------------------------------------------------------------- formulario por consola
def completar_formulario(preguntas, salario):
    respuestas = []
    for n, q in enumerate(preguntas, 1):
        print(f"\n  [{n}/{len(preguntas)}] {q or '(pregunta sin texto)'}")
        es_sal = bool(salario) and any(w in (q or "").lower() for w in PALABRAS_SALARIO)
        extra = f" [Enter = {salario}]" if es_sal else ""
        r = ""
        while not r:
            r = input(f"  Tu respuesta{extra} (o 's' para saltear este aviso): ").strip()
            if not r and es_sal:
                r = str(salario)
        if r.lower() == "s":
            return None
        respuestas.append(r)
    return respuestas


def minimizar_ventana(page):
    """Minimiza la ventana de Edge (el script sigue funcionando con la ventana minimizada)."""
    try:
        cdp = page.context.new_cdp_session(page)
        wid = cdp.send("Browser.getWindowForTarget")["windowId"]
        cdp.send("Browser.setWindowBounds", {"windowId": wid, "bounds": {"windowState": "minimized"}})
    except Exception:
        pass


def esperar_enter():
    try:
        input("\nPresioná Enter para cerrar...")
    except (EOFError, KeyboardInterrupt):
        pass


def desactivar_modo_seleccion():
    """En Windows, un clic dentro de la consola activa el "modo selección" (QuickEdit), que congela
    el script hasta apretar Esc. Lo desactivamos para que un clic no lo pause."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        h = k32.GetStdHandle(-10)  # STD_INPUT_HANDLE
        modo = ctypes.c_uint32()
        if k32.GetConsoleMode(h, ctypes.byref(modo)):
            # quitar ENABLE_QUICK_EDIT_MODE (0x40); ENABLE_EXTENDED_FLAGS (0x80) es necesario para que aplique
            k32.SetConsoleMode(h, (modo.value & ~0x40) | 0x80)
    except Exception:
        pass


# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--simular", action="store_true", help="no se postula, solo lista")
    ap.add_argument("--limite", type=int, default=None, help="máx. postulaciones sin preguntas")
    args = ap.parse_args()

    cfg = {**DEFAULT_CONFIG, **cargar_json(CONFIG_FILE, {})}
    # El sueldo se toma del archivo "Sueldo bruto pretendido.txt" de la carpeta raíz (si existe).
    # El sueldo se toma de "Tus datos para los formularios" de la app (datos/perfil.json), si está.
    if perfil.cargar()["sueldo"]:
        cfg["salario_pretendido"] = perfil.cargar()["sueldo"]
    if not CONFIG_FILE.exists():
        guardar_json(CONFIG_FILE, cfg)
    limite = args.limite or cfg["max_postulaciones_por_corrida"]
    historial = cargar_json(HISTORIAL_FILE, {})
    desc = None   # descartes (datos/empleosit/descartes.json), se arma tras el login
    umbral = cfg["umbral_repetidos"]

    def registrar(aviso, estado, detalle=None):
        historial[aviso["id"]] = {
            "titulo": aviso.get("titulo"), "empresa": aviso.get("empresa"), "estado": estado,
            "detalle": detalle, "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "url": aviso.get("url"),
        }
        guardar_json(HISTORIAL_FILE, historial)
        if estado == "descartado" and desc is not None:
            desc.agregar(aviso)

    def repetido_de_postulado(aviso):
        if not cfg["omitir_repetidos"]:
            return None
        for oid, h in historial.items():
            if oid != aviso["id"] and h.get("estado") in ESTADOS_POSTULADO and es_repetido(h, aviso, umbral):
                return h
        return None

    def resultado(a, etiqueta, estado, detalle):
        if estado == "postulado":
            print(f"✅ {etiqueta}")
        elif estado == "postulado_externo":
            print(f"✅» {etiqueta}: postulado, pero la empresa pide completar en su sitio: {detalle}")
        elif estado == "ya_postulado":
            print(f"• {etiqueta}: ya estabas postulado.")
        else:
            print(f"❌ {etiqueta}: {detalle}")
        registrar(a, estado, detalle)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PERFIL_DIR), channel="msedge", headless=False, viewport={"width": 1200, "height": 800})
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.set_default_timeout(90000)   # el sitio a veces tarda más de 40 s por página
        sitio = EmpleosIT(page)

        sitio.asegurar_login()
        desc = descartes.iniciar("empleosit", sitio.mail(), CONFIG_FILE, historial)
        minimizar_ventana(page)
        print("   (Minimicé la ventana de Edge: dejala abierta, no la cierres.)")

        print("\n🔎 Recorriendo el listado...")
        avisos = sitio.listar(cfg["url_busqueda"], cfg["max_paginas_listado"])
        print(f"   {len(avisos)} avisos encontrados.")

        excl = [w.lower() for w in cfg["palabras_excluidas_titulo"]]
        pendientes, con_preguntas = [], []
        for a in avisos:
            h = historial.get(a["id"])
            if a["id"] in desc or (h and h["estado"] in ESTADOS_FINALES):
                continue
            if any(w in a["titulo"].lower() for w in excl):
                continue
            (con_preguntas if h and h["estado"] == "con_preguntas" else pendientes).append(a)
        print(f"   Pendientes: {len(pendientes)} por intentar, {len(con_preguntas)} ya detectados con preguntas.")
        print(f"   Ya procesados antes: {len(avisos) - len(pendientes) - len(con_preguntas)}")

        if not pendientes and not con_preguntas:
            print("\n🎉 No hay ofertas nuevas para postularte en esta búsqueda.")
            print(f"   De las {len(avisos)} ofertas encontradas, ya te postulaste, descartaste u omitiste todas.")
            print("   Volvé a correr el script más adelante para ver si aparecen nuevas.")
            ctx.close()
            return

        if args.simular:
            for a in pendientes:
                print(f"   [pendiente] {a['titulo']} — {a['empresa']}")
            for a in con_preguntas:
                print(f"   [preguntas] {a['titulo']} — {a['empresa']}")
            ctx.close()
            return

        # Fase 1
        enviados = 0
        for n, a in enumerate(pendientes, 1):
            if enviados >= limite:
                print(f"\nLlegué al límite de {limite} postulaciones.")
                break
            etiqueta = f"[{n}/{len(pendientes)}] {a['titulo']} — {a['empresa']}"
            orig = repetido_de_postulado(a)
            if orig:
                print(f"≈ {etiqueta}: repetido de uno al que ya te postulaste, salteado.")
                registrar(a, "repetido", {"de": orig.get("titulo")})
                continue
            preguntas = sitio.abrir_form(a["id"])
            if preguntas is None:
                print(f"❌ {etiqueta}: no apareció el formulario de postulación.")
                registrar(a, "error", "sin formulario")
                continue
            if preguntas:
                print(f"📝 {etiqueta}: tiene {len(preguntas)} pregunta/s, queda para el final.")
                registrar(a, "con_preguntas", {"preguntas": preguntas})
                con_preguntas.append(a)
                time.sleep(random.uniform(1, 2))
                continue
            estado, detalle = sitio.enviar()
            resultado(a, etiqueta, estado, detalle)
            if estado.startswith("postulado"):
                enviados += 1
            pausa(cfg)
        print(f"\nResumen fase 1: {enviados} postulaciones nuevas, {len(con_preguntas)} con preguntas.")

        # Fase 2
        restantes = []
        for a in con_preguntas:
            orig = repetido_de_postulado(a)
            if orig:
                registrar(a, "repetido", {"de": orig.get("titulo")})
            else:
                restantes.append(a)
        grupos = agrupar_repetidos(restantes, umbral) if cfg["omitir_repetidos"] else [[a] for a in restantes]

        def marcar_resto(grupo, elegido, estado):
            for otro in grupo:
                if otro is not elegido:
                    registrar(otro, estado, {"de": elegido.get("titulo")})

        if grupos:
            print(f"\n📝 Hay {len(grupos)} avisos con preguntas"
                  + (f" ({len(con_preguntas)} contando repetidos)." if len(grupos) < len(con_preguntas) else "."))
            if preguntar("¿Querés postularte a ellos ahora? (s/n): ", {"s", "n"}).lower() == "s":
                for n, grupo in enumerate(grupos, 1):
                    a = grupo[0]
                    print("\n" + "=" * 70)
                    extra = f"  (+{len(grupo) - 1} repetido/s)" if len(grupo) > 1 else ""
                    print(f"[{n}/{len(grupos)}] {a['titulo']} — {a['empresa']}{extra}")
                    print(f"   {a['url']}")
                    accion = preguntar("   ¿Postularte? (s = sí / n = no, no mostrarlo nunca más / q = terminar): ",
                                       {"s", "n", "q"}).lower()
                    if accion == "q":
                        break
                    if accion == "n":   # "no" = descartado para siempre (también sus repetidos)
                        registrar(a, "descartado")
                        marcar_resto(grupo, a, "descartado")
                        continue
                    preguntas = sitio.abrir_form(a["id"])
                    if preguntas is None:
                        print("   No apareció el formulario, salteo.")
                        continue
                    respuestas = completar_formulario(preguntas, cfg["salario_pretendido"]) if preguntas else []
                    if respuestas is None:
                        print("   Salteado.")
                        continue
                    estado, detalle = sitio.enviar(respuestas)
                    if estado.startswith("postulado"):
                        detalle = {"preguntas": preguntas, "respuestas": respuestas, "redirect": detalle}
                    resultado(a, "  ", estado, detalle)
                    if estado in ESTADOS_POSTULADO:
                        marcar_resto(grupo, a, "repetido")
                    pausa(cfg)

        print("\nListo. Historial en", HISTORIAL_FILE)
        ctx.close()


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    desactivar_modo_seleccion()
    try:
        main()
    except KeyboardInterrupt:
        print("\nCortado por el usuario.")
    except Exception:
        import traceback
        print("\n❌ Ocurrió un error inesperado:\n")
        traceback.print_exc()
    esperar_enter()
