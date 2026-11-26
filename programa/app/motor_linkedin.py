"""
Motor de LinkedIn para la app (solo avisos con "Solicitud sencilla"). Mismos eventos y comandos que los
otros motores; hereda de MotorComputrabajo la lista de decisiones, los descartes y la ventana escondida.

- Búsqueda: con JobSpy (bolsas/linkedin/postulador.py), sin sesión y solo Solicitud sencilla.
- Tus postulaciones: "Registro de empleos > Solicitados" (/jobs-tracker/?stage=applied), con tu sesión.
- Con o sin preguntas: el listado no lo dice, y averiguarlo exige abrir el formulario de cada aviso (mucha
  actividad en tu cuenta). Por eso (decisión del usuario, 25-11-2026, opción "B") todos los avisos quedan
  en "Sin revisar" y se sabe al apretar Postularme: si no tiene preguntas se envía en el acto; si tiene,
  pasan a "Con preguntas" y te las muestra (página por página, como las pide LinkedIn).
- Auto no está disponible en LinkedIn (para no postular en cadena con tu cuenta).
- Si LinkedIn pide verificación (checkpoint, captcha, login), se frena y se avisa.
"""
import random
import re
import threading
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

li = cargar_postulador("linkedin")

DIALOGO = "dialog[open], [role=dialog]"
RE_APLICAR = re.compile(r"Aplicar a|Apply to|Solicitar empleo en")
RE_ENVIAR = re.compile(r"^\s*(Enviar solicitud|Enviar|Submit application|Submit)\s*$", re.I)
RE_AVANZAR = re.compile(r"^\s*(Siguiente|Next|Revisar|Review|Continuar|Continue)\s*$", re.I)
RE_BOTON_SENCILLA = re.compile(r"^(Solicitud sencilla|Easy Apply)$")
RE_ENVIADO = re.compile(r"Se envió tu solicitud|Solicitud enviada|Tu solicitud se ha enviado|application was sent|Application submitted", re.I)

# Lee los campos de la página actual del formulario de Solicitud sencilla.
# Cada campo: {clave (id del control o name del grupo de radios), tipo, titulo, opciones, valor, pendiente, combo}
LEER_PAGINA_JS = """() => {
  const m = [...document.querySelectorAll('dialog[open], [role=dialog]')].find(d => /Aplicar a|Apply to|Solicitar empleo en/.test(d.innerText));
  if (!m) return null;
  // textContent si innerText viene vacío: con la ventana de Edge oculta, innerText puede no traer el texto
  const txt = e => (e ? (e.innerText || e.textContent || '').replace(/\\s+/g, ' ').trim() : '');
  const limpiar = t => t.replace(/\\s*\\*\\s*$/, '').replace(/(.{8,}?)\\s*\\1$/, '$1').trim();   // "Pregunta* Pregunta" -> "Pregunta"
  const campos = [], gruposVistos = new Set();
  for (const el of m.querySelectorAll('input, select, textarea')) {
    if (el.type === 'hidden' || el.disabled) continue;
    const req = el.required || el.getAttribute('aria-required') === 'true';
    if (el.type === 'radio') {
      if (gruposVistos.has(el.name)) continue;
      gruposVistos.add(el.name);
      const grupo = [...m.querySelectorAll(`input[type=radio][name="${CSS.escape(el.name)}"]`)];
      const fs = el.closest('fieldset');
      // diseño nuevo de LinkedIn: cada opción es un div[role=radio] con la pregunta en aria-label y la
      // opción como texto ("Yes"/"No"); la <label> está vacía
      // caja de la opción: div[role=radio], o si no hay (otra variante), el contenedor más grande que tiene
      // un solo radio (ahí está el texto "Yes"/"No", al lado del input)
      const caja = r => {
        const rr = r.closest('[role=radio]');
        if (rr) return rr;
        let c = r;
        while (c.parentElement && c.parentElement !== m && c.parentElement.querySelectorAll('input[type=radio]').length === 1) c = c.parentElement;
        return c;
      };
      const rotulo = r => { for (let c = r; c && c !== m; c = c.parentElement) { const l = c.getAttribute('aria-label'); if (l) return l; } return ''; };
      const titulo = limpiar(txt(fs && fs.querySelector('legend')) || rotulo(el) || '');
      const opciones = grupo.map(r => ({valor: r.id, texto: txt(r.id && m.querySelector(`label[for="${CSS.escape(r.id)}"]`)) || txt(caja(r)) || r.value}));
      const marcado = grupo.find(r => r.checked || (caja(r) && caja(r).getAttribute('aria-checked') === 'true'));
      // el radio del CV (la lista de currículums) no es una pregunta
      const esCv = !!(fs && fs.querySelector('#easyApplyUploadedResumeRef')) || opciones.every(o => /\\.(pdf|docx?)$/i.test(o.texto));
      campos.push({clave: el.name, tipo: 'radio', titulo, opciones, valor: marcado ? marcado.id : '', pendiente: !marcado && !esCv, cv: esCv});
      continue;
    }
    let titulo = '';
    if (el.id) titulo = txt(m.querySelector(`label[for="${CSS.escape(el.id)}"]`));
    if (!titulo) titulo = el.getAttribute('aria-label') || '';
    titulo = limpiar(titulo);
    if (el.tagName === 'SELECT') {
      const ops = [...el.options].filter(o => o.value && !/^(Selecciona una opción|Select an option)$/i.test(o.text.trim()));
      const elegido = el.selectedOptions[0];
      const vacio = !elegido || !el.value || /^(Selecciona una opción|Select an option)$/i.test(elegido.text.trim());
      campos.push({clave: el.id, tipo: 'select', titulo, opciones: ops.map(o => ({valor: o.value, texto: o.text.trim()})),
                   valor: vacio ? '' : el.value, pendiente: vacio && req});
    } else if (el.type === 'checkbox') {
      campos.push({clave: el.id, tipo: 'checkbox', titulo: titulo || limpiar(txt(el.closest('fieldset') && el.closest('fieldset').querySelector('legend'))),
                   opciones: [{valor: 'si', texto: 'Sí'}], valor: el.checked ? 'si' : '', pendiente: req && !el.checked});
    } else if (el.type === 'file') {
      campos.push({clave: el.id, tipo: 'archivo', titulo, opciones: [], valor: '', pendiente: req && !el.files.length});
    } else {
      const v = String(el.value || '').trim();
      campos.push({clave: el.id, tipo: el.tagName === 'TEXTAREA' ? 'textarea' : (el.type || 'text'), titulo, opciones: [],
                   valor: v, pendiente: req && !v, combo: el.getAttribute('role') === 'combobox' || !!el.getAttribute('aria-autocomplete'),
                   maxlen: el.maxLength > 0 ? el.maxLength : null});
    }
  }
  const errores = [...m.querySelectorAll('[role=alert]')].map(txt).filter(Boolean);
  return {pagina: (m.innerText.match(/(\\d+\\/\\d+) páginas?/) || [])[1] || '', campos, errores};
}"""

# "Registro de empleos > Solicitados": una página de tarjetas -> [{id, titulo, empresa}]
SOLICITADOS_JS = """() => {
  const vistos = new Map();
  for (const a of document.querySelectorAll('a[href]')) {
    const m = a.href.match(/(?:jobs\\/view\\/|currentJobId=)(\\d+)/);
    if (!m || vistos.has(m[1])) continue;
    let c = a;
    for (let i = 0; i < 10 && c && !/Solicitado/.test(c.innerText || ''); i++) c = c.parentElement;
    if (!c) continue;
    const lineas = c.innerText.split('\\n').map(l => l.trim()).filter(Boolean)
      .filter(l => !/^(Empleos|Contactos|Notas)$/.test(l));
    const titulo = (lineas[0] || '').replace(/\\s*\\(empleo verificado\\)\\s*$/, '');
    const conPunto = lineas.find(l => l.includes(' · ')) || '';
    vistos.set(m[1], {id: m[1], titulo, empresa: conPunto.split(' · ')[0]});
  }
  return [...vistos.values()];
}"""

# Descripción del aviso (página del aviso con tu sesión): lo que sigue a "Acerca del empleo".
DETALLE_JS = """() => {
  const main = document.querySelector('main') || document.body;
  const t = main.innerText;
  let i = t.search(/Acerca del empleo|About the job/);
  let texto = i >= 0 ? t.slice(i).replace(/^(Acerca del empleo|About the job)\\s*/, '') : '';
  const fin = texto.search(/\\n(Acerca de la empresa|About the company|Mostrar menos|Show less|Ver más empleos|Más empleos)/);
  if (fin > 0) texto = texto.slice(0, fin);
  texto = texto.replace(/\\n?…\\s*más\\s*$/, '').replace(/\\n{3,}/g, '\\n\\n').trim();
  const botones = [...main.querySelectorAll('button, a')].map(b => (b.innerText || '').trim());
  const img = main.querySelector('img[src*="company-logo"], img[alt*="logo" i]');
  const tags = botones.filter(b => /^(En remoto|Híbrido|Presencial|Jornada completa|Media jornada|Contrato|Temporal|Prácticas)$/.test(b));
  return {texto, tags: [...new Set(tags)], logo: img ? img.src : '', requisitos: [],
          sencilla: botones.some(b => /^(Solicitud sencilla|Easy Apply)$/.test(b)),
          solicitado: botones.some(b => /^(Ver currículum|See application|Ver solicitud)$/.test(b))};
}"""


class Frenado(Exception):
    """LinkedIn pidió verificación (checkpoint/captcha/login): no se sigue."""


class MotorLinkedIn(MotorComputrabajo):
    plataforma = "linkedin"
    nombre = "LinkedIn"
    perfil_dir = li.PERFIL_DIR

    # ------------------------------------------------------------------ datos
    def cargar_config(self):
        cfg = {**li.DEFAULT_CONFIG, **li.cargar_json(li.CONFIG_FILE, {})}
        cfg["salario_pretendido"] = perfil.cargar()["sueldo"] or None
        return cfg

    def guardar_historial(self):
        li.guardar_json(li.HISTORIAL_FILE, self.historial)

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
            if (oid != aviso["id"] and h.get("estado") in li.ESTADOS_POSTULADO and h.get("empresa")
                    and pc.es_repetido(h, aviso, self.cfg["umbral_repetidos"])):
                return h
        return None

    def cmd_auto(self, activo):
        self.emitir("aviso", {"tipo": "info", "texto": "En LinkedIn no hay modo Auto: te postulás de a uno."})

    # ------------------------------------------------------------------ verificación de LinkedIn
    @staticmethod
    def pide_verificacion(page):
        u = page.url
        if any(k in u for k in ("/checkpoint", "/authwall", "/uas/login", "/login")):
            return True
        try:
            return page.locator('iframe[src*="captcha"], #captcha-internal').count() > 0
        except Exception:
            return False

    def controlar(self, page):
        if self.pide_verificacion(page):
            raise Frenado(page.url)

    def frenar(self):
        self.emitir("aviso", {"tipo": "error", "texto":
                    "LinkedIn pidió una verificación: freno acá. Volvé al menú y usá «Reconectar cuenta» si hace falta."})

    def logueado(self, ct=None):
        try:
            return any(c["name"] == "li_at" for c in self.ctx.cookies("https://www.linkedin.com")) and \
                not any(self.pide_verificacion(p) for p in self.ctx.pages if not p.is_closed())
        except Exception:
            return False

    # ------------------------------------------------------------------ tus postulaciones
    def sincronizar_postulaciones(self, page):
        """Anota como "ya_postulado" lo que figura en Registro de empleos > Solicitados (10 por página)."""
        self.estado("Leyendo tus postulaciones...")
        todas = {}
        try:
            self.ir(page, li.SITIO + "/jobs-tracker/?stage=applied")
            page.wait_for_timeout(4000)
            self.controlar(page)
            for _ in range(60):
                for t in page.evaluate(SOLICITADOS_JS):
                    todas.setdefault(t["id"], t)
                self.estado(f"Leyendo tus postulaciones ({len(todas)})...")
                self.atender()
                sig = page.locator("main button:visible").filter(has_text=re.compile(r"^\s*(Siguiente|Next)\s*$")).first
                if not sig.count() or not sig.is_enabled():
                    break                                # última página: el botón queda oculto
                antes = len(todas)
                sig.click()
                page.wait_for_timeout(2500)
                if not any(t["id"] not in todas for t in page.evaluate(SOLICITADOS_JS)):
                    page.wait_for_timeout(2500)
                    if not any(t["id"] not in todas for t in page.evaluate(SOLICITADOS_JS)) and len(todas) == antes:
                        break
        except Frenado:
            raise
        except Exception as e:
            print(f"[mis postulaciones] {e}")
            self.emitir("aviso", {"tipo": "error", "texto":
                        "No pude leer tus postulaciones: puede aparecer algún aviso al que ya te postulaste."})
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        nuevas = 0
        for oid, p in todas.items():
            if (self.historial.get(oid) or {}).get("estado") in (*li.ESTADOS_POSTULADO, "descartado"):
                continue
            self.historial[oid] = {"titulo": p["titulo"], "empresa": p["empresa"], "url": li.url_aviso(oid),
                                   "estado": "ya_postulado", "detalle": "Mis postulaciones", "fecha": ahora}
            nuevas += 1
        if nuevas:
            self.guardar_historial()
        print(f"[mis postulaciones] leídas {len(todas)}, nuevas en el historial {nuevas}")

    # ------------------------------------------------------------------ detalle
    def cmd_detalle(self, gid):
        if gid not in self.grupos:
            return
        if gid not in self.detalles:
            try:
                self.ir(self.pag_consulta, self.grupos[gid][0]["url"])
                self.pag_consulta.wait_for_timeout(2500)
                if self.pide_verificacion(self.pag_consulta):
                    self.frenar()
                    return
                d = self.pag_consulta.evaluate(DETALLE_JS)
                if not d["texto"]:
                    d["error"] = "No encontré la descripción (¿el aviso se cerró?)."
                if d.get("solicitado"):
                    d["texto"] = "Ya te postulaste a este aviso.\n\n" + d["texto"]
                self.detalles[gid] = d
            except Exception as e:
                self.emitir("detalle", {"gid": gid, "tags": [], "texto": "", "error": f"No pude cargar el aviso: {e}"})
                return
        self.emitir("detalle", {"gid": gid, **self.detalles[gid]})

    # ------------------------------------------------------------------ formulario de Solicitud sencilla
    def _dialogo(self):
        return self.pag_form.locator(DIALOGO).filter(has_text=RE_APLICAR).first

    def _descartar_borrador(self):
        """Si quedó una Solicitud sencilla abierta, la cierra eligiendo "Descartar" (no queda "En curso")."""
        p = self.pag_form
        try:
            if not self._dialogo().count():
                return
            p.keyboard.press("Escape")
            p.wait_for_timeout(1200)
            conf = p.locator(DIALOGO).filter(has_text=re.compile("guardar esta solicitud|save this application", re.I))
            if conf.count():
                conf.first.locator("button").filter(has_text=re.compile(r"^\s*(Descartar|Discard)\s*$")).first.click()
                p.wait_for_timeout(1200)
        except Exception as e:
            print(f"[linkedin] descartar borrador: {e}")

    def _abrir(self, a):
        """Abre la Solicitud sencilla del aviso. -> "abierto" | "ya_postulado" | "sin_sencilla"."""
        self._descartar_borrador()
        # al frente (dentro del Edge oculto): en una pestaña de fondo LinkedIn no termina de dibujar
        # los textos de las preguntas de sí/no
        self.pag_form.bring_to_front()
        self.ir(self.pag_form, a["url"])
        self.pag_form.wait_for_timeout(3000)
        self.controlar(self.pag_form)
        btn = self.pag_form.get_by_role("button", name=RE_BOTON_SENCILLA).first
        if not btn.count():
            d = self.pag_form.evaluate(DETALLE_JS)
            return "ya_postulado" if d.get("solicitado") else "sin_sencilla"
        btn.click()
        for _ in range(20):
            self.pag_form.wait_for_timeout(500)
            if self._dialogo().count():
                return "abierto"
        return "sin_sencilla"

    def _leer(self):
        """Lee la página actual del formulario cuando terminó de dibujarse: LinkedIn pone primero los
        controles y un instante después los textos de las preguntas (se lee hasta que dos lecturas coinciden)."""
        anterior = None
        for _ in range(6):
            d = self.pag_form.evaluate(LEER_PAGINA_JS)
            if d is not None and d == anterior and all(c["titulo"] for c in d["campos"] if c["pendiente"]):
                return d
            anterior = d
            self.pag_form.wait_for_timeout(600)
        return anterior

    def _botones(self):
        return self._dialogo().get_by_role("button").all()

    def _avanzar_hasta_preguntas(self):
        """Avanza por las páginas que ya están completas (contacto, CV). -> ("enviar", None) si llegó al
        botón Enviar sin nada pendiente; ("preguntas", pagina) si una página tiene campos sin completar;
        ("error", texto) si no se pudo seguir."""
        for _ in range(15):
            self.controlar(self.pag_form)
            d = self._leer()
            if not d:
                return "error", "Se cerró el formulario."
            if any(c["pendiente"] for c in d["campos"]):
                return "preguntas", d
            botones = self._botones()
            if any(RE_ENVIAR.match(b.inner_text() or "") for b in botones):
                return "enviar", None
            sig = next((b for b in botones if RE_AVANZAR.match(b.inner_text() or "")), None)
            if not sig:
                for _ in range(10):                       # a veces los botones tardan en dibujarse
                    self.pag_form.wait_for_timeout(500)
                    botones = self._botones()
                    if any(RE_ENVIAR.match(b.inner_text() or "") for b in botones):
                        return "enviar", None
                    sig = next((b for b in botones if RE_AVANZAR.match(b.inner_text() or "")), None)
                    if sig:
                        break
                else:
                    print(f"[linkedin] sin botón para seguir; botones: {[b.inner_text().strip() for b in botones]}")
                    return "error", "No encontré el botón para seguir. Probá en la web."
            antes = d["pagina"]
            sig.click()
            self.pag_form.wait_for_timeout(1800)
            d2 = self._leer()
            if d2 and d2["pagina"] == antes and not any(c["pendiente"] for c in d2["campos"]):
                return "error", "LinkedIn no dejó avanzar: " + ("; ".join(d2["errores"]) or "revisá el aviso en la web.")
        return "error", "El formulario tiene demasiadas páginas."

    def _enviar_solicitud(self):
        """Toca "Enviar solicitud" y espera la confirmación. -> True/False."""
        env = next((b for b in self._botones() if RE_ENVIAR.match(b.inner_text() or "")), None)
        if not env:
            return False
        env.click()
        for _ in range(20):
            self.pag_form.wait_for_timeout(500)
            if RE_ENVIADO.search(self.pag_form.evaluate("() => document.body.innerText")):
                self.pag_form.keyboard.press("Escape")         # cierra el cartel de "solicitud enviada"
                self.pag_form.wait_for_timeout(800)
                return True
        return False

    def _preguntas_para_la_app(self, d):
        """Campos pendientes de la página -> preguntas en el formato de la interfaz."""
        datos = perfil.cargar()
        salida = []
        for i, c in enumerate([c for c in d["campos"] if c["pendiente"]]):
            abierta = c["tipo"] in ("text", "number", "textarea", "tel", "email", "url")
            valor, tipo = perfil.precarga(c["titulo"], datos) if abierta else ("", None)
            if abierta and c["valor"]:
                valor, tipo = c["valor"], None
            salida.append({"indice": i, "clave": c["clave"], "tipo_campo": c["tipo"], "combo": c.get("combo", False),
                           "titulo": c["titulo"] or "(pregunta sin texto)", "abierta": abierta,
                           "opciones": [{"valor": o["valor"], "texto": o["texto"]} for o in c["opciones"]],
                           "maxlen": c.get("maxlen") or (2000 if c["tipo"] == "textarea" else 300),
                           "soportada": abierta or (c["tipo"] in ("select", "radio", "checkbox") and bool(c["opciones"])),
                           "precarga": valor, "precarga_tipo": tipo, "numero": c["tipo"] == "number"})
        return salida

    def _completar(self, preguntas, respuestas):
        """Escribe las respuestas en la página actual del formulario."""
        p = self.pag_form
        for q in preguntas:
            v = respuestas.get(q["indice"])
            if v is None:
                continue
            t = q["tipo_campo"]
            if t == "radio":
                caja = p.locator(f'[role=radio]:has([id="{v}"])')
                if caja.count():
                    caja.first.click()
                else:
                    p.locator(f'[id="{v}"]').evaluate("e => e.click()")   # el input está escondido visualmente
            elif t == "select":
                p.locator(f'[id="{q["clave"]}"]').select_option(value=str(v))
            elif t == "checkbox":
                p.locator(f'[id="{q["clave"]}"]').check(force=True)
            else:
                campo = p.locator(f'[id="{q["clave"]}"]')
                campo.fill(str(v))
                if q.get("combo"):                      # autocompletar (ej.: ciudad): elegir la primera sugerencia
                    p.wait_for_timeout(1200)
                    campo.press("ArrowDown")
                    campo.press("Enter")
            p.wait_for_timeout(250)

    def _mostrar_preguntas(self, gid, d):
        preguntas = self._preguntas_para_la_app(d)
        if any(q["titulo"] == "(pregunta sin texto)" or any(o["texto"] in ("on", "") for o in q["opciones"]) for q in preguntas):   # diagnóstico (app.log)
            print("[linkedin] pregunta sin texto:", self.pag_form.evaluate(
                "() => { const r = [...document.querySelectorAll('input[type=radio]')].find(x => !(x.closest('fieldset') || x)"
                ".querySelector('#easyApplyUploadedResumeRef')); return r ? (r.closest('fieldset') || r.parentElement)"
                ".outerHTML.replace(/class=\"[^\"]*\"/g, '').slice(0, 1500) : null }"))
        self.form_gid = gid
        self.form_preguntas = preguntas
        self.form_respuestas = getattr(self, "form_respuestas", None) or {"preguntas": [], "respuestas": {}}
        self.emitir("form", {"gid": gid, "preguntas": preguntas, "pagina": d.get("pagina")})

    def _resuelto(self, gid, a, estado, texto, con_form=False):
        grupo = self.quitar_grupo(gid)
        self.marcar_resto(grupo, a, "repetido")
        motivo = "ya_postulado" if estado == "ya_postulado" else "postulado"
        self.emitir("grupo_quitado", {"gid": gid, "motivo": motivo, "titulo": a["titulo"], "texto": texto, "con_form": con_form,
                                      "postulacion": recorrido.postulacion(self, a) if motivo == "postulado" else None})

    def _seguir_formulario(self, gid, a, con_form):
        """Desde la página actual: envía si no queda nada, o muestra las preguntas de la página."""
        res, d = self._avanzar_hasta_preguntas()
        if res == "enviar":
            if self._enviar_solicitud():
                det = self.form_respuestas if con_form and self.form_respuestas["preguntas"] else None
                self.registrar(a, "postulado", det)
                self.form_gid = None
                self._resuelto(gid, a, "postulado", "✅ Te postulaste.", con_form=con_form)
            else:
                self.emitir("form_error", {"gid": gid, "texto": "LinkedIn no confirmó el envío. Revisalo en la web."})
                self._descartar_borrador()
            return
        if res == "preguntas":
            if a.get("libre"):                               # resultó tener preguntas: pasa a "Con preguntas"
                for x in self.grupos[gid]:
                    x.pop("libre", None)
                    self.registrar(x, "con_preguntas")
                self.emitir("grupo_act", self.item(gid))
            self._mostrar_preguntas(gid, d)
            return
        self.emitir("form_error", {"gid": gid, "texto": d})
        self._descartar_borrador()

    def cmd_abrir_form(self, gid):
        if gid not in self.grupos:
            return
        a = self.grupos[gid][0]
        self.form_gid = None
        self.form_respuestas = {"preguntas": [], "respuestas": {}}
        try:
            res = self._abrir(a)
            if res == "ya_postulado":
                self.registrar(a, "ya_postulado")
                self._resuelto(gid, a, "ya_postulado", "Ya estabas postulado.")
                return
            if res == "sin_sencilla":
                self.emitir("form_error", {"gid": gid, "texto":
                            "Este aviso ya no tiene Solicitud sencilla (quizás se cerró). Abrilo en la web."})
                return
            self._seguir_formulario(gid, a, con_form=False)
        except Frenado:
            self.frenar()
            self.emitir("form_error", {"gid": gid, "texto": "LinkedIn pidió una verificación."})

    def cmd_enviar(self, gid, respuestas):
        if gid != self.form_gid or gid not in self.grupos or not self._dialogo().count():
            self.emitir("form_error", {"gid": gid, "texto": "El formulario ya no está abierto. Volvé a intentarlo."})
            return
        a = self.grupos[gid][0]
        resp = {int(r["indice"]): r["valor"] for r in respuestas}
        try:
            self._completar(self.form_preguntas, resp)
            for q in self.form_preguntas:                    # para el historial: pregunta y respuesta legible
                v = resp.get(q["indice"])
                texto = next((o["texto"] for o in q["opciones"] if o["valor"] == v), v)
                self.form_respuestas["respuestas"][str(len(self.form_respuestas["preguntas"]))] = texto
                self.form_respuestas["preguntas"].append(q["titulo"])
            antes = self._leer()
            botones = self._botones()
            env = next((b for b in botones if RE_ENVIAR.match(b.inner_text() or "")), None)
            if env:
                ok = self._enviar_solicitud()
                if ok:
                    self.registrar(a, "postulado", self.form_respuestas)
                    self.form_gid = None
                    self._resuelto(gid, a, "postulado", "✅ Te postulaste.", con_form=True)
                else:
                    self.emitir("form_error", {"gid": gid, "texto": "LinkedIn no confirmó el envío. Revisalo en la web."})
                return
            sig = next((b for b in botones if RE_AVANZAR.match(b.inner_text() or "")), None)
            if not sig:
                self.emitir("form_error", {"gid": gid, "texto": "No encontré el botón para seguir. Probá en la web."})
                return
            sig.click()
            self.pag_form.wait_for_timeout(1800)
            despues = self._leer()
            if despues and antes and despues["pagina"] == antes["pagina"]:
                errores = "; ".join(despues["errores"]) or "alguna respuesta no tiene el formato que pide LinkedIn"
                self.emitir("form_error", {"gid": gid, "texto": f"LinkedIn no aceptó las respuestas: {errores}."})
                self._mostrar_preguntas(gid, despues)
                return
            self._seguir_formulario(gid, a, con_form=True)
        except Frenado:
            self.frenar()
            self.emitir("form_error", {"gid": gid, "texto": "LinkedIn pidió una verificación."})
        except Exception as e:
            self.emitir("form_error", {"gid": gid, "texto": f"Falló al completar el formulario: {str(e).splitlines()[0][:160]}"})

    def postular_libre(self, a):
        return "preg"                                         # sin Auto en LinkedIn

    # ------------------------------------------------------------------ búsqueda en segundo plano
    # JobSpy espera 3-7 s entre página y página (10 avisos): con 300 avisos son más de 2 minutos. Para no
    # hacerte esperar, la búsqueda arranca apenas tocás Empezar (en paralelo con el login y la lectura de
    # tus postulaciones), de a una página, y los avisos se van sumando a la lista de la búsqueda: el
    # recorrido los procesa a medida que llegan (recorrido.llegan_mas). JobSpy no usa el navegador: no
    # toca tu sesión.
    def _buscar_en_fondo(self, urls):
        self._lotes = {u: {"avisos": [], "primera": False, "fin": False, "error": None, "ids": set()} for u in urls}

        def dormir(seg):
            fin = time.time() + seg
            while time.time() < fin and not self.cancelado:
                time.sleep(0.2)

        def trabajar():
            for url in urls:
                lote = self._lotes[url]
                resumen = busquedas.resumen(url)
                try:
                    for u in busquedas.expandir(self.plataforma, url):
                        inicio, reintentos = 0, 0
                        while not self.cancelado and inicio < self.cfg["max_resultados_busqueda"]:
                            avisos, frenado = li.buscar_pagina(u, inicio)
                            if frenado and not avisos:
                                if reintentos < 2:                     # LinkedIn frenó (429): esperar y reintentar
                                    reintentos += 1
                                    dormir(30)
                                    continue
                                lote["error"] = "frenado"
                                self.emitir("aviso", {"tipo": "error", "texto":
                                            f"LinkedIn está limitando las búsquedas: «{resumen}» puede quedar incompleta. Probá de nuevo en unos minutos."})
                                break
                            reintentos = 0
                            for a in avisos:
                                if a["id"] in lote["ids"]:
                                    continue
                                lote["ids"].add(a["id"])
                                a["busqueda"] = resumen
                                a["publicado"] = fechas.desde_fecha(a["fecha"]) if a.get("fecha") else ""
                                a["antiguedad"] = fechas.antiguedad(fecha_hora=a["fecha"] + " 12:00:00") if a.get("fecha") else None
                                lote["avisos"].append(a)           # la lista que recorre el recorrido
                            lote["primera"] = True
                            if len(avisos) < li.POR_PAGINA:
                                break                               # última página
                            inicio += li.POR_PAGINA
                            dormir(random.uniform(3, 7))           # la misma pausa que usa JobSpy
                except ImportError:
                    lote["error"] = "jobspy"
                except Exception as e:
                    print(f"[linkedin] búsqueda {url}: {e}")
                    lote["error"] = str(e)
                lote["primera"] = lote["fin"] = True
                print(f"[linkedin] búsqueda lista: {resumen} -> {len(lote['avisos'])} avisos ({lote['error'] or 'ok'})")
                if self.cancelado:
                    break
            for lote in self._lotes.values():                       # si se canceló, que nadie espere
                lote["primera"] = lote["fin"] = True

        threading.Thread(target=trabajar, daemon=True).start()

    def llegan_mas(self, url):
        lote = getattr(self, "_lotes", {}).get(url)
        return bool(lote) and not lote["fin"]

    # ------------------------------------------------------------------ flujo principal
    def _correr(self):
        self.cfg = self.cargar_config()
        self.historial = li.cargar_json(li.HISTORIAL_FILE, {})
        if not self.solo_cuenta:
            self._buscar_en_fondo(busquedas.lista(self.cfg))      # arranca ya, mientras se verifica la sesión
        page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()
        self.ventana(page, mostrar=False)

        # 1) login
        self.estado("Verificando la sesión...")
        try:
            self.ir(page, li.SITIO + "/feed/")
        except Exception:
            pass
        page.wait_for_timeout(2000)
        if self.solo_cuenta:
            self.ventana(page, mostrar=True)
        if not self.logueado():
            self.emitir("login", {})
            self.ventana(page, mostrar=True)
            if "/login" not in page.url and "/checkpoint" not in page.url:
                try:
                    self.ir(page, li.SITIO + "/login")
                except Exception:
                    pass
            while not self.logueado():
                self.atender()
                self.esperar_navegador(1.5)
            page.wait_for_timeout(2000)
            self.ventana(page, mostrar=False)
            self.emitir("login_ok", {})

        # 2) cuenta, descartes y postulaciones
        self.estado("Leyendo tu cuenta...")
        cuentas_bolsa.guardar(self.plataforma, "")
        if self.solo_cuenta:
            self.emitir("cuenta_ok", {"plataforma": self.plataforma, "mail": ""})
            return
        self.desc = descartes.iniciar(self.plataforma, None, li.CONFIG_FILE, self.historial)
        self.emitir("usuario", {"mail": "", "descartados": len(self.desc)})
        try:
            self.sincronizar_postulaciones(page)
        except Frenado:
            self.frenar()
            return
        self.pag_consulta = self.ctx.new_page()
        self.pag_form = self.ctx.new_page()
        page.bring_to_front()
        self.ventana(page, mostrar=False)

        # 3) búsquedas: JobSpy (sin sesión, solo Solicitud sencilla; ya están corriendo de fondo); todos
        #    quedan "Sin revisar"
        urls = busquedas.lista(self.cfg)
        excl = [w.lower() for w in self.cfg["palabras_excluidas_titulo"]]
        cuenta = {"ok": 0, "ya": 0, "preg": 0, "desc": 0, "omit": 0, "rep": 0, "ext": 0, "err": 0, "libre": 0}
        self.emitir("grupos", {"items": []})

        def cargar(url, resumen):
            """Espera la primera página de la búsqueda de fondo y devuelve su lista, que sigue creciendo."""
            lote = self._lotes.get(url)
            if lote is None:
                return []
            while not lote["primera"]:
                self.emitir("leyendo", {"pagina": 1, "avisos": len(lote["avisos"])})
                self.atender(time.time() + 0.5)
            if lote["error"] == "jobspy":
                self.emitir("aviso", {"tipo": "error", "texto":
                            "Falta JobSpy (python-jobspy). Reinstalá la app con Setup.exe para que lo instale."})
            return lote["avisos"]

        def procesar(a):
            h = self.historial.get(a["id"])
            previo = h["estado"] if h else None
            if a["id"] in self.desc or previo == "descartado":
                return "desc", False
            if previo in li.ESTADOS_POSTULADO:
                return "ya", False
            if previo == "repetido":
                return "rep", False
            if any(w in a["titulo"].lower() for w in excl):
                return "omit", False
            if previo == "con_preguntas":
                self.agregar_con_preguntas(a)
                return "preg", False
            original = self.repetido_de_postulado(a)
            if original:
                self.registrar(a, "repetido", {"de": original.get("titulo")})
                return "rep", False
            self.agregar_libre(a)                        # se sabe si tiene preguntas al apretar Postularme
            return "libre", False

        try:
            recorrido.recorrer(self, urls, cargar, procesar, cuenta)
            recorrido.quedar_atendiendo(self)
        finally:
            self._descartar_borrador()       # si volviste al menú con un formulario abierto, no queda "En curso"
