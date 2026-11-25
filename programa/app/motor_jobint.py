"""
Motor de Bumeran y ZonaJobs para la app (las dos son la plataforma Jobint/Navent: misma API, mismo
listado compartido). Hace lo mismo que motor_computrabajo.py —mismos eventos para la interfaz y
mismos comandos— pero todo por la API JSON de la plataforma, usando las funciones de
bolsas/<bolsa>/postulador.py (api, logueado, filtros_de_url, buscar_todos, ficha, postular, responder).

Diferencias con Computrabajo:
  - el listado ya dice qué avisos tienen preguntas (tienePreguntas) o piden salario: esos van directo
    a "Para decidir" sin abrir nada;
  - postularse a uno sin preguntas es un POST a la API (postularV2), no abrir un link;
  - el listado es compartido: los avisos del OTRO portal se saltean (se postulan desde el otro sitio);
  - un solo Edge con una sola pestaña: todas las consultas son fetch() dentro de la página
    (Cloudflare bloquea cualquier otra forma), y se hacen en el mismo hilo, entre aviso y aviso.
"""
import html
import queue
import re
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "comun"))   # módulos compartidos
import busquedas  # noqa: E402
import descartes  # noqa: E402
import perfil  # noqa: E402
import recorrido  # noqa: E402
import ventana_edge  # noqa: E402
import cuenta as cuentas_bolsa  # noqa: E402  (alias: "cuenta" es el contador del recorrido)
from motor_computrabajo import Cancelado, cargar_postulador, pc as _ct  # noqa: E402  (repetidos: misma lógica)

ESTADOS_POSTULADO = ("postulado", "ya_postulado", "postulado_sin_respuestas")
ESTADOS_FINALES = ESTADOS_POSTULADO + ("externo", "descartado", "repetido")


def html_a_texto(h):
    """Descripción del aviso (HTML) -> texto con saltos de línea y viñetas."""
    h = h or ""
    h = re.sub(r"(?i)<br\s*/?>", "\n", h)
    h = re.sub(r"(?i)<li[^>]*>", "\n• ", h)
    h = re.sub(r"(?i)</(p|div|h\d|li|ul|ol)>", "\n", h)
    h = re.sub(r"<[^>]+>", "", h)
    h = html.unescape(h).replace("\xa0", " ")
    lineas = [l.strip() for l in h.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lineas)).strip()


class MotorJobint:
    plataforma = None      # "bumeran" | "zonajobs" (lo ponen las subclases)
    nombre = None

    def __init__(self, emitir, solo_cuenta=False):
        self.emitir = emitir
        self.solo_cuenta = solo_cuenta   # True: solo vincular la cuenta (iniciar sesión y anotar el mail)
        self.mod = cargar_postulador(self.plataforma)
        self.sitio = self.mod.SITIO
        self.Cliente = getattr(self.mod, "Bumeran", None) or self.mod.Portal
        self.portal_propio = getattr(self.mod, "PORTAL_PROPIO", self.plataforma)
        self.comandos = queue.Queue()
        self.cancelado = False
        self.grupos = {}
        self.orden = []
        self.detalles = {}
        self.form_gid = None
        self.form_preguntas = {}
        self.deshacer_pila = []
        self.pausado = False

    # ------------------------------------------------------------------ comunicación
    def enviar_comando(self, nombre, datos):
        self.comandos.put((nombre, datos or {}))

    def atender(self, hasta=None):
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
        cfg = {**self.mod.DEFAULT_CONFIG, **self.mod.cargar_json(self.mod.CONFIG_FILE, {})}
        cfg.setdefault("omitir_repetidos", True)
        cfg.setdefault("umbral_repetidos", 0.85)
        sueldo = perfil.cargar()["sueldo"]
        cfg["salario_pretendido"] = sueldo or None      # sin sueldo en Ajustes: los que lo piden van a "Para decidir"
        return cfg

    def url_aviso(self, aviso_id):
        return f"{self.sitio}/empleos/{aviso_id}.html"

    def normalizar(self, a, resumen_busqueda):
        return {"id": str(a["id"]), "titulo": a.get("titulo") or "", "empresa": a.get("empresa") or "",
                "ubicacion": a.get("localizacion") or "", "url": self.url_aviso(a["id"]),
                "busqueda": resumen_busqueda, "raw": a}

    def registrar(self, aviso, estado, detalle=None):
        self.historial[aviso["id"]] = {
            "titulo": aviso.get("titulo"), "empresa": aviso.get("empresa"), "estado": estado,
            "detalle": detalle, "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "url": aviso.get("url"),
        }
        self.mod.guardar_json(self.mod.HISTORIAL_FILE, self.historial)
        if estado == "descartado":
            self.desc.agregar(aviso, url=aviso.get("url"))

    def repetido_de_postulado(self, aviso):
        if not self.cfg["omitir_repetidos"]:
            return None
        for oid, h in self.historial.items():
            if (oid != aviso["id"] and h.get("estado") in ESTADOS_POSTULADO
                    and _ct.es_repetido(h, aviso, self.cfg["umbral_repetidos"])):
                return h
        return None

    def item(self, gid):
        g = self.grupos[gid]
        a = g[0]
        return {"gid": gid, "titulo": a["titulo"], "empresa": a["empresa"], "ubicacion": a.get("ubicacion", ""),
                "url": a["url"], "busqueda": a.get("busqueda", ""),
                "repetidos": [{"titulo": x["titulo"], "url": x["url"]} for x in g[1:]]}

    def agregar_con_preguntas(self, aviso, avisar=True):
        orig = self.repetido_de_postulado(aviso)
        if orig:
            self.registrar(aviso, "repetido", {"de": orig.get("titulo")})
            return
        if self.cfg["omitir_repetidos"]:
            for gid in self.orden:
                if _ct.es_repetido(self.grupos[gid][0], aviso, self.cfg["umbral_repetidos"]):
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

    def necesita_form(self, raw):
        return bool(raw.get("tienePreguntas")) or (bool(raw.get("salarioObligatorio")) and not self.cfg["salario_pretendido"])

    # ------------------------------------------------------------------ comandos de la interfaz
    def cmd_pausa(self, pausado):
        self.pausado = bool(pausado)
        self.emitir("pausa", {"pausado": self.pausado})

    def cmd_cambiar_busqueda(self, indice):
        recorrido.cmd_cambiar_busqueda(self, indice)

    def cmd_detalle(self, gid):
        if gid not in self.grupos:
            return
        if gid not in self.detalles:
            a = self.grupos[gid][0]
            try:
                ficha = self.cli.ficha(a["id"])
            except Exception as e:
                self.emitir("detalle", {"gid": gid, "tags": [], "texto": "", "error": f"No pude cargar el aviso: {e}"})
                return
            if not ficha:
                self.detalles[gid] = {"tags": [], "texto": "", "error": "No encontré la descripción (¿el aviso se cerró?)."}
            else:
                raw = a.get("raw") or {}
                tags = [x for x in (raw.get("modalidadTrabajo"), raw.get("tipoTrabajo"),
                                    "Pide salario" if raw.get("salarioObligatorio") else None) if x]
                self.detalles[gid] = {"tags": tags, "texto": html_a_texto(ficha.get("detalle") or raw.get("detalle"))}
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
        self.mod.guardar_json(self.mod.HISTORIAL_FILE, self.historial)
        self.grupos[gid] = grupo
        self.orden.insert(min(pos, len(self.orden)), gid)
        self.emitir("deshecho", {"item": self.item(gid), "pos": self.orden.index(gid)})

    def _quitar_por(self, gid, a, estado, motivo, texto, detalle=None, con_form=False):
        grupo = self.quitar_grupo(gid)
        self.registrar(a, estado, detalle)
        if estado in ESTADOS_POSTULADO:
            self.marcar_resto(grupo, a, "repetido")
        self.emitir("grupo_quitado", {"gid": gid, "motivo": motivo, "titulo": a["titulo"], "texto": texto,
                                      "con_form": con_form})

    def cmd_abrir_form(self, gid):
        if gid not in self.grupos:
            return
        a = self.grupos[gid][0]
        self.form_gid = None
        ficha = self.cli.ficha(a["id"])
        if not ficha:
            self.emitir("form_error", {"gid": gid, "texto": "No pude abrir el aviso (¿se cerró?). Probá verlo en la web."})
            return
        if ficha.get("_postulacion"):
            self._quitar_por(gid, a, "ya_postulado", "ya_postulado", "Ya estabas postulado.", ficha["_postulacion"])
            return
        if self.mod.es_externo(ficha):
            self._quitar_por(gid, a, "externo", "externo", "Este aviso se postula en otro sitio: abrilo en la web.",
                             ficha.get("redireccionURL") or ficha.get("origenAviso"))
            return
        datos = perfil.cargar()
        preguntas = []
        for i, p in enumerate(ficha.get("preguntas") or []):
            if p.get("simple"):
                q = p["simple"]
                valor, tipo = perfil.precarga(q.get("texto"), datos)
                preguntas.append({"indice": str(i), "id": str(q["id"]), "titulo": (q.get("texto") or "").strip(),
                                  "abierta": True, "maxlen": 2000, "opciones": [], "soportada": True,
                                  "precarga": valor, "precarga_tipo": tipo})
            elif p.get("choice"):
                q = p["choice"]
                opciones = [{"valor": self.mod.valor_opcion(o), "texto": self.mod.texto_opcion(o)} for o in q.get("opciones") or []]
                preguntas.append({"indice": str(i), "id": str(q["id"]), "titulo": (q.get("texto") or "").strip(),
                                  "abierta": False, "maxlen": None, "opciones": opciones, "soportada": bool(opciones),
                                  "precarga": "", "precarga_tipo": None})
            else:
                preguntas.append({"indice": str(i), "id": "", "titulo": "(pregunta de un tipo que la app no conoce)",
                                  "abierta": False, "maxlen": None, "opciones": [], "soportada": False,
                                  "precarga": "", "precarga_tipo": None})
        if (a.get("raw") or {}).get("salarioObligatorio") and not self.cfg["salario_pretendido"]:
            preguntas.append({"indice": "salario", "id": "", "titulo": "Salario bruto pretendido (este aviso lo pide)",
                              "abierta": True, "maxlen": 12, "opciones": [], "soportada": True,
                              "precarga": "", "precarga_tipo": None})
        if not preguntas:
            # el aviso ya no tiene preguntas: se postula directo (como en Computrabajo al apretar S)
            st, resp = self.cli.postular(int(a["id"]), self.cfg["salario_pretendido"])
            if self.mod.postulacion_ok(st):
                self._quitar_por(gid, a, "postulado", "postulado", "Te postulaste (el aviso ya no tenía preguntas).", resp)
            elif "postulad" in str(resp).lower():
                self._quitar_por(gid, a, "ya_postulado", "ya_postulado", "Ya estabas postulado.", resp)
            else:
                self.emitir("form_error", {"gid": gid, "texto": f"No se pudo postular (HTTP {st}). Probá en la web."})
            return
        self.form_gid = gid
        self.form_preguntas[gid] = {q["indice"]: q for q in preguntas}
        self.emitir("form", {"gid": gid, "preguntas": preguntas})

    def cmd_enviar(self, gid, respuestas):
        if gid != self.form_gid or gid not in self.grupos:
            self.emitir("form_error", {"gid": gid, "texto": "El formulario ya no está abierto. Volvé a intentarlo."})
            return
        a = self.grupos[gid][0]
        preguntas = self.form_preguntas.get(gid, {})
        salario = self.cfg["salario_pretendido"]
        lista, titulos, legibles = [], [], {}
        for r in respuestas:
            q = preguntas.get(str(r["indice"]))
            if not q:
                continue
            valor = str(r["valor"]).strip()
            if q["indice"] == "salario":
                digitos = "".join(c for c in valor if c.isdigit())
                if not digitos:
                    self.emitir("form_error", {"gid": gid, "texto": "El salario tiene que ser un número."})
                    return
                salario = int(digitos)
                continue
            if q["abierta"]:
                valor = valor[:2000]
                texto = valor
            else:
                texto = next((o["texto"] for o in q["opciones"] if str(o["valor"]) == valor), valor)
            lista.append({"preguntaId": q["id"], "respuesta": valor})
            legibles[str(len(titulos))] = texto
            titulos.append(q["titulo"])
        st, resp = self.cli.postular(int(a["id"]), salario)
        self.form_gid = None
        if not self.mod.postulacion_ok(st):
            if "postulad" in str(resp).lower():
                self._quitar_por(gid, a, "ya_postulado", "ya_postulado", "Ya estabas postulado.", resp)
                return
            self.emitir("form_error", {"gid": gid, "texto": f"No se pudo postular (HTTP {st}). Revisalo en la web."})
            return
        detalle = {"preguntas": titulos, "respuestas": legibles}
        if lista:
            idp = self.mod.id_postulacion_de(resp) or a["id"]
            st2, resp2 = self.cli.responder(idp, lista)
            if not self.mod.postulacion_ok(st2):
                self._quitar_por(gid, a, "postulado_sin_respuestas", "postulado",
                                 "Te postulaste, pero las respuestas no se guardaron: completalas en «Mis postulaciones» de la web.",
                                 {**detalle, "error_respuestas": str(resp2)[:300]}, con_form=True)
                return
        self._quitar_por(gid, a, "postulado", "postulado", "✅ Te postulaste.", detalle, con_form=True)

    # ------------------------------------------------------------------ navegador
    def ir(self, page, url, intentos=3):
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
        vivas = [p for p in self.ctx.pages if not p.is_closed()]
        try:
            (vivas[0] if vivas else self.ctx.new_page()).wait_for_timeout(seg * 1000)
        except Exception:
            time.sleep(seg)

    def ventana(self, page, mostrar):
        """Muestra Edge (para iniciar sesión) o lo oculta del todo: ni en pantalla ni en la barra de tareas."""
        ventana_edge.ventana(self, page, mostrar)

    def pagina_viva(self):
        """La pestaña de la bolsa (si el login abrió otras, se usa la que quedó en el sitio)."""
        vivas = [p for p in self.ctx.pages if not p.is_closed()]
        for p in vivas:
            if p.url.startswith(self.sitio):
                return p
        return vivas[0] if vivas else self.ctx.new_page()

    # ------------------------------------------------------------------ flujo principal
    def correr(self):
        try:
            with sync_playwright() as p:
                self.ctx = p.chromium.launch_persistent_context(
                    str(self.mod.PERFIL_DIR), channel="msedge", headless=False, viewport={"width": 1200, "height": 800},
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
            if not self.cancelado:
                if self.solo_cuenta:
                    print(traceback.format_exc())
                    self.emitir("cuenta_error", {"plataforma": self.plataforma,
                                "texto": "No se pudo completar el inicio de sesión. Probá de nuevo."})
                else:
                    self.emitir("fatal", {"texto": traceback.format_exc()})

    def _correr(self):
        self.cfg = self.cargar_config()
        self.historial = self.mod.cargar_json(self.mod.HISTORIAL_FILE, {})
        page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()
        self.ventana(page, mostrar=False)
        self.cli = self.Cliente(page)

        # 1) login (Cloudflare: todo pasa dentro de este Edge)
        self.estado("Verificando la sesión...")
        self.ir(page, self.sitio + "/")
        if self.solo_cuenta:
            self.ventana(page, mostrar=True)
        if not self.cli.logueado():
            self.emitir("login", {})
            self.ventana(page, mostrar=True)
            try:
                self.ir(page, self.sitio + "/login")
            except Exception:
                pass
            while True:
                self.atender()
                self.esperar_navegador(1.5)
                page = self.pagina_viva()
                self.cli.page = page
                if self.cli.logueado():
                    break
            self.ventana(page, mostrar=False)
            self.emitir("login_ok", {})

        # 2) cuenta y descartes
        self.estado("Leyendo tu cuenta...")
        try:
            _, datos = self.cli.api("/api/candidates/datosPostulanteResumido")
        except Exception:
            datos = None
        dominio = self.sitio.split("www.")[-1]
        mail = descartes.buscar_mail(datos, excluir=(dominio, dominio.rsplit(".", 1)[0]))
        cuentas_bolsa.guardar(self.plataforma, mail)
        if self.solo_cuenta:
            self.emitir("cuenta_ok", {"plataforma": self.plataforma, "mail": mail or ""})
            return
        self.desc = descartes.iniciar(self.plataforma, mail, self.mod.CONFIG_FILE, self.historial)
        self.emitir("usuario", {"mail": self.desc.mail or "", "descartados": len(self.desc)})
        self.estado("Leyendo tus postulaciones...")
        try:
            ya = {str(x) for x in self.cli.ids_ya_postulados(
                al_avanzar=lambda n, total: self.estado(f"Leyendo tus postulaciones ({n} de {total})...")) if x is not None}
        except Exception:
            ya = set()

        # 3) búsquedas: una activa a la vez (ver recorrido.py; desde la interfaz se puede cambiar)
        urls = busquedas.lista(self.cfg)
        excl = [w.lower() for w in self.cfg["palabras_excluidas_titulo"]]
        cuenta = {"ok": 0, "ya": 0, "preg": 0, "desc": 0, "omit": 0, "rep": 0, "ext": 0, "err": 0, "otro": 0}
        abiertos = [0]
        self.emitir("grupos", {"items": []})

        def cargar(url, resumen):
            body = self.cli.filtros_de_url(url)
            self.atender()
            vistos = set()
            avisos = []
            for a in self.cli.buscar_todos(body):
                if str(a["id"]) not in vistos:
                    vistos.add(str(a["id"]))
                    avisos.append(self.normalizar(a, resumen))
            return avisos

        def procesar(a):
            raw = a["raw"]
            h = self.historial.get(a["id"])
            previo = h["estado"] if h else None
            if (raw.get("portal") or self.portal_propio).lower() != self.portal_propio:
                return "otro", False                         # aviso del otro portal del grupo
            if a["id"] in self.desc or previo == "descartado":
                return "desc", False
            if a["id"] in ya or raw.get("estadoPostulacion") or previo in ESTADOS_POSTULADO:
                if previo not in ESTADOS_POSTULADO:
                    self.registrar(a, "ya_postulado")
                return "ya", False
            if previo in ESTADOS_FINALES or any(w in a["titulo"].lower() for w in excl):
                return "omit", False
            if previo == "con_preguntas":
                self.agregar_con_preguntas(a)
                return "preg", False
            orig = self.repetido_de_postulado(a)
            if orig:
                self.registrar(a, "repetido", {"de": orig.get("titulo")})
                return "rep", False
            if self.necesita_form(raw):
                self.registrar(a, "con_preguntas")
                self.agregar_con_preguntas(a)
                return "preg", False
            if abiertos[0] >= self.cfg["max_postulaciones_por_corrida"]:
                self.emitir("aviso", {"tipo": "info", "texto":
                            f"Llegué al máximo de {abiertos[0]} postulaciones por corrida (config.json). Corto el recorrido acá."})
                return "corte"
            abiertos[0] += 1
            clave = self.postular_sin_form(a)
            if clave == "corte":
                return "corte"
            return clave, True

        recorrido.recorrer(self, urls, cargar, procesar, cuenta)
        self.atender(float("inf"))

    def postular_sin_form(self, a):
        """Un aviso que según el listado no tiene preguntas: se mira la ficha y se postula.
        -> clave del contador ("ok", "ya", "ext", "preg", "err") o "corte"."""
        try:
            ficha = self.cli.ficha(int(a["id"]))
        except Exception as e:
            print(f"[ficha] {a['id']}: {e}")
            ficha = None
        if not ficha:
            self.registrar(a, "error", "no se pudo leer la ficha")
            return "err"
        if ficha.get("_postulacion"):
            self.registrar(a, "ya_postulado", ficha["_postulacion"])
            return "ya"
        if self.mod.es_externo(ficha):
            self.registrar(a, "externo", ficha.get("redireccionURL") or ficha.get("origenAviso"))
            return "ext"
        if ficha.get("preguntas"):
            self.registrar(a, "con_preguntas")
            self.agregar_con_preguntas(a)
            return "preg"
        st, resp = self.cli.postular(int(a["id"]), self.cfg["salario_pretendido"])
        if self.mod.postulacion_ok(st):
            self.registrar(a, "postulado", resp)
            return "ok"
        texto = str(resp)
        if "postulad" in texto.lower():
            self.registrar(a, "ya_postulado", resp)
            return "ya"
        self.registrar(a, "error", {"status": st, "resp": texto[:300]})
        if st in (401, 403):
            self.emitir("aviso", {"tipo": "error", "texto":
                        f"{self.nombre} cortó la sesión o bloqueó las postulaciones (HTTP {st}). Corto el recorrido: volvé a entrar más tarde."})
            return "corte"
        if st == 429:
            self.emitir("aviso", {"tipo": "info", "texto": f"{self.nombre} pide ir más despacio: espero 2 minutos."})
            self.atender(time.time() + 120)
        return "err"


class MotorBumeran(MotorJobint):
    plataforma = "bumeran"
    nombre = "Bumeran"


class MotorZonaJobs(MotorJobint):
    plataforma = "zonajobs"
    nombre = "ZonaJobs"
