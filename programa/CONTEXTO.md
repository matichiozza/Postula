# Postulá: app para postularse a avisos de empleo

Documento para que otra persona u otro chat de IA entienda el proyecto y pueda seguir sin perder nada. **Actualizado el 25-11-2026 (versión 1.3.5).** Si sos un chat nuevo, leé primero **"Cómo trabajar con el usuario"**, **"Cómo funciona hoy"** y **"Pendientes"**. Las secciones por bolsa y el historial de versiones tienen el detalle; **si algo viejo contradice a "Cómo funciona hoy" o a una versión más nueva, vale lo nuevo**.

Repositorio: https://github.com/matichiozza/Postula (público). La app se llamaba "Laburo IA" hasta la 1.2.3.

## Qué es

App de escritorio para Windows (**Postulá**) más los scripts de consola de cada bolsa, para postularse a avisos de empleo en Argentina.

| Bolsa | Cómo funciona por dentro | Motor de la app |
|---|---|---|
| ar.computrabajo.com | HTML + formularios ASP.NET (Redarbor) | `app/motor_computrabajo.py` |
| bumeran.com.ar | API JSON interna (Jobint/Navent) | `app/motor_jobint.py` |
| zonajobs.com.ar | La misma API que Bumeran, con otro `x-site-id` | `app/motor_jobint.py` |
| empleosit.com.ar | HTML + formulario AJAX (SmartJobBoard) | `app/motor_empleosit.py` |
| linkedin.com (solo Solicitud sencilla) | Búsqueda con JobSpy (sin sesión) + formulario de Solicitud sencilla con tu sesión | `app/motor_linkedin.py` |

## Cómo funciona hoy

- **El recorrido no postula.** Lee las búsquedas activas y deja los avisos en dos listas: *Sin preguntas* y *Con preguntas*. En Computrabajo se averigua con `/candidate/kq` sin seguir redirecciones (1.2.7) y en EmpleosIT leyendo el formulario con `fetch` (1.2.8); ninguna de las dos consultas postula. Si no se puede saber, el aviso queda en *Sin preguntas* y, si al postularse resulta tener, pasa a la otra lista.
- **LinkedIn** es distinto: la primera lista se llama *Sin revisar* (no se sabe si hay preguntas hasta apretar Postularme) y no tiene Auto. Ver la sección de LinkedIn.
- **Auto** arranca **apagado** en cada recorrido. Activado postula de a uno con pausas (`recorrido.paso_auto`), solo la primera lista, sin tocar los restaurados.
- Al empezar, cada motor lee **las postulaciones de la cuenta** y las anota en el historial (`ya_postulado`).
- En Computrabajo, **abrir el link de postulación de un aviso sin preguntas ya postula**. En EmpleosIT abrir el formulario no postula: postula el envío. En Jobint se postula por API.
- Cabecera: contadores Nuevas postulaciones, Ya postulados, Para decidir, Repetidos y Descartados por vos; tres de ellos abren una barra lateral.
- Búsquedas: activas e inactivas, subáreas (Jobint) o varias categorías (EmpleosIT), varias localidades y remoto.

## Cómo trabajar con el usuario (importante)

- **Idioma:** español rioplatense, incluidos los mensajes cortos y los comentarios del código.
- **Cada cambio a la app sube la versión** (`const VERSION` en `app/ui/app.js`) y se anota abajo, en "Versiones de la app".
- **No agregar atajos de teclado nuevos** (pedido del 25-11-2026). Los que hay quedan.
- Para decisiones de diseño, el usuario prefiere ver **varias propuestas en un artefacto** y elegir por letra.
- **Probar antes de dar algo por terminado**, solo lo necesario, y contar qué se probó y qué no.
- **Nunca postularse a avisos reales para probar.** Usar motores simulados, o la sesión real en solo lectura con los envíos bloqueados (`ctx.route`), escribiendo en una carpeta temporal.
- **El perfil de Edge no se puede usar con la app abierta:** pedir que la cierre.
- **Decisiones que no hay que revertir:** los descartes son solo locales (no usar "Ocultar aviso" de Computrabajo); `n` = descartar para siempre; en ZonaJobs `omitir_duplicados_de_bumeran` queda en `false`; en el menú, tocar una bolsa solo la elige.
- **Privacidad:** `programa/datos/` (sesiones, tokens, perfil) nunca va al repositorio ni a servicios externos.

## Instalar

1. Ejecutar **`Setup.exe`** (asistente WinForms: Bienvenida → Opciones → Instalando → Listo). Instala en **`%LOCALAPPDATA%\Programs\Postulá`** (cambiable; no usar `C:\Program Files`: la app escribe sus datos adentro). Copia `programa/` y `Setup.exe`, y si el destino no tiene datos trae los que haya junto al instalador. Reinstalar encima no pisa los datos.
2. Pasos: Python ≥ 3.9 (ofrece instalar 3.12) → `pip install playwright pywebview` → `pip install python-jobspy` (para LinkedIn; si falla se sigue) → verifica Edge → copia → anota `datos/python.txt` → desempaqueta `Postulá.exe` → acceso en el menú Inicio y, opcional, en el escritorio. Detalle en `datos/registros/setup.log`.
3. Sin ventanas: `Setup.exe /silencioso [/destino C:\carpeta] [/nombre "X"] [/borrar] [/escritorio] [/sinmenu]`; `/capturas <carpeta>` guarda las pantallas. Desde Git Bash no pasar esos parámetros (los convierte en rutas).
4. Compilar: `programa/instalador/compilar.bat` (usa `csc.exe` de .NET Framework 4: solo C# 5). Desde PowerShell, `cmd /c compilar.bat` no lo encuentra por la "á" de la carpeta: correr los dos `csc` del .bat directo (lo hizo así la 1.3.0). El lanzador viaja dentro de `Setup.exe`. `Setup.exe` usa `instalador/setup.ico`; `Postulá.exe`, `app/recursos/logo.ico`.
5. Las sesiones (`perfil_edge/`) no sirven en otra PC: hay que volver a iniciar sesión.
6. **Detrás de un proxy que pide autenticación de Windows, `pip` falla con 407.** Se resolvió bajando las ruedas de PyPI con PowerShell (`-ProxyUseDefaultCredentials`) e instalando con `pip install --user --no-index --find-links`.

## Estructura de archivos

```
Postulá/
├─ Setup.exe                 instalador
├─ Postulá.exe               lo crea Setup.exe
└─ programa/
   ├─ CONTEXTO.md
   ├─ app/                   app.py, recorrido.py, motor_*.py, ventana_edge.py, recursos/, ui/ (index.html, estilo.css, app.js, fondo.js)
   ├─ bolsas/<bolsa>/        postulador.py (consola; la app lo reutiliza), filtros.json, actualizar_filtros.py
   ├─ comun/                 rutas, busquedas, descartes, perfil, cuenta, fechas, datos_usuario, sueldo_neto
   ├─ datos/                 TODO lo personal (no se sube): perfil.json, python.txt, <bolsa>/{config,cuenta,descartes,historial}.json y perfil_edge/, registros/
   └─ instalador/            Setup.cs, Lanzador.cs, compilar.bat, setup.svg/.ico
```

Los módulos comunes se importan agregando `programa/comun` a `sys.path`. Las rutas salen de `rutas.py`.

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
- **pywebview** (ventana propia con WebView2, título "Postulá", 1280×820, mínimo 900×600) + interfaz HTML/CSS/JS en `app/ui/` (sin frameworks, íconos SVG en línea, tema oscuro y claro según Windows).
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

### Flujo de una corrida
Ver "Cómo funciona hoy". El recorrido de las búsquedas es común (`recorrido.recorrer`): cada motor pone `cargar(url, resumen)` y `procesar(aviso)`, que solo clasifica, y `postular_libre(aviso)` para Auto. Una búsqueda con varios lugares se expande en varios links (`busquedas.expandir`) y se unen los resultados.

### Logo e identidad en Windows (24-11-2026)
- Logo: maletín blanco (el trabajo) con un destello amarillo (la IA) sobre un cuadrado verde redondeado. Original en `app/recursos/logo.svg`; `logo.ico` (16 a 256 px, entradas PNG) y `logo.png` se generan renderizando el SVG con Edge.
- En el menú y la cabecera reemplaza a la vieja "L" (`img.logo`). Hay una copia en `app/ui/logo.svg` porque pywebview sirve la interfaz solo desde `ui/` (`../recursos/` no carga).
- Ventana y barra de tareas: `webview.start(icon=logo.ico)` y, antes de crear la ventana, `SetCurrentProcessExplicitAppUserModelID("Postula.App")` (`identidad_windows()` en `app.py`). Sin eso Windows mostraba el ícono de Python y agrupaba la app con pythonw.

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
- **El listado y la ficha no dicen qué aviso tiene preguntas** (comparado el 25-11-2026, con y sin sesión). Se averigua pidiendo `https://candidato.ar.computrabajo.com/candidate/kq?oi=<ID>` **sin seguir redirecciones** (`ctx.request.get(..., max_redirects=0)`): con preguntas → 200 con `KillerQuestions[`; sin preguntas o ya postulado → 302 a `/apply/?oi=…&idcandidate=…`. **`/apply/` es lo que postula: nunca seguir esa redirección** (con `page.goto` el navegador la sigue, y `ctx.route` NO intercepta redirecciones del servidor). Probado con un aviso nuevo sin preguntas: no apareció en Mis postulaciones. `MotorComputrabajo.tiene_preguntas()`.
- **Abrir el link de postulación de un aviso sin preguntas ya te postula.** No hay confirmación. Por eso `--simular` es la única forma de ver los avisos sin postularse.

### Sitios y sesión
- Listado y fichas: `https://ar.computrabajo.com` (se leen sin sesión, pero **headless da 403**).
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
- Para reinstalar de cero sin perder nada. En **Ajustes**, tarjeta "Copia de tus datos": **Exportar** (`E`) abre el diálogo "Guardar como" de Windows (sugiere `Postulá - datos de <nombre>.json`) y **Importar** (`I`) el de "Abrir". Diálogos de pywebview (`create_file_dialog`, `webview.FileDialog.SAVE/OPEN`).
- **Probado por el usuario el 24-11-2026:** exportó, reinstaló con "Borrarlos" (Setup.exe) e importó: volvieron nombre, sueldo, zona y los 89 descartes de Computrabajo.
- El archivo: `{"app": "Postulá", "tipo": "datos-de-usuario", "version": 1, "exportado": "...", "nombre", "sueldo", "zona", "descartes": {"computrabajo": {...}, "bumeran": {...}}}, "busquedas": {"computrabajo": ["<link>", …], …}}`. **Las búsquedas viajan desde el 24-11-2026** (pedido del usuario).
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
- La API (`/api/...`) responde **403** a `curl`/`requests` y a Chromium o Edge **headless**. **Edge en ventana normal sí funciona.**
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

Plataforma **SmartJobBoard** (PHP, HTML clásico, jQuery). Se usa Edge por la sesión y por consistencia con las otras bolsas.

- **Sesión:** login en `/login/` → `/my-account/`. Cookies `PHPSESSID` y `session_key`. Login detectado por un link a `logout`. Mail en `input[name="email[original]"]` de `/edit-profile/`. `page.set_default_timeout(90000)` (el sitio a veces tarda).
- **Listado:** `/search-results-jobs/?action=search&view=list&listings_per_page=100&Location_City[multi_like_and][]=Ciudad Autónoma de Buenos Aires (CABA)&page=N` (`listings_per_page`: 10, 20, 50 o 100). Título en `.listing-title a[href*="/display-job/<ID>/..."]` (ID numérico), empresa en `.company-ico a` (a veces no hay), ubicación en `.location-ico`. 87 avisos en CABA el 21-11-2026.
- **Mis Postulaciones** (`/system/applications/view/`) muestra todas en una tabla (el 25-11-2026 eran 3, sin paginación). El formulario de un aviso donde ya estás postulado se ve igual que uno nuevo: lo que evita mostrarlos es esta lista.
- **Postulación:** `GET /apply-now/?listing_id=<ID>&ajaxRelocate=1` → `form#applyForm` (multipart) con ocultos (`is_data_submitted`, `listing_id`, `redirect_url`, `anonymous`), `comments`, `id_resume` (CV preseleccionado) y preguntas `input[name="QuestionAnswer[]"]` (**todas de texto**, en orden; el texto en el `div.inputName` anterior). Sin sesión pide reCAPTCHA; con sesión no.
- **Envío:** `fetch(form.action, {method: 'POST', body: new FormData(form)})` →
  - `{"status":"jobapplysuccess", "check_redirect_url": ""}` → postulado;
  - `jobapplysuccess` con `check_redirect_url` → `postulado_externo` (la empresa pide seguir en su sitio);
  - `jobapplyerror` con `APPLY_APPLIED_ERROR` → ya postulado; otro `jobapplyerror` → error.
- **Flujo:** login → listado → filtros (`descartes.json`, historial final: `postulado`, `ya_postulado`, `postulado_externo`, `descartado`, `repetido`; palabras excluidas) → fase 1 (chequea repetidos con el mismo criterio que Computrabajo; abre el formulario; sin preguntas lo envía, con preguntas marca `con_preguntas`) → fase 2 (`s`/`n`/`q`, preguntas por consola, Enter = salario).
- Verificado en vivo el 21-11-2026: login, listado, postulación sin preguntas (ID 132631) y repetición (`APPLY_APPLIED_ERROR`), lectura de preguntas (ID 132578). **Sin probar:** envío con preguntas completadas y avisos con `check_redirect_url`.

---

## LinkedIn (`bolsas/linkedin/`, `app/motor_linkedin.py`, 25-11-2026)

Pedido del usuario: buscar con su herramienta JobSpy (`python-jobspy` 1.5.0) **solo avisos con Solicitud sencilla** y postularse desde la app. El usuario aceptó el riesgo de los términos de LinkedIn (prohíben automatizar); para bajarlo: Edge normal con su sesión, de a un aviso, **sin Auto**, y si LinkedIn pide verificación (checkpoint/captcha/login) se frena y se avisa.

- **Búsqueda:** `postulador.buscar(url)` llama a `scrape_jobs(site_name=["linkedin"], easy_apply=True, …)`. JobSpy espera 3-7 s entre páginas de 10 avisos (con 300, más de 2 minutos): desde la 1.3.1 la app busca **en segundo plano, página por página** (`MotorLinkedIn._buscar_en_fondo`, `buscar_pagina`), arrancando apenas se toca Empezar (en paralelo con el login y Solicitados), y la lista de la búsqueda crece mientras se recorre (`recorrido.llegan_mas`). Ante un 429 espera 30 s y reintenta 2 veces. Es la búsqueda pública de empleos (sin sesión). Trae id, título, empresa, lugar, fecha y link; **no** trae si tiene preguntas. LinkedIn limita los pedidos (429; JobSpy lo escribe en su log y la app lo detecta y avisa): no pedir descripciones en la búsqueda. "desarrollador" en Capital Federal: 191 avisos con Solicitud sencilla.
- **Link guardado:** el de la web, `https://www.linkedin.com/jobs/search/?keywords=…&location=…&f_AL=true[&f_WT=2]` (`busquedas._armar_linkedin` / `_desarmar_linkedin` / `_leer_linkedin`). Sin categorías: el editor muestra solo Dónde + Palabra clave (`filtros.json` con `"solo_palabra": true`; los lugares son textos que LinkedIn entiende, ej. "Capital Federal, Buenos Aires, Argentina"). Remoto = `f_WT=2` en Argentina.
- **Tus postulaciones:** Registro de empleos → Solicitados (`/jobs-tracker/?stage=applied`), 10 por página con "Siguiente" (en la última queda oculto). `SOLICITADOS_JS` saca id, título y empresa. El 25-11-2026 eran 24.
- **Con o sin preguntas (opción "B" elegida por el usuario):** no se clasifica en el recorrido (habría que abrir el formulario de cada aviso: mucha actividad en la cuenta). Todos quedan en *Sin revisar*; al apretar Postularme se abre la Solicitud sencilla en la pestaña de formulario y se avanza por las páginas ya completas (contacto y CV vienen cargados). Si llega a "Enviar" sin nada pendiente, envía; si una página tiene campos obligatorios vacíos, el aviso pasa a *Con preguntas* y se muestran en la app **página por página** (evento `form` con `pagina`; la interfaz acepta la página siguiente después de enviar la anterior).
- **Formulario (diseño nuevo de LinkedIn, clases ofuscadas):** `<dialog>` con "Aplicar a <empresa>" y "N/4 páginas"; botones "Siguiente", "Revisar", "Enviar solicitud". Cerrar con Escape pregunta "¿Quieres guardar esta solicitud?" → **Descartar** (si no, queda "En curso"). Campos: texto/número, `select` ("Selecciona una opción" = vacío) y sí/no en **dos variantes**: `div[role=radio]` con la pregunta en `aria-label`, o el `aria-label` en el propio `input` con el texto de la opción al lado. La `<label>` está vacía. El radio del CV se reconoce por `#easyApplyUploadedResumeRef`. Con la ventana de Edge oculta, `innerText` puede venir vacío y la página tarda en dibujar los textos: se usa `aria-label`/`textContent` y se lee hasta que dos lecturas coinciden (`_leer`); los radios se marcan con `click()` por JS (el input está escondido).
- **Aviso donde ya te postulaste:** no tiene el botón "Solicitud sencilla" sino "Ver currículum". Descripción: texto después de "Acerca del empleo" (`DETALLE_JS`, pestaña de consulta con sesión).
- **Probado el 25-11-2026 con la cuenta real:** login; 1 postulación real sin preguntas (Atentus, "Ingeniero/a de Software C/C++", por consola: Solicitados pasó de 23 a 24); el motor **en seco** (el botón Enviar reemplazado): lee las 24 postulaciones y ninguna aparece en la lista; búsqueda con JobSpy; descripción; 3 formularios con preguntas (sí/no de las dos variantes, años, sueldo precargado) completados hasta el botón Enviar sin tocarlo; "En curso" quedó en 2 (no quedaron borradores). **Falta:** una postulación real desde la app (con y sin preguntas).

## Pendientes e ideas

1. **Barra de título azul:** el usuario la quiere gris oscuro. En Windows 10 una app no puede cambiarla (tiene activado el color de énfasis). Opciones ofrecidas, sin respuesta: desactivarlo en Windows, o ventana sin marco con barra propia.
2. **Pruebas reales que faltan:** postulación desde la app en Bumeran y ZonaJobs; envío de un formulario con preguntas en EmpleosIT; paginación de "Mis Postulaciones" de EmpleosIT con más de una página.
3. Bumeran informa como máximo 250 postulaciones. El 25-11-2026 su búsqueda devolvió HTTP 503 un rato (se resolvió solo).
4. Los scripts de consola no entienden `lugares` (recorren el primero) y los de Bumeran, ZonaJobs y EmpleosIT usan solo la primera búsqueda.
5. Actualizar `sueldo_neto.py` cuando cambien los valores (tope ANSES mensual; Ganancias semestral).
6. Ideas: respuestas predefinidas para preguntas frecuentes.

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

- **1.0.8** (25-11-2026): **el recorrido ya no postula solo.** La columna "Para decidir" tiene una pastilla con dos listas (`← →`): **Sin preguntas** (en Computrabajo se llama **Sin revisar**, porque no se sabe si tienen preguntas hasta abrir el link, y abrirlo ya postula) y **Con preguntas**. En la primera hay un interruptor **Auto** (`A`), **desactivado al empezar cada recorrido** (pedido del usuario): activado, postula uno por uno con las pausas de siempre; desactivado, el usuario se postula de a uno con `S`. Si uno resulta tener preguntas pasa a la otra lista. El recorrido solo lee y clasifica (`agregar_libre`, items con `libre: true`); Auto está en `recorrido.py` (`paso_auto`, `quedar_atendiendo`, comando `auto`) y cada motor pone `postular_libre`. `max_postulaciones_por_corrida` ahora limita solo a Auto (las manuales no cuentan). Los avisos de la primera lista no se anotan en el historial hasta que se actúa sobre ellos. **Reemplaza lo que dicen más arriba "Flujo de una corrida" y los motores sobre postular durante el recorrido** (los scripts de consola no cambiaron). Probado con la bolsa simulada y la interfaz en Edge headless; **falta la prueba real**.
- **1.0.9** (25-11-2026): (1) Cabecera: contadores **Repetidos** (nuevo) y **Descartados por vos** separados; externos, omitidos, errores y "de la otra bolsa" ya no suman en la cabecera (quedan en el registro, `L`). Al terminar ya no dice "N para decidir" arriba. (2) **Computrabajo lee "Mis postulaciones" al empezar** (resuelve el pendiente 1): `Computrabajo.mis_postulaciones()` pide con `fetch` las páginas `/candidate/match?p=N` (10 por página; ítem `[data-match]`, link del aviso en `[data-shortcut-see-offer]`, el ID son los últimos 32 hex; **solo lectura**: cada ítem tiene "Eliminar la postulación"). `sincronizar_postulaciones` las anota en el historial como `ya_postulado` (`detalle: "Mis postulaciones"`), sin pisar `postulado` ni `descartado`. En muchas la web no muestra la empresa: esas se excluyen por ID pero no se usan para detectar repetidos. Probado con la cuenta real en solo lectura (293 leídas; la lista "Sin revisar" bajó de 107 a unos 40).
- **1.1.0** (25-11-2026): (1) **Logo de la empresa** en el aviso (Computrabajo: `img` de `/logos/empresas/` en la ficha; Jobint: `logoURL`), con la inicial si no hay. (2) **Descripción ordenada** (`descripcion()` en `app.js`: subtítulos, viñetas, "Etiqueta: valor") y sección **Requerimientos** al final solo si la bolsa los informa (`requisitos` en el evento `detalle`; Computrabajo: lista bajo "Requerimientos", y ya no se cuela el pie de la página, pendiente 4 resuelto; Jobint: `ficha.requisitos`, experiencia en meses). En Jobint la descripción se lee de `ficha.descripcion` (antes `detalle`, que viene vacío). (3) Clic en el contador **Descartados por vos** o `D`: barra lateral con "Restaurar" y "Ver en la web" (comando `recuperar`, en `recorrido.cmd_recuperar`). Un restaurado vuelve a su lista pero **Auto no se postula a él**. (4) Todo vale para Computrabajo, Bumeran y ZonaJobs. Probado con avisos públicos y bolsas simuladas; **Bumeran y ZonaJobs siguen sin prueba con sesión real**.
- **1.1.1** (25-11-2026): Bumeran y ZonaJobs anotan "Mis postulaciones" en el historial (`sincronizar_postulaciones`, con título y empresa que trae la API) para detectar también republicaciones; `postulador.py` de cada una tiene `mis_postulaciones()` (`ids_ya_postulados` la usa). En Jobint, avisos sin empresa o **"Confidencial"** nunca se toman como repetidos. **Probado con las sesiones reales, en solo lectura y con Auto apagado** (login automático, 207 avisos en Tecnología/CABA en cada una; Bumeran 250 postulaciones leídas, que es el máximo de la API; ZonaJobs 44). **Falta la primera postulación real** en esas dos bolsas.
- **1.1.2** (25-11-2026): si el servidor de la bolsa no responde (Bumeran devolvió HTTP 503 en la búsqueda), se reintenta dos veces, se dice que la bolsa no está respondiendo (antes mandaba a revisar la búsqueda) y se avisa si no se pudieron leer las postulaciones (antes seguía en silencio).

- **1.1.3** (25-11-2026): (1) La lista y la cabecera del aviso muestran **cuándo se publicó** en vez de la ubicación (`comun/fechas.py`; Computrabajo: `p.fc_aux` del listado; Jobint: `fechaPublicacion`). (2) Bumeran/ZonaJobs **cuentan y recorren solo los avisos propios** (los de la otra bolsa se filtran en `cargar`). (3) Los contadores **Nuevas postulaciones**, **Repetidos** y **Descartados por vos** abren una barra lateral; todas se cierran con la flecha o `Esc`. (4) **Se quitaron los atajos `D` y `H`** y el panel "Con tus respuestas" (las respuestas del recorrido actual se ven en Nuevas postulaciones). **Decisión del usuario: no agregar más atajos de teclado.** (5) En el menú, tocar la bolsa solo la elige (se empieza con el botón). (6) Bolsa elegida, Empezar y cuenta en blanco/gris/negro. (7) **Cerrar sesión** en el menú de cuenta (`api.cerrar_sesion`).

- **1.1.4** (25-11-2026): al terminar el recorrido aparece **Ordenar por fecha de publicación** (más recientes primero; Auto sigue ese orden; campo `antiguedad` en minutos, `fechas.antiguedad`). Se quitó del menú la nota de avisos descartados y de Ajustes el detalle por bolsa; el "← Volver" de Ajustes es una flecha redonda.

- **1.1.5** (25-11-2026): fondo del menú y Ajustes = diseño **A "Corrientes"** elegido por el usuario (artefacto https://claude.ai/artifact/LshWXGTxXD3kr5bE5d41MK), con movimiento visible, en `ui/fondo.js` (canvas; reemplaza las manchas CSS). La velocidad es `VELOCIDAD_FONDO`.

- **1.1.6** (25-11-2026): velocidad del fondo en **0.6** (elegida por el usuario).

- **1.1.7** (25-11-2026): (1) Se pueden borrar todas las búsquedas (antes `list index out of range`). (2) Cada búsqueda se puede **activar/desactivar** (`urls_inactivas` en `config.json`; `busquedas.lista` devuelve solo las activas, `todas` todas). (3) El editor ya no se achica al pegar un link. (4) **EmpleosIT en la app** (`app/motor_empleosit.py`, hereda de Computrabajo): listas desde `bolsas/empleosit/filtros.json` (`actualizar_filtros.py`; la web no filtra por provincia, solo ciudad), logo, fecha, descripción (no informa requisitos), "Sin revisar" como Computrabajo (abrir el formulario no postula; postula el envío). **Falta**: leer "Mis postulaciones" y probar con la sesión real.

- **1.1.8** (25-11-2026): EmpleosIT lee **Mis Postulaciones** (`/system/applications/view/?page=N`, tabla; solo lectura) al empezar. Probado con la sesión real en solo lectura: login automático, 86 avisos en CABA, formularios con preguntas de texto bien leídos, CV preseleccionado. **Falta la primera postulación real** desde la app (con y sin preguntas).

- **1.1.9** (25-11-2026): **subáreas** en el editor. Bumeran/ZonaJobs: varias subáreas por búsqueda (`?subareas=a,b` en el link; es de la app: `filtros_de_url` lo saca y `buscar_todos` busca cada una y une, porque la API las toma como "y"); listas en `filtros.json` (`categorias[].subareas`). EmpleosIT: no tiene subáreas, se pueden tildar **varias categorías** (la web las suma). Computrabajo no tiene.

- **1.1.9**, además: **varias localidades (y remoto) por búsqueda** en las cuatro bolsas. Se guarda el link del primer lugar más `lugares=prov~ciudad;...` (es de la app); `busquedas.expandir` da un link por lugar y cada motor une los resultados. Los scripts de consola recorren solo el primero.

- 25-11-2026: el usuario **confirmó una postulación real en EmpleosIT** desde la app: funcionó.

- **1.2.0** (25-11-2026): editor de búsquedas con el diseño **A "Compacto"** elegido por el usuario (artefacto https://claude.ai/artifact/S4STJsnkj4EK2PYRKbe6uA): renglones con desplegable y buscador (categoría, subáreas, dónde con ciudades dentro de cada provincia), interruptor arriba a la derecha, sin verde. `Esc` cierra primero el desplegable.

- **1.2.1** (25-11-2026): la ventana **abre maximizada** (`maximized=True`; al restaurarla queda en 1280x820). Pedido del usuario.

- **1.2.2** (25-11-2026): el saludo dice **"¡Che <nombre>, postulate!"** (antes "Hey"). Cambiado también el texto en `Setup.cs`, sin recompilar `Setup.exe`.

- **1.2.3** (25-11-2026): logo nuevo, **E "Piloto automático" en blanco** (artefacto https://claude.ai/artifact/KfaTjh9go669nWdMnnhfMQ): `recursos/logo.{svg,png,ico}` y `ui/logo.svg`; se ve arriba a la izquierda del menú. **Pendiente:** el nombre de la app al lado del logo (el usuario quiere elegirlo entre ideas) y el color de la barra de título.

- **1.2.4** (25-11-2026): **la app se llama "Postulá"** (antes "Laburo IA"; elegido por el usuario): textos, `Postulá.exe`, instalador, carpeta del proyecto y nombre al lado del logo en el menú. Las exportaciones de datos viejas se siguen importando. El repositorio de GitHub conserva el nombre anterior.

- **1.2.5** (25-11-2026): **Setup instala en `%LOCALAPPDATA%\Programs\Postulá`** (antes en el lugar), copia el programa, trae los datos y crea el acceso en el menú Inicio. README y este documento actualizados; subido a https://github.com/matichiozza/Postula.

- **1.2.6** (25-11-2026): **Ajustes → Buscar actualizaciones** (`comun/actualizar.py`): compara `const VERSION` con la de `main` en GitHub; si es más nueva baja el zip y corre su `Setup.exe /silencioso /destino <carpeta de la app> /sinmenu`, que no toca `datos/`. Descarga con PowerShell para pasar el proxy con la sesión de Windows. **Para publicar una versión hay que subir al repo `app.js` con la versión nueva y, si cambió el instalador o el lanzador, `Setup.exe` recompilado.**

- **1.2.7** (25-11-2026): **Computrabajo ya separa los avisos en *Sin preguntas* y *Con preguntas* durante el recorrido** (antes, *Sin revisar*, y al postularse saltaban a *Con preguntas*). Por cada aviso nuevo, `tiene_preguntas()` pide `/candidate/kq` sin seguir redirecciones (200 con formulario = con preguntas; 302 a `/apply/` = sin preguntas; otra cosa = no se sabe y queda en la primera lista como antes), con una pausa de 0,5–1,2 s. Los que tienen preguntas se anotan `con_preguntas`. Probado con la sesión real y Auto apagado: las 2 búsquedas del usuario (69 avisos, 11 nuevos) en 27 s, los 11 con preguntas (6 de ellos antes estaban en *Sin revisar*). EmpleosIT sigue con *Sin revisar*.

- **1.2.8** (25-11-2026): (1) **EmpleosIT también separa *Sin preguntas* / *Con preguntas*** durante el recorrido: `MotorEmpleosIT.tiene_preguntas()` lee `/apply-now/` con `fetch` (`FORM_JS`: cantidad de `QuestionAnswer[]`, otros campos de pregunta, captcha). Ya no hay *Sin revisar* en ninguna bolsa (`sinAnticipo` se quitó de `app.js`). (2) Botón "Editar búsquedas" del menú más visible (borde punteado claro). **Pruebas con la cuenta real (permiso del usuario para hasta 8 postulaciones; se hicieron 4):** EmpleosIT CABA: 87 avisos nuevos → 21 sin preguntas y 66 con preguntas, en 116 s; postulación a 2 sin preguntas (124349, 130545) confirmada sin formulario. Computrabajo "soporte técnico" en Capital Federal: postulación a 2 sin preguntas (D546166F…, 821CA39E…) confirmada sin formulario; recorrido: 88 sin preguntas, 93 con preguntas. En las dos bolsas se borraron del historial local esas postulaciones y se volvió a recorrer: se leyeron de Mis Postulaciones (EmpleosIT 3, Computrabajo 297) y **no aparecieron en ninguna lista**.

- **1.2.9** (25-11-2026): si *Sin preguntas* está vacía y hay avisos en *Con preguntas*, la lista pasa sola a *Con preguntas* (`pintarLista` en `app.js`; todas las bolsas). Si después llegan avisos sin preguntas no se vuelve sola. Probado en la interfaz con avisos simulados.

- **1.3.0** (25-11-2026): **LinkedIn en la app** (ver su sección): búsqueda con JobSpy solo Solicitud sencilla, Solicitados de la cuenta, *Sin revisar* + Postularme (envía si no hay preguntas; si hay, las muestra página por página), sin Auto, editor solo con palabra clave + lugar. `Setup.exe` instala `python-jobspy` (si falla, sigue sin LinkedIn) y se recompiló.

- **1.3.1** (25-11-2026): LinkedIn busca en segundo plano y muestra los avisos a medida que llegan (pedido del usuario: tardaba ~2 minutos en mostrar algo). Probado con la sesión real: "programador" en Capital Federal, primer aviso a los 26 s (lo que tarda leer la sesión y las 26 postulaciones), 191 avisos en 145 s, ninguno ya postulado en la lista.


- **1.3.3** (25-11-2026): **pantalla de carga** mientras se leen los avisos, en todas las bolsas: diseño **E "Contador gigante"** elegido por el usuario (artefacto https://claude.ai/artifact/KMP2txv4VwPUijvm2jhsSF). `#carga` tapa la pantalla de trabajo desde Empezar: bolsa y búsqueda arriba, la cantidad de avisos en grande (sube con animación, del evento `leyendo`), una barra fina y el paso actual (eventos `estado`). Con el primer `listado` se desvanece (0,6 s) y queda la pantalla de siempre. Se esconde para el login y vuelve después; con "reducir movimiento" no se anima. El usuario pidió sacar la frase "en cuanto termine, empiezo a clasificarlos". Probada en la interfaz con eventos simulados.

- **1.3.4** (25-11-2026): EmpleosIT. (1) Una búsqueda nueva arranca con **todas las categorías marcadas** (pedido del usuario) y el desplegable tiene arriba "Todas las categorías" para marcar o desmarcar todo; con todas marcadas el link no lleva `JobCategory` (equivale) y el resumen dice "Todas las categorías". (2) **La web sí filtra por provincia** (`Location_State[multi_like][]=<n>`; lo mostró el usuario): `actualizar_filtros.py` lee del lateral "refinar" las provincias que tienen avisos (61 Buenos Aires, 65 Córdoba, 80 Santa Fe; 84 = "Remoto" no se usa, remoto sigue por `JobType`) y pone cada ciudad dentro de su provincia; una ciudad cuya provincia no está en el lateral queda suelta. Los números de las provincias sin avisos NO se conocen (probados 59-62, 72, 74, 83, 85: 0 avisos y ningún nombre): no se inventan. Probado contra la web: todas/todo el país 102 avisos, todas/Buenos Aires 96, todas/CABA 89.

- **1.3.5** (25-11-2026): **se quitó la pantalla de carga de la 1.3.3** (pedido del usuario: "dejalo como estaba antes"). `index.html` y `estilo.css` volvieron a como estaban en la 1.3.2 y en `app.js` se sacaron sus funciones y llamadas; lo de EmpleosIT de la 1.3.4 queda.

## Lecciones técnicas (para no repetir errores)

- Con **pythonw**, cualquier `print` con emoji falla si la salida no está redirigida a un archivo UTF-8.
- En Playwright sync, **no usar `time.sleep` para esperar cambios del navegador**: `page.url` y `ctx.pages` no se actualizan. Usar `page.wait_for_timeout`.
- **Headless no sirve** en Bumeran/ZonaJobs ni en Computrabajo (403). Para pruebas sin molestar al usuario: ventana fuera de la pantalla (`--window-position=-2400,0`).
- Edge **bloquea navegar a URLs `data:`** en la pestaña principal; para pruebas con páginas falsas, usar archivos locales (`file:///…`).
- En el sandbox de Claude Code, las pruebas que usan internet pueden necesitar desactivar el sandbox (si no, `ERR_NAME_NOT_RESOLVED`).
- `instalador/compilar.bat` está en **CRLF** (editarlo preservando los `\r\n`).
- Desde Git Bash, un heredoc puede convertir `\\` en `\`: para editar archivos con barras invertidas (como `Setup.cs`) usar el editor, no scripts escritos en un heredoc.
- En PowerShell las variables no distinguen mayúsculas: `$R` y `$r` son la misma.
- En esta PC el Python con las librerías es el de `programa/datos/python.txt` (hoy `%LOCALAPPDATA%\Programs\Python\Python312\`).
- **`ctx.route` de Playwright no intercepta las redirecciones del servidor** (302): bloquear `/apply/` con una ruta no alcanza si se navega a una página que redirige ahí. Para mirar una redirección sin seguirla, `ctx.request.get(url, max_redirects=0)` (usa las cookies de la sesión).
- Desde Git Bash, un argumento que empieza con `/` se convierte en ruta de Windows (`/empleos-...` → `C:/Program Files/Git/empleos-...`): pasar los caminos sin la barra inicial.
