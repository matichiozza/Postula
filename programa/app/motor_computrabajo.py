"""
Motor de Computrabajo para la app. Hace lo mismo que computrabajo/postulador.py (y usa sus
funciones), pero en vez de preguntar por consola le manda eventos a la interfaz y recibe sus
decisiones como comandos.

Corre en un hilo aparte, con tres pestañas del mismo Edge:
  - principal: login, listado y el recorrido aviso por aviso (postula los que no tienen preguntas);
  - formulario: abrir y enviar las preguntas de los avisos que elegís postular;
  - consulta: leer la descripción de los avisos (fetch dentro de ar.computrabajo.com).
Así podés ir decidiendo los avisos con preguntas mientras el recorrido sigue.
"""
import importlib.util
import queue
import random
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "comun"))   # módulos compartidos
import descartes  # noqa: E402
import perfil  # noqa: E402
import busquedas  # noqa: E402
import rutas  # noqa: E402
import recorrido  # noqa: E402
import ventana_edge  # noqa: E402
import cuenta as cuentas_bolsa  # noqa: E402  (alias: "cuenta" es el contador del recorrido)
import fechas  # noqa: E402


def cargar_postulador(carpeta):
    """Importa bolsas/<carpeta>/postulador.py con un nombre propio (los 4 se llaman igual)."""
    spec = importlib.util.spec_from_file_location(f"postulador_{carpeta}", rutas.codigo_bolsa(carpeta) / "postulador.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


pc = cargar_postulador("computrabajo")

DETALLE_JS = """async (url) => {
    const html = await (await fetch(url, {credentials: 'include'})).text();
    const d = new DOMParser().parseFromString(html, 'text/html');
    const box = d.querySelector('[div-link="oferta"]');
    if (!box) return null;
    // solo las etiquetas del principio (sueldo, contrato, jornada), no las "aptitudes" de abajo
    const tags = [...box.querySelectorAll('.tag.base')].map(t => t.textContent.trim()).filter(Boolean);
    const partes = [];
    let requisitos = [];
    for (const el of box.children) {
        // la descripción termina donde empiezan los requerimientos, las aptitudes o el pie de la página
        if (el.matches('p.fwB') && /requerimientos/i.test(el.textContent)) {
            const ul = el.nextElementSibling;
            if (ul && ul.matches('ul')) requisitos = [...ul.querySelectorAll('li')].map(li => li.textContent.trim()).filter(Boolean);
            break;
        }
        if (el.matches('p.fwB, p.fc_aux, .posSticky_m')) break;
        if (el.matches('h2') || el.matches('.tag') || el.querySelector('.tag')) continue;
        const c = el.cloneNode(true);
        c.querySelectorAll('br').forEach(b => b.replaceWith('\\n'));
        c.querySelectorAll('li').forEach(li => { li.prepend('• '); li.append('\\n'); });
        c.querySelectorAll('h3, h4, p').forEach(p => p.append('\\n'));
        const t = c.textContent.split('\\n').map(l => l.trim()).join('\\n').replace(/\\n{3,}/g, '\\n\\n').trim();
        if (t) partes.push(t);
    }
    const img = d.querySelector('img[src*="/logos/empresas/"], img[data-src*="/logos/empresas/"]');
    const src = img ? (img.getAttribute('data-src') || img.getAttribute('src')) : '';
    const logo = src ? new URL(src, 'https://ar.computrabajo.com').href : '';
    return {tags, texto: partes.join('\\n\\n'), requisitos, logo};
}"""


class Cancelado(Exception):
    pass


class MotorComputrabajo:
    plataforma = "computrabajo"
    nombre = "Computrabajo"
    perfil_dir = pc.PERFIL_DIR

    def __init__(self, emitir, solo_cuenta=False):
        self.emitir = emitir
        self.solo_cuenta = solo_cuenta   # True: solo vincular la cuenta (iniciar sesión y anotar el mail)
        self.comandos = queue.Queue()
        self.cancelado = False
        self.grupos = {}          # gid (id del primer aviso) -> [avisos repetidos entre sí]
        self.orden = []           # gids en el orden en que se muestran
        self.detalles = {}        # gid -> {tags, texto}
        self.form_gid = None      # grupo cuyo formulario está abierto en la pestaña de formulario
        self.deshacer_pila = []   # [(gid, grupo, entradas previas del historial, posición)]
        self.pausado = False      # pausa del recorrido (tus decisiones se siguen atendiendo)
        recorrido.iniciar_auto(self)

    # ------------------------------------------------------------------ comunicación
    def enviar_comando(self, nombre, datos):
        self.comandos.put((nombre, datos or {}))

    def atender(self, hasta=None):
        """Ejecuta los comandos de la interfaz que haya. Si se pasa `hasta` (time.time()),
        sigue atendiendo hasta ese momento (sirve de pausa entre postulaciones)."""
        ventana_edge.repasar(self)      # si se abrió alguna ventana de Edge nueva, se oculta
        while True:
            if self.cancelado:
                raise Cancelado()
            restante = (hasta - time.time()) if hasta else 0
            try:
                if restante > 0:
                    nombre, datos = self.comandos.get(timeout=min(0.2, restante))
                else:
                    nombre, datos = self.comandos.get_nowait()
            except queue.Empty:
                if not hasta or time.time() >= hasta:
                    return
                continue
            try:
                getattr(self, "cmd_" + nombre)(**datos)
            except Cancelado:
                raise
            except Exception as e:
                self.emitir("aviso", {"tipo": "error", "texto": f"Falló '{nombre}': {e}"})
                traceback.print_exc()

    def estado(self, texto):
        self.emitir("estado", {"texto": texto})

    # ------------------------------------------------------------------ datos
    def cargar_config(self):
        cfg = {**pc.DEFAULT_CONFIG, **pc.cargar_json(pc.CONFIG_FILE, {})}
        sueldo = perfil.cargar()["sueldo"]
        if sueldo:
            cfg["salario_pretendido"] = sueldo
        return cfg

    def registrar(self, aviso, estado, detalle=None):
        self.historial[aviso["id"]] = {
            "titulo": aviso.get("titulo"), "empresa": aviso.get("empresa"), "estado": estado,
            "detalle": detalle, "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "url": aviso.get("url"),
        }
        pc.guardar_json(pc.HISTORIAL_FILE, self.historial)
        if estado == "descartado":
            self.desc.agregar(aviso)

    def sincronizar_postulaciones(self, ct):
        """Anota como "ya_postulado" lo que figura en "Mis postulaciones" de la web (también lo que
        hiciste fuera de la app): así no aparece en "Para decidir", ni él ni sus repetidos."""
        self.estado("Leyendo tus postulaciones...")
        try:
            todas, completo = ct.mis_postulaciones(
                al_avanzar=lambda n: (self.estado(f"Leyendo tus postulaciones ({n})..."), self.atender()))
        except Cancelado:
            raise
        except Exception as e:
            print(f"[mis postulaciones] {e}")
            todas, completo = {}, False
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        nuevas = 0
        for oid, p in todas.items():
            if (self.historial.get(oid) or {}).get("estado") in (*pc.ESTADOS_POSTULADO, "descartado"):
                continue
            self.historial[oid] = {**p, "estado": "ya_postulado", "detalle": "Mis postulaciones", "fecha": ahora}
            nuevas += 1
        if nuevas:
            pc.guardar_json(pc.HISTORIAL_FILE, self.historial)
        print(f"[mis postulaciones] leídas {len(todas)}, nuevas en el historial {nuevas}, completo={completo}")
        if not completo or not todas:
            self.emitir("aviso", {"tipo": "error", "texto":
                        "No pude leer todas tus postulaciones: puede aparecer algún aviso al que ya te postulaste."
                        if todas or not completo else
                        "No encontré postulaciones en tu cuenta. Si ya tenés, puede haber cambiado la página de Computrabajo."})

    def repetido_de_postulado(self, aviso):
        if not self.cfg["omitir_repetidos"]:
            return None
        for oid, h in self.historial.items():
            if h.get("detalle") == "Mis postulaciones" and not h.get("empresa"):
                continue      # la web no dice la empresa: sirve para saltear ESE aviso, no para buscar repetidos
            if (oid != aviso["id"] and h.get("estado") in pc.ESTADOS_POSTULADO
                    and pc.es_repetido(h, aviso, self.cfg["umbral_repetidos"])):
                return h
        return None

    def item(self, gid):
        g = self.grupos[gid]
        a = g[0]
        return {"gid": gid, "titulo": a["titulo"], "empresa": a["empresa"], "publicado": a.get("publicado", ""), "antiguedad": a.get("antiguedad"),
                "url": a["url"], "busqueda": a.get("busqueda", ""), "libre": bool(a.get("libre")),
                "repetidos": [{"titulo": x["titulo"], "url": x["url"]} for x in g[1:]]}

    def agregar_con_preguntas(self, aviso, avisar=True):
        """Suma un aviso con preguntas a la lista de decisiones (agrupando repetidos)."""
        orig = self.repetido_de_postulado(aviso)
        if orig:
            self.registrar(aviso, "repetido", {"de": orig.get("titulo")})
            return
        aviso.pop("libre", None)
        self._sumar_a_lista(aviso, avisar)

    def agregar_libre(self, aviso):
        """Suma un aviso sin revisar: lo postula el usuario o el modo Auto."""
        aviso["libre"] = True
        self._sumar_a_lista(aviso)

    def _sumar_a_lista(self, aviso, avisar=True):
        if self.cfg["omitir_repetidos"]:
            for gid in self.orden:
                primero = self.grupos[gid][0]
                if (bool(primero.get("libre")) == bool(aviso.get("libre"))
                        and pc.es_repetido(primero, aviso, self.cfg["umbral_repetidos"])):
                    self.grupos[gid].append(aviso)
                    if avisar:
                        self.emitir("grupo_act", self.item(gid))
                    return
        self.grupos[aviso["id"]] = [aviso]
        self.orden.append(aviso["id"])
        if avisar:
            self.emitir("grupo_nuevo", self.item(aviso["id"]))

    def quitar_grupo(self, gid):
        self.orden.remove(gid)
        return self.grupos.pop(gid)

    def marcar_resto(self, grupo, elegido, estado):
        for otro in grupo:
            if otro is not elegido:
                self.registrar(otro, estado, {"de": elegido.get("titulo")})

    # ------------------------------------------------------------------ comandos de la interfaz
    def cmd_pausa(self, pausado):
        self.pausado = bool(pausado)
        self.emitir("pausa", {"pausado": self.pausado})

    def cmd_cambiar_busqueda(self, indice):
        recorrido.cmd_cambiar_busqueda(self, indice)

    def cmd_recuperar(self, id):
        recorrido.cmd_recuperar(self, id)

    def guardar_historial(self):
        pc.guardar_json(pc.HISTORIAL_FILE, self.historial)

    def necesita_form(self, aviso):
        return False                 # sin consultar no se sabe (ver tiene_preguntas)

    def tiene_preguntas(self, oid):
        """¿El aviso tiene preguntas? Sin postularse: pide la página de preguntas (/candidate/kq)
        SIN seguir redirecciones. Con preguntas responde 200 con el formulario; sin preguntas
        redirige a /apply/, que es lo que postula, y esa redirección nunca se sigue.
        Probado el 25-11-2026 con un aviso nuevo sin preguntas: no quedó en "Mis postulaciones".
        Devuelve True / False, o None si no se pudo saber (queda como antes: se sabe al postularse).
        OJO: no usar page.goto para esto: el navegador sigue la redirección y postula."""
        try:
            r = self.ctx.request.get(f"{pc.CANDIDATO}/candidate/kq?oi={oid}", max_redirects=0, timeout=20000)
            if r.status == 200:
                return True if "KillerQuestions[" in r.text() else None
            if r.status in (301, 302, 303, 307, 308):
                return False if "/apply" in (r.headers.get("location") or "").lower() else None
            print(f"[kq] {oid}: HTTP {r.status}")
        except Exception as e:
            print(f"[kq] {oid}: {e}")
        return None

    def cmd_ordenar(self, activo):
        recorrido.cmd_ordenar(self, activo)

    def cmd_auto(self, activo):
        recorrido.cmd_auto(self, activo)

    def postular_libre(self, a):
        """Abre el link de postulación (si no tiene preguntas, eso ya postula)."""
        try:
            res = self.ct.abrir_postulacion(a["id"])
        except Exception as e:
            res = "desconocido"
            print(f"error de navegación: {e}")
        if res in ("postulado", "ya_postulado"):
            self.registrar(a, res)
        elif res == "externo":
            self.registrar(a, "externo", self.ct.page.url)
        elif res != "preguntas":
            self.registrar(a, "error", self.ct.page.url)
        return {"postulado": "ok", "ya_postulado": "ya", "preguntas": "preg", "externo": "ext"}.get(res, "err")

    def cmd_detalle(self, gid):
        if gid not in self.grupos:
            return
        if gid not in self.detalles:
            try:
                self.detalles[gid] = self.pag_consulta.evaluate(DETALLE_JS, self.grupos[gid][0]["url"]) or {
                    "tags": [], "texto": "", "error": "No encontré la descripción (¿el aviso se cerró?)."}
            except Exception as e:
                self.emitir("detalle", {"gid": gid, "tags": [], "texto": "", "error": f"No pude cargar el aviso: {e}"})
                return
        self.emitir("detalle", {"gid": gid, **self.detalles[gid]})

    def cmd_descartar(self, gid):
        if gid not in self.grupos:
            return
        pos = self.orden.index(gid)
        grupo = self.quitar_grupo(gid)
        previas = {a["id"]: self.historial.get(a["id"]) for a in grupo}
        self.registrar(grupo[0], "descartado")
        self.marcar_resto(grupo, grupo[0], "descartado")
        self.deshacer_pila.append((gid, grupo, previas, pos))
        self.emitir("grupo_quitado", {"gid": gid, "motivo": "descartado", "titulo": grupo[0]["titulo"]})

    def cmd_deshacer(self):
        if not self.deshacer_pila:
            self.emitir("aviso", {"tipo": "info", "texto": "No hay nada para deshacer."})
            return
        gid, grupo, previas, pos = self.deshacer_pila.pop()
        for oid, entrada in previas.items():
            if entrada is None:
                self.historial.pop(oid, None)
            else:
                self.historial[oid] = entrada
            self.desc.quitar(oid)
        self.guardar_historial()
        self.grupos[gid] = grupo
        self.orden.insert(min(pos, len(self.orden)), gid)
        self.emitir("deshecho", {"item": self.item(gid), "pos": self.orden.index(gid)})

    def cmd_abrir_form(self, gid):
        if gid not in self.grupos:
            return
        a = self.grupos[gid][0]
        self.form_gid = None
        ct = pc.Computrabajo(self.pag_form)
        res = ct.abrir_postulacion(a["id"])
        libre = bool(a.get("libre"))
        if res == "preguntas":
            if libre:                    # resultó tener preguntas: pasa a "Con preguntas"
                for x in self.grupos[gid]:
                    x.pop("libre", None)
                    self.registrar(x, "con_preguntas")
                self.emitir("grupo_act", self.item(gid))
            preguntas = ct.leer_preguntas()
            # Se lee en cada formulario: así toma lo último que se guardó en "Tus datos".
            datos = perfil.cargar()
            for q in preguntas:
                valor, tipo = perfil.precarga(q["titulo"], datos) if q["abierta"] else ("", None)
                q["precarga"] = valor
                q["precarga_tipo"] = tipo
                q["soportada"] = q["abierta"] or bool(q["opciones"])
            self.form_gid = gid
            self.emitir("form", {"gid": gid, "preguntas": preguntas})
        elif res in ("postulado", "ya_postulado"):
            # Pasa si el aviso dejó de tener preguntas: abrir el link ya postula.
            grupo = self.quitar_grupo(gid)
            self.registrar(a, res)
            self.marcar_resto(grupo, a, "repetido")
            hecho = "✅ Te postulaste." if libre else "Te postulaste (el aviso ya no tenía preguntas)."
            texto = hecho if res == "postulado" else "Ya estabas postulado."
            self.emitir("grupo_quitado", {"gid": gid, "motivo": res, "titulo": a["titulo"], "texto": texto,
                                          "postulacion": recorrido.postulacion(self, a)})
        elif res == "externo":
            self.quitar_grupo(gid)
            self.registrar(a, "externo", self.pag_form.url)
            self.emitir("grupo_quitado", {"gid": gid, "motivo": "externo", "titulo": a["titulo"],
                                          "texto": "Este aviso se postula en otro sitio: abrilo en la web."})
        else:
            self.emitir("form_error", {"gid": gid, "texto":
                        f"No apareció el formulario (resultado: {res}). Probá abrir el aviso en el navegador."})

    def cmd_enviar(self, gid, respuestas):
        if gid != self.form_gid or gid not in self.grupos:
            self.emitir("form_error", {"gid": gid, "texto": "El formulario ya no está abierto. Volvé a intentarlo."})
            return
        preguntas = {q["indice"]: q for q in pc.Computrabajo(self.pag_form).leer_preguntas()}
        resp = {}
        for r in respuestas:
            i = int(r["indice"])
            if r["tipo"] == "texto":
                resp[i] = ("texto", str(r["valor"])[: (preguntas.get(i) or {}).get("maxlen") or 500])
            else:
                resp[i] = ("radio", str(r["valor"]))
        ok, url_final = pc.Computrabajo(self.pag_form).enviar_respuestas(resp)
        self.form_gid = None
        a = self.grupos[gid][0]
        if ok:
            grupo = self.quitar_grupo(gid)
            # Para el historial (tecla H): en las de opciones se guarda el TEXTO elegido, no su número.
            def legible(i, tipo, valor):
                if tipo == "radio":
                    for o in (preguntas.get(i) or {}).get("opciones") or []:
                        if str(o.get("valor")) == str(valor):
                            return o.get("texto") or valor
                return valor
            orden = sorted(preguntas)
            self.registrar(a, "postulado", {"preguntas": [preguntas[i]["titulo"] for i in orden],
                                            "respuestas": {str(n): legible(i, *resp[i]) for n, i in enumerate(orden) if i in resp}})
            self.marcar_resto(grupo, a, "repetido")
            self.emitir("grupo_quitado", {"gid": gid, "motivo": "postulado", "titulo": a["titulo"],
                                          "texto": "✅ Te postulaste.", "con_form": True,
                                          "postulacion": recorrido.postulacion(self, a)})
        else:
            self.registrar(a, "con_preguntas", {"error_envio": url_final})
            self.emitir("form_error", {"gid": gid, "texto":
                        f"El envío no se confirmó (terminó en {url_final[:90]}). Revisalo en la web."})

    def ir(self, page, url, intentos=3):
        """goto tolerante: a veces la carga se corta (net::ERR_ABORTED) porque el sitio redirige o
        recarga por su cuenta. Si después de eso la pestaña igual quedó en el sitio, alcanza; si no,
        se reintenta. Antes esto frenaba la app con "Ocurrió un error"."""
        host = url.split("/")[2]
        for n in range(1, intentos + 1):
            try:
                page.goto(url, wait_until="domcontentloaded")
                return
            except Exception as e:
                if self.cancelado:
                    raise Cancelado()
                print(f"[ir] intento {n} a {url}: {str(e).splitlines()[0]}")
                if "ERR_ABORTED" not in str(e) and n == intentos:
                    raise
                page.wait_for_timeout(1500)
                if "ERR_ABORTED" in str(e) and page.url.split("/")[2:3] == [host]:
                    return
        raise RuntimeError(f"No pude abrir {url} después de {intentos} intentos.")

    def esperar_navegador(self, seg):
        """Espera dejando que Playwright procese lo que pasa en Edge. Con time.sleep, page.url y
        ctx.pages NO se actualizan (Playwright solo procesa eventos cuando se lo llama), y la app
        seguía viendo la página de login aunque ya hubieras entrado."""
        vivas = [p for p in self.ctx.pages if not p.is_closed()]
        try:
            (vivas[0] if vivas else self.ctx.new_page()).wait_for_timeout(seg * 1000)
        except Exception:
            time.sleep(seg)

    def logueado(self, ct):
        """¿Ya iniciaste sesión? Se miran TODAS las pestañas de este Edge, porque el login puede
        terminar en otra (Google, una pestaña nueva, etc.) y en cualquier página: Computrabajo a
        veces te deja en su portada y no en el área de candidato.
          - si alguna pestaña está en el área de candidato -> listo (se sigue con esa);
          - si alguna está en una página de login -> todavía no, no se toca nada;
          - si no -> se abre /candidate/home para confirmar la sesión."""
        paginas = [p for p in self.ctx.pages if not p.is_closed()]
        if not paginas:
            paginas = [self.ctx.new_page()]
        urls = [p.url for p in paginas]
        if urls != getattr(self, "_urls_login", None):
            self._urls_login = urls
            print(f"[login] {datetime.now():%H:%M:%S} pestañas: {urls}")
        for p in paginas:
            if p.url.startswith(pc.CANDIDATO + "/candidate/"):
                ct.page = p
                return True
        if any(self.es_pagina_de_login(u) for u in urls):
            return False
        if ct.page.is_closed():
            ct.page = paginas[-1]
        try:
            ct.page.goto(pc.CANDIDATO + "/candidate/home", wait_until="domcontentloaded")
        except Exception as e:
            print(f"[login] no pude abrir /candidate/home: {e}")
            return False
        print(f"[login] confirmación: {ct.page.url}")
        return ct.en_area_candidato()

    def ventana(self, page, mostrar):
        """Muestra Edge (para iniciar sesión) o lo oculta del todo: ni en pantalla ni en la barra de tareas."""
        ventana_edge.ventana(self, page, mostrar)

    @staticmethod
    def es_pagina_de_login(url):
        host = url.split("/")[2].lower() if url.count("/") >= 2 else ""
        if not host or url.startswith(("about:", "edge:", "chrome:")):
            return False
        # el login propio de Computrabajo, o cualquier sitio que no sea Computrabajo (Google, Microsoft...)
        return host.startswith("secure.") or "/account/" in url.lower() or not host.endswith("computrabajo.com")

    # ------------------------------------------------------------------ flujo principal
    def correr(self):
        try:
            with sync_playwright() as p:
                # Edge nace fuera de la pantalla (headless no sirve: Computrabajo lo bloquea con 403)
                # y se minimiza enseguida; solo se muestra si hay que iniciar sesión.
                self.ctx = p.chromium.launch_persistent_context(
                    str(self.perfil_dir), channel="msedge", headless=False, viewport={"width": 1200, "height": 800},
                    args=["--window-position=-2400,0"])
                try:
                    self._correr()
                finally:
                    try:
                        self.ctx.close()
                    except Exception:
                        pass
        except Cancelado:
            pass
        except Exception:
            # si ya se pidió volver al menú, lo que falle mientras se cierra no importa
            if not self.cancelado:
                if self.solo_cuenta:
                    print(traceback.format_exc())
                    self.emitir("cuenta_error", {"plataforma": self.plataforma,
                                "texto": "No se pudo completar el inicio de sesión. Probá de nuevo."})
                else:
                    self.emitir("fatal", {"texto": traceback.format_exc()})

    def _correr(self):
        self.cfg = self.cargar_config()
        self.historial = pc.cargar_json(pc.HISTORIAL_FILE, {})
        page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()
        self.ventana(page, mostrar=False)
        ct = pc.Computrabajo(page)

        # 1) login
        self.estado("Verificando la sesión...")
        self.ir(page, pc.CANDIDATO + "/candidate/home")
        if self.solo_cuenta:
            self.ventana(page, mostrar=True)
        if not ct.en_area_candidato():
            self.emitir("login", {})
            self.ventana(page, mostrar=True)
            while not self.logueado(ct):
                self.atender()
                self.esperar_navegador(1.5)
            page = ct.page          # la pestaña donde quedó la sesión
            self.ventana(page, mostrar=False)
            self.emitir("login_ok", {})

        # 2) descartes (datos/computrabajo/descartes.json; hay un solo usuario). El mail de la
        #    cuenta solo se muestra en la cabecera, para saber con qué cuenta entraste.
        self.estado("Leyendo tu cuenta...")
        mail = ct.mail()
        cuentas_bolsa.guardar(self.plataforma, mail)
        if self.solo_cuenta:
            self.emitir("cuenta_ok", {"plataforma": self.plataforma, "mail": mail or ""})
            return
        self.desc = descartes.iniciar(self.plataforma, mail, pc.CONFIG_FILE, self.historial)
        self.emitir("usuario", {"mail": self.desc.mail or "", "descartados": len(self.desc)})
        self.sincronizar_postulaciones(ct)

        self.ct = ct                     # pestaña principal: listado y modo Auto
        # pestañas auxiliares (por las dudas se vuelve a esconder Edge después de abrirlas)
        self.pag_consulta = self.ctx.new_page()
        self.ir(self.pag_consulta, pc.SITIO + "/")
        self.pag_form = self.ctx.new_page()
        page.bring_to_front()
        self.ventana(page, mostrar=False)

        # 3) búsquedas: una activa a la vez (ver recorrido.py; desde la interfaz se puede cambiar).
        #    En cada aviso:
        #    - ya postulado / descartado / ya visto antes  -> se omite
        #    - con preguntas                              -> aparece en la lista para que decidas
        #    - sin preguntas (se consulta /candidate/kq)  -> queda en la lista (lo postulás vos o Auto)
        #    Entre aviso y aviso se atienden tus decisiones.
        urls = busquedas.lista(self.cfg)
        excl = [w.lower() for w in self.cfg["palabras_excluidas_titulo"]]
        cuenta = {"ok": 0, "ya": 0, "preg": 0, "desc": 0, "omit": 0, "rep": 0, "ext": 0, "err": 0, "libre": 0}
        self.emitir("grupos", {"items": []})

        def cargar(url, resumen):
            unidos = {}
            for u in busquedas.expandir(self.plataforma, url):          # un link por lugar elegido
                for a in ct.listar(
                        u, self.cfg["max_paginas_listado"],
                        al_avanzar=lambda n, total: self.emitir("leyendo", {"pagina": n + 1, "avisos": len(unidos) + total}),
                        esperar=lambda seg: self.atender(time.time() + seg)):
                    unidos.setdefault(a["id"], a)
            encontrados = list(unidos.values())
            for a in encontrados:
                a["busqueda"] = resumen
                a["publicado"] = fechas.desde_texto(a.get("fecha"))
                a["antiguedad"] = fechas.antiguedad(a.get("fecha"))
            return encontrados

        def procesar(a):
            h = self.historial.get(a["id"])
            estado_previo = h["estado"] if h else None
            if a["id"] in self.desc or estado_previo == "descartado":
                return "desc", False
            if estado_previo in pc.ESTADOS_POSTULADO:
                return "ya", False
            if estado_previo == "repetido":
                return "rep", False
            if estado_previo in pc.ESTADOS_FINALES or any(w in a["titulo"].lower() for w in excl):
                return "omit", False                    # externo o palabra excluida
            if estado_previo == "con_preguntas":
                self.agregar_con_preguntas(a)           # ya sabemos que tiene preguntas: no se reabre
                return "preg", False
            orig = self.repetido_de_postulado(a)
            if orig:
                self.registrar(a, "repetido", {"de": orig.get("titulo")})
                return "rep", False
            # se consulta si tiene preguntas sin abrir el link de postulación (abrirlo ya postula)
            preguntas = self.tiene_preguntas(a["id"])
            self.atender(time.time() + random.uniform(0.5, 1.2))   # pausa corta entre consultas
            if preguntas:
                self.registrar(a, "con_preguntas")
                self.agregar_con_preguntas(a)
                return "preg", False
            self.agregar_libre(a)                       # sin preguntas (o no se pudo saber)
            return "libre", False

        recorrido.recorrer(self, urls, cargar, procesar, cuenta)

        # 5) quedan tus decisiones (y Auto): atender hasta que se cierre la ventana
        recorrido.quedar_atendiendo(self)
