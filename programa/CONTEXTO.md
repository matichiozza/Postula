# Laburo IA: postuladores automáticos de empleo

Documento para que otra persona u otro chat de IA entienda el proyecto completo y pueda seguir trabajando sin perder nada. **Actualizado el 24-11-2026** (búsquedas de Computrabajo armadas desde listas). Si sos un chat nuevo, leé primero **"Cómo trabajar con el usuario"** y **"Pendientes"**.

## Qué es

Herramientas para postularse automáticamente a avisos de empleo en Argentina:

| Carpeta | Bolsa | Cómo funciona por dentro | En la app de escritorio |
|---|---|---|---|
| `computrabajo/` | ar.computrabajo.com | HTML + formularios ASP.NET (plataforma Redarbor) | **Sí** |
| `bumeran/` | bumeran.com.ar | API JSON interna (plataforma Jobint/Navent) | **Sí** (24-11-2026) |
| `zonajobs/` | zonajobs.com.ar | La misma API que Bumeran, con otro `x-site-id` | **Sí** (24-11-2026) |
| `empleosit/` | empleosit.com.ar | HTML + formulario AJAX (plataforma SmartJobBoard) | No (consola) |

Hay dos formas de usarlo:
- **App de escritorio "Laburo IA"** (`programa/app/`, `Laburo IA.exe` en la raíz, con el logo): interfaz visual, todo con el teclado. **Por ahora solo Computrabajo.** Es donde se está trabajando.
- **Scripts de consola** (`programa/bolsas/<bolsa>/postulador.py`): uno por bolsa, se corren a mano con `python postulador.py` desde su carpeta (ya no hay accesos directos "Postular en…"; pedido del usuario).

## Estado actual (24-11-2026)

- **La app de Computrabajo está en uso real y funciona:** login, recorrido aviso por aviso con postulación automática, formularios de preguntas, descartes, varias búsquedas, Edge escondido. El usuario la usó varias veces (por ejemplo, una corrida con 35 postulaciones nuevas).
- Los 4 scripts de consola funcionan (verificados en vivo entre el 19 y el 22-11-2026).
- **Bumeran y ZonaJobs ya están en la app** (24-11-2026, `app/motor_jobint.py`). Probados contra el sitio real con postulación SIMULADA (sin sesión: el usuario había reinstalado de cero). **Falta la primera prueba real con la sesión del usuario** (iniciar sesión y postularse a unos pocos avisos).
- Próximo paso: EmpleosIT a la app.

---

## Cómo trabajar con el usuario (importante)

- **Idioma:** todo en **español rioplatense** (vos, "postulate", etc.), incluidos los mensajes cortos entre pasos. El usuario lo pidió explícitamente. Los comentarios del código también están en español.
- **Prioridad de la app:** que las decisiones se tomen **rápido y con el teclado** (flechas, letras, Enter, Esc). Interfaz clara, sin términos confusos.
- **Probar antes de dar algo por terminado**, pero **solo lo necesario** ("no hace falta que pruebes todo"). Contar qué se probó y qué no.
- **Nunca postularse a avisos reales para probar.** En Computrabajo **abrir el link de postulación de un aviso sin preguntas ya te postula**. Para probar se usan:
  - motores con `abrir_postulacion`/`postular` simulados (monkeypatch) y copias de `datos/` en una carpeta temporal;
  - la ventana real de la app fuera de la pantalla (`x=-3000`) con `evaluate_js`, haciendo **copia de seguridad** de cualquier archivo real que se toque y restaurándolo al final;
  - Edge headless (`channel="msedge"`) contra `app/ui/index.html` con estado inyectado, para capturas de pantalla.
- **El perfil de Edge (`perfil_edge/`) no se puede usar mientras la app está abierta.** Antes de probar algo con la sesión real, pedirle al usuario que cierre la app. Si hace falta que inicie sesión, pedírselo.
- **Decisiones del usuario que no hay que revertir:**
  - Los descartes son **solo locales** (`datos/<bolsa>/descartes.json`). **No usar "Ocultar aviso" de Computrabajo** ni nada que cambie la cuenta en la web.
  - `n` = descartar **para siempre** (no existe "no por ahora").
  - En ZonaJobs, `omitir_duplicados_de_bumeran` queda en `false`.
- **No evadir anti-bots.** Si un sitio bloquea (Cloudflare, captchas que se repiten), no se usan técnicas para esquivarlo. Por eso **Indeed quedó descartado** (su verificación entraba en loop). LinkedIn se investigó pero no se implementó (sus términos prohíben la automatización y el riesgo para la cuenta es alto). Automatizar puede ir contra los términos de estos sitios: por eso hay pausas aleatorias y un máximo por corrida.
- **Privacidad:** `perfil_edge/` (sesiones), los tokens y las cookies no se comparten ni se mandan a ningún servicio externo.

---

## Instalar en otro equipo

1. Copiar la carpeta **`Laburo IA`** completa (`Setup.exe` y `programa/`; `Laburo IA.exe` no hace falta, lo vuelve a crear Setup). Todo lo personal está en **`programa/datos/`**: descartes, historiales y config de cada bolsa, y `perfil.json` (nombre, sueldo y zona). Para un usuario nuevo, no copiar `datos/` (o usar la opción "Borrarlos" de Setup).
   - **Forma recomendada (24-11-2026): Exportar / Importar desde la app.** En la instalación vieja, "Exportar" (`E`) guarda un `.json` con nombre, sueldo, zona y avisos descartados; en la nueva, "Importar" (`I`) los trae. Ver "Exportar e importar tus datos" más abajo.
2. **Las sesiones (`datos/<bolsa>/perfil_edge/`) no sirven en otra PC:** Edge cifra las cookies con la cuenta de Windows de cada equipo. Hay que iniciar sesión de nuevo en cada bolsa (la app abre Edge en el login y sigue sola).
3. Doble clic en **`Setup.exe`** (24-11-2026; reemplaza a `instalar.bat`). Es un **asistente con ventana nativa de Windows** (WinForms): Bienvenida → Opciones → Instalando (barra de progreso y detalle) → Listo ("Abrir Laburo IA ahora"). Instala **en el lugar** (no copia archivos) y necesita `programa/` al lado. Pasos:
   1. Busca Python ≥ 3.9 (`py -3`, `python`, `%LOCALAPPDATA%\Programs\Python\Python3*`, `%ProgramFiles%\Python3*`; descarta el alias de Microsoft Store). Si no hay, pregunta y lo instala (3.12 con winget; sin winget, el instalador de python.org).
   2. `pip install playwright pywebview` (sin `--upgrade`, para no cambiar versiones que andan) y verifica que se importen.
   3. Verifica Microsoft Edge (si falta, solo avisa).
   4. Anota el python.exe en **`datos/python.txt`** (lo usa `Laburo IA.exe`). Borra los viejos accesos "Postular en <Bolsa>.lnk" si quedaron.
   5. **Desempaqueta `Laburo IA.exe` en la raíz** (viaja adentro de `Setup.exe` como recurso `LaburoIA.exe`; si ya estaba, lo reemplaza) y, si se tilda en Opciones, crea un acceso "Laburo IA" en el escritorio. Pedido del usuario (24-11-2026): antes de instalar, la raíz tiene solo `Setup.exe` y `programa/`, para no confundir cuál abrir.
   6. Si se tilda "Borrarlos" (aparece solo si hay datos de un usuario anterior): borra de `datos/<bolsa>/` `perfil_edge/`, `historial.json`, `descartes.json` y `config.json` (búsquedas), y `datos/perfil.json` (pide confirmación y recuerda exportar antes desde Ajustes). Es lo mismo que "Empezar de cero" de la app. Se hace **antes** de guardar el nombre nuevo.
   - **Pide el nombre** ("¿Cómo te llamás?", obligatorio; se precarga si ya había uno) y lo guarda en `datos/perfil.json` usando `comun/perfil.py` (corre Python con el nombre en la variable de entorno `LABURO_NOMBRE`, para no lidiar con comillas). La app saluda con "¡Hey <primer nombre>, postulate!". Modo silencioso: `/nombre "Mati"`.
   - **No pregunta el sueldo** (pedido del usuario): en una instalación nueva la app muestra sueldo y zona vacíos hasta que se completan en "Tus datos" (o se importan).
   - **Ya no crea accesos "Postular en <Bolsa>"** (pedido del usuario): los scripts de consola se corren a mano si hace falta (`python postulador.py` en `programa/bolsas/<bolsa>/`).
   - Detalle de cada instalación en `datos/registros/setup.log`.
4. **`Setup.exe` se compila** con `programa/instalador/compilar.bat` (primero compila el lanzador en `%TEMP%` y lo mete adentro de Setup.exe con `/resource:...,LaburoIA.exe`; en la raíz solo queda Setup.exe) (usa el `csc.exe` de .NET Framework 4 que trae Windows: solo C# 5, nada de `out _`, `$"..."` ni `?.`). Fuentes: `instalador/Setup.cs` y `instalador/Lanzador.cs`. Íconos: `Laburo IA.exe` usa `app/recursos/logo.ico` (el maletín); **`Setup.exe` usa `instalador/setup.ico`** (una caja abierta con una flecha verde que entra, para no confundirlo con la app; fuente `setup.svg`). El asistente muestra el logo de la app embebido (`logo.png`). Para probar sin clics: `Setup.exe /silencioso [/borrar] [/escritorio]`, y `Setup.exe /capturas <carpeta>` guarda una imagen de cada pantalla sin instalar (la ventana aparece un instante en pantalla). **Desde Git Bash no pasar `/silencioso` ni `/capturas`**: los convierte en rutas y abre el asistente normal; usar PowerShell. El asistente escala a mano según los DPI (`P()`/`Z()`): el escalado automático de WinForms estiraba los textos con pantallas al 125 %.
   - `Laburo IA.exe` (lanzador): lee `programa/datos/python.txt`, abre `pythonw app.py` en `programa/app/` (con `PYTHONDONTWRITEBYTECODE=1`) y termina. Si falta `python.txt` dice "ejecutá Setup.exe". No tiene rutas fijas: si se mueve la carpeta sigue andando.
   - Sin firma digital: si se pasan por internet, Windows SmartScreen puede advertir la primera vez ("Más información" → "Ejecutar de todas formas").
5. Versiones: playwright 1.65.2, pywebview 6.2.1, pythonnet 3.2.1. En esta PC el Python es `%LOCALAPPDATA%\Programs\Python\Python312\` (el 3.14 que mencionaban versiones viejas de este documento ya no está). Ante la duda, mirar `datos/python.txt`.

---

## Estructura de archivos

Pedido del usuario (24-11-2026): en la raíz **solo** tres cosas, y adentro de `programa/` el **código separado de los datos**, sin archivos sueltos que hagan ruido.

```
Laburo IA/
├─ Setup.exe                      instalador (asistente de Windows; ícono de caja)
├─ Laburo IA.exe                  el ejecutable de la app (ícono del maletín). NO viene suelto: lo crea Setup.exe al instalar
└─ programa/
   ├─ CONTEXTO.md                 este documento
   ├─ app/                        la app de escritorio
   │  ├─ app.py                   ventana pywebview + API para la interfaz
   │  ├─ motor_computrabajo.py    lógica de Computrabajo para la app (hilo aparte)
   │  ├─ recursos/                logo.svg (original), logo.ico (ventana, barra de tareas, .exe), logo.png (asistente)
   │  └─ ui/                      index.html, estilo.css, app.js, logo.svg (copia: pywebview solo sirve ui/), logos/ (logos originales de las 4 bolsas: <bolsa>.svg/png y <bolsa>-icono.*)
   ├─ bolsas/<bolsa>/             código de cada bolsa (computrabajo, bumeran, zonajobs, empleosit)
   │  ├─ postulador.py            script de consola (la app reutiliza el de computrabajo)
   │  └─ filtros.json, actualizar_filtros.py   (solo computrabajo) categorías, provincias y ciudades
   ├─ comun/                      módulos compartidos
   │  ├─ rutas.py                 dónde está cada cosa (todos los demás lo usan; no hay rutas armadas a mano)
   │  ├─ busquedas.py             links de búsqueda de cada plataforma (y armarlos desde listas)
   │  ├─ descartes.py             descartes por usuario
   │  ├─ perfil.py                sueldo y zona: leer, guardar, detectar preguntas
   │  └─ sueldo_neto.py           bruto -> neto estimado (Argentina)
   ├─ datos/                      TODO lo personal (borrar esta carpeta = empezar de cero)
   │  ├─ perfil.json              {"nombre": "...", "sueldo": N o null, "zona": "..."} (antes "Sueldo bruto pretendido.txt")
   │  ├─ python.txt               el Python que usa Laburo IA.exe (lo escribe Setup.exe)
   │  ├─ <bolsa>/config.json      búsquedas, pausas, máximos, mail_usuario (solo para mostrar), etc.
   │  ├─ <bolsa>/descartes.json   avisos descartados para siempre (antes datos/usuarios/<mail>/<bolsa>.json)
   │  ├─ <bolsa>/historial.json   estado de cada aviso procesado
   │  ├─ <bolsa>/perfil_edge/     sesión de Edge (PRIVADO, no sirve en otra PC)
   │  └─ registros/               app.log (lo que imprime el motor, se pisa al abrir), errores.log (último error fatal), setup.log
   └─ instalador/                 Setup.cs, Lanzador.cs, compilar.bat (CRLF), setup.svg/.ico
```

- Los módulos se importan agregando `programa/comun` a `sys.path` (`app.py`, `motor_computrabajo.py` y cada `postulador.py`). La app y los scripts ponen `sys.dont_write_bytecode = True` para que no aparezcan carpetas `__pycache__`.
- Si se agrega un archivo nuevo, va en el lugar que le corresponde según esta tabla (código en `app/`, `bolsas/` o `comun/`; datos en `datos/`), con la ruta sacada de `rutas.py`.

---

## Módulos compartidos (`programa/comun/`)

Los scripts y la app los importan agregando la raíz a `sys.path`.

### `descartes.py`: descartes por usuario
- **La app es de un solo usuario** (pedido del usuario, 24-11-2026): no hay carpetas por mail. Lo que se descarta ("para siempre") se guarda en `datos/<plataforma>/descartes.json` como `{id: {titulo, empresa, url, motivo, fecha}}`. Ese aviso no se vuelve a mostrar. No depende de la web.
- `iniciar(plataforma, mail_detectado, config_file, historial)`: el mail ya **no decide nada** ni se pide; si se detecta, se recuerda en `mail_usuario` del `config.json` solo para mostrarlo en la cabecera de la app. Devuelve un `Descartes` (`in`, `len`, `agregar`, `quitar`, `importar_historial`). También: `todos()` (para exportar) y `sumar(plataforma, avisos)` (para importar, sin borrar los que hay).
- De dónde sale el mail (solo para mostrar): Bumeran y ZonaJobs de `datosPostulanteResumido`, Computrabajo de `/configuration`, EmpleosIT del campo `email[original]` de `/edit-profile/`.
- **`descartes.json` es la fuente de verdad:**
  - si el archivo no existe, se arma con los `descartado` que había en `historial.json` (migración);
  - si existe, un `descartado` del historial que no está en `descartes.json` se borra del historial (en memoria; se guarda en la siguiente escritura) y el aviso **vuelve a aparecer como nuevo**. Así, **vaciar el archivo reinicia los descartes** (lo hizo el usuario el 22-11-2026 y funcionó).
  - archivo vacío = sin descartes; JSON roto = se renombra a `.roto-<fecha>.json`, se deja `{}` y se sigue (antes tiraba la app).

### `perfil.py`: nombre, sueldo y zona
- Guarda en `datos/perfil.json`: `{"nombre": "...", "sueldo": N o null, "zona": "..."}`; `guardar(sueldo=None, zona=None, nombre=None)` cambia solo lo que se pasa (antes era `Sueldo bruto pretendido.txt` en la raíz; se migró el 24-11-2026). Los scripts de consola también toman el sueldo de ahí (`perfil.cargar()`).
- `cargar()` → `{"sueldo": int|None, "zona": str}`; `guardar(sueldo, zona)`.
- `tipo_pregunta(titulo)` → `"sueldo"` / `"zona"` / `None` por palabras clave:
  - sueldo: `salari`, `remuneraci`, `sueldo`, `pretensi`, `pretendid`;
  - zona: `zona`, `reside`, `residencia`, `vivís`, `barrio`, `localidad`, `domicilio`, `dónde viv`, `ubicad`, `ubicación`…, **salvo** que la pregunta diga `disponib`, `traslad`, `viajar`, `movilizar`, `oficina`, `presencial`, `podés ir` (ej.: "¿podés ir a zona norte?").
- Solo se precargan **preguntas abiertas**; las de opciones las elige el usuario.

### `sueldo_neto.py`: neto estimado
- `calcular(bruto)` → `{bruto, aportes: {Jubilación, PAMI, Obra social}, con_tope, ganancias, neto, vigencia}` (montos mensuales).
- Aportes 17% (11% jubilación + 3% PAMI + 3% obra social) sobre el bruto con **tope SIPA**.
- Ganancias 4ta categoría: se anualiza con **13 sueldos** (12 + aguinaldo, que también paga), se restan aportes, ganancia no imponible y deducción especial, se aplica la escala del art. 94 y se reparte en 13. Supone soltero, sin hijos, sin otras deducciones ni cuota sindical.
- **Los valores vencen:** `TOPE_APORTES` cambia todos los meses (resolución ANSES) y la escala y deducciones cada semestre (ARCA). Están cargados con valores de **noviembre 2026** (tope $4.861.685,38, Res. ANSES 304/2026) y **anuales 2026** (GNI $6.019.671,36, deducción especial $28.894.422,56; escala art. 94 anual 2026 tomada de fussionconsultora.com, que cita a ARCA). Con 13 sueldos, Ganancias empieza en ~$3,24 M bruto; la prensa dice ~$3,5 M porque usa 12.

### `busquedas.py`: links de búsqueda
- Cada plataforma guarda en su `config.json` **`urls_busqueda`** (lista) y **`url_busqueda`** (el primero, por compatibilidad con los scripts que leen uno solo).
- `PLATAFORMAS`: hosts válidos de cada bolsa, el parámetro de página que se quita (`p` en Computrabajo, `page` en las otras) y un link de ejemplo.
- `validar(plataforma, url)`: solo acepta links del host de la plataforma (Computrabajo: **solo `ar.computrabajo.com`**, ni `candidato.`, ni otros países); rechaza links de un aviso suelto (`/ofertas-de-trabajo/`) o de la cuenta (`/candidate/`); agrega `https://` si falta y saca `#…` y el número de página.
- `guardar(plataforma, urls)`: ignora vacíos, deduplica, y si un link no sirve devuelve `{"ok": False, "error": "Link N: …", "fila": N-1}`.
- `lista(cfg)`: los links de un config (lee los dos formatos). `resumen(url)`: nombre legible. En Computrabajo lo saca de `filtros.json` ("“desarrollador” · Informática / Telecomunicaciones — Palermo, Capital Federal"); si no lo reconoce (links con otros filtros), lo arma del texto del link ("Trabajo de contador en cordoba").
- La interfaz hace la **misma validación al instante** (`problemaLink` en `app.js`, con `hosts` en `PLATAFORMAS`) y Python la repite al guardar.
- **Armar búsquedas desde listas (solo Computrabajo, 24-11-2026):** `filtros(plataforma)` lee `bolsas/computrabajo/filtros.json`; `armar(plataforma, {puesto, categoria, provincia, ciudad})` → `{ok, url, resumen}`; `slug(texto)` ("Diseñador gráfico" → `disenador-grafico`, igual que la web). Formatos de link verificados en vivo:
  - `/empleos-de-<categoría><lugar>` · `/trabajo-de-<puesto>[-de-<categoría>]<lugar>` · `/empleos<lugar>`
  - `<lugar>` = nada (todo el país) | `-en-remoto` | `-en-<provincia>` | `-en-<provincia>-en-<ciudad>` (el "sem" del filtro de la web; ojo, Formosa es `-en-formosa-capital`).
  - **Un slug inventado no da error** (`/empleos-de-cualquier-cosa` trae avisos tomándolo como palabra clave): por eso categoría y lugar se eligen de listas y `armar` rechaza valores que no están en `filtros.json`.
  - Otros filtros de la web, no incluidos en las listas: `?pubdate=1|3|7|15|30|99(urgente)`, `?sal=1..7`, `?cont=N`, sufijos `-sin-experiencia`, `-jornada-completa`, `-jornada-partida`, `-hibrido`.

---

## App de escritorio (`app/`)

### Tecnología
- **pywebview** (ventana propia con WebView2, título "Laburo IA", 1280×820, mínimo 900×600) + interfaz HTML/CSS/JS en `app/ui/` (sin frameworks, íconos SVG en línea, tema oscuro y claro según Windows).
- Se abre con `pythonw.exe app.py` (sin consola). **`redirigir_salida()`** manda `stdout` y `stderr` a `datos/registros/app.log` en UTF-8. Es obligatorio: con pythonw la salida es cp1252 y un `print` con emoji tiraba la app (pasó el 22-11-2026).
- Errores fatales: se muestran en la app y quedan en `datos/registros/errores.log`.

### `app.py`: API que la interfaz llama con `window.pywebview.api.<método>`
`iniciar(plataforma)`, `detener()` (corta la plataforma y cierra su Edge; join de hasta 25 s), `comando(nombre, datos)` (pone un comando en la cola del motor), `perfil()` / `guardar_perfil({sueldo, zona})`, `busqueda(plataforma)` / `guardar_busqueda(plataforma, urls)` (no deja cambiar búsquedas con una plataforma corriendo), `neto(bruto)`, `abrir_url(url)` (solo https, en el navegador del sistema). Los atributos con `_` no se exponen. `MOTORES = {"computrabajo": MotorComputrabajo}`.

### `motor_computrabajo.py`
- Carga `bolsas/computrabajo/postulador.py` con `importlib` como `pc` (los 4 scripts se llaman igual) y reutiliza sus funciones (`Computrabajo.listar`, `abrir_postulacion`, `leer_preguntas`, `enviar_respuestas`, `es_repetido`, etc.).
- Corre en un hilo. **Python → interfaz:** `emitir(tipo, datos)` → `evaluate_js("window.app.evento(...)")`. **Interfaz → Python:** cola `comandos`, que el motor atiende entre aviso y aviso y durante las pausas (`atender(hasta)`). Así **se puede decidir mientras el recorrido postula**. `cancelado = True` (Esc / cerrar) hace que `atender` lance `Cancelado`.
- **Tres pestañas del mismo Edge:** principal (login, listado, recorrido), formulario (abrir y enviar preguntas) y consulta (descripción de los avisos con `fetch` dentro de `ar.computrabajo.com`, `DETALLE_JS`).
- Comandos: `pausa`, `detalle`, `descartar`, `deshacer`, `abrir_form`, `enviar`.
- Eventos: `estado`, `login`, `login_ok`, `usuario` (mail si se leyó, y cantidad de descartados), `busqueda`, `leyendo`, `listado`, `grupos`, `grupo_nuevo`, `grupo_act`, `grupo_quitado`, `deshecho`, `progreso`, `pausa`, `detalle`, `form`, `form_error`, `aviso` (cartel), `fase1_fin`, `fatal`.

### Flujo de una corrida (`_correr`)
1. **Edge escondido:** se lanza con `--window-position=-2400,0` (fuera de la pantalla; **headless no sirve: Computrabajo devuelve 403**) y `ventana(page, mostrar=False)` lo manda fuera de la pantalla por CDP y lo **oculta con Windows** (`app/ventana_edge.py`, `ShowWindow(SW_HIDE)`): no aparece ni en pantalla ni en la barra de tareas ni en Alt+Tab. Las ventanas de *este* Edge se encuentran poniéndole a la pestaña un título único y tomando su proceso; `repasar()` (llamado al inicio de `atender`) oculta cualquier ventana nueva de ese proceso. Para el login se vuelve a mostrar. Si no encuentra la ventana, minimiza como antes.
2. **Login:** abre `/candidate/home`. Si no está logueado, emite `login`, **muestra Edge** (en 80,40, adelante) y espera revisando **todas las pestañas** (`logueado()`): si alguna está en `/candidate/` listo; si alguna está en una página de login (`secure.*`, `/account/` o un sitio que no es Computrabajo, como Google) espera; si no, abre `/candidate/home` para confirmar. Después vuelve a esconder Edge. Los cambios de URL quedan en `app.log` como `[login] …`.
3. **Mail** (`ct.mail()` desde `/configuration`; si no, `config.json`; si no, se pide en la interfaz) → `descartes.iniciar`.
4. Abre las pestañas de consulta y formulario y vuelve a esconder Edge (`bring_to_front` lo des-minimiza, pero queda fuera de la pantalla).
5. **Búsqueda por búsqueda** (`busquedas.lista(cfg)`): emite `busqueda`, lee el listado (`leyendo` por página, `listado {total, en_otras}`) y recorre sus avisos. Un aviso que ya salió en una búsqueda anterior de la misma corrida no se repite. Si una búsqueda no trae avisos, avisa.
6. **Un solo recorrido, aviso por aviso** (contadores entre paréntesis):
   - en `descartes.json` (o `descartado` en el historial) → se saltea (`desc`);
   - ya postulado según el historial → (`ya`);
   - otro estado final (`externo`, `repetido`) o palabra excluida del título → (`omit`);
   - `con_preguntas` en el historial → va a "Para decidir" **sin volver a abrirlo** (`preg`; ver "Pendientes": puede estar desactualizado);
   - repite uno ya postulado (`es_repetido`) → se registra `repetido` (`rep`);
   - si no: **abre el link de postulación** → `postulado` (`ok`), `ya_postulado` (`ya`), `preguntas` (va a "Para decidir", `preg`), `externo` (`ext`) o error (`err`, se reintenta en otra corrida);
   - pausa aleatoria entre `pausa_min_seg` y `pausa_max_seg` (hoy 2–4 s) **solo después de abrir un link**; con 2 errores seguidos la pausa se duplica (hasta ×8) y se avisa;
   - tope `max_postulaciones_por_corrida` (links abiertos);
   - `progreso` en cada aviso.
7. `fase1_fin` y queda atendiendo las decisiones del usuario hasta que vuelva al menú o cierre.

### Logo e identidad en Windows (24-11-2026)
- Logo: maletín blanco (el trabajo) con un destello amarillo (la IA) sobre un cuadrado verde redondeado. Original en `app/recursos/logo.svg`; `logo.ico` (16 a 256 px, entradas PNG) y `logo.png` se generan renderizando el SVG con Edge.
- En el menú y la cabecera reemplaza a la vieja "L" (`img.logo`). Hay una copia en `app/ui/logo.svg` porque pywebview sirve la interfaz solo desde `ui/` (`../recursos/` no carga).
- Ventana y barra de tareas: `webview.start(icon=logo.ico)` y, antes de crear la ventana, `SetCurrentProcessExplicitAppUserModelID("LaburoIA.App")` (`identidad_windows()` en `app.py`). Sin eso Windows mostraba el ícono de Python y agrupaba la app con pythonw.

### Interfaz
- **Menú** (diseño "F · minimalista centrado", elegido por el usuario el 24-11-2026 entre 7 propuestas; las propuestas están en el artefacto https://claude.ai/artifact/4vJyJp1vrN4ZCrqQoM4YzA). Siempre en tema oscuro:
  - Logo de la app, el saludo grande y "¿En qué bolsa buscamos hoy?". Arriba a la derecha, **Ajustes** (botón de texto con ícono).
  - **Las 4 bolsas como íconos cuadrados con su logo original** (`ui/logos/<bolsa>-icono.*`, sacados de sus páginas públicas el 24-11-2026; el de EmpleosIT es el símbolo recortado de su logo). La elegida tiene borde verde; las que no están en la app, más apagadas y con "· pronto" en el nombre. Un clic elige; un clic en la ya elegida entra. **Las que no están elegidas se ven tenues** (opacidad .4, como EmpleosIT), y la elegida se enciende (v1.0.0).
  - Debajo, **tus búsquedas como etiquetas** ("qué" en negrita y "dónde" en gris, sacados del resumen) y la etiqueta "Editar búsquedas" (o "Elegir qué buscar" si no hay ninguna), un botón grande **"Empezar en <bolsa>"** (deshabilitado si la bolsa todavía no está en la app) y la nota "Los N avisos que descartaste se saltean solos" (`busqueda()` de `app.py` devuelve `descartados`).
  - **Fondo animado:** tres manchas difuminadas (`.fondo .mancha`) con un `radial-gradient` de los colores de la marca elegida (`colores` en `PLATAFORMAS` de `app.js`: Computrabajo azul + naranja, Bumeran azul + magenta + celeste, ZonaJobs naranjas, EmpleosIT azules), que se mueven lento (28–40 s, `ease-in-out`, ida y vuelta). Los colores son variables `--c1..--c3` registradas con `@property`, así que al cambiar de bolsa el degradé hace una transición de 1,2 s en vez de saltar. Con "reducir movimiento" de Windows no se anima.
  - **Editor de búsquedas** (diseño "D", elegido por el usuario el 24-11-2026; v1.0.0): ventana con la **lista de búsquedas a la izquierda** ("+ Nueva búsqueda" y, abajo, "Pegar un link de la web") y **a la derecha la que se edita**. Cada búsqueda se arma **Por categoría** (categoría obligatoria + Dónde: provincia/Remoto y ciudad + "Afinar con una palabra (opcional)", borde punteado) o **Por palabra clave** (palabra obligatoria + Dónde, sin categoría). Las búsquedas guardadas se abren con sus campos (`busquedas.desarmar()`: link → {categoria, provincia, ciudad, puesto}; `leer()` lo devuelve como `campos`); las que no se pueden armar con las listas (pegadas a mano con otros filtros) se editan como link. "Quitar esta búsqueda", "Cerrar", "Guardar" (las nuevas que quedaron vacías se ignoran; los links pegados a mano se prueban en la web). Se puede guardar sin ninguna búsqueda. Siempre oscuro. Lo mismo para las tres bolsas.
  - **Saludo:** "¡Hey <primer nombre>, postulate!"; sin nombre, "¿Dónde buscamos hoy?".
  - Si falta sueldo o zona, debajo aparece "Completá tu sueldo pretendido y tu zona en Ajustes →" (clic: abre Ajustes).
  - Si la plataforma no tiene ninguna búsqueda guardada (por ejemplo, después de "Empezar de cero"), `Enter` abre el editor de búsquedas en vez de arrancar.
- **Ajustes** (pantalla propia, 24-11-2026; `Esc` o "Volver" regresa al menú y guarda lo que estabas escribiendo):
  - **Tus datos:** tu nombre (se puede cambiar acá; también lo ponen Setup.exe y el importar), sueldo bruto (con puntos de miles mientras se escribe y, debajo, **neto estimado en vivo** con aportes y Ganancias; al pasar el mouse, el detalle) y zona de residencia. Se guardan solos al salir de cada campo (`Enter` pasa al siguiente; `Esc` sale del campo).
  - **Copia de tus datos:** Exportar (`E`) e Importar (`I`) (ver "Exportar e importar tus datos").
  - **Avisos descartados** (24-11-2026): la tarjeta dice cuántos hay por bolsa; "Ver y recuperar" abre una ventana con una pestaña por bolsa (solo las que tienen), la lista con casillas (título, empresa, fecha), "Seleccionar todos" / "Deseleccionar todos" y "Recuperar N". Recuperar = `descartes.recuperar()` saca los ids de `descartes.json`; en el próximo recorrido `iniciar()` los olvida también del historial y vuelven a aparecer como nuevos (`api.descartados` / `api.recuperar_descartados`; no se puede con una plataforma corriendo).
  - **Empezar de cero:** "Borrar todos los datos" abre una confirmación donde hay que **escribir BORRAR** (el botón queda deshabilitado hasta entonces; también ofrece "Exportar primero", `Ctrl+E`). Llama a `datos_usuario.borrar_todo()`: borra todo `datos/` (perfil, y de cada bolsa config/búsquedas, historial, descartes y la sesión de Edge, más los registros viejos) **salvo `python.txt`** (es de la instalación: sin él no abre la app) **y `app.log`** (lo tiene abierto la app). Solo desde el menú: con una plataforma corriendo se rechaza (su Edge tiene la sesión abierta). Si algo no se pudo borrar, lo dice.
  - (El recuadro "Tus datos" que estaba en el menú y el de 3 pasos se sacaron a pedido del usuario el 24-11-2026.)
  - **Atajos de teclado: solo se MUESTRAN durante el recorrido** (pedido del usuario, 24-11-2026). En el menú, Ajustes y el editor de búsquedas no se ve ninguna tecla (`boton()` agrega el `<kbd>` solo si `E.activo`), pero siguen funcionando: `← →` elegir bolsa, `Enter` entrar, `B` búsquedas, `A` ajustes, `E`/`I` exportar/importar en Ajustes, `Esc` volver.
- **Pantalla de trabajo:**
  - Cabecera: plataforma, mail y cantidad de descartados; título del recorrido ("Leyendo el listado…", "Revisando los avisos uno por uno", "Listo: te postulaste a N avisos nuevos"); botón **Pausar** (`P`); línea **"Búsqueda 2 de 3 · <resumen>"**; barra y "40 de 120" (de la búsqueda actual); último resultado.
  - 4 recuadros de totales: **Postulados ahora**, **Para decidir**, **Ya te habías postulado**, **Salteados** (al pasar el mouse: descartados, omitidos, repetidos, externos, errores).
  - Izquierda: lista **Para decidir** (avisos con preguntas; los repetidos se agrupan con "×N"). Derecha: detalle del aviso (empresa, ubicación, de qué búsqueda salió si hay varias, etiquetas y descripción) o el formulario.
  - Al cambiar de aviso, el panel arranca **desde arriba**. En el formulario, la pregunta activa se **centra** en el panel con desplazamiento suave (hay un espacio al final para centrar también la última y el botón Enviar).
  - Registro del recorrido (`L`), con un separador por búsqueda.
- **Teclas en la lista:** `↑ ↓` / `j k` moverse, `PgUp PgDn Home End`, `S` o `Enter` postularme (abre el formulario), `N` o `Supr` descartar para siempre (instantáneo; el motor lo registra después), `Z` deshacer el último descarte, `O` ver en la web, `L` registro, `P` pausar/seguir, `Esc` volver al menú (pide confirmación si el recorrido sigue).
- **Teclas en el formulario:** número de la opción (elige y pasa a la siguiente), `↑ ↓` y `Enter`, `Tab` cambiar de pregunta, `Ctrl+Enter` enviar, `Esc` cancelar (no descarta). Las preguntas abiertas de sueldo y zona vienen precargadas (se pueden cambiar). Si hay un tipo de pregunta no soportado, ofrece abrir el aviso en la web.
- Si el aviso ya no tiene preguntas o ya estabas postulado, al apretar `S` se resuelve solo y sale de la lista.
- Al volver al menú, los eventos que lleguen tarde se ignoran (`E.activo`), y lo que falle mientras se cierra Edge no se muestra como error.

### Correcciones del 24-11-2026 (pedidas por el usuario)
- **Links pegados a mano se prueban al guardar** (`busquedas.probar` → `api.verificar_busqueda`): se abren en un Edge temporal fuera de la pantalla (sin la sesión) y se cuentan los avisos. Computrabajo: total del `h1` / `article.box_offer`, y si redirige a la portada = 0. Bumeran/ZonaJobs: total de la respuesta de `searchV2` que pide la propia web; `/404` = 0. Con 0 avisos la fila queda en rojo ("Ese link no trae ningún aviso. ¿Está bien copiado?") y no se guarda. Los links armados con las listas no se prueban (ya son válidos).
- "Puesto o palabra clave **(opcional)**" en el editor (placeholder: "Vacío = toda la categoría").
- **Recuadros del recorrido:** "Postulaciones automáticas" (sin preguntas, las hizo la app; incluye las que al apretar S ya no tenían preguntas) y "Con tus respuestas" (formularios que mandaste; el motor emite `grupo_quitado` con `con_form: true`). Después: Para decidir, Ya te habías postulado, Salteados. La UI cuenta `form` y `autoExtra` aparte de `ok` del motor.
- **Tecla `H` (recorrido):** panel "Postulaciones con tus respuestas": de `historial.json`, los `postulado` con `detalle.preguntas` (más nuevos primero), con cada pregunta y respuesta y "Ver el aviso en la web" (`api.postulaciones_con_respuestas`). Desde esta fecha, en las preguntas de opciones se guarda el TEXTO elegido (antes, el número de la opción).
- **Fondo compartido:** `.fondo` es fijo detrás del menú y de Ajustes; los colores van en `:root` (`--c1..--c3`, `@property`). Ajustes es siempre oscuro (redefine los tokens en `#ajustes`).
- Menú sin el ícono de la app arriba (el saludo queda centrado) y pie "Made by Matichiozza" muy tenue (`.firma`).
- **Sueldo neto:** si la pregunta pide el sueldo "neto/neta/en mano/de bolsillo", se precarga el neto estimado (`perfil.precarga`, redondeado a miles; `precarga_tipo: "sueldo_neto"`), si no el bruto. Lo usan los tres motores.

### Robustez (problemas reales ya resueltos)
- **`page.url` desactualizado:** Playwright solo procesa eventos cuando se lo llama; con `time.sleep` la app seguía viendo `/login` aunque el usuario ya había entrado. Para esperar se usa `page.wait_for_timeout` (`esperar_navegador`). Esto hacía que el login "no avanzara" (resuelto el 22-11-2026).
- **`net::ERR_ABORTED`:** a veces una carga se corta porque el sitio redirige o recarga solo. `MotorComputrabajo.ir(page, url)` reintenta hasta 3 veces y da por buena la carga si la pestaña igual quedó en el sitio. `listar()` reintenta una vez cada página.
- **Velocidad:** `abrir_postulacion` ya no espera `networkidle`. Tras `domcontentloaded` consulta cada 300 ms `_resultado_postulacion()` y devuelve apenas hay un resultado claro (hasta 15 s si no). Las páginas cargan en 0,3–2 s; lo que más pesa es la pausa (2–4 s).

---

## Bumeran y ZonaJobs en la app (`app/motor_jobint.py`, 24-11-2026)

- `MotorJobint` (+ `MotorBumeran`, `MotorZonaJobs`): mismos eventos y comandos que `motor_computrabajo.py` (la interfaz es la misma), pero todo por la API usando `bolsas/<bolsa>/postulador.py` (clase `Bumeran` o `Portal`: `api`, `logueado`, `filtros_de_url`, `buscar_todos`, `ids_ya_postulados`, `ficha`, `postular`, `responder`; y `es_externo`, `id_postulacion_de`, `valor_opcion`, `texto_opcion`).
- **Un solo Edge con una pestaña** (perfil `datos/<bolsa>/perfil_edge`, fuera de la pantalla; se muestra solo para el login en `/login`). Las consultas de la interfaz (descripción, formulario) se atienden en el mismo hilo, entre aviso y aviso.
- Recorrido aviso por aviso (contadores como en Computrabajo, más `otro`):
  - `portal` distinto del propio → `otro` ("es de la otra bolsa"; Bumeran y ZonaJobs comparten avisos);
  - descartado → `desc`; ya postulado (`estadoPostulacion` del listado, "Mis postulaciones" o historial) → `ya`;
  - estados finales / palabra excluida → `omit`; `con_preguntas` de antes → "Para decidir" sin abrir;
  - **repetidos** con la misma lógica que Computrabajo (`es_repetido`: misma empresa + Ref. o Jaccard de palabras) → `rep`;
  - `tienePreguntas` o `salarioObligatorio` sin sueldo cargado → directo a "Para decidir" **sin abrir nada** (lo dice el listado);
  - si no: ficha → ya postulado / externo / con preguntas / `postularV2` (con el sueldo de Ajustes). 401/403 corta el recorrido; 429 espera 2 minutos. Pausa aleatoria `pausa_min_seg`–`pausa_max_seg` (4–9 s) después de cada ficha.
- Formulario: preguntas `simple` → abiertas (hasta 2000), `choice` → opciones (valor = id de la opción). Si el aviso pide salario y no hay sueldo en Ajustes, se agrega la pregunta "Salario bruto pretendido". Enviar = `postularV2` → id de la postulación → `respuestas`; si fallan las respuestas queda `postulado_sin_respuestas` y se avisa.
- Historial: clave = id del aviso (texto), `url` = `<sitio>/empleos/<id>.html`; los formularios guardan `{preguntas, respuestas}` como Computrabajo (los usa la tecla H).
- **Búsquedas desde listas**: `bolsas/bumeran/actualizar_filtros.py` pide a la API de búsqueda (sin sesión) las facetas: 26 áreas, 23 provincias y sus localidades (Buenos Aires: 203; solo las que tienen avisos). Escribe el mismo `filtros.json` en `bolsas/bumeran/` y `bolsas/zonajobs/`. "Capital Federal (CABA)" se agrega también como provincia propia (sem `buenos-aires/capital-federal`), porque para la plataforma es una localidad de Buenos Aires.
- Formato de los links (verificado en los dos sitios): `/[en-<provincia>/[<localidad>/]]empleos[-area-<área>][-modalidad-remoto][-busqueda-<palabras>].html`. El orden importa (`-modalidad-remoto` después de `-busqueda-` se lee como palabras); las palabras sin tildes ni ñ; área inventada = 0 avisos; link roto = `/404`. `busquedas._armar_jobint` / `_leer_jobint` (resumen legible).
- **Probado el 24-11-2026 contra el sitio real, SIN sesión y con `postularV2`/`respuestas` SIMULADOS** (`login`, "ya postulados" también simulados): Bumeran, Capital Federal + Tecnología: 206 avisos, 25 postulaciones simuladas, 1 repetido, 2 para decidir (descripción real, 3 preguntas reales, envío y registro OK, descartar/deshacer OK). ZonaJobs: 8 simuladas, 1 con formulario ("remuneración neta pretendida": de ahí la precarga del neto). Las búsquedas armadas trajeron avisos reales (206, 5, 14, 97, 10). **Falta probar con la sesión real.**

## Lo común a los scripts de consola

- **Comandos** (desde la carpeta de cada bolsa): `python postulador.py`, `--simular` (solo lista, no se postula) y `--limite N` (como máximo N postulaciones en la fase 1).
- **Sesión:** `datos/<bolsa>/perfil_edge/`. La primera vez el usuario inicia sesión a mano en la ventana y el script lo detecta. Bumeran y ZonaJobs exigen la cookie `token_auth_postulante` y que `GET /api/candidates/datosPostulanteResumido` devuelva datos; Computrabajo, terminar en `/candidate/`; EmpleosIT, que aparezca el link de `logout`. Después minimiza Edge (`minimizar_ventana()`, CDP) y sigue funcionando minimizado.
- **Nunca se cierra de golpe:** si no hay ofertas nuevas lo dice; al final, y ante un error inesperado (con el detalle), espera "Presioná Enter para cerrar".
- **Dos fases:** primero se postula a todo lo que no tiene preguntas. Después pregunta si se quiere seguir con los avisos con formulario y, por cada uno, ofrece `s` (sí: hace las preguntas por consola y envía), `n` (no: **lo descarta para siempre**) o `q` (terminar; lo que queda aparece en la próxima corrida).
- **Salario:** se toma de `datos/perfil.json` (lo que se cargó en la app); si no hay, de `salario_pretendido` del `config.json`. En las preguntas de salario, Enter lo completa. (La zona solo la precarga la app.)
- **Búsquedas:** el script de **Computrabajo** recorre todos los links de `urls_busqueda`. **Bumeran, ZonaJobs y EmpleosIT todavía usan solo `url_busqueda`** (el primero).
- **`historial.json`:** registra cada aviso procesado. Los estados finales no se reintentan; `error` y `con_preguntas` sí.
- **`config.json`:** búsquedas, salario, pausas aleatorias, máximo por corrida, palabras a excluir del título, `mail_usuario`, más opciones propias de cada bolsa.

---

## Computrabajo (`computrabajo/`)

Plataforma Redarbor. Es la única que está en la app; el motor de la app reutiliza este script.

### Uso y configuración
```
python postulador.py              # corrida normal
python postulador.py --simular    # solo lista los avisos, sin postularse
python postulador.py --limite 10  # como máximo 10 avisos en la fase 1
```
`config.json` (valores por defecto en `DEFAULT_CONFIG`): `urls_busqueda` / `url_busqueda`, `salario_pretendido`, `pausa_min_seg` 2, `pausa_max_seg` 4, `max_postulaciones_por_corrida` 150, `max_paginas_listado` 50, `palabras_excluidas_titulo`, `omitir_repetidos` true, `umbral_repetidos` 0.85, `mail_usuario`. Hoy la búsqueda del usuario es `https://ar.computrabajo.com/trabajo-de-desarrollador-en-capital-federal`.

### Diferencias clave con Bumeran y ZonaJobs
- **No hay API JSON.** Todo es HTML del servidor (ASP.NET MVC). Se navega con Edge (Playwright) y se lee y completa el HTML.
- **No se sabe de antemano qué aviso tiene preguntas:** se descubre al abrir el link de postulación.
- **Abrir el link de postulación de un aviso sin preguntas ya te postula.** No hay confirmación. Por eso `--simular` es la única forma de ver los avisos sin postularse.

### Sitios y sesión
- Listado y fichas: `https://ar.computrabajo.com` (se leen sin sesión y sin Cloudflare, pero **headless da 403**).
- Área del candidato: `https://candidato.ar.computrabajo.com`.
- Login: `https://secure.computrabajo.com/Account/Login` (OpenID Connect, client `redarbor.computrabajo.ac.web.client`). Después del login a veces deja al usuario en la portada y no en el área de candidato.
- La cookie `AspNet.SharedCookie` no sobrevive al cerrar Edge; `idsrv` e `idsrv.session` de `secure.computrabajo.com` sí, y con ellas vuelve a loguear solo.
- Por eso la detección de login no mira cookies: abre `/candidate/home` y comprueba que la URL final empiece con `https://candidato.ar.computrabajo.com/candidate/`.
- Mail de la cuenta: en `/configuration`.

### Listado
- Paginación `?p=2`, `?p=3`… (20 avisos por página; se corta cuando una página no trae avisos nuevos). `listar()` agrega `&p=N` si el link ya tiene parámetros.
- Cada aviso: `<article class="box_offer" data-id="<ID>">`, título en `h2 a` (`/ofertas-de-trabajo/oferta-de-trabajo-de-...-<ID>`), empresa en `[offer-grid-article-company-url]`, ubicación en el segundo `p`.
- El ID es un hex de 32 caracteres (ej.: `B2CCEBF2F65D037C61373E686DCF3405`).
- Ficha del aviso: `[div-link="oferta"]`, con `.tag` y párrafos (la app la lee con `DETALLE_JS`). Al final del texto se cuela texto de la página que no es del aviso ("Avísame con ofertas similares", "Denunciar empleo"…).

### Flujo de postulación
Link: `https://candidato.ar.computrabajo.com/match/?oi=<ID>&p=57&idb=1&d=32` (el del botón "Postularme", `data-href-offer-apply`). Redirige `/match/` → `/acceso/?rfl=...` → `/apply/?oi=<ID>&...` → y termina en:

| Termina en | Significa |
|---|---|
| `/candidate/postapply?oi=...` o "Te postulaste correctamente" | **Postulado** (sin preguntas). |
| "Ya te postulaste a esta oferta" | Ya estabas postulado. |
| `/candidate/kq?oi=...` con `form[action*="/candidate/kq"]` | Tiene **preguntas** (killer questions). **Todavía no se postuló.** |
| fuera de `computrabajo.com` | Externo (se postula en la web de la empresa). |
| otra cosa | `desconocido` → `error`. Pasó con "Help Desk Jr." (`FECE5F1ADF37642E61373E686DCF3405`): `/candidate/kq` → `/apply/?oi=<id corto>` → `/candidate/home`, sin quedar postulado. |

### Formulario de preguntas (`/candidate/kq`)
- Formulario ASP.NET con `__RequestVerificationToken`, ocultos (`EncryptedCvId`, `EncryptedOfferId`, …) y `KillerQuestions[i]` (`.Id`, `.Title`, `.Type`, …).
- **Tipo 1 (abierta):** `textarea[name="KillerQuestions[i].OpenQuestion"]` (maxlength 500).
- **Tipo 2 (cerrada):** radios `KillerQuestions[i].ClosedQuestion` con `value` 0, 1…; texto en el `<label>` y en `KillerQuestions[i].DataOptions[j].Answer`.
- Envío: se completan los campos en la página y se hace clic en `#btnKiller` ("Enviar mi CV"); así el token y los ocultos van como los generó la web. Éxito si termina en `/candidate/postapply` o aparece "Te postulaste correctamente".
- Otros tipos (checkboxes) **no están soportados**: se saltea el aviso (en la app, se ofrece abrirlo en la web).

### Flujo del script de consola
1. `asegurar_login()`: abre `/candidate/home`; si no está en el área de candidato, espera (con `wait_for_timeout`, no `time.sleep`) y si cae en la portada vuelve a abrir `/candidate/home`.
2. Mail y descartes (`descartes.iniciar`).
3. Lista todas las búsquedas (sin repetir avisos).
4. Filtra: en `descartes.json`, estados finales del historial (`postulado`, `ya_postulado`, `externo`, `descartado`, `repetido`) y palabras excluidas. Los `con_preguntas` de corridas anteriores pasan directo a la fase 2.
5. **Fase 1:** `abrir_postulacion()` por aviso, con pausa. Registra `postulado`, `ya_postulado`, `con_preguntas`, `externo` o `error`.
6. **Fase 2:** agrupa repetidos; por grupo ofrece `s`, `n` o `q`; vuelve a abrir el link, lee las preguntas, las hace por consola y envía.

### Avisos repetidos
Las empresas publican la misma oferta varias veces con distinto ID. `es_repetido(a, b, umbral)`: **misma empresa** (normalizada) y
- el mismo código `Ref. NNNN` en los dos títulos (común en consultoras como ADN), o
- sin código, títulos normalizados (sin acentos, sin "/a" ni "(a)", sin signos) con casi las mismas **palabras**: Jaccard ≥ `umbral_repetidos` (0.85).

Se comparan palabras y no letras a propósito: por letras, "Consultor SAP SD Senior", "SAP TD" y "SAP CO" salían iguales, y son módulos distintos.

Uso (`omitir_repetidos: true`): si un aviso repite uno ya postulado, se registra `repetido` y no se abre; los avisos con preguntas se agrupan y se muestra **uno por grupo** (en la app, "×N"). Postularse a uno marca el resto como `repetido`; descartarlo descarta todo el grupo.

### "Ocultar aviso" (investigado el 22-11-2026, NO se usa)
**Decisión del usuario: no se oculta nada en la cuenta de Computrabajo**; los descartes son solo de `datos/<bolsa>/descartes.json`. Queda documentado por si alguna vez se quiere:
- `POST https://candidato.ar.computrabajo.com/candidate/hidden/addhiddenoffer` (con credenciales, form-urlencoded) con `idOffer=<ID>` y `lstf=<lista actual>` → JSON `{success, id, hiddenOffers}`. Des-ocultar: `/candidate/hidden/removehiddenoffer` con `id` (el del ocultamiento). **Sin encabezados extra** (por ejemplo `X-Requested-With`), porque es un pedido entre dominios y el navegador lo rechaza por CORS.
- La lista es de la cuenta (`/candidate/hidden/`, `[data-hidden-offer-container][id-offer]`), máximo 100. El listado igual trae los ocultos (la web los difumina con la clase `hide_offer`). La web guarda una copia en `localStorage` (`hide_<pi>_<#ic>`).

### Verificado en vivo
- 20-11-2026: login y re-login automático; listado de 297 avisos; postulación sin preguntas ("administrador/a de sistemas"); "Ya te postulaste…" al repetir; lectura y **envío** de un formulario ("Consultor de Preventa", respuestas "<sueldo>" y "SI").
- 22–23-11-2026 (app): corridas reales completas, con postulaciones automáticas y formularios enviados desde la app.

### Categorías, provincias y ciudades (`filtros.json`)
- Lo arma **`bolsas/computrabajo/actualizar_filtros.py`** (`python actualizar_filtros.py`, unos 2 minutos). Lee solo páginas públicas con un perfil de Edge **temporal** fuera de la pantalla: no usa `perfil_edge/`, se puede correr con la app abierta.
- Categorías: de `/empleos-por-categoria/` (22; los nombres "Construccion" y "Mercadotécnia" se corrigen al guardar). Provincias: del filtro "Provincia" de `/empleos-en-capital-federal` (25, sin "Extranjero"). Ciudades: del filtro "Ciudad" de `/empleos-en-<provincia>` (~245; CABA 44 barrios, GBA 82). La ciudad capital se muestra como "<Provincia> (capital)".
- **La web solo lista las ciudades que tienen avisos en ese momento**, así que conviene volver a correrlo cada tanto. Relevado el 24-11-2026.
- `/empleos-por-ciudad/` tiene ~226 ciudades más, pero con slugs viejos (`pto.-madryn` en vez de `pto-madryn`): no se usa.

### Comparación con la web (24-11-2026, sin postularse)
Se compararon 10 búsquedas armadas por la app (`busquedas.armar` + `Computrabajo.listar`) contra lo que da la web usando su buscador o sus filtros: Informática–Palermo, Administración–Córdoba capital, Ventas–Rosario, Contabilidad–San Isidro, Medicina–Mendoza, Atención a clientes–La Plata, RRHH–Neuquén capital, Almacén–Remoto, Ingeniería–Rosario y "desarrollador"–Capital Federal. En las 10: **mismo link, mismo total de avisos** y todos los avisos de la primera página de la web estaban en lo que leyó la app. En una corrida, Administración–Córdoba leyó 112 de 114; releída página por página dio 114 sin repetidos (avisos que se corren de página mientras se lee). Para probar se bloquearon por las dudas `/match/`, `/apply/` y `/candidate/kq`.
- Detalle para pruebas: el buscador de la web sugiere con `ul.autocomplete li[data-autocomplete-item-selectable-url]`; el primer clic tras abrir un Edge nuevo a veces no responde (cartel de la primera visita). El interruptor "Remoto" lleva a `data-url` de `#remote`.

### Exportar e importar tus datos (`comun/datos_usuario.py`, 24-11-2026)
- Para reinstalar de cero sin perder nada. En **Ajustes**, tarjeta "Copia de tus datos": **Exportar** (`E`) abre el diálogo "Guardar como" de Windows (sugiere `Laburo IA - datos de <nombre>.json`) y **Importar** (`I`) el de "Abrir". Diálogos de pywebview (`create_file_dialog`, `webview.FileDialog.SAVE/OPEN`).
- **Probado por el usuario el 24-11-2026:** exportó, reinstaló con "Borrarlos" (Setup.exe) e importó: volvieron nombre, sueldo, zona y los 89 descartes de Computrabajo.
- El archivo: `{"app": "Laburo IA", "tipo": "datos-de-usuario", "version": 1, "exportado": "...", "nombre", "sueldo", "zona", "descartes": {"computrabajo": {...}, "bumeran": {...}}}, "busquedas": {"computrabajo": ["<link>", …], …}}`. **Las búsquedas viajan desde el 24-11-2026** (pedido del usuario).
- **Importar reemplaza** nombre, sueldo y zona (solo los que vienen completos) y **suma** los descartes y las **búsquedas** a los que haya (no borra; importar dos veces no duplica; una búsqueda que no es válida para su bolsa se ignora). Rechaza archivos que no tengan `"tipo": "datos-de-usuario"`; los exportados antes de que viajaran las búsquedas se importan igual. No se puede con una plataforma corriendo.
- No viajan: sesiones de Edge (no sirven en otra PC) e historiales.
- Probado el 24-11-2026 sobre copias: 89 descartes de Computrabajo + nombre, sueldo y zona exportados e importados en un `datos/` vacío; un aviso importado se saltea al iniciar.

### Si Computrabajo cambia el HTML
Revisar los selectores: `article.box_offer`, `[offer-grid-article-company-url]`, `form[action*="/candidate/kq"]`, `KillerQuestions[i].*`, `#btnKiller`, `[div-link="oferta"]`, y los textos "Te postulaste correctamente" / "Ya te postulaste".

---

## Bumeran (`bumeran/`)

### Objetivo y uso
Se postula a los avisos de un listado de Bumeran (por defecto: Tecnología, Sistemas y Telecomunicaciones en Capital Federal). Primero los que no tienen formulario; después, si el usuario quiere, los que tienen preguntas, respondiéndolas por consola. Omite avisos de ZonaJobs (u otro portal) y los que derivan a sitios externos.
```
python postulador.py | --simular | --limite 10
```
`config.json`: `url_busqueda` (cualquier listado: el script **captura el body de búsqueda que arma la propia web**, así que sirve con cualquier combinación de filtros), `salario_pretendido` (si es `null`, los avisos con salario obligatorio pasan al grupo con formulario), `pausa_min_seg`, `pausa_max_seg`, `max_postulaciones_por_corrida`, `palabras_excluidas_titulo`, `mail_usuario`.

### Por qué usa un navegador visible (decisión importante)
- La API (`/api/...`) está detrás de **Cloudflare**: `curl`/`requests` y Chromium o Edge **headless** reciben **403**. **Edge en ventana normal sí funciona.**
- Se descartó imitar la huella TLS de Chrome (`curl_cffi`, etc.): es evadir la protección. **No seguir ese camino.**
- Solución: Edge visible con perfil persistente y **todas las acciones con `fetch()` dentro de la página** (`page.evaluate`), con los mismos headers que la web. Sin clics: rápido y estable. La ventana se puede minimizar, no cerrar.

### Autenticación
- Cookie **`token_auth_postulante`** (también `refresh_token_auth_postulante` y `token_expiration_auth_postulante_milis`); `fetch` al mismo origen las manda sola.
- Header **`x-session-jwt`** (de `localStorage.sessionJwt`; las respuestas pueden traer uno nuevo y se vuelve a guardar) y siempre **`x-site-id: BMAR`**.
- Login detectado por la cookie (`Bumeran.logueado()`) más `datosPostulanteResumido`.

### Endpoints (relativos a `https://www.bumeran.com.ar`)
Sacados del bundle JS de la web (`/candidate/static/js/main.*.js`) y verificados en vivo.
- **Buscar:** `POST /api/avisos/searchV2?pageSize=100&page=0&sort=RECIENTES`, body `{"filtros":[{"id":"area","value":"tecnologia-sistemas-y-telecomunicaciones"},{"id":"localidad","value":"argentina|buenos-aires|capital-federal"},{"id":"provincia","value":"argentina|buenos-aires"}]}`. Respuesta `{number, size, total, content: [...]}`; por aviso: `id`, `titulo`, `empresa`, `portal` (`bumeran`/`zonajobs`; se omite lo que no es `bumeran`), `tienePreguntas`, `salarioObligatorio`, y con sesión `estadoPostulacion` (`"REALIZADA"` si ya te postulaste).
- **Ficha:** `GET /api/candidates/fichaAvisoNormalizada/{idAviso}` → `aviso.preguntas`: `{"simple": {id, texto}}` (texto libre, hasta 2000) o `{"choice": {id, texto, opciones: [{id, opcion}]}}`; `redireccionURL` (externo si no es null); `origenAviso` (`PORTAL`, `HIRING_ROOM` o `ZONAJOBS`; **solo se omite `ZONAJOBS` o si hay `redireccionURL`**; los `HIRING_ROOM` se postulan normal, verificado el 21-11-2026). Con sesión, la raíz trae `postulacion` si ya estás postulado.
- **Postularse:** `POST /api/candidates/aviso/{idAviso}/postularV2` con `{"salarioPretendido": <sueldo>, "actualizarSalario": false, "utmOrigen": null, "preguntasObligatorias": false, "feria": false, "origenPostulacion": null}` → `200 {"estado":"realizada","id":<id de postulación>}`. Si ya estabas postulado: `400` genérico.
- **Respuestas del formulario:** `POST /api/candidates/aviso/{idPostulacion}/respuestas` (**id de la postulación**, no del aviso) con `[{"preguntaId": "…", "respuesta": "…"}]`; en `choice`, la respuesta es el **id de la opción como string**. OK → `200` vacío. Flujo: `postularV2` → `id` → `respuestas`.
- **Mis postulaciones:** `GET /api/candidates/postulaciones?pageSize=30&page=N&sort=fechaPostulacion`. Máximo 30 por página aunque se pida más (hay que paginar), y **nunca informa más de 250**: es solo un respaldo; la fuente principal es `estadoPostulacion` del listado.
- **Mail:** `GET /api/candidates/datosPostulanteResumido`.

### Flujo
Carga config e historial → Edge y login → abre `url_busqueda`, intercepta el body de `searchV2` → pagina de a 100 → precarga "Mis postulaciones" → filtra (otro portal, ya postulado, `users/`, historial final, palabra excluida) → divide en sin formulario (`tienePreguntas == false` y sin salario obligatorio o con salario configurado) y con formulario → **fase 1** (lee la ficha; externo → `externo`; si aparecen preguntas pasa a la fase 2; `postularV2`; pausa; 401/403 corta, 429 espera 2 min) → **fase 2** (`s`/`n`/`q`; `simple` por texto, Enter = salario en las de salario; `choice` con menú; si fallan las respuestas → `postulado_sin_respuestas`).

Estados: `postulado`, `ya_postulado`, `externo`, `descartado` (finales), `error`, `postulado_sin_respuestas` (se reintentan).

### Verificado en vivo (19-11-2026)
202 avisos (66 de ZonaJobs); postulación sin formulario OK; con formulario `simple` (salario) OK; repetir da 400. **Sin probar con envío real:** preguntas `choice`.

### Si cambia
Revisar el bundle `/candidate/static/js/main.<hash>.js` (y chunks como `fichaAviso.<hash>.chunk.js`) buscando `path=` y `api/`.

---

## ZonaJobs (`zonajobs/`)

**Misma plataforma que Bumeran** (mismos endpoints, datos y sesión). Diferencias:

| | Bumeran | ZonaJobs |
|---|---|---|
| Sitio | `https://www.bumeran.com.ar` | `https://www.zonajobs.com.ar` |
| `x-site-id` | `BMAR` | `ZJAR` (de `/candidate/site.js` → `window.SITE_ID`) |
| Avisos que se postulan | `portal == "bumeran"` | `portal == "zonajobs"` |
| Clase en el script | `Bumeran` | `Portal` |

Constantes `SITIO`, `SITE_ID` y `PORTAL_PROPIO` al principio de `postulador.py`.

- **El listado es compartido:** `searchV2` devuelve los mismos avisos en los dos sitios (203 el 20-11-2026: 136 de Bumeran y 67 de ZonaJobs). Desde ZonaJobs la ficha de un aviso de Bumeran da 404: se omiten.
- Cuentas y postulaciones **separadas** en cada sitio.
- **Duplicados con Bumeran:** opción `omitir_duplicados_de_bumeran` (mismo título y empresa que uno postulado en `datos/bumeran/historial.json`). **Por pedido del usuario está en `false`.**
- Verificado en vivo el 20-11-2026: login, postulación sin formulario OK.

---

## EmpleosIT (`empleosit/`)

Plataforma **SmartJobBoard** (PHP, HTML clásico, jQuery). Sin Cloudflare ni anti-bots; igual se usa Edge por la sesión y por consistencia.

- **Sesión:** login en `/login/` → `/my-account/`. Cookies `PHPSESSID` y `session_key`. Login detectado por un link a `logout`. Mail en `input[name="email[original]"]` de `/edit-profile/`. `page.set_default_timeout(90000)` (el sitio a veces tarda).
- **Listado:** `/search-results-jobs/?action=search&view=list&listings_per_page=100&Location_City[multi_like_and][]=Ciudad Autónoma de Buenos Aires (CABA)&page=N` (`listings_per_page`: 10, 20, 50 o 100). Título en `.listing-title a[href*="/display-job/<ID>/..."]` (ID numérico), empresa en `.company-ico a` (a veces no hay), ubicación en `.location-ico`. 87 avisos en CABA el 21-11-2026.
- **Postulación:** `GET /apply-now/?listing_id=<ID>&ajaxRelocate=1` → `form#applyForm` (multipart) con ocultos (`is_data_submitted`, `listing_id`, `redirect_url`, `anonymous`), `comments`, `id_resume` (CV preseleccionado) y preguntas `input[name="QuestionAnswer[]"]` (**todas de texto**, en orden; el texto en el `div.inputName` anterior). Sin sesión pide reCAPTCHA; con sesión no.
- **Envío:** `fetch(form.action, {method: 'POST', body: new FormData(form)})` →
  - `{"status":"jobapplysuccess", "check_redirect_url": ""}` → postulado;
  - `jobapplysuccess` con `check_redirect_url` → `postulado_externo` (la empresa pide seguir en su sitio);
  - `jobapplyerror` con `APPLY_APPLIED_ERROR` → ya postulado; otro `jobapplyerror` → error.
- **Flujo:** login → listado → filtros (`descartes.json`, historial final: `postulado`, `ya_postulado`, `postulado_externo`, `descartado`, `repetido`; palabras excluidas) → fase 1 (chequea repetidos con el mismo criterio que Computrabajo; abre el formulario; sin preguntas lo envía, con preguntas marca `con_preguntas`) → fase 2 (`s`/`n`/`q`, preguntas por consola, Enter = salario).
- Verificado en vivo el 21-11-2026: login, listado, postulación sin preguntas (ID 132631) y repetición (`APPLY_APPLIED_ERROR`), lectura de preguntas (ID 132578). **Sin probar:** envío con preguntas completadas y avisos con `check_redirect_url`.

---

## Pendientes e ideas

1. **Avisos "con preguntas" desactualizados (Computrabajo, importante).** El historial guarda `con_preguntas` para los avisos pendientes de decidir y la app los pone en "Para decidir" **sin volver a abrirlos**. Si el usuario se postuló por fuera de la app (directo en la web), la app igual se lo muestra como pendiente. No hay doble postulación (al apretar `S`, Computrabajo responde "Ya te postulaste" y la app lo saca), pero apretar `N` lo anotaría como descartado. **Arreglo propuesto:** al empezar cada corrida, leer "Mis postulaciones" de Computrabajo (área del candidato) y tomar esos IDs como ya postulados. Falta investigar esa página con la sesión real (URL, estructura de cada ítem, dónde está el ID del aviso, paginación), con la app cerrada. La alternativa (reabrir cada `con_preguntas`) suma unos 10 minutos por corrida.
2. **Llevar EmpleosIT a la app** (Bumeran y ZonaJobs ya están: `motor_jobint.py`). Hacer la primera corrida real de Bumeran y ZonaJobs con la sesión del usuario.
3. **Varias búsquedas en las consolas de Bumeran, ZonaJobs y EmpleosIT:** hoy usan solo `url_busqueda`. Usar `busquedas.lista(cfg)` como en Computrabajo.
4. **Limpiar la descripción de los avisos de Computrabajo:** al final se cuela texto de la página que no es del aviso ("Avísame con ofertas similares", "Denunciar empleo", "Gracias por ayudarnos…"). Se le ofreció al usuario y no respondió todavía.
5. **Actualizar los valores de `sueldo_neto.py`** cuando cambien (tope ANSES mensual; deducciones y escala de Ganancias semestrales).
6. Respuestas predefinidas para preguntas frecuentes (disponibilidad, presencialidad, inglés…).
7. (Hecho en la app el 24-11-2026: Bumeran y ZonaJobs detectan repetidos como Computrabajo. Los scripts de consola de Bumeran/ZonaJobs todavía no.)
8. (Hecho el 24-11-2026: las búsquedas viajan al exportar/importar.)

---

## Versiones de la app

**Regla del usuario (24-11-2026): cada cambio a la app, por mínimo que sea, sube la versión en uno** (1.0.0 → 1.0.1 → … → 1.0.9 → 1.1.0). La versión está en `app/ui/app.js` (`const VERSION`) y se muestra abajo a la izquierda del menú, tan tenue como "Made by Matichiozza".

- **1.0.0** (24-11-2026): punto de partida. Incluye todo lo de este documento hasta esa fecha: Computrabajo, Bumeran y ZonaJobs en la app, menú F con fondo animado, Ajustes (datos, exportar/importar con búsquedas, avisos descartados, empezar de cero), editor de búsquedas D, bolsas no elegidas tenues.
- **1.0.1** (24-11-2026): al pasar el mouse por una búsqueda (etiquetas del menú, lista del editor, cabecera del recorrido) ya no aparece la leyenda con el link.
- **1.0.2** (24-11-2026): cabecera del recorrido nueva (diseño C, una sola franja de 64 px): logo de la bolsa (leyenda: el mail), selector de búsqueda, `12/48`, estado corto, 3 contadores con leyenda mínima al pasar el mouse (✓ **Ya postulados** = automáticas + con tus respuestas + las que ya tenías; ? **Para decidir**; ✕ **Descartados** = descartados, salteados y los que descartás con N) y Pausar/Seguir; el progreso es una línea fina en el borde de abajo. **Cambio de búsqueda en vivo**: tocando la búsqueda se elige otra; la actual queda pausada donde estaba y al volver retoma desde ese aviso. Solo corre una a la vez. La lógica está en `app/recorrido.py` (compartida por los 3 motores: `recorrer(motor, urls, cargar, procesar, cuenta)` y el comando `cambiar_busqueda`); cada listado se lee recién la primera vez que esa búsqueda se activa.
- **1.0.3** (24-11-2026): **botón de cuenta** a la izquierda de "Empezar en …" (menú). Muestra la cuenta de la bolsa elegida: apagado y con borde punteado si no está vinculada, con el color de la bolsa y una marca verde si sí. Al tocarlo: *Vincular cuenta* (abre Edge para iniciar sesión, se cierra solo al entrar) o, si ya está vinculada, el mail y *Reconectar cuenta* (borra la sesión guardada, `perfil_edge/`, y vuelve a pedir el login: sirve si no entra o para usar otra cuenta; historial/descartes no se tocan). **No se puede empezar sin cuenta vinculada** (botón Empezar deshabilitado y `Api.iniciar` lo rechaza). Código: `comun/cuenta.py` (`datos/<bolsa>/cuenta.json` con mail y fecha; vinculada = ese archivo + `perfil_edge/`), `Api.cuentas()` / `Api.vincular(plataforma, reconectar)`, y los motores con `solo_cuenta=True` (hacen solo el paso de login, guardan la cuenta y emiten `cuenta_ok` / `cuenta_error`). Cada corrida normal también vuelve a guardar la cuenta; si la sesión venció, el recorrido sigue pidiendo el login como antes.
- **1.0.4** (24-11-2026): arreglo: al vincular, el login andaba pero fallaba al guardar la cuenta (`UnboundLocalError`), porque en `_correr` la variable `cuenta` (contadores del recorrido) tapaba al módulo. En los motores se importa como `cuentas_bolsa`.
- **1.0.5** (24-11-2026): (1) Contadores de la cabecera: primero **Nuevas postulaciones** (blanco: las de esta corrida, las hizo la app sola o vos con tus respuestas, unificadas), después ✓ **Ya postulados** (ahora solo las que ya tenías de antes), ? Para decidir y ✕ Descartados. (2) Bumeran/ZonaJobs parecían "tildados" en "Leyendo tus postulaciones": la API tarda ~5,5 s por página de 30 y se leían una por una (250 postulaciones ≈ 1 minuto). Ahora `ids_ya_postulados` pide la primera y después las demás juntas (`Promise.all`, de a 8) y avisa el avance: 250 en ~11 s.
- **1.0.6** (24-11-2026): Edge de los motores **oculto del todo** (ni en pantalla ni en la barra de tareas), en vez de minimizado: `app/ventana_edge.py`. Sigue siendo el mismo Edge con ventana (para los sitios no cambia nada). Al abrir puede aparecer un instante en la barra de tareas hasta que se oculta.
- **1.0.7** (24-11-2026): (1) El selector de búsqueda andaba bien; lo que confundía es que los avisos ya revisados en otras corridas se saltean al instante, y en las búsquedas del usuario (Informática en Catamarca: 50 avisos, SQL en Chubut: 20) **no había ninguno nuevo**, así que al cambiar ambas terminaban en un segundo sin decir nada. Ahora `busqueda_fin` trae `total` y `abiertos` (avisos nuevos) y la interfaz avisa: «X: no hay avisos nuevos (los N ya los habías revisado)», «Vuelvo a X donde la dejaste (12 de 48)»; el final dice «Listo · sin avisos nuevos». (2) EmpleosIT no se puede elegir: gris, etiqueta «Próximamente», al tocarlo solo avisa y las flechas la saltean. (3) **No se puede empezar sin nombre, sueldo bruto y zona** (Empezar deshabilitado + aviso «Para empezar, completá … en Ajustes →»; `Api.iniciar` también lo rechaza).


## Lecciones técnicas (para no repetir errores)

- Con **pythonw**, cualquier `print` con emoji falla si la salida no está redirigida a un archivo UTF-8.
- En Playwright sync, **no usar `time.sleep` para esperar cambios del navegador**: `page.url` y `ctx.pages` no se actualizan. Usar `page.wait_for_timeout`.
- **Headless no sirve** en Bumeran/ZonaJobs (Cloudflare) ni en Computrabajo (403). Para pruebas sin molestar al usuario: ventana fuera de la pantalla (`--window-position=-2400,0`).
- Edge **bloquea navegar a URLs `data:`** en la pestaña principal; para pruebas con páginas falsas, usar archivos locales (`file:///…`).
- En el sandbox de Claude Code, las pruebas que usan internet pueden necesitar desactivar el sandbox (si no, `ERR_NAME_NOT_RESOLVED`).
- `instalador/compilar.bat` está en **CRLF** (editarlo preservando los `\r\n`).
- Desde Git Bash, un heredoc puede convertir `\\` en `\`: para editar archivos con barras invertidas (como `Setup.cs`) usar el editor, no scripts escritos en un heredoc.
- En PowerShell las variables no distinguen mayúsculas: `$R` y `$r` son la misma.
- En esta PC el Python con las librerías es el de `programa/datos/python.txt` (hoy `%LOCALAPPDATA%\Programs\Python\Python312\`).
- Desde Git Bash, un argumento que empieza con `/` se convierte en ruta de Windows (`/empleos-...` → `C:/Program Files/Git/empleos-...`): pasar los caminos sin la barra inicial.
