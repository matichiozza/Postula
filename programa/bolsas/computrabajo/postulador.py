"""
Postulador automático para Computrabajo Argentina.

Uso:
    python postulador.py              -> corre normal
    python postulador.py --simular    -> lista los avisos, sin postularse
    python postulador.py --limite 5   -> intenta como máximo 5 avisos en la fase 1

Computrabajo NO tiene una API JSON como Bumeran/ZonaJobs: todo es HTML (ASP.NET) y se maneja
navegando con Edge. Ver CONTEXTO.md.

Flujo:
 1. Abre Edge con un perfil propio (perfil_edge). Si no hay sesión, iniciás sesión vos y el
    script lo detecta. La sesión queda guardada.
 2. Recorre todas las páginas del listado de config.json y junta los avisos.
 3. Fase 1: abre el link de postulación de cada aviso.
      - Sin preguntas -> Computrabajo postula directo ("Te postulaste correctamente").
      - Con preguntas -> aparece el formulario de "Preguntas de selección": NO se envía nada,
        el aviso queda para el final.
 4. Fase 2: te pregunta si querés seguir con los que tienen preguntas, te las hace por consola,
    completa el formulario y lo envía.
Todo queda en historial.json para no repetir.
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

DATOS = rutas.datos_bolsa("computrabajo")   # datos/computrabajo/: lo personal va separado del código
CONFIG_FILE = DATOS / "config.json"
HISTORIAL_FILE = DATOS / "historial.json"
PERFIL_DIR = DATOS / "perfil_edge"
SITIO = "https://ar.computrabajo.com"
CANDIDATO = "https://candidato.ar.computrabajo.com"
URL_POSTULAR = CANDIDATO + "/match/?oi={oi}&p=57&idb=1&d=32"

DEFAULT_CONFIG = {
    "url_busqueda": SITIO + "/empleos-de-informatica-y-telecom-en-capital-federal",
    "salario_pretendido": None,
    "pausa_min_seg": 2,
    "pausa_max_seg": 4,
    "max_postulaciones_por_corrida": 150,
    "max_paginas_listado": 50,
    "palabras_excluidas_titulo": [],
    # Repetidos: misma empresa y (mismo "Ref. NNNN" o títulos con casi las mismas palabras).
    "omitir_repetidos": True,
    "umbral_repetidos": 0.85,
}

PALABRAS_SALARIO = ("salari", "remuneraci", "sueldo", "pretensi", "pretendid")
ESTADOS_FINALES = ("postulado", "ya_postulado", "externo", "descartado", "repetido")
ESTADOS_POSTULADO = ("postulado", "ya_postulado")


# ----------------------------------------------------------------- repetidos
def normalizar(t):
    t = unicodedata.normalize("NFKD", (t or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"\b(\w+)\s*/\s*(a|as|o|os)\b", r"\1", t)   # consultor/a -> consultor
    t = re.sub(r"\((a|as|o|os)\)", "", t)                   # desarrollador(a) -> desarrollador
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return " ".join(t.split())


def codigo_ref(titulo):
    m = re.search(r"\bref\.?\s*:?\s*(\d{3,})", (titulo or "").lower())
    return m.group(1) if m else None


def es_repetido(a, b, umbral):
    """Misma empresa y: mismo código 'Ref. NNNN', o títulos con casi las mismas palabras
    (índice de Jaccard >= umbral). Comparar palabras (y no letras) evita confundir, por
    ejemplo, 'Consultor SAP SD' con 'Consultor SAP TD'."""
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


def texto_pagina(page):
    try:
        return re.sub(r"\s+", " ", page.inner_text("body"))
    except Exception:
        return ""


# ----------------------------------------------------------------- Computrabajo
# Lee en paralelo varias páginas de "Mis postulaciones". Por página: lista de avisos, o null si falló
# (error HTTP o la sesión no llevó a la lista).
MIS_POSTULACIONES_JS = """async (paginas) => Promise.all(paginas.map(async (n) => {
    try {
        const res = await fetch('/candidate/match?p=' + n, {credentials: 'include'});
        if (!res.ok || !new URL(res.url).pathname.startsWith('/candidate/match')) return null;
        const d = new DOMParser().parseFromString(await res.text(), 'text/html');
        const texto = (e) => (e ? e.textContent : '').replace(/\\s+/g, ' ').trim();
        return [...d.querySelectorAll('[data-match]')].map((it) => {
            const ver = it.querySelector('[data-shortcut-see-offer]');
            const url = ver ? ver.getAttribute('data-shortcut-see-offer').split(/[#?]/)[0] : '';
            const id = (url.match(/[0-9A-F]{32}$/i) || [''])[0].toUpperCase();
            const emp = it.querySelector('h1 ~ p');
            // la empresa es el texto suelto del primer párrafo (después vienen las estrellas)
            const suelto = emp && [...emp.childNodes].find((c) => c.nodeType === 3 && c.textContent.trim());
            return {id, url, titulo: texto(it.querySelector('h1')), empresa: texto(suelto || (emp && emp.querySelector('a')))};
        }).filter((x) => x.id);
    } catch (e) {
        return null;
    }
}))"""


class Computrabajo:
    def __init__(self, page):
        self.page = page

    def en_area_candidato(self):
        """True si la página actual es el área privada del candidato (o sea, hay sesión).
        Ojo: la cookie de sesión de candidato no sobrevive al cerrar Edge, pero Computrabajo
        re-loguea solo con la cookie del servidor de login (secure.computrabajo.com)."""
        try:
            url = self.page.url
        except Exception:
            return False
        return url.startswith(CANDIDATO + "/candidate/")

    def asegurar_login(self):
        self.page.goto(CANDIDATO + "/candidate/home", wait_until="domcontentloaded")
        if self.en_area_candidato():
            print("✅ Ya hay una sesión iniciada.")
            return
        print("👉 Iniciá sesión en la ventana de Edge que se abrió. Espero...")
        while not self.en_area_candidato():
            # wait_for_timeout (y no time.sleep): así Playwright actualiza page.url mientras esperamos
            self.page.wait_for_timeout(2000)
            # Tras el login, Computrabajo puede dejarte en su portada y no en el área de candidato:
            # si ya saliste de la página de login, se abre /candidate/home para confirmar la sesión.
            host = self.page.url.split("/")[2] if self.page.url.count("/") >= 2 else ""
            if host in ("ar.computrabajo.com", "candidato.ar.computrabajo.com") and not self.en_area_candidato():
                try:
                    self.page.goto(CANDIDATO + "/candidate/home", wait_until="domcontentloaded")
                except Exception:
                    pass
        print("✅ Sesión detectada.")

    def mail(self):
        """Mail de la cuenta logueada, leído de la página "Configuración". None si no aparece."""
        try:
            self.page.goto(CANDIDATO + "/configuration", wait_until="domcontentloaded")
            return descartes.buscar_mail(self.page.content(), excluir=("computrabajo.com", "redarbor.net"))
        except Exception:
            return None

    def mis_postulaciones(self, al_avanzar=None, max_paginas=300):
        """Todo lo que figura en "Mis postulaciones" (/candidate/match): {id del aviso: {titulo,
        empresa, url}}. SOLO LEE: pide las páginas con fetch, no hace clic en nada (cada ítem tiene
        un "Eliminar la postulación"). -> (postulaciones, completo)."""
        if not self.page.url.startswith(CANDIDATO + "/"):
            self.page.goto(CANDIDATO + "/candidate/match", wait_until="domcontentloaded")
        todas, pagina, completo = {}, 1, True
        while pagina <= max_paginas:
            numeros = list(range(pagina, pagina + 4))
            resultados = self.page.evaluate(MIS_POSTULACIONES_JS, numeros)
            hay_nuevas = False
            for n, r in zip(numeros, resultados):
                if r is None:                       # esa página falló: se reintenta una vez
                    r = self.page.evaluate(MIS_POSTULACIONES_JS, [n])[0]
                if r is None:
                    completo = False
                    continue
                for it in r:
                    if it["id"] not in todas:
                        hay_nuevas = True
                        todas[it["id"]] = {k: it[k] for k in ("titulo", "empresa", "url")}
            if al_avanzar:
                al_avanzar(len(todas))
            if not hay_nuevas:                      # se terminaron las páginas (o no se pueden leer)
                break
            pagina += 4
        return todas, completo

    def listar(self, url, max_paginas, al_avanzar=None, esperar=time.sleep):
        """Recorre el listado página por página (?p=N) y devuelve los avisos.
        al_avanzar(pagina, avisos_hasta_ahora) y esperar(segundos) los usa la app para mostrar el
        avance y seguir atendiendo la interfaz entre página y página."""
        avisos, vistos = [], set()
        sep = "&" if "?" in url else "?"
        for n in range(1, max_paginas + 1):
            destino = url if n == 1 else f"{url}{sep}p={n}"
            try:
                self.page.goto(destino, wait_until="domcontentloaded")
            except Exception as e:
                # a veces la carga se corta (net::ERR_ABORTED) porque el sitio recarga solo: un reintento
                if "ERR_ABORTED" not in str(e):
                    raise
                self.page.wait_for_timeout(1500)
                self.page.goto(destino, wait_until="domcontentloaded")
            items = self.page.evaluate("""() => [...document.querySelectorAll('article.box_offer')].map(a => {
                const link = a.querySelector('h2 a');
                const emp = a.querySelector('[offer-grid-article-company-url]');
                const ps = [...a.querySelectorAll('p')].map(p => p.innerText.trim());
                return {id: a.dataset.id, titulo: link ? link.innerText.trim() : '',
                        url: link ? link.href.split('#')[0] : '',
                        empresa: emp ? emp.innerText.trim() : (ps[0] || ''),
                        ubicacion: ps[1] || '',
                        fecha: ((a.querySelector('p.fc_aux') || {}).textContent || '').trim()};
            })""")
            nuevos = [i for i in items if i["id"] and i["id"] not in vistos]
            if not nuevos:
                break
            for i in nuevos:
                vistos.add(i["id"])
                avisos.append(i)
            print(f"   página {n}: {len(nuevos)} avisos")
            if al_avanzar:
                al_avanzar(n, len(avisos))
            esperar(random.uniform(1.5, 3))
        return avisos

    def abrir_postulacion(self, oi):
        """Abre el link de postulación y clasifica dónde terminó.
        Devuelve: 'postulado' | 'ya_postulado' | 'preguntas' | 'externo' | 'desconocido'."""
        self.page.goto(URL_POSTULAR.format(oi=oi), wait_until="domcontentloaded", timeout=60000)
        # Se clasifica apenas aparece un resultado claro (antes se esperaba a que la página dejara
        # de cargar todo, hasta 15 s). Si no aparece ninguno, se espera hasta 15 s como antes.
        limite = time.time() + 15
        while True:
            res = self._resultado_postulacion()
            if res != "desconocido" or time.time() > limite:
                return res
            self.page.wait_for_timeout(300)

    def _resultado_postulacion(self):
        url = self.page.url
        txt = texto_pagina(self.page)
        if "/candidate/postapply" in url or "Te postulaste correctamente" in txt:
            return "postulado"
        if "Ya te postulaste" in txt:
            return "ya_postulado"
        if "/candidate/kq" in url and self.page.locator('form[action*="/candidate/kq"]').count():
            return "preguntas"
        if not url.startswith(CANDIDATO) and "computrabajo.com" not in url:
            return "externo"
        return "desconocido"

    def leer_preguntas(self):
        """Lee las preguntas del formulario /candidate/kq abierto en la página."""
        return self.page.evaluate("""() => {
          const f = document.querySelector('form[action*="/candidate/kq"]');
          const qs = [];
          for (let i = 0; ; i++) {
            const pre = `KillerQuestions[${i}]`;
            const id = f.querySelector(`input[name="${pre}.Id"]`);
            if (!id) break;
            const val = n => { const e = f.querySelector(`[name="${pre}.${n}"]`); return e ? e.value : null; };
            const ta = f.querySelector(`textarea[name="${pre}.OpenQuestion"]`);
            const radios = [...f.querySelectorAll(`input[type=radio][name="${pre}.ClosedQuestion"]`)];
            const checks = [...f.querySelectorAll(`input[type=checkbox][name^="${pre}"]`)];
            const opciones = radios.map((r, j) => {
              let t = '';
              const lab = r.closest('label') || (r.id && f.querySelector(`label[for="${r.id}"]`)) || r.nextElementSibling;
              if (lab) t = lab.innerText.trim();
              if (!t) t = val(`DataOptions[${r.value}].Answer`) || val(`DataOptions[${j}].Answer`) || r.value;
              return {valor: r.value, texto: t};
            });
            qs.push({indice: i, id: id.value, titulo: val('Title'), tipo: val('Type'),
                     abierta: !!ta, maxlen: ta ? (ta.maxLength > 0 ? ta.maxLength : 500) : null,
                     opciones, otros_controles: checks.length});
          }
          return qs;
        }""")

    def enviar_respuestas(self, respuestas):
        """respuestas: {indice: ('texto', str) | ('radio', valor)}. Completa y envía el form."""
        for i, (tipo, valor) in respuestas.items():
            pre = f"KillerQuestions[{i}]"
            if tipo == "texto":
                self.page.fill(f'textarea[name="{pre}.OpenQuestion"]', valor)
            else:
                self.page.evaluate("""([name, v]) => {
                    const r = document.querySelector(`input[type=radio][name="${name}"][value="${v}"]`);
                    r.checked = true; r.dispatchEvent(new Event('change', {bubbles: true}));
                    r.dispatchEvent(new Event('click', {bubbles: true}));
                }""", [f"{pre}.ClosedQuestion", valor])
        with self.page.expect_navigation(timeout=60000):
            self.page.click("#btnKiller")
        try:
            self.page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        txt = texto_pagina(self.page)
        if "/candidate/postapply" in self.page.url or "Te postulaste correctamente" in txt:
            return True, self.page.url
        if "Ya te postulaste" in txt:
            return True, self.page.url
        return False, self.page.url


# ----------------------------------------------------------------- formulario por consola
def completar_formulario(preguntas, salario):
    respuestas = {}
    for n, q in enumerate(preguntas, 1):
        print(f"\n  [{n}/{len(preguntas)}] {(q['titulo'] or '').strip()}")
        if q["abierta"]:
            es_sal = bool(salario) and any(w in (q["titulo"] or "").lower() for w in PALABRAS_SALARIO)
            extra = f" [Enter = {salario}]" if es_sal else ""
            r = ""
            while not r:
                r = input(f"  Tu respuesta{extra} (o 's' para saltear este aviso): ").strip()
                if not r and es_sal:
                    r = str(salario)
            if r.lower() == "s":
                return None
            respuestas[q["indice"]] = ("texto", r[: q["maxlen"] or 500])
        elif q["opciones"]:
            for k, o in enumerate(q["opciones"], 1):
                print(f"     {k}) {o['texto']}")
            validas = {str(k) for k in range(1, len(q["opciones"]) + 1)} | {"s"}
            r = preguntar("  Elegí el número (o 's' para saltear este aviso): ", validas)
            if r.lower() == "s":
                return None
            respuestas[q["indice"]] = ("radio", q["opciones"][int(r) - 1]["valor"])
        else:
            print(f"  ⚠ Tipo de pregunta no soportado (tipo {q['tipo']}). Salteo este aviso; "
                  "postulate a mano desde la web.")
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
    ap.add_argument("--simular", action="store_true", help="no se postula, solo lista")
    ap.add_argument("--limite", type=int, default=None, help="máx. avisos a intentar en la fase 1")
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
    desc = None   # descartes (datos/computrabajo/descartes.json), se arma tras el login

    def registrar(aviso, estado, detalle=None):
        historial[aviso["id"]] = {
            "titulo": aviso.get("titulo"), "empresa": aviso.get("empresa"), "estado": estado,
            "detalle": detalle, "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "url": aviso.get("url"),
        }
        guardar_json(HISTORIAL_FILE, historial)
        if estado == "descartado" and desc is not None:
            desc.agregar(aviso)

    umbral = cfg["umbral_repetidos"]

    def repetido_de_postulado(aviso):
        """Si el aviso repite uno al que ya te postulaste, devuelve ese; si no, None."""
        if not cfg["omitir_repetidos"]:
            return None
        for oid, h in historial.items():
            if oid != aviso["id"] and h.get("estado") in ESTADOS_POSTULADO and es_repetido(h, aviso, umbral):
                return h
        return None

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PERFIL_DIR), channel="msedge", headless=False, viewport={"width": 1200, "height": 800})
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        ct = Computrabajo(page)

        ct.asegurar_login()
        desc = descartes.iniciar("computrabajo", ct.mail(), CONFIG_FILE, historial)
        minimizar_ventana(page)
        print("   (Minimicé la ventana de Edge: dejala abierta, no la cierres.)")

        import busquedas   # en comun/ (ya está en sys.path)
        avisos, vistos = [], set()
        urls = busquedas.lista(cfg)
        for i, url in enumerate(urls, 1):
            print(f"\n🔎 Búsqueda {i} de {len(urls)}: {busquedas.resumen(url)}")
            for a in ct.listar(url, cfg["max_paginas_listado"]):
                if a["id"] not in vistos:          # el mismo aviso en dos búsquedas se revisa una vez
                    vistos.add(a["id"])
                    avisos.append(a)
        print(f"   {len(avisos)} avisos encontrados.")

        excl = [w.lower() for w in cfg["palabras_excluidas_titulo"]]
        pendientes, con_preguntas = [], []
        for a in avisos:
            h = historial.get(a["id"])
            if a["id"] in desc or (h and h["estado"] in ESTADOS_FINALES):
                continue
            if any(w in a["titulo"].lower() for w in excl):
                continue
            if h and h["estado"] == "con_preguntas":
                con_preguntas.append(a)   # ya sabemos que tiene preguntas: directo a la fase 2
            else:
                pendientes.append(a)
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

        # Fase 1: abrir el link de postulación de cada aviso
        ok = ya = err = 0
        total = min(len(pendientes), limite)
        for n, a in enumerate(pendientes[:limite], 1):
            etiqueta = f"[{n}/{total}] {a['titulo']} — {a['empresa']}"
            orig = repetido_de_postulado(a)
            if orig:
                print(f"≈ {etiqueta}: repetido de uno al que ya te postulaste, salteado.")
                registrar(a, "repetido", {"de": orig.get("titulo")})
                continue
            try:
                res = ct.abrir_postulacion(a["id"])
            except Exception as e:
                res = "desconocido"
                print(f"   (error de navegación: {e})")
            if res == "postulado":
                ok += 1
                print(f"✅ {etiqueta}")
                registrar(a, "postulado")
            elif res == "ya_postulado":
                ya += 1
                print(f"• {etiqueta}: ya estabas postulado.")
                registrar(a, "ya_postulado")
            elif res == "preguntas":
                print(f"📝 {etiqueta}: tiene preguntas, queda para el final.")
                registrar(a, "con_preguntas")
                con_preguntas.append(a)
            elif res == "externo":
                print(f"» {etiqueta}: deriva a un sitio externo, salteado.")
                registrar(a, "externo", page.url)
            else:
                err += 1
                print(f"❌ {etiqueta}: no se pudo postular (terminó en {page.url[:100]}).")
                registrar(a, "error", page.url)
            pausa(cfg)
        print(f"\nResumen fase 1: {ok} postulaciones nuevas, {ya} ya estabas, {err} con error, "
              f"{len(con_preguntas)} con preguntas.")

        # Fase 2: avisos con preguntas
        # Los repetidos entre sí se agrupan: se muestra uno solo por grupo.
        restantes = []
        for a in con_preguntas:
            orig = repetido_de_postulado(a)
            if orig:
                registrar(a, "repetido", {"de": orig.get("titulo")})
            else:
                restantes.append(a)
        if cfg["omitir_repetidos"]:
            grupos = agrupar_repetidos(restantes, umbral)
        else:
            grupos = [[a] for a in restantes]
        if len(restantes) < len(con_preguntas) or len(grupos) < len(restantes):
            print(f"\n≈ {len(con_preguntas)} avisos con preguntas → {len(grupos)} únicos "
                  f"(sin contar repetidos).")

        def marcar_resto(grupo, elegido, estado):
            for otro in grupo:
                if otro is not elegido:
                    registrar(otro, estado, {"de": elegido.get("titulo")})

        if grupos:
            print(f"\n📝 Hay {len(grupos)} avisos con preguntas de selección.")
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
                    res = ct.abrir_postulacion(a["id"])
                    if res != "preguntas":
                        print(f"   Estado inesperado: {res}.")
                        if res in ("postulado", "ya_postulado"):
                            registrar(a, res)
                            marcar_resto(grupo, a, "repetido")
                        continue
                    preguntas = ct.leer_preguntas()
                    respuestas = completar_formulario(preguntas, cfg["salario_pretendido"])
                    if respuestas is None:
                        print("   Salteado.")
                        continue
                    exito, url_final = ct.enviar_respuestas(respuestas)
                    if exito:
                        print("   ✅ Postulado.")
                        registrar(a, "postulado", {"preguntas": [q["titulo"] for q in preguntas],
                                                   "respuestas": {str(k): v[1] for k, v in respuestas.items()}})
                        marcar_resto(grupo, a, "repetido")
                    else:
                        print(f"   ❌ El envío no se confirmó (terminó en {url_final[:100]}). Revisalo en la web.")
                        registrar(a, "con_preguntas", {"error_envio": url_final})
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
