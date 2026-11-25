"""
Avisos descartados para siempre ('n' / "Descartar para siempre"), uno por plataforma. La app es de
un solo usuario, así que no hay carpetas por usuario:

    datos/<plataforma>/descartes.json   ->  {"<id del aviso>": {titulo, empresa, url, motivo, fecha}}

Lo usan los cuatro postuladores. No depende de que la plataforma tenga "Ocultar aviso": lo que
está acá no se vuelve a mostrar. Se exporta e importa con datos_usuario.py.
"""
import json
import re
from datetime import datetime

import rutas  # noqa: E402
RE_MAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")


def buscar_mail(dato, excluir=()):
    """Primer mail que aparezca en un texto o en un JSON (dict/list), ignorando los de los
    dominios de `excluir` (los del propio sitio, de soporte, etc.). Dentro de un dict prioriza
    las claves que contienen 'mail'."""
    if isinstance(dato, dict):
        for k, v in dato.items():
            if "mail" in str(k).lower():
                m = buscar_mail(v, excluir)
                if m:
                    return m
        dato = list(dato.values())
    if isinstance(dato, list):
        for v in dato:
            m = buscar_mail(v, excluir)
            if m:
                return m
        return None
    if isinstance(dato, str):
        for m in RE_MAIL.findall(dato):
            m = m.lower()
            if not any(m.endswith(d) for d in excluir):
                return m
    return None


def iniciar(plataforma, detectado, config_file, historial, estados=("descartado",)):
    """Arma los Descartes de la plataforma. El mail de la cuenta ya no decide nada (hay un solo
    usuario): solo se recuerda en config.json (mail_usuario) para mostrarlo en la app.

    datos/<plataforma>/descartes.json es LA lista de descartes:
      - si todavía no existe, se arma con los descartes que había en historial.json (migración);
      - si existe, manda ella: un aviso marcado "descartado" en el historial que ya no está en el
        archivo (porque lo borraste de ahí) se olvida del historial y vuelve a aparecer como nuevo.
    El historial se corrige en memoria (el dict que se pasa); se guarda cuando el script guarde."""
    cfg = json.loads(config_file.read_text(encoding="utf-8")) if config_file.exists() else {}
    mail = (detectado or "").lower() or cfg.get("mail_usuario")
    if detectado and cfg.get("mail_usuario") != mail:
        cfg["mail_usuario"] = mail
        config_file.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    desc = Descartes(plataforma, mail)
    if desc.existia:
        olvidados = [oid for oid, h in historial.items() if h.get("estado") in estados and oid not in desc]
        for oid in olvidados:
            del historial[oid]
        if olvidados:
            print(f"♻ {len(olvidados)} avisos que habías descartado ya no están en descartes.json: vuelven a aparecer.")
    else:
        desc.importar_historial(historial, estados)
    print(f"👤 Cuenta: {mail or '(sin mail)'} ({len(desc)} avisos descartados para siempre)")
    return desc


def archivo(plataforma):
    return rutas.datos_bolsa(plataforma) / "descartes.json"


def todos():
    """{plataforma: {id: aviso}} de las plataformas que tienen descartes (para exportar)."""
    res = {}
    for p in rutas.PLATAFORMAS:
        a = rutas.DATOS / p / "descartes.json"
        if a.exists():
            avisos = Descartes(p).avisos
            if avisos:
                res[p] = avisos
    return res


def listar(plataforma):
    """Los descartados de una plataforma, más nuevos primero (para Ajustes > Avisos descartados)."""
    d = Descartes(plataforma)
    items = [{"id": oid, "titulo": a.get("titulo") or "", "empresa": a.get("empresa") or "",
              "url": a.get("url") or "", "fecha": a.get("fecha") or ""} for oid, a in d.avisos.items()]
    items.sort(key=lambda x: x["fecha"], reverse=True)
    return items


def recuperar(plataforma, ids):
    """Saca avisos de los descartados: vuelven a aparecer en el próximo recorrido. Si el historial
    todavía los tiene como "descartado", iniciar() los olvida (este archivo manda). -> cuántos sacó."""
    d = Descartes(plataforma)
    sacados = 0
    for oid in ids or []:
        if d.avisos.pop(str(oid), None) is not None:
            sacados += 1
    if sacados:
        d._guardar()
    return sacados


def sumar(plataforma, avisos):
    """Agrega avisos descartados (de un archivo importado) sin borrar los que ya hay. -> cuántos sumó."""
    d = Descartes(plataforma)
    nuevos = 0
    for oid, aviso in (avisos or {}).items():
        if str(oid) not in d.avisos and isinstance(aviso, dict):
            d.avisos[str(oid)] = aviso
            nuevos += 1
    if nuevos or not d.existia:
        d._guardar()
    return nuevos


class Descartes:
    def __init__(self, plataforma, mail=None):
        self.mail = mail              # solo para mostrar en qué cuenta estás
        self.archivo = archivo(plataforma)
        self.existia = self.archivo.exists()
        self.avisos = self._leer() if self.existia else {}

    def _leer(self):
        """Archivo vacío = sin descartes. Si está roto, se guarda una copia aparte y se arranca de cero
        (en vez de frenar la app)."""
        texto = self.archivo.read_text(encoding="utf-8", errors="replace").strip()
        if not texto:
            return {}
        try:
            datos = json.loads(texto)
            if isinstance(datos, dict):
                return {str(k): v for k, v in datos.items()}
        except ValueError:
            pass
        copia = self.archivo.with_name(f"{self.archivo.stem}.roto-{datetime.now():%Y%m%d-%H%M%S}.json")
        self.archivo.replace(copia)
        self.archivo.write_text("{}", encoding="utf-8")   # sigue existiendo: el archivo manda (ver iniciar)
        print(f"⚠ {self.archivo.name} no se pudo leer; lo guardé como {copia.name} y arranco sin descartes.")
        return {}

    def __contains__(self, aviso_id):
        return str(aviso_id) in self.avisos

    def __len__(self):
        return len(self.avisos)

    def _guardar(self):
        self.archivo.parent.mkdir(parents=True, exist_ok=True)
        self.archivo.write_text(json.dumps(self.avisos, ensure_ascii=False, indent=2), encoding="utf-8")

    def agregar(self, aviso, url=None, motivo="descartado"):
        self.avisos[str(aviso["id"])] = {
            "titulo": aviso.get("titulo"), "empresa": aviso.get("empresa"), "url": url or aviso.get("url"),
            "motivo": motivo, "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._guardar()

    def quitar(self, aviso_id):
        """Deshace un descarte (lo usa el "deshacer" de la app)."""
        if self.avisos.pop(str(aviso_id), None) is not None:
            self._guardar()

    def importar_historial(self, historial, estados=("descartado",)):
        """Copia los descartes que ya estaban en el historial.json de la plataforma (de antes de
        que existieran los archivos de descartes). Devuelve cuántos agregó."""
        nuevos = 0
        for oid, h in historial.items():
            if h.get("estado") in estados and oid not in self.avisos:
                self.avisos[oid] = {"titulo": h.get("titulo"), "empresa": h.get("empresa"), "url": h.get("url"),
                                    "motivo": h["estado"], "fecha": h.get("fecha")}
                nuevos += 1
        if nuevos:
            self._guardar()
        return nuevos
