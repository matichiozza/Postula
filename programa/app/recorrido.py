"""
Recorrido de las búsquedas, compartido por los motores (Computrabajo, Bumeran, ZonaJobs).

Hay una sola búsqueda activa a la vez. Desde la interfaz se puede elegir otra (comando
"cambiar_busqueda"): la actual queda pausada donde estaba (su posición se guarda) y se sigue con la
elegida; al volver a una búsqueda pausada, retoma desde ese aviso. Cuando la activa termina, se pasa
sola a la siguiente que no haya terminado. Cada listado se lee recién la primera vez que esa
búsqueda se activa. Un aviso que ya se revisó en otra búsqueda no se vuelve a revisar.

Cada motor pone:
  - cargar(url, resumen) -> lista de avisos (dicts con "id", "titulo", "empresa"; el motor puede
    emitir "leyendo" mientras lee);
  - procesar(aviso) -> (clave del contador, abrio) o "corte" (se terminó la corrida, p. ej. la
    sesión se cortó). "abrio" = se abrió/postuló algo y hay que hacer pausa.

El recorrido NO postula: clasifica. Los avisos sin preguntas (o, en Computrabajo, sin revisar)
quedan en la lista con "libre": True. Los postula el usuario de a uno, o el modo Auto (apagado al
empezar), que va uno por uno con pausas. Cada motor pone postular_libre(aviso) -> "ok", "ya",
"ext", "preg", "err" o "corte" (registra en el historial; no toca la lista).
"""
import random
import time

import busquedas


def recorrer(m, urls, cargar, procesar, cuenta):
    """m: el motor (emitir, atender, pausado, cfg, nombre). Termina emitiendo "fase1_fin"."""
    m.busq = [{"url": u, "resumen": busquedas.resumen(u), "avisos": None, "pos": 0, "fin": False, "abiertos": 0}
              for u in urls]
    m.cambio = None
    m.emitir("busquedas", {"items": [{"indice": i + 1, "resumen": b["resumen"]} for i, b in enumerate(m.busq)]})
    if not m.busq:
        m.emitir("fase1_fin", cuenta)
        return
    procesados = m.procesados = set()
    fallo = False                  # alguna búsqueda no se pudo leer
    fallas_seguidas = 0
    freno = 1                      # multiplica la pausa si el sitio empieza a fallar seguido
    activa = 0
    while True:
        b = m.busq[activa]
        m.emitir("busqueda", {"indice": activa + 1, "total": len(m.busq), "resumen": b["resumen"], "url": b["url"]})
        if b["avisos"] is None:
            m.emitir("leyendo", {"pagina": 1, "avisos": 0})
            try:
                avisos = cargar(b["url"], b["resumen"])
            except Exception as e:
                if type(e).__name__ == "Cancelado":
                    raise
                print(f"[búsqueda] no pude leer {b['url']}: {e}")
                caido = any(f"HTTP {n}" in str(e) for n in (500, 502, 503, 504))
                m.emitir("aviso", {"tipo": "error", "texto":
                         f"{m.nombre} no está respondiendo (error de su servidor). Tu búsqueda está bien: probá en un rato."
                         if caido else f"No pude leer la búsqueda «{b['resumen']}». Probá de nuevo; si sigue, revisala en el menú."})
                avisos = []
                b["error"] = fallo = True
            b["avisos"] = avisos
            if not avisos and getattr(m, "sin_propios", False):
                b["sin_propios"] = True
                m.emitir("aviso", {"tipo": "info", "texto":
                         f"«{b['resumen']}» no tiene avisos propios de {m.nombre}: son todos de la otra bolsa."})
            elif not avisos and not b.get("error"):
                m.emitir("aviso", {"tipo": "error", "texto":
                         f"La búsqueda «{b['resumen']}» no trajo ningún aviso. Revisala en el menú (Búsquedas)."})
            m.emitir("listado", {"total": len(avisos), "en_otras": sum(1 for a in avisos if a["id"] in procesados)})
        else:
            # se retoma una búsqueda pausada: la barra vuelve a donde estaba
            m.emitir("listado", {"total": len(b["avisos"]), "en_otras": 0, "retoma": b["pos"]})
            m.emitir("progreso", {"hechos": b["pos"], "total": len(b["avisos"]), "busqueda": activa + 1, **cuenta, "ultimo": None})

        cambio = None
        while b["pos"] < len(b["avisos"]):
            m.atender()
            paso_auto(m)                          # con Auto activado, postula mientras se sigue leyendo
            while m.pausado and m.cambio is None:
                m.atender(time.time() + 0.5)
            if m.cambio is not None:
                pedido, m.cambio = m.cambio, None
                if 0 <= pedido < len(m.busq) and pedido != activa and not m.busq[pedido]["fin"]:
                    cambio = pedido
                    break
                continue
            a = b["avisos"][b["pos"]]
            b["pos"] += 1
            if a["id"] in procesados:            # ya revisado en otra búsqueda
                m.emitir("progreso", {"hechos": b["pos"], "total": len(b["avisos"]), "busqueda": activa + 1, **cuenta,
                                      "ultimo": None})
                continue
            procesados.add(a["id"])
            r = procesar(a)
            if r == "corte":
                m.emitir("fase1_fin", cuenta)
                return
            clave, abrio = r
            cuenta[clave] = cuenta.get(clave, 0) + 1
            if abrio or clave in ("preg", "libre"):
                b["abiertos"] += 1            # aviso nuevo (no estaba en el historial)
            if abrio:
                fallas_seguidas = fallas_seguidas + 1 if clave == "err" else 0
                if fallas_seguidas >= 2 and freno < 8:
                    freno *= 2
                    fallas_seguidas = 0
                    m.emitir("aviso", {"tipo": "info", "texto": f"{m.nombre} está fallando seguido: voy más despacio (pausa ×{freno})."})
            ultimo = {"titulo": a.get("titulo", ""), "empresa": a.get("empresa", ""), "res": clave}
            if clave == "rep":                       # para la barra "Repetidos": cuál es y a cuál repite
                det = (getattr(m, "historial", {}).get(a["id"]) or {}).get("detalle")
                ultimo.update(url=a.get("url"), de=det.get("de") if isinstance(det, dict) else None)
            m.emitir("progreso", {"hechos": b["pos"], "total": len(b["avisos"]), "busqueda": activa + 1, **cuenta,
                                  "ultimo": ultimo})
            if abrio:
                m.atender(time.time() + freno * random.uniform(m.cfg["pausa_min_seg"], m.cfg["pausa_max_seg"]))

        if cambio is not None:
            m.emitir("aviso", {"tipo": "info", "texto":
                     f"Pausé «{b['resumen']}» en el aviso {b['pos']} de {len(b['avisos'])}. Sigo con «{m.busq[cambio]['resumen']}»."})
            activa = cambio
            continue
        b["fin"] = True
        # "abiertos": avisos nuevos de esta búsqueda; el resto ya se había revisado antes (se saltea al instante)
        fin = {"indice": activa + 1, "resumen": b["resumen"], "abiertos": b["abiertos"]}
        if not b.get("error") and not b.get("sin_propios"):   # sin "total" la interfaz no dice "no trajo avisos"
            fin["total"] = len(b["avisos"])
        m.emitir("busqueda_fin", fin)
        n = len(m.busq)
        pendientes = [i for i in list(range(activa + 1, n)) + list(range(0, activa)) if not m.busq[i]["fin"]]
        if not pendientes:
            break
        activa = pendientes[0]
    m.emitir("fase1_fin", {**cuenta, "fallo": fallo})


def postulacion(m, a):
    """Datos de una postulación recién hecha, para la barra "Nuevas postulaciones" (sale del historial)."""
    h = m.historial.get(a["id"]) or {}
    det = h.get("detalle") if isinstance(h.get("detalle"), dict) else {}
    respuestas = det.get("respuestas") or {}
    return {"titulo": a.get("titulo"), "empresa": a.get("empresa"), "url": a.get("url"),
            "sin_respuestas": h.get("estado") == "postulado_sin_respuestas",
            "respuestas": [{"pregunta": (q or "").strip(), "respuesta": str(respuestas.get(str(i), ""))}
                           for i, q in enumerate(det.get("preguntas") or [])]}


def iniciar_auto(m):
    """Estado del modo Auto: siempre arranca desactivado."""
    m.auto = False
    m.auto_proximo = 0        # time.time() a partir del cual se puede postular el siguiente
    m.auto_abiertos = 0       # postulaciones intentadas por Auto en esta corrida (tiene máximo)
    m.auto_fallas = 0
    m.auto_freno = 1
    m.busq = []
    m.por_fecha = False       # la lista está ordenada por fecha: Auto sigue ese orden
    m.procesados = set()      # ids de avisos que el recorrido ya clasificó


def cmd_recuperar(m, id):
    """Restaurar un descartado desde la barra lateral, con el recorrido abierto. Si ya había pasado
    por él, vuelve a la lista; Auto no lo toca (lo descartaste una vez: se postula solo a mano)."""
    deshacer = next((e for e in m.deshacer_pila if id in e[2]), None)
    previa = deshacer and deshacer[2].get(id)
    # el contador de la cabecera sumó uno por grupo descartado: solo resta si es el principal
    contado = deshacer[1][0]["id"] == id if deshacer else id in m.procesados
    if deshacer:
        m.deshacer_pila.remove(deshacer)
    m.desc.quitar(id)
    if (m.historial.get(id) or {}).get("estado") == "descartado":
        del m.historial[id]
        m.guardar_historial()

    aviso = next((a for b in m.busq for a in (b["avisos"] or []) if a["id"] == id), None)
    lista = None
    if aviso and id in m.procesados and not any(x["id"] == id for g in m.grupos.values() for x in g):
        aviso = dict(aviso)
        aviso["manual"] = True
        if (previa and previa.get("estado") == "con_preguntas") or m.necesita_form(aviso):
            m.registrar(aviso, "con_preguntas")
            m.agregar_con_preguntas(aviso)
            lista = "preg"
        else:
            m.agregar_libre(aviso)
            lista = "libres"
    m.emitir("recuperado", {"id": id, "lista": lista, "contado": contado,
                            "gid_deshacer": deshacer[0] if deshacer else None})


def cmd_ordenar(m, activo):
    m.por_fecha = bool(activo)


def _antiguedad(m, gid):
    return min((x["antiguedad"] for x in m.grupos[gid] if x.get("antiguedad") is not None), default=float("inf"))


def cmd_auto(m, activo):
    m.auto = bool(activo)
    m.emitir("auto", {"activo": m.auto})


def paso_auto(m):
    """Si Auto está activado, no hay pausa y ya pasó la espera, postula UN aviso libre."""
    if not m.auto or m.pausado or time.time() < m.auto_proximo:
        return
    orden = sorted(m.orden, key=lambda g: _antiguedad(m, g)) if m.por_fecha else m.orden
    gid = next((g for g in orden
                if m.grupos[g][0].get("libre") and not any(x.get("manual") for x in m.grupos[g])), None)
    if gid is None:
        return
    maximo = m.cfg["max_postulaciones_por_corrida"]
    if m.auto_abiertos >= maximo:
        m.emitir("aviso", {"tipo": "info", "texto":
                 f"Llegué al máximo de {maximo} postulaciones automáticas por corrida (config.json). Apago Auto."})
        cmd_auto(m, False)
        return

    grupo = m.quitar_grupo(gid)
    a = grupo[0]
    original = m.repetido_de_postulado(a)
    if original:
        for x in grupo:
            m.registrar(x, "repetido", {"de": original.get("titulo")})
        m.emitir("grupo_quitado", {"gid": gid, "motivo": "repetido", "titulo": a["titulo"], "auto": True,
                                   "texto": "Salteado, ya te postulaste a uno igual:", "url": a.get("url"),
                                   "empresa": a.get("empresa"), "de": original.get("titulo")})
        return

    m.emitir("auto_en", {"gid": gid})
    m.auto_abiertos += 1
    try:
        res = m.postular_libre(a)
    except Exception as e:
        if type(e).__name__ == "Cancelado":
            raise
        print(f"[auto] {a['id']}: {e}")
        m.registrar(a, "error", str(e)[:300])
        res = "err"

    if res in ("ok", "ya"):
        m.marcar_resto(grupo, a, "repetido")
    motivo, texto = {"ok": ("postulado", "✅ Te postulaste."), "ya": ("ya_postulado", "Ya estabas postulado."),
                     "preg": ("preguntas", "Tiene preguntas:"), "ext": ("externo", "Se postula en otro sitio:")
                     }.get(res, ("error", "No se pudo postular:"))
    m.emitir("grupo_quitado", {"gid": gid, "motivo": motivo, "titulo": a["titulo"], "texto": texto, "auto": True,
                               "url": a.get("url"), "postulacion": postulacion(m, a) if res == "ok" else None})
    if res == "preg":                       # pasa a "Con preguntas" (después de quitarlo de la otra lista)
        for x in grupo:
            m.registrar(x, "con_preguntas")
            m.agregar_con_preguntas(x)
    if res == "corte":
        cmd_auto(m, False)

    m.auto_fallas = m.auto_fallas + 1 if res == "err" else 0
    if m.auto_fallas >= 2 and m.auto_freno < 8:
        m.auto_freno *= 2
        m.auto_fallas = 0
        m.emitir("aviso", {"tipo": "info", "texto":
                 f"{m.nombre} está fallando seguido: voy más despacio (pausa ×{m.auto_freno})."})
    m.auto_proximo = time.time() + m.auto_freno * random.uniform(m.cfg["pausa_min_seg"], m.cfg["pausa_max_seg"])


def quedar_atendiendo(m):
    """Terminado el recorrido: atender las decisiones del usuario (y Auto) hasta que se cierre."""
    while True:
        m.atender(time.time() + 0.3)
        m.pausado = False                    # ya no hay recorrido que pausar
        paso_auto(m)


def cmd_cambiar_busqueda(m, indice):
    """Elegir otra búsqueda desde la interfaz (indice empieza en 1). Si estaba en pausa, sigue."""
    m.cambio = int(indice) - 1
    if m.pausado:
        m.pausado = False
        m.emitir("pausa", {"pausado": False})
