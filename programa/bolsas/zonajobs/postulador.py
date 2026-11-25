"""
Postulador automático para ZonaJobs (misma plataforma que Bumeran, sitio ZJAR).

Uso:
    python postulador.py              -> corre normal
    python postulador.py --simular    -> lista lo que haría, sin postularse
    python postulador.py --limite 5   -> se postula como máximo a 5 avisos sin formulario

Flujo:
 1. Abre Edge con un perfil propio (carpeta perfil_edge). Si no hay sesión, iniciás sesión vos
    en la ventana y el script lo detecta solo. La sesión queda guardada para la próxima.
 2. Carga la URL de búsqueda de config.json y toma los mismos filtros que usa la web.
 3. Trae todos los avisos (todas las páginas).
 4. Se postula a los que NO tienen preguntas ni salario obligatorio.
 5. Al final te pregunta si querés seguir con los que tienen formulario y te hace las preguntas
    por consola.
Todo queda registrado en historial.json para no repetir postulaciones.
"""
import argparse
import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE.parent.parent / "comun"))   # módulos compartidos
sys.dont_write_bytecode = True
import descartes  # noqa: E402
import perfil  # noqa: E402
import rutas  # noqa: E402
DATOS = rutas.datos_bolsa("zonajobs")   # datos/zonajobs/: lo personal va separado del código
CONFIG_FILE = DATOS / "config.json"
HISTORIAL_FILE = DATOS / "historial.json"
PERFIL_DIR = DATOS / "perfil_edge"
SITIO = "https://www.zonajobs.com.ar"
SITE_ID = "ZJAR"
PORTAL_PROPIO = "zonajobs"
HISTORIAL_BUMERAN = rutas.datos_bolsa("bumeran") / "historial.json"

DEFAULT_CONFIG = {
    "url_busqueda": SITIO + "/en-buenos-aires/capital-federal/empleos-area-tecnologia-sistemas-y-telecomunicaciones.html",
    "salario_pretendido": 1800000,
    "pausa_min_seg": 4,
    "pausa_max_seg": 9,
    "max_postulaciones_por_corrida": 150,
    "palabras_excluidas_titulo": [],
    # Omite avisos que son el mismo puesto (mismo título y empresa) que uno al que ya te
    # postulaste por Bumeran con el otro script.
    "omitir_duplicados_de_bumeran": False,
}

# Hace un fetch desde la página, con los mismos encabezados que usa la web.
FETCH_JS = """async ([path, method, body]) => {
  const h = {'x-site-id': '__SITE_ID__', 'Content-Type': 'application/json'};
  const tok = localStorage.getItem('token');
  const jwt = localStorage.getItem('sessionJwt');
  if (tok) h['Authorization'] = 'Bearer ' + tok;
  if (jwt) h['x-session-jwt'] = jwt;
  const r = await fetch(path, {method, headers: h, credentials: 'include',
                               body: body === null ? undefined : JSON.stringify(body)});
  const nuevoJwt = r.headers.get('x-session-jwt');
  if (nuevoJwt) localStorage.setItem('sessionJwt', nuevoJwt);
  return [r.status, await r.text()];
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


class Portal:
    def __init__(self, page):
        self.page = page

    def api(self, path, method="GET", body=None, intentos=3, navegar=True):
        """Llama a la API desde la página. Reintenta si falla la red ("Failed to fetch") o si la
        página estaba navegando justo en ese momento."""
        js = FETCH_JS.replace("__SITE_ID__", SITE_ID)
        for intento in range(1, intentos + 1):
            try:
                if navegar and not self.page.url.startswith(SITIO):
                    self.page.goto(SITIO + "/", wait_until="domcontentloaded")
                status, text = self.page.evaluate(js, [path, method, body])
                break
            except Exception as e:
                if intento == intentos:
                    raise
                print(f"   (falló la conexión con el sitio, reintento {intento}/{intentos - 1}: {str(e).splitlines()[0][:80]})")
                time.sleep(3 * intento)
        try:
            data = json.loads(text) if text else None
        except json.JSONDecodeError:
            data = text
        return status, data

    def logueado(self):
        """Sesión real: existe la cookie de sesión Y la API devuelve tus datos de candidato."""
        try:
            cookies = self.page.context.cookies(SITIO)
            if not any(c["name"] == "token_auth_postulante" and c["value"] for c in cookies):
                return False
            # sin navegar ni reintentar: mientras te logueás la página puede estar en otro sitio (ej. Google)
            if not self.page.url.startswith(SITIO):
                return False
            status, datos = self.api("/api/candidates/datosPostulanteResumido", intentos=1, navegar=False)
            return status == 200 and isinstance(datos, dict) and bool(datos)
        except Exception:
            return False

    def filtros_de_url(self, url):
        """Abre la URL del listado y captura el body de búsqueda que arma la propia web."""
        with self.page.expect_request(lambda r: "api/avisos/searchV2" in r.url, timeout=60000) as req:
            self.page.goto(url, wait_until="domcontentloaded")
        return json.loads(req.value.post_data)

    def buscar_todos(self, body):
        avisos, pagina = [], 0
        while True:
            st, d = self.api(f"/api/avisos/searchV2?pageSize=100&page={pagina}&sort=RECIENTES", "POST", body)
            if st != 200 or not isinstance(d, dict):
                raise RuntimeError(f"Error en búsqueda (HTTP {st}): {str(d)[:200]}")
            contenido = d.get("content") or []
            avisos.extend(contenido)
            if not contenido or len(avisos) >= d.get("total", 0):
                break
            pagina += 1
            time.sleep(1.5)
        # sin duplicados
        vistos, unicos = set(), []
        for a in avisos:
            if a["id"] not in vistos:
                vistos.add(a["id"])
                unicos.append(a)
        return unicos

    def ids_ya_postulados(self, al_avanzar=None):
        """IDs de avisos a los que ya te postulaste (sección 'Mis postulaciones').
        La API devuelve como máximo 30 por página y tarda unos 5 s en cada una, así que después de
        la primera (que dice el 'total') se piden las demás todas juntas, de a tandas de 8.
        al_avanzar(leidas, total) se llama después de cada tanda."""
        ruta = "/api/candidates/postulaciones?pageSize=30&page={}&sort=fechaPostulacion"
        try:
            st, d = self.api(ruta.format(0))
        except Exception:
            print("   (no pude leer 'Mis postulaciones'; sigo igual, uso el estado que trae cada aviso)")
            return set()
        if st != 200 or not isinstance(d, dict):
            return set()
        contenido = d.get("content") or []
        ids = {x.get("avisoId") for x in contenido}
        total = d.get("total") or 0
        tam = len(contenido) or 30
        paginas = list(range(1, min(200, -(-total // tam))))
        if al_avanzar:
            al_avanzar(len(contenido), total)
        js = "async (rutas) => { const f = " + FETCH_JS + "; return await Promise.all(rutas.map(r => f([r, 'GET', null]))); }"
        for i in range(0, len(paginas), 8):
            tanda = [ruta.format(n) for n in paginas[i:i + 8]]
            try:
                respuestas = self.page.evaluate(js, tanda)
            except Exception as e:
                print(f"   (no pude leer parte de 'Mis postulaciones': {str(e).splitlines()[0][:80]})")
                break
            for st, texto in respuestas:
                try:
                    pag = json.loads(texto) if st == 200 and texto else {}
                except json.JSONDecodeError:
                    pag = {}
                ids.update(x.get("avisoId") for x in (pag.get("content") or []))
            if al_avanzar:
                al_avanzar(min(total, tam * (paginas[min(i + 8, len(paginas)) - 1] + 1)), total)
        ids.discard(None)
        return ids

    def ficha(self, id_aviso):
        """Ficha del aviso. Si ya estás postulado, '_postulacion' trae fecha/estado de esa postulación."""
        st, d = self.api(f"/api/candidates/fichaAvisoNormalizada/{id_aviso}")
        if st != 200 or not isinstance(d, dict) or not d.get("aviso"):
            return None
        aviso = d["aviso"]
        # Ojo: si NO estás postulado, "postulacion" igual viene, pero con todos los campos en null.
        post = d.get("postulacion") or {}
        aviso["_postulacion"] = post if (post.get("idPostulacion") or post.get("estado")) else None
        return aviso

    def postular(self, id_aviso, salario=None):
        body = {"salarioPretendido": salario, "actualizarSalario": False, "utmOrigen": None,
                "preguntasObligatorias": False, "feria": False, "origenPostulacion": None}
        return self.api(f"/api/candidates/aviso/{id_aviso}/postularV2", "POST", body)

    def responder(self, id_postulacion, respuestas):
        return self.api(f"/api/candidates/aviso/{id_postulacion}/respuestas", "POST", respuestas)


# Valores de "origenAviso" que indican que el aviso es de OTRO portal del grupo. Otros valores, como
# "PORTAL" o "HIRING_ROOM" (avisos publicados desde el sistema de selección HiringRoom), se postulan
# normalmente desde este sitio (verificado 21-11-2026).
ORIGENES_OTRO_PORTAL = {"ZONAJOBS", "BUMERAN"} - {"ZONAJOBS"}


def es_externo(ficha):
    """True si el aviso deriva a otro sitio (redireccionURL) o pertenece a otro portal del grupo."""
    origen = (ficha.get("origenAviso") or "PORTAL").upper()
    return bool(ficha.get("redireccionURL")) or origen in ORIGENES_OTRO_PORTAL


def normalizar(t):
    import unicodedata
    t = unicodedata.normalize("NFKD", (t or "").lower())
    return " ".join("".join(c for c in t if c.isalnum() or c.isspace()).split())


def clave(aviso):
    return (normalizar(aviso.get("titulo")), normalizar(aviso.get("empresa")))


def claves_bumeran():
    """Título+empresa de los avisos a los que ya te postulaste con el script de Bumeran."""
    if not HISTORIAL_BUMERAN.exists():
        return set()
    h = json.loads(HISTORIAL_BUMERAN.read_text(encoding="utf-8"))
    return {clave(v) for v in h.values() if v.get("estado") in ("postulado", "ya_postulado", "postulado_sin_respuestas")}


def id_postulacion_de(resp):
    if isinstance(resp, dict):
        for k in ("idPostulacion", "postulacionId", "id"):
            if resp.get(k):
                return resp[k]
    return None


def postulacion_ok(status):
    return 200 <= status < 300


# ----------------------------------------------------------------- formularios
def texto_opcion(o):
    if isinstance(o, dict):
        for k in ("opcion", "texto", "label", "valor", "value", "descripcion", "nombre"):
            if o.get(k) not in (None, ""):
                return str(o[k])
        return json.dumps(o, ensure_ascii=False)
    return str(o)


def valor_opcion(o):
    if isinstance(o, dict):
        for k in ("id", "value", "valor"):
            if o.get(k) is not None:
                return str(o[k])
    return str(o)


PALABRAS_SALARIO = ("salari", "remuneraci", "sueldo", "pretensi", "pretendid")


def completar_formulario(preguntas, salario=None):
    """Hace cada pregunta por consola. Devuelve la lista de respuestas, o None si se saltea."""
    respuestas = []
    for i, p in enumerate(preguntas, 1):
        if "simple" in p and p["simple"]:
            q = p["simple"]
            print(f"\n  [{i}/{len(preguntas)}] {q['texto'].strip()}")
            es_salario = bool(salario) and any(w in q["texto"].lower() for w in PALABRAS_SALARIO)
            extra = f" [Enter = {salario}]" if es_salario else ""
            r = ""
            while not r:
                r = input(f"  Tu respuesta{extra} (o 's' para saltear este aviso): ").strip()
                if not r and es_salario:
                    r = str(salario)
            if r.lower() == "s":
                return None
            respuestas.append({"preguntaId": str(q["id"]), "respuesta": r[:2000]})
        elif "choice" in p and p["choice"]:
            q = p["choice"]
            opciones = q.get("opciones") or []
            print(f"\n  [{i}/{len(preguntas)}] {q['texto'].strip()}")
            for n, o in enumerate(opciones, 1):
                print(f"     {n}) {texto_opcion(o)}")
            validas = {str(n) for n in range(1, len(opciones) + 1)} | {"s"}
            r = preguntar("  Elegí el número (o 's' para saltear este aviso): ", validas)
            if r.lower() == "s":
                return None
            respuestas.append({"preguntaId": str(q["id"]), "respuesta": valor_opcion(opciones[int(r) - 1])})
        else:
            print(f"\n  ⚠ Tipo de pregunta desconocido: {json.dumps(p, ensure_ascii=False)[:300]}")
            return None
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
    ap.add_argument("--simular", action="store_true", help="no se postula, solo muestra")
    ap.add_argument("--limite", type=int, default=None, help="máx. postulaciones sin formulario")
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
    desc = None   # descartes (datos/zonajobs/descartes.json), se arma tras el login

    def registrar(aviso, estado, detalle=None):
        historial[str(aviso["id"])] = {
            "titulo": aviso.get("titulo"), "empresa": aviso.get("empresa"), "estado": estado,
            "detalle": detalle, "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "url": f"{SITIO}/empleos/{aviso['id']}.html",
        }
        guardar_json(HISTORIAL_FILE, historial)
        if estado == "descartado" and desc is not None:
            desc.agregar(aviso, url=f"{SITIO}/empleos/{aviso['id']}.html")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PERFIL_DIR), channel="msedge", headless=False, viewport={"width": 1200, "height": 800})
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        bm = Portal(page)

        # 1) login
        page.goto(SITIO + "/", wait_until="domcontentloaded")
        if not bm.logueado():
            page.goto(SITIO + "/login", wait_until="domcontentloaded")
            print("👉 Iniciá sesión en la ventana de Edge que se abrió. Espero...")
            while not bm.logueado():
                time.sleep(2)
            print("✅ Sesión detectada.")
        else:
            print("✅ Ya hay una sesión iniciada.")
        try:
            _, datos = bm.api("/api/candidates/datosPostulanteResumido")
        except Exception:
            datos = None
        desc = descartes.iniciar("zonajobs", descartes.buscar_mail(datos, excluir=("zonajobs.com.ar", "zonajobs.com")),
                                 CONFIG_FILE, historial)
        minimizar_ventana(page)
        print("   (Minimicé la ventana de Edge: dejala abierta, no la cierres.)")

        # 2) búsqueda
        print("\n🔎 Leyendo filtros de búsqueda...")
        body = bm.filtros_de_url(cfg["url_busqueda"])
        avisos = bm.buscar_todos(body)
        print(f"   {len(avisos)} avisos encontrados.")

        ya = bm.ids_ya_postulados()
        print(f"   Ya postulado (según el listado): {sum(1 for a in avisos if a.get('estadoPostulacion'))} de estos avisos.")
        excl = [w.lower() for w in cfg["palabras_excluidas_titulo"]]
        pendientes = []
        externos = [a for a in avisos if (a.get("portal") or "").lower() != PORTAL_PROPIO]
        if externos:
            print(f"   Omitidos {len(externos)} avisos de otros portales (Bumeran, etc.).")
        dup_bum = claves_bumeran() if cfg["omitir_duplicados_de_bumeran"] else set()
        n_dup = 0
        for a in avisos:
            # "estadoPostulacion" viene en el listado cuando hay sesión (p. ej. "REALIZADA").
            # "Mis postulaciones" (ya) sirve de respaldo, pero esa API devuelve como máximo 250.
            if a in externos or a["id"] in ya or a.get("estadoPostulacion"):
                continue
            if clave(a) in dup_bum:
                n_dup += 1
                continue
            h = historial.get(str(a["id"]))
            if a["id"] in desc or h and h["estado"] in ("postulado", "ya_postulado", "externo", "descartado"):
                continue
            if any(w in (a.get("titulo") or "").lower() for w in excl):
                continue
            pendientes.append(a)

        if n_dup:
            print(f"   Omitidos {n_dup} duplicados de avisos a los que ya te postulaste por Bumeran.")

        def necesita_form(a):
            return bool(a.get("tienePreguntas")) or (bool(a.get("salarioObligatorio")) and not cfg["salario_pretendido"])
        sin_form = [a for a in pendientes if not necesita_form(a)]
        con_form = [a for a in pendientes if necesita_form(a)]
        print(f"   Pendientes: {len(sin_form)} sin formulario, {len(con_form)} con formulario/salario.")
        print(f"   Ya postulados o procesados antes (de ZonaJobs): {len(avisos) - len(externos) - n_dup - len(pendientes)}")

        if not sin_form and not con_form:
            print("\n🎉 No hay ofertas nuevas para postularte en esta búsqueda.")
            print(f"   De las {len(avisos)} ofertas encontradas, ya te postulaste, descartaste u omitiste todas.")
            print("   Volvé a correr el script más adelante para ver si aparecen nuevas.")
            ctx.close()
            return

        if args.simular:
            for a in sin_form:
                print(f"   [sin form] {a['titulo']} — {a['empresa']}")
            for a in con_form:
                print(f"   [con form] {a['titulo']} — {a['empresa']}")
            ctx.close()
            return

        # 3) postulaciones sin formulario
        ok = err = 0
        for n, a in enumerate(sin_form[:limite], 1):
            etiqueta = f"[{n}/{min(len(sin_form), limite)}] {a['titulo']} — {a['empresa']}"
            ficha = bm.ficha(a["id"])
            if ficha and ficha.get("_postulacion"):
                print(f"• {etiqueta}: ya estabas postulado ({ficha['_postulacion'].get('fecha', '')}).")
                registrar(a, "ya_postulado", ficha["_postulacion"])
                continue
            if ficha and es_externo(ficha):
                print(f"» {etiqueta}: se postula en sitio externo, salteado.")
                registrar(a, "externo", ficha.get("redireccionURL") or ficha.get("origenAviso"))
                continue
            if ficha and ficha.get("preguntas"):
                con_form.append(a)
                continue
            st, resp = bm.postular(a["id"], cfg["salario_pretendido"])
            if postulacion_ok(st):
                ok += 1
                print(f"✅ {etiqueta}")
                registrar(a, "postulado", resp)
            else:
                texto = json.dumps(resp, ensure_ascii=False) if not isinstance(resp, str) else resp
                if "postulad" in texto.lower():
                    print(f"• {etiqueta}: ya estabas postulado.")
                    registrar(a, "ya_postulado", resp)
                else:
                    err += 1
                    print(f"❌ {etiqueta}: HTTP {st} {texto[:200]}")
                    registrar(a, "error", {"status": st, "resp": resp})
                if st in (401, 403):
                    print("⚠ La sesión parece haber expirado o hubo un bloqueo. Corto acá.")
                    break
                if st == 429:
                    print("⚠ Demasiadas peticiones. Espero 2 minutos...")
                    time.sleep(120)
            pausa(cfg)
        print(f"\nResumen: {ok} postulaciones OK, {err} errores.")

        # 4) con formulario
        if con_form:
            print(f"\n📝 Hay {len(con_form)} avisos con formulario o salario obligatorio.")
            if preguntar("¿Querés postularte a ellos ahora? (s/n): ", {"s", "n"}).lower() == "s":
                salario = cfg["salario_pretendido"]
                for n, a in enumerate(con_form, 1):
                    print("\n" + "=" * 70)
                    print(f"[{n}/{len(con_form)}] {a['titulo']} — {a['empresa']}")
                    print(f"   {SITIO}/empleos/{a['id']}.html")
                    ficha = bm.ficha(a["id"])
                    if not ficha:
                        print("   No pude cargar la ficha, salteo.")
                        continue
                    if ficha.get("_postulacion"):
                        print(f"   Ya estabas postulado ({ficha['_postulacion'].get('fecha', '')}), salteo.")
                        registrar(a, "ya_postulado", ficha["_postulacion"])
                        continue
                    if es_externo(ficha):
                        print("   Se postula en sitio externo, salteo.")
                        registrar(a, "externo", ficha.get("redireccionURL") or ficha.get("origenAviso"))
                        continue
                    accion = preguntar("   ¿Postularte? (s = sí / n = no, no mostrarlo nunca más / q = terminar): ",
                                       {"s", "n", "q"}).lower()
                    if accion == "q":
                        break
                    if accion == "n":   # "no" = descartado para siempre
                        registrar(a, "descartado")
                        continue

                    if a.get("salarioObligatorio") and not salario:
                        r = ""
                        while not r.isdigit():
                            r = input("   Salario bruto pretendido (solo números, se reutiliza): ").strip()
                        salario = int(r)

                    respuestas = []
                    if ficha.get("preguntas"):
                        respuestas = completar_formulario(ficha["preguntas"], salario)
                        if respuestas is None:
                            print("   Salteado.")
                            continue

                    st, resp = bm.postular(a["id"], salario)
                    if not postulacion_ok(st):
                        print(f"   ❌ Error al postular: HTTP {st} {str(resp)[:200]}")
                        registrar(a, "error", {"status": st, "resp": resp})
                        continue
                    if respuestas:
                        idp = id_postulacion_de(resp) or a["id"]
                        st2, resp2 = bm.responder(idp, respuestas)
                        if not postulacion_ok(st2):
                            print(f"   ⚠ Postulado, pero falló el envío de respuestas: HTTP {st2} {str(resp2)[:200]}")
                            print("     Respondelas desde 'Mis postulaciones' en la web.")
                            registrar(a, "postulado_sin_respuestas", {"postular": resp, "respuestas": resp2})
                            continue
                    print("   ✅ Postulado.")
                    registrar(a, "postulado", {"respuestas": respuestas, "resp": resp})
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
