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
  - procesar(aviso) -> (clave del contador, abrio) o "corte" (se terminó la corrida, p. ej. máximo
    de postulaciones o la sesión se cortó). "abrio" = se abrió/postuló algo y hay que hacer pausa.
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
    procesados = set()
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
                m.emitir("aviso", {"tipo": "error", "texto": f"No pude abrir la búsqueda «{b['resumen']}». Revisala en el menú."})
                avisos = []
            b["avisos"] = avisos
            if not avisos:
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
            if abrio or clave == "preg":
                b["abiertos"] += 1            # aviso nuevo (no estaba en el historial)
            if abrio:
                fallas_seguidas = fallas_seguidas + 1 if clave == "err" else 0
                if fallas_seguidas >= 2 and freno < 8:
                    freno *= 2
                    fallas_seguidas = 0
                    m.emitir("aviso", {"tipo": "info", "texto": f"{m.nombre} está fallando seguido: voy más despacio (pausa ×{freno})."})
            m.emitir("progreso", {"hechos": b["pos"], "total": len(b["avisos"]), "busqueda": activa + 1, **cuenta,
                                  "ultimo": {"titulo": a.get("titulo", ""), "empresa": a.get("empresa", ""), "res": clave}})
            if abrio:
                m.atender(time.time() + freno * random.uniform(m.cfg["pausa_min_seg"], m.cfg["pausa_max_seg"]))

        if cambio is not None:
            m.emitir("aviso", {"tipo": "info", "texto":
                     f"Pausé «{b['resumen']}» en el aviso {b['pos']} de {len(b['avisos'])}. Sigo con «{m.busq[cambio]['resumen']}»."})
            activa = cambio
            continue
        b["fin"] = True
        # "abiertos": avisos nuevos de esta búsqueda; el resto ya se había revisado antes (se saltea al instante)
        m.emitir("busqueda_fin", {"indice": activa + 1, "resumen": b["resumen"], "total": len(b["avisos"]),
                                  "abiertos": b["abiertos"]})
        n = len(m.busq)
        pendientes = [i for i in list(range(activa + 1, n)) + list(range(0, activa)) if not m.busq[i]["fin"]]
        if not pendientes:
            break
        activa = pendientes[0]
    m.emitir("fase1_fin", cuenta)


def cmd_cambiar_busqueda(m, indice):
    """Elegir otra búsqueda desde la interfaz (indice empieza en 1). Si estaba en pausa, sigue."""
    m.cambio = int(indice) - 1
    if m.pausado:
        m.pausado = False
        m.emitir("pausa", {"pausado": False})
