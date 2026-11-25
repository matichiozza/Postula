"""
Mostrar / ocultar el Edge que usan los motores, sin que aparezca en pantalla ni en la barra de tareas.

Edge corre siempre con ventana normal (headless no sirve en estas bolsas). Para que el usuario no lo vea,
la ventana se oculta con Windows (ShowWindow SW_HIDE): no está en pantalla, ni minimizada, ni en la barra
de tareas, ni en Alt+Tab. Para el sitio es lo mismo que una ventana minimizada. Cuando hay que iniciar
sesión, se vuelve a mostrar.

Para encontrar las ventanas de ESTE Edge (y no las del Edge personal del usuario) se le pone a la pestaña
un título único, se busca la ventana que lo muestra y de ahí se saca el proceso: después se ocultan todas
las ventanas visibles de ese proceso (pestañas nuevas o popups que se abran más tarde también, porque
repasar() se llama seguido desde el bucle del motor).
"""
import ctypes
import time
import uuid
from ctypes import wintypes

user32 = ctypes.windll.user32
SW_HIDE, SW_SHOW = 0, 5
_EnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def _ventanas():
    """[(hwnd, pid, visible, título, clase)] de todas las ventanas de primer nivel."""
    res = []

    def cb(hwnd, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        n = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        clase = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(hwnd, clase, 64)
        res.append((hwnd, pid.value, bool(user32.IsWindowVisible(hwnd)), buf.value, clase.value))
        return True

    user32.EnumWindows(_EnumProc(cb), 0)
    return res


def _pid(m, page):
    """Proceso de Edge de este motor (se averigua una vez)."""
    if getattr(m, "_edge_pid", None):
        return m._edge_pid
    marca = "laburoia-" + uuid.uuid4().hex[:10]
    try:
        previo = page.title()
        page.evaluate("t => { document.title = t; }", marca)
        for _ in range(20):
            for hwnd, pid, _v, titulo, _c in _ventanas():
                if marca in titulo:
                    m._edge_pid = pid
                    break
            if getattr(m, "_edge_pid", None):
                break
            time.sleep(0.1)
        page.evaluate("t => { document.title = t; }", previo)
    except Exception as e:
        print(f"[ventana] no encontré la ventana de Edge: {e}")
    return getattr(m, "_edge_pid", None)


def _de_edge(pid, solo_visibles):
    return [h for h, p, vis, titulo, clase in _ventanas()
            if p == pid and clase.startswith("Chrome_WidgetWin") and titulo and (vis or not solo_visibles)]


def ocultar(m, page=None):
    pid = _pid(m, page) if page is not None else getattr(m, "_edge_pid", None)
    if not pid:
        return False
    ocultas = getattr(m, "_edge_ocultas", set())
    for h in _de_edge(pid, solo_visibles=True):
        user32.ShowWindow(h, SW_HIDE)
        ocultas.add(h)
    m._edge_ocultas = ocultas
    m._edge_oculto = True
    return True


def mostrar(m, page):
    pid = _pid(m, page)
    m._edge_oculto = False
    for h in getattr(m, "_edge_ocultas", set()):
        if user32.IsWindow(h):
            user32.ShowWindow(h, SW_SHOW)
    m._edge_ocultas = set()
    if pid:
        for h in _de_edge(pid, solo_visibles=True)[:1]:
            user32.SetForegroundWindow(h)


def repasar(m):
    """Si Edge debe estar oculto, oculta cualquier ventana suya que haya aparecido (como mucho cada 1 s)."""
    if not getattr(m, "_edge_oculto", False):
        return
    ahora = time.time()
    if ahora - getattr(m, "_edge_repaso", 0) < 1:
        return
    m._edge_repaso = ahora
    try:
        ocultar(m)
    except Exception:
        pass


def ventana(m, page, mostrar_ventana):
    """Lo que usan los motores: mostrar Edge para iniciar sesión, o esconderlo del todo."""
    try:
        cdp = m.ctx.new_cdp_session(page)
        wid = cdp.send("Browser.getWindowForTarget")["windowId"]
        # un cambio de posición solo se acepta con la ventana en estado normal
        cdp.send("Browser.setWindowBounds", {"windowId": wid, "bounds": {"windowState": "normal"}})
        if mostrar_ventana:
            mostrar(m, page)
            cdp.send("Browser.setWindowBounds", {"windowId": wid, "bounds": {
                "left": 80, "top": 40, "width": 1220, "height": 900}})
            page.bring_to_front()
        else:
            # fuera de la pantalla por si algo la vuelve a mostrar, y oculta (sin barra de tareas)
            cdp.send("Browser.setWindowBounds", {"windowId": wid, "bounds": {"left": -2400, "top": 0}})
            if not ocultar(m, page):
                cdp.send("Browser.setWindowBounds", {"windowId": wid, "bounds": {"windowState": "minimized"}})
        cdp.detach()
    except Exception as e:
        print(f"[ventana] no pude {'mostrar' if mostrar_ventana else 'esconder'} Edge: {e}")
