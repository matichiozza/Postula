# Laburo IA

App de escritorio para Windows que **se postula sola a avisos de trabajo** en **Computrabajo**, **Bumeran** y **ZonaJobs** (EmpleosIT, próximamente).

Elegís qué buscar (categoría, zona o palabra clave) y la app recorre los avisos por vos:

- **Sin preguntas** → te postula automáticamente.
- **Con preguntas** → los junta en una lista para que decidas y respondas (con tu sueldo pretendido y datos ya precargados).
- **Ya postulados, repetidos o descartados** → los saltea solos, así nunca repetís una postulación.

Se maneja con el teclado, podés pausar o cambiar de búsqueda en cualquier momento y el navegador trabaja oculto: no aparece ni en pantalla ni en la barra de tareas.

## Requisitos

- Windows 10 u 11
- Microsoft Edge (viene con Windows)
- Conexión a internet
- Python 3.9 o superior: **si no lo tenés, el instalador lo instala por vos**

## Instalación

1. Descargá el proyecto: botón verde **Code → Download ZIP** (o `git clone https://github.com/matichiozza/Laburo-IA.git`).
2. Descomprimilo en la carpeta donde quieras tener la app (por ejemplo, el Escritorio).
3. Ejecutá **`Setup.exe`** y seguí los pasos. El instalador:
   - busca Python (y si falta, ofrece instalar Python 3.12);
   - instala las librerías que usa la app (Playwright y pywebview);
   - verifica que esté Microsoft Edge;
   - crea **`Laburo IA.exe`** en la misma carpeta y, si querés, un acceso directo en el escritorio.

> Windows puede mostrar un aviso de SmartScreen porque el instalador no está firmado: **Más información → Ejecutar de todas formas**.

## Configuración (la primera vez)

1. Abrí **Laburo IA.exe**.
2. **Ajustes** (arriba a la derecha) → completá **nombre**, **sueldo bruto pretendido** y **zona de residencia**. Son obligatorios: se usan para responder los formularios (la app calcula el neto cuando un aviso lo pide).
3. En el menú, elegí la bolsa y tocá **Elegir qué buscar**: por categoría (con zona y, si querés, palabra clave) o solo por palabra clave. Podés cargar varias búsquedas.
4. Tocá el **botón de cuenta** (a la izquierda de *Empezar*) → **Vincular cuenta**: se abre Edge, iniciás sesión en la bolsa una única vez y la app la recuerda. Si algún día no entra o querés usar otra cuenta: **Reconectar cuenta**.
5. Tocá **Empezar** y listo.

### Atajos durante el recorrido

| Tecla | Acción |
|---|---|
| `P` | Pausar / seguir |
| `S` o `Enter` | Postularme al aviso elegido (abre sus preguntas) |
| `↑` `↓` | Moverse por la lista de avisos para decidir |
| `N` | Descartarlo para siempre (`Z` deshace) |
| `O` | Abrir el aviso en el navegador |
| `H` | Historial de postulaciones que hiciste respondiendo preguntas |
| `Esc` | Volver / cerrar |

## Tus datos

Todo queda **en tu computadora**, en `programa/datos/` (sesiones, historial, descartes y perfil). Esa carpeta no se sube nunca al repositorio. Desde **Ajustes** podés exportar e importar tus datos (para reinstalar sin perder nada) o empezar de cero.

## Estructura

```
Setup.exe             instalador
Laburo IA.exe         lo crea Setup.exe (abre la app)
programa/
  app/                interfaz (HTML/CSS/JS con pywebview) y motores de cada bolsa
  bolsas/             conexión con cada sitio y sus filtros (categorías y zonas)
  comun/              búsquedas, perfil, descartes, cuentas, cálculo de sueldo neto
  instalador/         código del instalador (C#) y compilar.bat
  datos/              tus datos (se crea al usar la app)
  CONTEXTO.md         documentación técnica completa
```

---

Made by **Matichiozza**
