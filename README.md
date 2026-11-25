# Postulá

App de escritorio para Windows para **postularte a avisos de trabajo** en **Computrabajo**, **Bumeran**, **ZonaJobs** y **EmpleosIT**, de a uno o en automático.

Elegís qué buscar, tocás **Empezar** y la app lee todos los avisos y te los deja ordenados para decidir. **Nada se envía sin que vos lo pidas.**

## Qué hace

- **Dos listas.** Los avisos *sin preguntas* y los *con preguntas*. En Computrabajo y EmpleosIT la primera se llama *Sin revisar*, porque esas bolsas no avisan si hay preguntas hasta abrir el aviso.
- **Auto, apagado al empezar.** Si lo activás, se postula uno por uno, con pausas. Si no, te postulás vos de a uno.
- **No repetís postulaciones.** Al empezar lee las postulaciones de tu cuenta (también las que hiciste desde la web) y saltea esos avisos y sus republicaciones.
- **Formularios** con tu sueldo pretendido y tu zona precargados.
- **El aviso a la vista:** logo de la empresa, fecha de publicación, descripción ordenada y requisitos.
- **Barras de resumen:** nuevas postulaciones (con las respuestas que diste), repetidos y descartados (con opción de restaurarlos).
- **Orden por fecha** de publicación cuando termina de leer.
- **Búsquedas armadas desde listas:** categoría, subáreas, varias localidades, remoto y palabra clave. Podés tener varias y activarlas o desactivarlas.

El navegador trabaja oculto: no aparece en pantalla ni en la barra de tareas (salvo para iniciar sesión).

| | Computrabajo | Bumeran | ZonaJobs | EmpleosIT |
|---|:---:|:---:|:---:|:---:|
| Subáreas | — | Sí | Sí | Varias categorías |
| Avisa de antemano si hay preguntas | No | Sí | Sí | No |
| Requisitos aparte | Sí | Sí | Sí | No |

## Requisitos

- Windows 10 u 11
- Microsoft Edge (viene con Windows)
- Conexión a internet
- Python 3.9 o superior: **si no lo tenés, el instalador ofrece instalarlo**

## Instalación

1. Descargá el proyecto: botón verde **Code → Download ZIP** (o `git clone https://github.com/matichiozza/Postula.git`).
2. Descomprimilo.
3. Ejecutá **`Setup.exe`** y seguí los pasos. El instalador:
   - busca Python (y si falta, ofrece instalar Python 3.12);
   - instala las librerías que usa la app (Playwright y pywebview);
   - verifica que esté Microsoft Edge;
   - instala Postulá en `%LOCALAPPDATA%\Programs\Postulá` (no pide permisos de administrador; podés elegir otra carpeta);
   - crea el acceso en el menú Inicio y, si querés, en el escritorio.

Para actualizar, descargá la versión nueva y volvé a ejecutar su `Setup.exe`: tus datos se conservan.

> Windows puede mostrar un aviso de SmartScreen porque el instalador no está firmado: **Más información → Ejecutar de todas formas**.

## La primera vez

1. Abrí **Postulá**.
2. En **Ajustes** completá **nombre**, **sueldo bruto pretendido** y **zona de residencia** (son obligatorios).
3. Elegí la bolsa y tocá **Elegir qué buscar**.
4. Tocá el **botón de cuenta** → **Vincular cuenta**: se abre Edge, iniciás sesión una vez y la app la recuerda. Desde ahí también podés reconectar o cerrar la sesión.
5. Tocá **Empezar en …**.

### Atajos durante el recorrido

| Tecla | Acción |
|---|---|
| `↑` `↓` | Moverse por la lista |
| `←` `→` | Cambiar entre las dos listas |
| `S` o `Enter` | Postularme al aviso elegido |
| `A` | Activar o desactivar Auto |
| `N` | Descartarlo para siempre (`Z` deshace) |
| `O` | Abrir el aviso en el navegador |
| `L` | Registro del recorrido |
| `P` | Pausar / seguir |
| `Esc` | Volver / cerrar |

## Antes de usarla

Automatizar postulaciones puede ir contra los términos de uso de estas bolsas. La app hace pausas entre envíos y tiene un máximo por corrida, pero usala con criterio y bajo tu responsabilidad. No esquiva captchas ni protecciones: si un sitio frena, se detiene.

## Tus datos

Todo queda **en tu computadora**, en `programa/datos/` dentro de la carpeta instalada (sesiones, historial, descartes y perfil). Esa carpeta no se sube nunca al repositorio. Desde **Ajustes** podés exportar e importar tus datos o empezar de cero.

## Estructura

```
Setup.exe             instalador
programa/
  app/                interfaz (HTML/CSS/JS con pywebview) y motores de cada bolsa
  bolsas/             conexión con cada sitio y sus filtros
  comun/              búsquedas, perfil, descartes, cuentas, fechas, sueldo neto
  instalador/         código del instalador (C#) y compilar.bat
  CONTEXTO.md         documentación técnica completa
```

---

Made by **Matichiozza**
