"""
Motor de EmpleosIT para la app. Mismos eventos y comandos que los otros (la interfaz es la misma);
hereda de MotorComputrabajo la lista de decisiones, los descartes, Auto y la ventana escondida, y
usa las funciones de bolsas/empleosit/postulador.py (listar, abrir_form, enviar).

El listado no dice qué avisos tienen preguntas: el recorrido lee el formulario de cada aviso nuevo
con fetch (tiene_preguntas) y lo pone en "Sin preguntas" o "Con preguntas". Abrir el formulario NO
postula: postula el envío, que se hace recién cuando vos o Auto lo piden.
"""
import random
import time
from datetime import datetime

from playwright.sync_api import sync_playwright  # noqa: F401  (lo usa MotorComputrabajo.correr)

import busquedas
import descartes
import fechas
import perfil
import recorrido
import cuenta as cuentas_bolsa
from motor_computrabajo import MotorComputrabajo, cargar_postulador, pc

eit = cargar_postulador("empleosit")

# Descripción, etiquetas y logo de la ficha (fetch dentro del sitio, sin navegar).
DETALLE_JS = """async (url) => {
    const d = new DOMParser().parseFromString(await (await fetch(url, {credentials: 'include'})).text(), 'text/html');
    const bloques = [...d.querySelectorAll('.displayFieldBlock')];
    const valor = (titulo) => {
        const b = bloques.find(x => (x.querySelector('h3, h2') || {}).textContent?.trim().startsWith(titulo));
        const v = b && b.querySelector('.displayField');
        return v ? v.textContent.replace(/\\s+/g, ' ').trim() : '';
    };
    const secciones = [];
    for (const b of d.querySelectorAll('#col-wide .displayFieldBlock')) {
        const h = b.querySelector('h2, h3'), c = b.querySelector('.displayField');
        if (!c) continue;
        const copia = c.cloneNode(true);
        copia.querySelectorAll('br').forEach(x => x.replaceWith('\\n'));
        copia.querySelectorAll('li').forEach(x => { x.prepend('• '); x.append('\\n'); });
        copia.querySelectorAll('p, div, h3, h4').forEach(x => x.append('\\n'));
        const texto = copia.textContent.replace(/\\u00a0/g, ' ').split('\\n').map(l => l.trim()).join('\\n').replace(/\\n{3,}/g, '\\n\\n').trim();
        const titulo = h ? h.textContent.trim().replace(/:$/, '') : '';
        if (texto) secciones.push(/^descripci/i.test(titulo) || !titulo ? texto : titulo + ':\\n' + texto);
    }
    if (!secciones.length) return null;
    const img = d.querySelector('img[src*="/files/pictures/"]');
    return {texto: secciones.join('\\n\\n'), tags: [valor('Modalidad'), valor('Tipo de Trabajo'), valor('Categor')].filter(Boolean),
            logo: img ? new URL(img.getAttribute('src'), url).href : '', requisitos: []};
}"""

# Una página de "Mis Postulaciones" (tabla: casilla, fecha, puesto con link, empresa, estado).
# null si no es esa página (sesión caída) -> se avisa.
POSTULACIONES_JS = """async (pagina) => {
    const res = await fetch('/system/applications/view/?page=' + pagina, {credentials: 'include'});
    if (!res.ok || !new URL(res.url).pathname.startsWith('/system/applications')) return null;
    const d = new DOMParser().parseFromString(await res.text(), 'text/html');
    return [...d.querySelectorAll('table tr')].map(tr => {
        const a = tr.querySelector('a[href*="/display-job/"]');
        const id = a && (a.getAttribute('href').match(/display-job\\/(\\d+)/) || [])[1];
        const empresa = a && a.closest('td').nextElementSibling;
        return id ? {id, titulo: a.textContent.trim(), url: new URL(a.getAttribute('href'), res.url).href,
                     empresa: empresa ? empresa.textContent.replace(/\\s+/g, ' ').trim() : ''} : null;
    }).filter(Boolean);
}"""

# Lee el formulario de postulación SIN abrirlo en una pestaña (fetch; abrirlo no postula, postula el
# envío): cuántas preguntas tiene, si tiene campos que la app no completa y si pide captcha.
FORM_JS = """async (lid) => {
    const res = await fetch('/apply-now/?listing_id=' + lid + '&ajaxRelocate=1', {credentials: 'include'});
    const d = new DOMParser().parseFromString(await res.text(), 'text/html');
    const f = d.querySelector('#applyForm');
    if (!f) return {form: false, status: res.status};
    return {form: true,
            preguntas: f.querySelectorAll('input[name="QuestionAnswer[]"]').length,
            otros: [...f.querySelectorAll('input, select, textarea')].some(e =>
                /question/i.test(e.name) && !(e.name === 'QuestionAnswer[]' && e.type === 'text')),
            captcha: !!d.querySelector('.g-recaptcha, iframe[src*="recaptcha"]')};
}"""

# Estado del formulario ya abierto: si pide captcha (sesión caída) y si tiene algo que la app no completa.
REVISAR_FORM_JS = """() => {
    const f = document.querySelector('#applyForm');
    return {captcha: !!document.querySelector('.g-recaptcha, iframe[src*="recaptcha"]'),
            otros: !!f && [...f.querySelectorAll('input, select, textarea')].some(e =>
                /question/i.test(e.name) && !(e.name === 'QuestionAnswer[]' && e.type === 'text'))};
}"""


class MotorEmpleosIT(MotorComputrabajo):
    plataforma = "empleosit"
    nombre = "EmpleosIT"
    perfil_dir = eit.PERFIL_DIR

    # ------------------------------------------------------------------ datos
    def cargar_config(self):
        guardado = eit.cargar_json(eit.CONFIG_FILE, {})
        base = {k: v for k, v in eit.DEFAULT_CONFIG.items() if k != "url_busqueda"}   # sin búsqueda de fábrica
        cfg = {**base, **guardado}
        cfg["salario_pretendido"] = perfil.cargar()["sueldo"] or None
        return cfg

    def guardar_historial(self):
        eit.guardar_json(eit.HISTORIAL_FILE, self.historial)

    def registrar(self, aviso, estado, detalle=None):
        self.historial[aviso["id"]] = {
            "titulo": aviso.get("titulo"), "empresa": aviso.get("empresa"), "estado": estado,
            "detalle": detalle, "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "url": aviso.get("url"),
        }
        self.guardar_historial()
        if estado == "descartado":
            self.desc.agregar(aviso, url=aviso.get("url"))

    def repetido_de_postulado(self, aviso):
        if not self.cfg["omitir_repetidos"] or not aviso.get("empresa"):
            return None
        for oid, h in self.historial.items():
            if (oid != aviso["id"] and h.get("estado") in eit.ESTADOS_POSTULADO and h.get("empresa")
                    and pc.es_repetido(h, aviso, self.cfg["umbral_repetidos"])):
                return h
        return None

    def leer_postulaciones(self):
        """{id: {titulo, empresa, url}} de "Mis Postulaciones". SOLO LEE (fetch; no toca las casillas)."""
        todas = {}
        for pagina in range(1, 100):
            filas = self.pag_consulta.evaluate(POSTULACIONES_JS, pagina)
            if filas is None:
                raise RuntimeError("la página de postulaciones no respondió como se esperaba")
            nuevas = {f["id"]: {k: f[k] for k in ("titulo", "empresa", "url")} for f in filas if f["id"] not in todas}
            if not nuevas:
                break
            todas.update(nuevas)
        return todas

    def sincronizar_postulaciones(self):
        """Anota como "ya_postulado" lo que figura en "Mis Postulaciones" (también lo que hiciste fuera
        de la app): así no aparece en "Para decidir", ni él ni sus repetidos."""
        self.estado("Leyendo tus postulaciones...")
        try:
            todas = self.leer_postulaciones()
        except Exception as e:
            print(f"[mis postulaciones] {e}")
            self.emitir("aviso", {"tipo": "error", "texto":
                        "No pude leer tus postulaciones: puede aparecer algún aviso al que ya te postulaste."})
            return
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        nuevas = 0
        for oid, p in todas.items():
            if (self.historial.get(oid) or {}).get("estado") in (*eit.ESTADOS_POSTULADO, "descartado"):
                continue
            self.historial[oid] = {**p, "estado": "ya_postulado", "detalle": "Mis postulaciones", "fecha": ahora}
            nuevas += 1
        if nuevas:
            self.guardar_historial()
        print(f"[mis postulaciones] leídas {len(todas)}, nuevas en el historial {nuevas}")

    # ------------------------------------------------------------------ formulario
    def tiene_preguntas(self, lid):
        """¿El aviso tiene preguntas? Lee el formulario de postulación con fetch (abrirlo NO postula:
        postula el envío). True / False, o None si no se pudo saber (queda en la primera lista y se
        sabe al postularse, como antes)."""
        try:
            r = self.pag_consulta.evaluate(FORM_JS, lid)
        except Exception as e:
            print(f"[form] {lid}: {e}")
            return None
        if not r or not r.get("form") or r.get("captcha"):
            print(f"[form] {lid}: {r}")
            if r and r.get("captcha") and not getattr(self, "_avisado_captcha", False):
                self._avisado_captcha = True
                self._sin_sesion()
            return None
        return bool(r["preguntas"] or r["otros"])

    def _abrir(self, a):
        """Abre el formulario en la pestaña de formulario -> (preguntas | None, {captcha, otros})."""
        preguntas = eit.EmpleosIT(self.pag_form).abrir_form(a["id"])
        return preguntas, self.pag_form.evaluate(REVISAR_FORM_JS)

    def _sin_sesion(self):
        self.emitir("aviso", {"tipo": "error", "texto":
                    "EmpleosIT pide un captcha: se cerró la sesión. Volvé al menú y usá «Reconectar cuenta»."})

    def _enviar_y_registrar(self, a, respuestas=None, detalle_form=None):
        """Envía el formulario abierto. -> (estado, detalle); registra postulado / ya_postulado / error."""
        estado, detalle = eit.EmpleosIT(self.pag_form).enviar(respuestas)
        if estado.startswith("postulado") and detalle_form:
            detalle = {**detalle_form, "redirect": detalle}
        self.registrar(a, estado, detalle)
        if estado == "postulado_externo":
            self.emitir("aviso", {"tipo": "info", "texto":
                        f"Te postulaste a «{a['titulo']}», pero la empresa pide completar en su sitio: abrí el aviso."})
        return estado, detalle

    def postular_libre(self, a):
        preguntas, form = self._abrir(a)
        if form["captcha"]:
            self.registrar(a, "error", "pide captcha")
            self._sin_sesion()
            return "corte"
        if preguntas is None:
            self.registrar(a, "error", "no apareció el formulario")
            return "err"
        if preguntas or form["otros"]:
            return "preg"
        estado, _ = self._enviar_y_registrar(a)
        return {"postulado": "ok", "postulado_externo": "ok", "ya_postulado": "ya"}.get(estado, "err")

    def _resuelto(self, gid, a, estado, texto, con_form=False):
        grupo = self.quitar_grupo(gid)
        self.marcar_resto(grupo, a, "repetido")
        motivo = "ya_postulado" if estado == "ya_postulado" else "postulado"
        self.emitir("grupo_quitado", {"gid": gid, "motivo": motivo, "titulo": a["titulo"], "texto": texto, "con_form": con_form,
                                      "postulacion": recorrido.postulacion(self, a) if motivo == "postulado" else None})

    def cmd_abrir_form(self, gid):
        if gid not in self.grupos:
            return
        a = self.grupos[gid][0]
        self.form_gid = None
        preguntas, form = self._abrir(a)
        if form["captcha"]:
            self._sin_sesion()
        if form["captcha"] or preguntas is None:
            self.emitir("form_error", {"gid": gid, "texto": "No apareció el formulario. Probá abrir el aviso en la web."})
            return
        libre = bool(a.get("libre"))
        if not preguntas and not form["otros"]:
            estado, _ = self._enviar_y_registrar(a)
            if estado in eit.ESTADOS_POSTULADO:
                texto = "Ya estabas postulado." if estado == "ya_postulado" else "✅ Te postulaste."
                self._resuelto(gid, a, estado, texto)
            else:
                self.emitir("form_error", {"gid": gid, "texto": "No se pudo postular. Probá en la web."})
            return
        if libre:                                    # resultó tener preguntas: pasa a "Con preguntas"
            for x in self.grupos[gid]:
                x.pop("libre", None)
                self.registrar(x, "con_preguntas")
            self.emitir("grupo_act", self.item(gid))
        datos = perfil.cargar()
        lista = []
        for i, titulo in enumerate(preguntas):
            valor, tipo = perfil.precarga(titulo, datos)
            lista.append({"indice": i, "titulo": titulo or "(pregunta sin texto)", "abierta": True, "opciones": [],
                          "maxlen": 500, "soportada": not form["otros"], "precarga": valor, "precarga_tipo": tipo})
        if form["otros"] and not lista:
            lista.append({"indice": 0, "titulo": "(pregunta de un tipo que la app no conoce)", "abierta": False,
                          "opciones": [], "maxlen": None, "soportada": False, "precarga": "", "precarga_tipo": None})
        self.form_gid = gid
        self.form_preguntas = preguntas
        self.emitir("form", {"gid": gid, "preguntas": lista})

    def cmd_enviar(self, gid, respuestas):
        if gid != self.form_gid or gid not in self.grupos:
            self.emitir("form_error", {"gid": gid, "texto": "El formulario ya no está abierto. Volvé a intentarlo."})
            return
        a = self.grupos[gid][0]
        valores = [str(r["valor"]).strip()[:500] for r in sorted(respuestas, key=lambda r: int(r["indice"]))]
        detalle = {"preguntas": self.form_preguntas, "respuestas": {str(i): v for i, v in enumerate(valores)}}
        estado, error = self._enviar_y_registrar(a, valores, detalle)
        self.form_gid = None
        if estado in eit.ESTADOS_POSTULADO:
            texto = "Ya estabas postulado." if estado == "ya_postulado" else "✅ Te postulaste."
            self._resuelto(gid, a, estado, texto, con_form=estado != "ya_postulado")
        else:
            self.registrar(a, "con_preguntas", {"error_envio": str(error)[:300]})
            self.emitir("form_error", {"gid": gid, "texto": "El envío no se confirmó. Revisalo en la web."})

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

    # ------------------------------------------------------------------ flujo principal
    def logueado_en_alguna(self):
        for p in self.ctx.pages:
            if not p.is_closed() and eit.EmpleosIT(p).logueado():
                return p
        return None

    def _correr(self):
        self.cfg = self.cargar_config()
        self.historial = eit.cargar_json(eit.HISTORIAL_FILE, {})
        page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()
        self.ctx.set_default_timeout(90000)            # el sitio a veces tarda mucho
        self.ventana(page, mostrar=False)

        # 1) login: sin sesión, /my-account/ redirige al login
        self.estado("Verificando la sesión...")
        try:
            self.ir(page, eit.SITIO + "/my-account/")
        except Exception as e:
            if "/login" not in page.url:
                raise e
        if self.solo_cuenta:
            self.ventana(page, mostrar=True)
        if not eit.EmpleosIT(page).logueado():
            self.emitir("login", {})
            self.ventana(page, mostrar=True)
            while not self.logueado_en_alguna():
                self.atender()
                self.esperar_navegador(1.5)
            page = self.logueado_en_alguna()
            self.ventana(page, mostrar=False)
            self.emitir("login_ok", {})
        sitio = eit.EmpleosIT(page)

        # 2) cuenta, descartes y postulaciones
        self.estado("Leyendo tu cuenta...")
        mail = sitio.mail()
        cuentas_bolsa.guardar(self.plataforma, mail)
        if self.solo_cuenta:
            self.emitir("cuenta_ok", {"plataforma": self.plataforma, "mail": mail or ""})
            return
        self.desc = descartes.iniciar(self.plataforma, mail, eit.CONFIG_FILE, self.historial)
        self.emitir("usuario", {"mail": self.desc.mail or "", "descartados": len(self.desc)})
        self.pag_consulta = self.ctx.new_page()
        self.pag_form = self.ctx.new_page()
        self.ir(self.pag_consulta, eit.SITIO + "/find-jobs/")   # las consultas fetch() salen de acá
        self.sincronizar_postulaciones()
        page.bring_to_front()
        self.ventana(page, mostrar=False)

        # 3) búsquedas (el recorrido clasifica; postulan vos o Auto)
        urls = busquedas.lista(self.cfg)
        excl = [w.lower() for w in self.cfg["palabras_excluidas_titulo"]]
        cuenta = {"ok": 0, "ya": 0, "preg": 0, "desc": 0, "omit": 0, "rep": 0, "ext": 0, "err": 0, "libre": 0}
        self.emitir("grupos", {"items": []})

        def cargar(url, resumen):
            unidos = {}
            for u in busquedas.expandir(self.plataforma, url):          # un link por lugar elegido
                for a in sitio.listar(
                        u, self.cfg["max_paginas_listado"],
                        al_avanzar=lambda n, total: self.emitir("leyendo", {"pagina": n + 1, "avisos": len(unidos) + total}),
                        esperar=lambda seg: self.atender(time.time() + seg)):
                    unidos.setdefault(a["id"], a)
            avisos = list(unidos.values())
            for a in avisos:
                a["busqueda"] = resumen
                a["publicado"] = fechas.desde_fecha(a.get("fecha"))
                a["antiguedad"] = fechas.antiguedad(fecha_hora=(a.get("fecha") or "").replace("/", "-") or None)
            return avisos

        def procesar(a):
            h = self.historial.get(a["id"])
            previo = h["estado"] if h else None
            if a["id"] in self.desc or previo == "descartado":
                return "desc", False
            if previo in eit.ESTADOS_POSTULADO:
                return "ya", False
            if previo == "repetido":
                return "rep", False
            if previo == "externo" or any(w in a["titulo"].lower() for w in excl):
                return "omit", False
            if previo == "con_preguntas":
                self.agregar_con_preguntas(a)
                return "preg", False
            original = self.repetido_de_postulado(a)
            if original:
                self.registrar(a, "repetido", {"de": original.get("titulo")})
                return "rep", False
            preguntas = self.tiene_preguntas(a["id"])
            self.atender(time.time() + random.uniform(0.5, 1.2))   # pausa corta entre consultas
            if preguntas:
                self.registrar(a, "con_preguntas")
                self.agregar_con_preguntas(a)
                return "preg", False
            self.agregar_libre(a)                       # sin preguntas (o no se pudo saber)
            return "libre", False

        recorrido.recorrer(self, urls, cargar, procesar, cuenta)
        recorrido.quedar_atendiendo(self)
