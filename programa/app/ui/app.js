'use strict';
// Versión de la app: se muestra abajo a la izquierda del menú. Regla del usuario: CADA cambio a la app,
// por mínimo que sea, la sube en uno (1.0.0 → 1.0.1 → … → 1.0.9 → 1.1.0). Anotar cada una en CONTEXTO.md.
const VERSION = '1.2.5';
/* Interfaz de Postulá. Habla con Python (app.py) por window.pywebview.api y recibe los
   eventos del motor en window.app.evento(tipo, datos). Todo se maneja con el teclado. */

// ================================================================== utilidades
const $ = s => document.querySelector(s);
const el = (tag, cls, txt) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (txt != null) e.textContent = txt;
  return e;
};
const kbd = t => el('kbd', null, t);
const api = () => window.pywebview && window.pywebview.api;

const ICONOS = {
  check: '<polyline points="20 6 9 17 4 12"/>',
  pregunta: '<circle cx="12" cy="12" r="10"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>',
  ya: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>',
  saltar: '<polygon points="5 4 15 12 5 20 5 4"/><line x1="19" y1="5" x2="19" y2="19"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
  alerta: '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
  x: '<path d="M18 6 6 18"/><path d="M6 6l12 12"/>',
  abajo: '<path d="m6 9 6 6 6-6"/>',
  copia: '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  flecha: '<path d="M5 12h14"/><path d="M12 5l7 7-7 7"/>',
  bandeja: '<polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
  listo: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
  reloj: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
  empresa: '<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M9 22v-4h6v4"/><path d="M8 6h.01M12 6h.01M16 6h.01M8 10h.01M12 10h.01M16 10h.01M8 14h.01M12 14h.01M16 14h.01"/>',
  usuario: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
  buscar: '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
  externo: '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>',
};
function ic(nombre) {
  const t = document.createElement('template');
  t.innerHTML = `<svg class="ic" viewBox="0 0 24 24">${ICONOS[nombre] || ''}</svg>`;
  return t.content.firstChild;
}

const PLATAFORMAS = [
  // hosts: los únicos de los que se aceptan links de búsqueda (lo vuelve a controlar busquedas.py al guardar)
  // icono: logo original de la bolsa (ui/logos/). colores: los de su marca, para el degradé animado del
  // fondo del menú (el azul marino de Computrabajo se aclara un poco para que se vea sobre el fondo oscuro).
  {id: 'computrabajo', nombre: 'Computrabajo', sitio: 'ar.computrabajo.com', activa: true, hosts: ['ar.computrabajo.com'],
   icono: 'logos/computrabajo-icono.svg', colores: ['#1f5fd0', '#ff6f00', '#0d3878']},
  {id: 'bumeran', nombre: 'Bumeran', sitio: 'bumeran.com.ar', activa: true, hosts: ['www.bumeran.com.ar', 'bumeran.com.ar'],
   icono: 'logos/bumeran-icono.png', colores: ['#1f2bff', '#eb0064', '#00dcd4']},
  {id: 'zonajobs', nombre: 'ZonaJobs', sitio: 'zonajobs.com.ar', activa: true, hosts: ['www.zonajobs.com.ar', 'zonajobs.com.ar'],
   icono: 'logos/zonajobs-icono.png', colores: ['#fe633f', '#ff9f43', '#c2361a']},
  {id: 'empleosit', nombre: 'EmpleosIT', sitio: 'empleosit.com.ar', activa: true, hosts: ['www.empleosit.com.ar', 'empleosit.com.ar'],
   icono: 'logos/empleosit-icono.png', colores: ['#1e80c1', '#86dced', '#2197c9']},
];

// Qué significa cada resultado del recorrido, en palabras simples.
const RESULTADO = {
  ok:   {cat: 'ok',       icono: 'check',    texto: 'Te postulaste'},
  libre: {cat: 'decidir', icono: 'bandeja',  texto: 'Nuevo: quedó en la lista'},
  preg: {cat: 'decidir',  icono: 'pregunta', texto: 'Tiene preguntas: quedó para que decidas'},
  ya:   {cat: 'ya',       icono: 'ya',       texto: 'Ya te habías postulado'},
  desc: {cat: 'salteado', icono: 'saltar',   texto: 'Salteado: lo descartaste antes'},
  omit: {cat: 'salteado', icono: 'saltar',   texto: 'Salteado: revisado en una corrida anterior'},
  rep:  {cat: 'salteado', icono: 'saltar',   texto: 'Salteado: repite uno al que ya te postulaste'},
  ext:  {cat: 'salteado', icono: 'externo',  texto: 'Salteado: se postula en la web de la empresa'},
  err:  {cat: 'error',    icono: 'alerta',   texto: 'No se pudo abrir: se reintenta la próxima vez'},
  otro: {cat: 'salteado', icono: 'saltar',   texto: 'Salteado: es de la otra bolsa (Bumeran/ZonaJobs comparten avisos)'},
};

const estadoInicial = () => ({
  modo: 'inicio',        // inicio | lista | cargando | form | velo
  activo: false,         // hay una plataforma corriendo
  plataforma: '',
  items: [],             // avisos para decidir, de las dos listas (uno por grupo de repetidos; "libre" = sin preguntas)
  tab: 'libres',         // lista a la vista: libres (sin preguntas) | preg (con preguntas)
  auto: false,           // modo Auto: siempre arranca desactivado
  autoGid: null,         // aviso que Auto está postulando en este momento
  yaExtra: 0,            // "ya estabas postulado" que salieron al postular desde la lista
  repExtra: 0,           // repetidos que Auto salteó desde la lista
  recuperados: 0,        // descartados que restauraste desde la barra lateral
  porFecha: false,       // lista ordenada por fecha (solo se puede al terminar el recorrido)
  nuevas: [],            // postulaciones hechas en este recorrido (barra "Nuevas postulaciones")
  repetidos: [],         // avisos salteados por repetidos (barra "Repetidos")
  selGid: null,
  detalles: {},
  pedidos: new Set(),
  descartados: [],       // pila para deshacer: {it, pos}
  cargandoGid: null,
  form: null,
  terminado: false,
  hayTotal: false,
  leyendo: null,         // {pagina, avisos} mientras se lee el listado
  pausado: false,        // confirmado por el motor
  pausaPedida: null,     // true/false mientras el motor todavía no confirmó
  cuenta: {ok: 0, ya: 0, preg: 0, desc: 0, omit: 0, rep: 0, ext: 0, err: 0, otro: 0, form: 0, autoExtra: 0},
  descN: 0,              // avisos que descartaste vos desde la lista (N)
  busqs: [],             // búsquedas del recorrido: {indice, resumen, hechos, total, fin}
  busqActiva: 0,         // índice (desde 1) de la búsqueda que se está recorriendo
  cambioPedido: false,   // elegiste otra búsqueda y el motor todavía no la empezó
  nuevos: new Set(),
  veloPrevio: null,
  veloTipo: null,
});
let E = estadoInicial();
let platSel = 0;
let cuentas = {};            // plataforma -> {vinculada, mail, fecha} (datos/<bolsa>/cuenta.json)
let vinculando = null;       // plataforma cuyo login está abierto en Edge

function toast(texto, tipo = 'info', ms = 4200) {
  const t = el('div', 'toast ' + tipo);
  t.append(ic({ok: 'check', error: 'alerta', descarte: 'saltar', info: 'info'}[tipo] || 'info'), el('span', null, texto));
  const caja = $('#toasts');
  caja.append(t);
  while (caja.children.length > 3) caja.firstChild.remove();
  setTimeout(() => t.remove(), ms);
}
const edad = x => x.antiguedad ?? 1e12;               // sin fecha conocida, al final
const visibles = () => {
  const v = E.items.filter(x => !!x.libre === (E.tab === 'libres'));
  // al terminar ya están todos los avisos: recién ahí se puede ordenar del más reciente al más viejo
  return E.terminado && E.porFecha ? v.sort((a, b) => edad(a) - edad(b)) : v;
};
const idxSel = () => visibles().findIndex(x => x.gid === E.selGid);
const actual = () => visibles()[idxSel()];
// Computrabajo y EmpleosIT no avisan de antemano si un aviso tiene preguntas: la primera lista no puede prometerlo.
const sinAnticipo = () => ['computrabajo', 'empleosit'].includes(E.plataformaId);
const nombreLibres = () => sinAnticipo() ? 'Sin revisar' : 'Sin preguntas';
const inicial = t => ((t || '?').trim()[0] || '?').toUpperCase();

// ================================================================== menú
const busquedas = {};   // plataforma -> {url, resumen, ejemplo}
const filtrosPlat = {}; // plataforma -> {categorias, provincias, remoto, relevado} (para armar búsquedas desde listas)

function pintarInicio() {
  const c = $('#plataformas');
  c.innerHTML = '';
  PLATAFORMAS.forEach((p, i) => {
    const item = el('div', 'plat ' + (p.activa ? 'on' : 'off') + (i === platSel ? ' sel' : ''));
    const b = el('button', 'plat-ic');
    b.setAttribute('aria-label', p.activa ? p.nombre : `${p.nombre} (próximamente)`);
    if (!p.activa) b.setAttribute('aria-disabled', 'true');
    const img = el('img');
    img.src = p.icono;
    img.alt = '';
    b.append(img);
    // el clic solo elige la bolsa: el recorrido empieza únicamente con el botón "Empezar en …"
    b.onclick = () => {
      if (!p.activa) { toast(`${p.nombre} todavía no se puede usar: llega pronto.`); return; }
      if (platSel !== i) { platSel = i; pintarInicio(); }
    };
    item.append(b, el('span', 'plat-nombre', p.nombre));
    if (!p.activa) item.append(el('span', 'plat-pronto', 'Próximamente'));
    c.append(item);
  });

  const p = PLATAFORMAS[platSel];
  // fondo: los colores de la bolsa elegida (el CSS hace la transición y la animación)
  p.colores.forEach((col, k) => document.documentElement.style.setProperty(`--c${k + 1}`, col));

  const zona = $('#busquedas-zona');
  zona.innerHTML = '';
  const empezar = $('#btn-empezar');
  const nota = $('#nota-inicio');
  nota.textContent = '';
  if (!p.activa) {
    zona.append(el('span', 'pronto', `${p.nombre} llega pronto a la app.`));
    empezar.textContent = `${p.nombre}: próximamente`;
    empezar.disabled = true;
    pintarCuenta();
    return;
  }
  const bq = busquedas[p.id] || {};
  const lista = bq.busquedas;
  for (const b of (lista || [])) {
    // "Informática / Telecomunicaciones — Remoto (todo el país)" -> qué (en negrita) y dónde
    const [que, donde] = b.resumen.split(' — ');
    const chip = el('span', 'chip' + (b.activa === false ? ' apagada' : ''));
    chip.append(el('b', null, que));
    if (donde) chip.append(el('span', null, donde.replace(' (todo el país)', '')));
    zona.append(chip);
  }
  const editar = el('button', 'chip chip-btn', lista && lista.length ? 'Editar búsquedas' : 'Elegir qué buscar');
  editar.onclick = () => editarBusqueda();
  zona.append(editar);
  empezar.textContent = `Empezar en ${p.nombre}`;
  const cu = cuentas[p.id];
  empezar.disabled = !(cu && cu.vinculada) || !!vinculando || faltanDatos().length > 0;
  if (vinculando) nota.textContent = 'Iniciá sesión en la ventana de Edge que se abrió.';
  else if (cu && !cu.vinculada) nota.textContent = `Para empezar, vinculá tu cuenta de ${p.nombre} con el botón de la izquierda.`;
  pintarCuenta();
}

// ------------------------------------------------------------------ cuenta de la bolsa elegida
async function cargarCuentas() {
  if (!api() || !api().cuentas) return;
  cuentas = await api().cuentas();
  pintarInicio();
}

function pintarCuenta() {
  const p = PLATAFORMAS[platSel];
  const b = $('#btn-cuenta');
  const cu = cuentas[p.id] || {};
  const esperando = vinculando === p.id;
  b.innerHTML = '';
  b.className = 'btn-cuenta' + (cu.vinculada ? ' vinculada' : '') + (esperando ? ' esperando' : '');
  b.disabled = !p.activa;
  b.setAttribute('aria-label', !p.activa ? 'Cuenta' : cu.vinculada ? `Cuenta de ${p.nombre}: vinculada` : `Cuenta de ${p.nombre}: sin vincular`);
  const marca = el('span', 'marca');
  marca.append(ic(esperando ? 'buscar' : cu.vinculada ? 'check' : 'x'));
  b.append(ic('usuario'));
  if (p.activa) b.append(marca);
  b.onclick = ev => { ev.stopPropagation(); alternarMenuCuenta(); };
  if ($('#cuenta-menu').classList.contains('ver')) llenarMenuCuenta();
}

function alternarMenuCuenta() {
  const m = $('#cuenta-menu');
  if (m.classList.contains('ver')) { cerrarMenuCuenta(); return; }
  llenarMenuCuenta();
  m.classList.add('ver');
  $('#btn-cuenta').classList.add('abierto');
}

function cerrarMenuCuenta() {
  $('#cuenta-menu').classList.remove('ver');
  $('#btn-cuenta').classList.remove('abierto');
}

function llenarMenuCuenta() {
  const p = PLATAFORMAS[platSel];
  const cu = cuentas[p.id] || {};
  const m = $('#cuenta-menu');
  m.innerHTML = '';
  m.onclick = ev => ev.stopPropagation();
  m.append(el('h3', null, `Cuenta de ${p.nombre}`));
  const estado = (cls, txt) => { const e = el('div', 'estado ' + cls); e.append(el('span', 'p'), el('span', null, txt)); return e; };
  const acc = (txt, cls, fn) => { const a = el('button', 'acc ' + (cls || ''), txt); a.type = 'button'; a.onclick = fn; return a; };
  const acciones = el('div', 'acciones');
  if (vinculando === p.id) {
    m.append(estado('espera', 'Esperando que inicies sesión…'),
             el('p', null, `Se abrió una ventana de Edge con ${p.nombre}. Entrá con tu cuenta: cuando termines, se cierra sola.`));
    acciones.append(acc('Cancelar', '', cancelarVincular));
  } else if (vinculando) {
    m.append(el('p', null, 'Ya hay un inicio de sesión abierto en otra bolsa. Terminalo o cancelalo primero.'));
  } else if (cu.vinculada) {
    m.append(estado('ok', 'Vinculada'));
    if (cu.mail) m.append(el('div', 'mail', cu.mail));
    m.append(el('p', null, 'Al empezar, la app entra con esta cuenta.'));
    acciones.append(acc('Reconectar cuenta', '', () => vincularCuenta(true)),
                    el('div', 'sub', 'Si no entra, o si querés usar otra cuenta.'),
                    acc('Cerrar sesión', '', cerrarSesion));
  } else {
    m.append(estado('', 'Sin vincular'),
             el('p', null, `Iniciá sesión una vez en ${p.nombre} y la app recuerda tu cuenta. Después tocás Empezar y arranca solo.`));
    acciones.append(acc('Vincular cuenta', 'prim', () => vincularCuenta(false)));
  }
  m.append(acciones);
}

async function vincularCuenta(reconectar) {
  const p = PLATAFORMAS[platSel];
  if (!api() || !api().vincular) return;
  const r = await api().vincular(p.id, reconectar);
  if (!r.ok) { toast(r.error, 'error'); return; }
  vinculando = p.id;
  E.activo = false;
  pintarInicio();
}

async function cerrarSesion() {
  const p = PLATAFORMAS[platSel];
  if (!api() || !api().cerrar_sesion) return;
  const r = await api().cerrar_sesion(p.id);
  if (!r.ok) { toast(r.error, 'error', 7000); return; }
  toast(`Cerré la sesión de ${p.nombre}. Tus búsquedas e historial siguen guardados.`, 'ok');
  cerrarMenuCuenta();
  cargarCuentas();
}

function cancelarVincular() {
  const id = vinculando;
  vinculando = null;
  const fin = () => { cargarCuentas(); if (id) toast('Inicio de sesión cancelado.'); };
  api().detener().then(fin, fin);
  pintarInicio();
}

const eventosCuenta = {
  cuenta_ok(d) {
    vinculando = null;
    cuentas[d.plataforma] = {vinculada: true, mail: d.mail || '', fecha: ''};
    const p = PLATAFORMAS.find(x => x.id === d.plataforma);
    toast(`Cuenta de ${p ? p.nombre : d.plataforma} vinculada${d.mail ? ': ' + d.mail : ''}.`, 'ok');
    cerrarMenuCuenta();
    pintarInicio();
  },
  cuenta_error(d) {
    vinculando = null;
    toast(d.texto, 'error', 7000);
    cargarCuentas();
  },
};

document.addEventListener('click', ev => {
  if (!ev.target.closest('.cuenta-sel')) cerrarMenuCuenta();
});

async function cargarBusquedas() {
  if (!api() || !api().busqueda) return;
  for (const p of PLATAFORMAS.filter(x => x.activa)) {
    const r = await api().busqueda(p.id);
    if (r.ok) busquedas[p.id] = r;
    if (api().filtros) filtrosPlat[p.id] = await api().filtros(p.id);
  }
  if (api().cuentas) cuentas = await api().cuentas();
  pintarInicio();
}

// Resumen legible de un link (igual que busquedas.resumen en Python), para mostrarlo mientras se escribe.
function resumenLink(url) {
  try {
    const u = new URL(/^https?:\/\//i.test(url) ? url : 'https://' + url);
    let t = decodeURIComponent(u.pathname.replace(/\/+$/, '').split('/').pop() || '').replace(/\.html?$/, '');
    t = t.replace(/[-_]+/g, ' ').trim();
    const q = u.searchParams.get('q');
    if (q) t = t ? `${t} · “${q}”` : `“${q}”`;
    return t ? t[0].toUpperCase() + t.slice(1) : u.host;
  } catch (e) { return ''; }
}

// null si el link sirve para esa plataforma; si no, el motivo (mismo criterio que busquedas.validar).
function problemaLink(p, valor) {
  const v = valor.trim();
  if (!v) return null;
  let u;
  try { u = new URL(/^https?:\/\//i.test(v) ? v : 'https://' + v); } catch (e) { return 'Eso no es un link.'; }
  if (!p.hosts.includes(u.host.toLowerCase())) return `Solo se aceptan links de ${p.sitio}.`;
  const jobint = p.id === 'bumeran' || p.id === 'zonajobs';
  if (/\/candidate\/|\/ofertas-de-trabajo\/|\/display-job\//.test(u.pathname) || (jobint && /\/(empleos|postulantes)\//.test(u.pathname)))
    return 'Es el link de un aviso o de tu cuenta: pegá el de la lista de resultados.';
  if (p.id === 'empleosit' && !u.pathname.includes('/search-results-jobs')) return 'Pegá el link de una lista de resultados.';
  if (jobint && !/\.html$/.test(u.pathname))
    return 'Pegá el link de una lista de avisos (termina en .html).';
  return null;
}

// Editor de búsquedas (diseño "A, compacto", elegido por el usuario el 25-11-2026): a la izquierda la lista de
// búsquedas, a la derecha la que se edita. Cada búsqueda se arma de una de dos formas:
//   - Por categoría: categoría + dónde (provincia/ciudad o remoto) + una palabra para afinar (opcional);
//   - Por palabra clave: la palabra (obligatoria) + dónde, sin categoría.
// Las que no se pueden armar con las listas (pegadas a mano con otros filtros) se editan como link.
function editarBusqueda() {
  const p = PLATAFORMAS[platSel];
  if (!p.activa) { toast(`${p.nombre} todavía no está en la app.`); return; }
  const bq = busquedas[p.id] || {};
  const filtros = filtrosPlat[p.id];
  const vacios = () => ({categoria: '', subareas: [], lugares: [], puesto: ''});
  const varias = !!(filtros && filtros.varias_categorias);     // EmpleosIT: sin subáreas, pero se tildan varias categorías
  const entradas = (bq.busquedas || []).map(b => ({
    url: b.url, resumen: b.resumen, original: b.url, error: null, activa: b.activa !== false,
    manual: !(filtros && b.campos), campos: b.campos ? {...b.campos, subareas: [...(b.campos.subareas || [])],
                        lugares: b.campos.lugares || (b.campos.provincia ? [{provincia: b.campos.provincia, ciudad: b.campos.ciudad}] : [])} : vacios(),
    modo: b.campos && !b.campos.categoria && !(b.campos.subareas || []).length && b.campos.puesto ? 'palabra' : 'categoria',
  }));
  let sel = 0;
  let pedido = 0;

  const caja = el('div', 'ed a');
  const lista = el('aside', 'ed-lista');
  const panel = el('section', 'ed-panel');
  caja.append(lista, panel);

  const nueva = (manual = false) => {
    entradas.push({url: null, resumen: null, original: null, error: null, manual: manual || !filtros,
                   campos: vacios(), modo: 'categoria', activa: true});
    sel = entradas.length - 1;
    pintar();
    setTimeout(() => { const f = panel.querySelector('.ed-desp, input'); if (f) f.focus(); }, 30);
  };
  const vacia = e => !e.url && !e.campos.categoria && !e.campos.subareas.length && !e.campos.puesto && !e.campos.lugares.length && !(e.manual && e.linkTexto);

  // armar el link de la búsqueda con lo elegido (o validar el link pegado)
  const recalcular = async e => {
    if (e.manual) {
      const v = (e.linkTexto ?? e.url ?? '').trim();
      const mal = v ? problemaLink(p, v) : 'Pegá el link de una lista de avisos.';
      e.error = mal; e.url = mal ? null : v; e.resumen = mal ? null : resumenLink(v);
      pintarLista(); pintarTitulo();
      return;
    }
    const c = e.campos;
    if (e.modo === 'categoria' && !(varias ? c.subareas.length : c.categoria)) { e.url = null; e.resumen = null; e.error = 'Elegí una categoría.'; pintarLista(); pintarTitulo(); return; }
    if (e.modo === 'palabra' && !c.puesto.trim()) { e.url = null; e.resumen = null; e.error = 'Escribí la palabra clave.'; pintarLista(); pintarTitulo(); return; }
    const yo = ++pedido;
    const r = await api().armar_busqueda(p.id, {categoria: e.modo === 'categoria' ? c.categoria : '', puesto: c.puesto,
                                                subareas: e.modo === 'categoria' ? c.subareas : [],
                                                lugares: c.lugares});
    if (yo !== pedido) return;
    e.url = r.ok ? r.url : null; e.resumen = r.ok ? r.resumen : null; e.error = r.ok ? null : r.error;
    pintarLista(); pintarTitulo();
  };

  const partes = e => {
    if (!e.resumen) return [e.manual ? 'Link pegado a mano' : e.original ? 'Búsqueda sin terminar' : 'Nueva búsqueda',
                            e.error || 'Completá los campos'];
    const [que, donde] = e.resumen.split(' — ');
    return [que, (donde || '').replace(' (todo el país)', '')];
  };

  const pintarLista = () => {
    lista.innerHTML = '';
    const cab = el('div', 'ed-cab');
    const ico = el('img'); ico.src = p.icono; ico.alt = '';
    cab.append(ico, el('span', null, 'Búsquedas'));
    lista.append(cab);
    entradas.forEach((e, i) => {
      const b = el('button', 'ed-item' + (i === sel ? ' sel' : '') + (e.url ? '' : ' incompleta') + (e.activa ? '' : ' apagada'));
      const [que, donde] = partes(e);
      b.append(el('b', null, que), el('span', null, e.activa ? donde : ['Desactivada', donde].filter(Boolean).join(' · ')));
      b.onclick = () => { sel = i; pintar(); };
      lista.append(b);
    });
    const mas = el('button', 'ed-nueva', '+ Nueva búsqueda');
    mas.onclick = () => nueva(false);
    lista.append(mas);
    if (filtros) {
      const link = el('a', 'ed-link', 'Pegar un link de la web');
      link.onclick = () => nueva(true);
      lista.append(link);
    }
  };

  let tituloEl = null;
  const pintarTitulo = () => {
    const e = entradas[sel];
    if (tituloEl) tituloEl.textContent = e && e.resumen ? e.resumen.replace(' — ', ' · ') : (e && e.manual ? 'Link pegado a mano' : 'Nueva búsqueda');
  };

  // ---- desplegable con buscador (categoría, subáreas, lugares)
  let pop = null;                          // {nodo, boton}
  const cerrarPop = () => { if (pop) { pop.nodo.remove(); pop.boton.setAttribute('aria-expanded', 'false'); pop = null; } };
  const llano = t => t.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

  // opciones(filtro) -> [{texto, marcado, tocar, nivel?, abrir?, abierto?}]; uno = se elige una sola y se cierra
  function abrirPop(btn, opciones, uno) {
    if (pop && pop.boton === btn) { cerrarPop(); return; }
    cerrarPop();
    const nodo = el('div', 'ed-pop');
    const buscar = el('input');
    buscar.placeholder = 'Buscar…';
    buscar.spellcheck = false;
    buscar.setAttribute('aria-label', 'Buscar en la lista');
    const ul = el('div', 'ed-opciones');
    const llenar = () => {
      const arriba = ul.scrollTop;
      ul.innerHTML = '';
      const items = opciones(llano(buscar.value.trim()));
      if (!items.length) ul.append(el('p', 'ed-nota', 'Nada coincide.'));
      for (const o of items) {
        const fila = el('div', 'ed-fila' + (o.nivel ? ' hija' : ''));
        const op = el('button', 'ed-op' + (uno ? ' uno' : ''));
        op.type = 'button';
        op.setAttribute('role', uno ? 'radio' : 'checkbox');
        op.setAttribute('aria-checked', o.marcado);
        op.append(el('i', null, o.marcado ? '✓' : ''), el('span', null, o.texto));
        op.onclick = () => { o.tocar(); if (uno) cerrarPop(); else { llenar(); buscar.focus(); } };
        fila.append(op);
        if (o.abrir) {
          const mas = el('button', 'ed-mas' + (o.abierto ? ' abierto' : ''), '›');
          mas.type = 'button';
          mas.setAttribute('aria-label', `Ciudades de ${o.texto}`);
          mas.onclick = () => { o.abrir(); llenar(); buscar.focus(); };
          fila.append(mas);
        }
        ul.append(fila);
      }
      ul.scrollTop = arriba;
    };
    buscar.oninput = () => { ul.scrollTop = 0; llenar(); };
    nodo.append(buscar, ul);
    nodo.onclick = ev => ev.stopPropagation();
    caja.append(nodo);
    pop = {nodo, boton: btn};
    btn.setAttribute('aria-expanded', 'true');
    llenar();
    // debajo del botón; si no entra, arriba
    const rc = caja.getBoundingClientRect(), rb = btn.getBoundingClientRect();
    const abajo = rc.bottom - rb.bottom - 12, encima = rb.top - rc.top - 12;
    const alto = Math.min(300, Math.max(abajo, encima));
    nodo.style.left = `${rb.left - rc.left}px`;
    nodo.style.width = `${rb.width}px`;
    nodo.style.maxHeight = `${alto}px`;
    if (abajo >= Math.min(alto, 220)) nodo.style.top = `${rb.bottom - rc.top + 4}px`;
    else nodo.style.bottom = `${rc.bottom - rb.top + 4}px`;
    buscar.focus();
  }

  const resumir = (nombres, vacio, plural) => !nombres.length ? vacio : nombres.length <= 2 ? nombres.join(', ') : `${nombres.length} ${plural}`;
  const campo = (nombre, control) => {
    const f = el('div', 'ed-renglon');
    f.append(el('span', null, nombre), control);
    return f;
  };
  const desplegable = (texto, vacio, opciones, uno) => {
    const b = el('button', 'ed-desp' + (vacio ? ' vacio' : ''));
    b.type = 'button';
    b.setAttribute('aria-haspopup', 'listbox');
    b.setAttribute('aria-expanded', 'false');
    b.append(el('b', null, texto));
    b.onclick = ev => { ev.stopPropagation(); abrirPop(b, opciones, uno); };
    b.actualizar = (t, v) => { b.firstChild.textContent = t; b.classList.toggle('vacio', v); };
    return b;
  };

  const res = el('div', 'velo-resumen');
  const pintarPanel = () => {
    cerrarPop();
    panel.innerHTML = '';
    const e = entradas[sel];
    const cab = el('div', 'ed-cabecera');
    tituloEl = el('h2', 'ed-titulo');
    cab.append(tituloEl);
    pintarTitulo();
    if (e) {                                   // activar / desactivar sin borrarla
      const llave = el('button', 'ed-activa' + (e.activa ? ' si' : ''));
      llave.type = 'button';
      llave.setAttribute('role', 'switch');
      llave.setAttribute('aria-checked', e.activa);
      llave.setAttribute('aria-label', 'Búsqueda activada');
      llave.title = e.activa ? 'Activada: se recorre al empezar' : 'Desactivada: queda guardada, no se recorre';
      llave.append(el('span', 'llave'));
      llave.onclick = () => { e.activa = !e.activa; pintar(); };
      cab.append(llave);
    }
    const cuerpo = el('div', 'ed-cuerpo');
    cuerpo.onscroll = cerrarPop;
    panel.append(cab, cuerpo);

    if (!e) {
      cuerpo.append(el('p', 'tenue', 'Todavía no tenés búsquedas. Tocá «+ Nueva búsqueda».'));
    } else if (e.manual) {
      const inp = el('input', 'url');
      inp.value = e.linkTexto ?? e.url ?? '';
      inp.placeholder = bq.ejemplo || 'https://';
      inp.spellcheck = false;
      const ayuda = el('div', 'ed-ayuda');
      const revisar = () => { e.linkTexto = inp.value; recalcular(e).then(() => { ayuda.textContent = e.error || e.resumen || ''; ayuda.classList.toggle('error', !!e.error && !!inp.value.trim()); }); };
      inp.oninput = revisar;
      cuerpo.append(campo('Link', inp), ayuda);
      if (filtros) cuerpo.append(el('p', 'ed-nota', 'Para links con filtros que no están en las listas. Al guardar se prueba en la web que traiga avisos.'));
      if (inp.value) revisar();
    } else {
      const c = e.campos;
      const f = filtros;
      const modos = el('div', 'ed-modos');
      for (const [m, t] of [['categoria', 'Por categoría'], ['palabra', 'Por palabra clave']]) {
        const b = el('button', 'ed-modo' + (e.modo === m ? ' sel' : ''), t);
        b.type = 'button';
        b.onclick = () => { if (e.modo !== m) { e.modo = m; pintarPanel(); recalcular(e); } };
        modos.append(b);
      }
      cuerpo.append(modos);

      // varias marcadas a la vez, guardadas en c.subareas (subáreas, o categorías en EmpleosIT)
      const multiple = (lista, vacio, plural) => {
        const texto = () => resumir(lista.filter(o => c.subareas.includes(o.slug)).map(o => o.nombre), vacio, plural);
        const b = desplegable(texto(), !c.subareas.length, q => lista.filter(o => llano(o.nombre).includes(q)).map(o => ({
          texto: o.nombre, marcado: c.subareas.includes(o.slug),
          tocar: () => {
            c.subareas = c.subareas.includes(o.slug) ? c.subareas.filter(v => v !== o.slug) : [...c.subareas, o.slug];
            b.actualizar(texto(), !c.subareas.length);
            recalcular(e);
          },
        })), false);
        return b;
      };

      if (e.modo === 'categoria') {
        if (varias) cuerpo.append(campo('Categorías', multiple(f.categorias, 'Elegí una o varias', 'categorías')));
        else {
          const actualCat = f.categorias.find(v => v.slug === c.categoria);
          cuerpo.append(campo('Categoría', desplegable(actualCat ? actualCat.nombre : 'Elegí una categoría', !actualCat,
            q => f.categorias.filter(o => llano(o.nombre).includes(q)).map(o => ({
              texto: o.nombre, marcado: c.categoria === o.slug,
              tocar: () => { if (c.categoria !== o.slug) { c.categoria = o.slug; c.subareas = []; } pintarPanel(); recalcular(e); },
            })), true)));
          const subs = (actualCat && actualCat.subareas) || [];
          if (subs.length) cuerpo.append(campo('Subáreas', multiple(subs, 'Todas', 'subáreas')));
        }
      }

      // Dónde: remoto, provincias y sus ciudades; se pueden sumar varios (ninguno = todo el país)
      const REM = f.remoto.sem;
      const abiertas = new Set(c.lugares.filter(l => l.ciudad).map(l => l.provincia));
      const nombreLugar = l => {
        if (l.provincia === REM) return 'Remoto';
        const pr = f.provincias.find(v => v.sem === l.provincia);
        if (!pr) return l.provincia;
        const ci = pr.ciudades.find(v => v.sem === l.ciudad);
        return ci ? ci.nombre : pr.nombre;
      };
      const textoLugar = () => resumir(c.lugares.map(nombreLugar), 'Todo el país', 'lugares');
      const esta = (provincia, ciudad) => c.lugares.some(l => l.provincia === provincia && (l.ciudad || '') === ciudad);
      const alternar = (provincia, ciudad) => {
        if (esta(provincia, ciudad)) c.lugares = c.lugares.filter(l => !(l.provincia === provincia && (l.ciudad || '') === ciudad));
        else {
          // "toda la provincia" reemplaza a sus ciudades, y una ciudad reemplaza a "toda la provincia"
          c.lugares = c.lugares.filter(l => l.provincia !== provincia || (ciudad && l.ciudad));
          c.lugares.push({provincia, ciudad});
          if (ciudad) abiertas.add(provincia);   // la ciudad elegida queda a la vista
        }
        donde.actualizar(textoLugar(), !c.lugares.length);
        recalcular(e);
      };
      const donde = desplegable(textoLugar(), !c.lugares.length, q => {
        const salida = [];
        if (llano('Remoto').includes(q)) salida.push({texto: 'Remoto', marcado: esta(REM, ''), tocar: () => alternar(REM, '')});
        for (const pr of f.provincias) {
          const coincide = llano(pr.nombre).includes(q);
          const ciudades = pr.ciudades.filter(ci => !q ? abiertas.has(pr.sem) : coincide ? abiertas.has(pr.sem) : llano(ci.nombre).includes(q));
          if (!coincide && !ciudades.length) continue;
          salida.push({texto: pr.nombre, marcado: esta(pr.sem, ''), tocar: () => alternar(pr.sem, ''),
                       abrir: pr.ciudades.length ? () => { if (abiertas.has(pr.sem)) abiertas.delete(pr.sem); else abiertas.add(pr.sem); } : null,
                       abierto: abiertas.has(pr.sem)});
          for (const ci of ciudades) salida.push({texto: ci.nombre, nivel: 1, marcado: esta(pr.sem, ci.sem), tocar: () => alternar(pr.sem, ci.sem)});
        }
        return salida;
      }, false);
      cuerpo.append(campo('Dónde', donde));

      const palabra = el('input');
      palabra.value = c.puesto;
      palabra.spellcheck = false;
      palabra.placeholder = e.modo === 'categoria' ? 'Opcional' : 'Ej: analista funcional';
      palabra.setAttribute('aria-label', 'Palabra clave');
      palabra.onfocus = cerrarPop;
      let tPal = null;
      palabra.oninput = () => { c.puesto = palabra.value; clearTimeout(tPal); tPal = setTimeout(() => recalcular(e), 200); };
      cuerpo.append(campo(e.modo === 'categoria' ? 'Palabra' : 'Palabra clave', palabra));
    }
    panel.append(res);
    const pie = el('div', 'ed-pie');
    if (e) {
      const quitar = el('button', 'ed-quitar', 'Eliminar');
      quitar.onclick = () => { entradas.splice(sel, 1); sel = Math.max(0, Math.min(sel, entradas.length - 1)); res.textContent = ''; pintar(); };
      pie.append(quitar);
    }
    pie.append(boton('Cerrar', 'Esc', '', cerrarVelo), boton('Guardar', 'Ctrl+Enter', 'si', guardar));
    panel.append(pie);
  };

  caja.addEventListener('click', cerrarPop);                 // clic afuera del desplegable
  caja.addEventListener('keydown', ev => {                   // Esc cierra primero el desplegable
    if (ev.key === 'Escape' && pop) { ev.preventDefault(); ev.stopPropagation(); const btn = pop.boton; cerrarPop(); btn.focus(); }
  });

  const pintar = () => { pintarLista(); pintarPanel(); };

  const guardar = async () => {
    res.className = 'velo-resumen'; res.textContent = '';
    // las nuevas sin tocar no cuentan; las incompletas o con error se marcan
    const usar = entradas.filter(e => !vacia(e));
    const mala = usar.find(e => !e.url);
    if (mala) {
      sel = entradas.indexOf(mala); pintar();
      res.className = 'velo-resumen error';
      res.textContent = mala.error || 'Completá esta búsqueda o eliminala.';
      return;
    }
    // los links pegados a mano (nuevos o cambiados) se prueban en la web: tienen que traer avisos
    const aProbar = usar.filter(e => e.manual && e.url !== e.original);
    if (aProbar.length && api().verificar_busqueda) {
      const btnG = panel.querySelector('.ed-pie .btn.si');
      btnG.disabled = true;
      res.textContent = aProbar.length === 1 ? 'Probando el link en la web…' : `Probando ${aProbar.length} links en la web…`;
      try {
        for (const e of aProbar) {
          const v = await api().verificar_busqueda(p.id, e.url);
          if (!v.ok) {
            sel = entradas.indexOf(e); e.error = v.error; pintar();
            res.className = 'velo-resumen error';
            res.textContent = v.error;
            return;
          }
          e.resumen = v.resumen;
        }
      } finally { const b = panel.querySelector('.ed-pie .btn.si'); if (b) b.disabled = false; }
    }
    const r = await api().guardar_busqueda(p.id, usar.map(e => e.url), usar.filter(e => !e.activa).map(e => e.url));
    if (!r.ok) { res.className = 'velo-resumen error'; res.textContent = r.error; return; }
    busquedas[p.id] = {...r, descartados: (busquedas[p.id] || {}).descartados};   // guardar no trae el conteo de descartes
    cerrarVelo();
    pintarInicio();
    const n = r.busquedas.length;
    toast(!n ? 'Sin búsquedas guardadas.' : n === 1 ? `Búsqueda guardada: ${r.busquedas[0].resumen}` : `${n} búsquedas guardadas`, 'ok');
  };

  caja.addEventListener('keydown', ev => {
    if (ev.key === 'Enter' && ev.ctrlKey) { ev.preventDefault(); ev.stopPropagation(); guardar(); }
  });
  if (!entradas.length) { entradas.push({url: null, resumen: null, original: null, error: null, manual: !filtros, campos: vacios(), modo: 'categoria', activa: true}); }
  pintar();
  velo(null, null, caja, 'busqueda');
  setTimeout(() => { const f = panel.querySelector('.ed-desp, input'); if (f) f.focus(); }, 50);
}

// ------------------------------------------------------------------ tus datos (sueldo y zona)
const miles = v => { const d = String(v || '').replace(/\D/g, ''); return d ? Number(d).toLocaleString('es-AR') : ''; };
let datosGuardados = null;   // lo último que confirmó Python: {sueldo, zona}

function estadoDatos(texto, cls) {
  const e = $('#datos-estado');
  e.className = 'datos-estado ' + (cls || 'tenue');
  e.innerHTML = '';
  if (!texto) { e.append('Se guarda solo al salir del campo'); return; }
  if (cls === 'ok') e.append(ic('check'));
  e.append(texto);
}

// Neto estimado (el cálculo está en sueldo_neto.py). Se pide con un pequeño retraso mientras se escribe.
let netoTimer = null, netoPedido = 0;
const pesos = n => '$ ' + Math.round(n).toLocaleString('es-AR');

function pedirNeto() {
  clearTimeout(netoTimer);
  netoTimer = setTimeout(async () => {
    const caja = $('#d-neto');
    const bruto = Number($('#d-sueldo').value.replace(/\D/g, '')) || 0;
    if (!bruto || !api() || !api().neto) { caja.innerHTML = ''; return; }
    const yo = ++netoPedido;
    const r = await api().neto(bruto);
    if (yo !== netoPedido) return;   // llegó tarde: ya se pidió otro
    const aportes = Object.values(r.aportes).reduce((a, b) => a + b, 0);
    caja.innerHTML = '';
    const linea = el('span');
    linea.append('≈ ', el('strong', null, pesos(r.neto)), ' neto por mes');
    const det = el('small', null,
      `Aportes: −${pesos(aportes)}${r.con_tope ? ' (con tope)' : ''} · Ganancias: ` +
      (r.ganancias > 0 ? `−${pesos(r.ganancias)}` : 'no paga'));
    caja.append(linea, det);
    caja.title = `Estimación con valores de ${r.vigencia}, soltero sin hijos.\n` +
      Object.entries(r.aportes).map(([k, v]) => `${k}: −${pesos(v)}`).join('\n') +
      `\nGanancias (promedio mensual, incluye aguinaldo): −${pesos(r.ganancias)}` +
      '\nNo incluye cuota sindical ni deducciones de Ganancias (alquiler, prepaga, hijos…).';
  }, 150);
}

// ================================================================== ajustes
// "¡Che Mati, postulate!" con el nombre de Ajustes (lo pide Setup.exe; también llega al importar).
// Sin nombre, la pregunta de siempre.
function pintarSaludo(nombre) {
  const primero = (nombre || '').trim().split(/\s+/)[0];
  $('#saludo').textContent = primero ? `¡Che ${primero}, postulate!` : '¿Dónde buscamos hoy?';
}

// En el menú, un recordatorio si todavía no cargaste sueldo o zona (los usan los formularios).
// Nombre, sueldo bruto y zona son obligatorios: sin ellos no se puede empezar un recorrido.
function faltanDatos() {
  if (!datosGuardados) return [];          // todavía no cargó: Python lo vuelve a controlar al empezar
  const d = datosGuardados;
  return [!(d.nombre || '').trim() && 'tu nombre', !d.sueldo && 'tu sueldo bruto', !(d.zona || '').trim() && 'tu zona'].filter(Boolean);
}
const listaYo = xs => xs.length > 1 ? `${xs.slice(0, -1).join(', ')} y ${xs[xs.length - 1]}` : xs[0];

function pintarAvisoDatos() {
  const falta = faltanDatos();
  $('#aviso-datos').textContent = falta.length ? `Para empezar, completá ${listaYo(falta)} en Ajustes →` : '';
  pintarInicio();
}

function mostrarDatos(d) {
  datosGuardados = d;
  $('#d-nombre').value = d.nombre || '';
  $('#d-sueldo').value = miles(d.sueldo);
  $('#d-zona').value = d.zona || '';
  pintarSaludo(d.nombre);
  pintarAvisoDatos();
  pedirNeto();
}

async function cargarDatos() {
  if (!api() || !api().perfil) return;
  mostrarDatos(await api().perfil());
}

async function guardarDatos() {
  if (!api() || !datosGuardados) return;
  const nombre = $('#d-nombre').value.trim().replace(/\s+/g, ' ');
  const sueldo = $('#d-sueldo').value.replace(/\D/g, '');
  const zona = $('#d-zona').value.trim().replace(/\s+/g, ' ');
  if ((datosGuardados.nombre || '') === nombre && String(datosGuardados.sueldo || '') === sueldo
      && (datosGuardados.zona || '') === zona) return;
  const r = await api().guardar_perfil({nombre, sueldo, zona});
  if (!r.ok) { estadoDatos('No se pudo guardar: ' + r.error, 'error'); return; }
  datosGuardados = r;
  pintarSaludo(r.nombre);
  pintarAvisoDatos();
  estadoDatos('Guardado', 'ok');
  setTimeout(() => { if (!document.activeElement || !document.activeElement.closest('#datos')) estadoDatos(); }, 2200);
}

function abrirAjustes() {
  if (E.modo !== 'inicio') return;
  E.modo = 'ajustes';
  $('#inicio').classList.remove('activa');
  $('#ajustes').classList.add('activa');
  estadoDatos();
  pintarResumenDescartados();
}

async function cerrarAjustes() {
  if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
  await guardarDatos();
  E.modo = 'inicio';
  $('#ajustes').classList.remove('activa');
  $('#inicio').classList.add('activa');
  pintarInicio();
}

// ---- exportar / importar (nombre, sueldo, zona y avisos descartados de todas las bolsas)
let dialogoAbierto = false;
async function exportarDatos() {
  if (!api() || dialogoAbierto) return;
  dialogoAbierto = true;
  try {
    await guardarDatos();                      // lo último que escribiste también viaja
    const r = await api().exportar();
    if (r.cancelado) return;
    if (!r.ok) { toast('No se pudo exportar: ' + r.error, 'error', 7000); return; }
    toast(`Listo: exporté tus datos, ${r.busquedas} búsquedas y ${r.descartes} avisos descartados a ${r.archivo.split(/[\\/]/).pop()}`, 'ok', 7000);
  } finally { dialogoAbierto = false; }
}

async function importarDatos() {
  if (!api() || dialogoAbierto) return;
  dialogoAbierto = true;
  try {
    const r = await api().importar();
    if (r.cancelado) return;
    if (!r.ok) { toast(r.error, 'error', 7000); return; }
    mostrarDatos(r);
    const nuevos = r.descartes_nuevos;
    const busq = r.busquedas_nuevas ? `, ${r.busquedas_nuevas} búsquedas` : '';
    toast(`Importé tus datos${r.nombre ? ` (${r.nombre})` : ''}${busq} y ${r.descartes_archivo} avisos descartados` +
          (nuevos !== r.descartes_archivo ? ` (${nuevos} eran nuevos)` : '') + '.', 'ok', 7000);
    for (const k of Object.keys(busquedas)) delete busquedas[k];
    cargarBusquedas();                          // las búsquedas importadas aparecen en el menú
  } finally { dialogoAbierto = false; }
}

// ---- avisos descartados: elegir bolsa, tildar y recuperar (vuelven a aparecer en el próximo recorrido)
async function verDescartados() {
  const r = await api().descartados();
  if (!r.ok) { toast('No pude leer los descartados: ' + r.error, 'error'); return; }
  const bolsas = PLATAFORMAS.filter(p => (r.bolsas[p.id] || []).length);
  const caja = el('div', 'descartados');
  if (!bolsas.length) {
    caja.append(el('p', 'tenue', 'No tenés avisos descartados.'));
    const b = el('div', 'velo-botones');
    b.append(boton('Cerrar', 'Esc', '', cerrarVelo));
    caja.append(b);
    velo('Avisos descartados', '', caja, 'descartados');
    return;
  }
  let actual = bolsas[0].id;
  const marcados = new Set();
  const pestañas = el('div', 'desc-tabs');
  const lista = el('div', 'desc-lista');
  const recuperar = boton('Recuperar', 'Enter', 'si', async () => {
    if (!marcados.size) return;
    const res = await api().recuperar_descartados(actual, [...marcados]);
    if (!res.ok) { toast(res.error, 'error'); return; }
    const nombre = PLATAFORMAS.find(p => p.id === actual).nombre;
    r.bolsas[actual] = r.bolsas[actual].filter(x => !marcados.has(x.id));
    toast(res.recuperados === 1 ? `Recuperé 1 aviso de ${nombre}: va a volver a aparecer.`
                                : `Recuperé ${res.recuperados} avisos de ${nombre}: van a volver a aparecer.`, 'ok');
    if (busquedas[actual]) busquedas[actual].descartados = r.bolsas[actual].length;
    marcados.clear();
    pintar();
    pintarResumenDescartados();
  });
  const todos = boton('Seleccionar todos', 'A', '', () => {
    const items = r.bolsas[actual] || [];
    if (marcados.size === items.length) marcados.clear(); else items.forEach(x => marcados.add(x.id));
    pintar();
  });
  const pintar = () => {
    pestañas.innerHTML = '';
    for (const p of bolsas) {
      const t = el('button', 'desc-tab' + (p.id === actual ? ' sel' : ''), `${p.nombre} (${(r.bolsas[p.id] || []).length})`);
      t.onclick = () => { actual = p.id; marcados.clear(); pintar(); };
      pestañas.append(t);
    }
    const items = r.bolsas[actual] || [];
    lista.innerHTML = '';
    if (!items.length) lista.append(el('div', 'desc-vacia tenue', 'No quedan avisos descartados en esta bolsa.'));
    for (const x of items) {
      const fila = el('label', 'desc-fila' + (marcados.has(x.id) ? ' sel' : ''));
      const cb = el('input');
      cb.type = 'checkbox';
      cb.checked = marcados.has(x.id);
      cb.onchange = () => { if (cb.checked) marcados.add(x.id); else marcados.delete(x.id); pintar(); };
      const txt = el('span', 'desc-txt');
      txt.append(el('b', null, x.titulo || '(sin título)'),
                 el('small', null, [x.empresa, (x.fecha || '').slice(0, 10)].filter(Boolean).join(' · ')));
      fila.append(cb, txt);
      lista.append(fila);
    }
    recuperar.querySelector('span').textContent = marcados.size ? `Recuperar ${marcados.size}` : 'Recuperar';
    recuperar.disabled = !marcados.size;
    todos.querySelector('span').textContent = items.length && marcados.size === items.length ? 'Deseleccionar todos' : 'Seleccionar todos';
    todos.disabled = !items.length;
  };
  const botones = el('div', 'velo-botones');
  botones.append(recuperar, todos, boton('Cerrar', 'Esc', '', cerrarVelo));
  caja.append(pestañas, lista, botones);
  velo('Avisos descartados', 'Tildá los que quieras recuperar: vuelven a aparecer en el próximo recorrido de esa bolsa.', caja, 'descartados');
  pintar();
}

async function pintarResumenDescartados() {
  if (!api() || !api().descartados) return;
  const r = await api().descartados();
  if (!r.ok) return;
  const hay = PLATAFORMAS.some(p => (r.bolsas[p.id] || []).length);
  $('#descartados-resumen').textContent = hay
    ? 'Los avisos que descartaste no se te vuelven a mostrar. Si te arrepentiste de alguno, recuperalo acá.'
    : 'No tenés avisos descartados.';
}

// ---- empezar de cero: confirmación fuerte (hay que escribir BORRAR)
function confirmarBorrado() {
  const caja = el('div');
  const ul = el('ul', 'lista-borrar');
  for (const x of ['Tu nombre, sueldo y zona', 'Los avisos que descartaste para siempre',
                   'Los historiales (a qué te postulaste) y tus búsquedas',
                   'Las sesiones iniciadas en las bolsas (vas a tener que volver a entrar)'])
    ul.append(el('li', null, x));
  const inp = el('input');
  inp.placeholder = 'Escribí BORRAR para confirmar';
  inp.spellcheck = false;
  const borrar = boton('Borrar todo', 'Enter', 'no', () => ejecutarBorrado(inp));
  borrar.disabled = true;
  inp.oninput = () => { borrar.disabled = inp.value.trim().toUpperCase() !== 'BORRAR'; };
  inp.onkeydown = ev => {
    if (ev.key === 'Enter') { ev.preventDefault(); ev.stopPropagation(); if (!borrar.disabled) ejecutarBorrado(inp); }
  };
  const botones = el('div', 'velo-botones');
  botones.append(borrar, boton('Exportar primero', 'Ctrl+E', '', exportarDatos), boton('Cancelar', 'Esc', '', cerrarVelo));
  caja.append(ul, inp, botones);
  velo('¿Borrar todos tus datos?',
       'La app queda como recién instalada. Si querés conservar algo, exportalo primero. Se borra:', caja, 'borrar');
  setTimeout(() => inp.focus(), 50);
}

async function ejecutarBorrado(inp) {
  if (inp.value.trim().toUpperCase() !== 'BORRAR') return;
  const r = await api().borrar_datos();
  if (r.error) { toast('No se pudo borrar: ' + r.error, 'error', 7000); return; }
  cerrarVelo();
  mostrarDatos(r);
  for (const k of Object.keys(busquedas)) delete busquedas[k];
  cargarBusquedas();
  if (r.fallaron && r.fallaron.length)
    toast(`Borré casi todo, pero no pude borrar: ${r.fallaron.join(', ')}. Cerrá Edge y probá de nuevo.`, 'error', 9000);
  else
    toast('Listo: borré todos tus datos. La app quedó como recién instalada.', 'ok', 6000);
}

function prepararDatos() {
  const n = $('#d-nombre'), s = $('#d-sueldo'), z = $('#d-zona');
  $('#btn-ajustes').onclick = abrirAjustes;
  $('#btn-empezar').onclick = () => elegirPlataforma();
  $('#aviso-datos').onclick = abrirAjustes;
  $('#btn-volver').onclick = cerrarAjustes;
  $('#btn-exportar').onclick = exportarDatos;
  $('#btn-importar').onclick = importarDatos;
  $('#btn-borrar').onclick = confirmarBorrado;
  $('#btn-descartados').onclick = verDescartados;
  s.oninput = () => {
    // Formatea con puntos de miles sin mandar el cursor al final.
    const antes = s.value.slice(0, s.selectionStart).replace(/\D/g, '').length;
    s.value = miles(s.value);
    let pos = 0, k = 0;
    while (pos < s.value.length && k < antes) { if (/\d/.test(s.value[pos])) k++; pos++; }
    s.setSelectionRange(pos, pos);
    pedirNeto();
  };
  for (const inp of [n, s, z]) {
    inp.onfocus = () => estadoDatos('Se guarda solo al salir del campo');
    inp.onblur = () => { estadoDatos(); guardarDatos(); };
    inp.onkeydown = ev => {
      if (ev.key === 'Enter') { ev.preventDefault(); if (inp === n) s.focus(); else if (inp === s) z.focus(); else z.blur(); }
      else if (ev.key === 'Escape') { ev.preventDefault(); inp.blur(); }
      ev.stopPropagation();   // mientras se escribe, las teclas no activan atajos
    };
  }
}

async function elegirPlataforma() {
  const p = PLATAFORMAS[platSel];
  if (!p.activa) {
    toast(`${p.nombre} todavía no está en la app.`);
    return;
  }
  if (!api()) { toast('La app todavía está cargando, probá de nuevo en un segundo.'); return; }
  if (vinculando) { toast('Primero terminá (o cancelá) el inicio de sesión.'); return; }
  const falta = faltanDatos();
  if (falta.length) {
    toast(`Antes de empezar, completá ${listaYo(falta)} en Ajustes.`);
    abrirAjustes();
    return;
  }
  if (!(cuentas[p.id] && cuentas[p.id].vinculada)) {
    toast(`Primero vinculá tu cuenta de ${p.nombre}.`);
    if (!$('#cuenta-menu').classList.contains('ver')) alternarMenuCuenta();
    return;
  }
  const bq = busquedas[p.id];
  if (bq && bq.busquedas && !bq.busquedas.some(b => b.activa !== false)) {     // ninguna, o todas desactivadas
    toast(bq.busquedas.length ? 'Todas tus búsquedas están desactivadas: activá al menos una.' : 'Primero elegí qué buscar.');
    editarBusqueda();
    return;
  }
  const r = await api().iniciar(p.id);
  if (!r.ok) { toast(r.error, 'error'); return; }
  E = estadoInicial();
  E.activo = true;
  E.modo = 'lista';
  E.plataforma = r.nombre;
  E.plataformaId = p.id;
  $('#inicio').classList.remove('activa');
  $('#trabajo').classList.add('activa');
  $('#t-icono').src = p.icono;
  $('#t-icono').title = r.nombre;
  $('#busq-menu').classList.remove('ver');
  $('#registro-lista').innerHTML = '';
  cerrarLaterales();
  $('#lateral-desc-lista').innerHTML = '';
  $('#r-barra').style.width = '0';
  $('#r-barra').classList.add('indeterminado');
  $('#r-cuenta').textContent = '';
  $('#r-busq').innerHTML = '';
  pintarStats();
  $('#btn-pausa').classList.add('oculto');
  $('.recorrido').classList.remove('pausado');
  ponerTitulo('Preparando…', false);
  pintarTodo();
}

function volverAlMenu(confirmado = false) {
  if (!E.activo) return;
  if (!confirmado && E.hayTotal && (!E.terminado || (E.auto && E.items.some(x => x.libre)))) {
    const b = el('div', 'botones');
    b.append(boton('Seguir acá', 'Esc', '', cerrarVelo), boton('Volver al menú', 'Enter', 'si', () => volverAlMenu(true)));
    velo('¿Volver al menú?', 'El recorrido se corta acá. Lo que ya se postuló y lo que descartaste queda guardado.', b, 'confirmar');
    return;
  }
  const s = el('div', 'cargando');
  s.append(el('div', 'spinner'), el('span', null, 'Cerrando la sesión de Edge…'));
  velo(`Cerrando ${E.plataforma}`, 'Un momento.', s, 'cerrando');
  E.activo = false;
  const fin = () => {
    E = estadoInicial();
    $('#velo').classList.remove('ver');
    $('#toasts').innerHTML = '';
    $('#trabajo').classList.remove('activa');
    $('#inicio').classList.add('activa');
    pintarInicio();
  };
  api().detener().then(fin, fin);
}

// ================================================================== pausa
function recorriendo() { return E.hayTotal && !E.terminado; }

function alternarPausa() {
  if (!recorriendo()) return;
  const quiero = !(E.pausaPedida ?? E.pausado);
  E.pausaPedida = quiero;
  api().comando('pausa', {pausado: quiero});
  pintarPausa();
}

function pintarPausa() {
  const b = $('#btn-pausa');
  b.classList.toggle('oculto', !recorriendo());
  b.innerHTML = '';
  const pendiente = E.pausaPedida !== null && E.pausaPedida !== E.pausado;
  const enPausa = E.pausaPedida ?? E.pausado;
  b.append(el('span', null, enPausa ? 'Seguir' : 'Pausar'), kbd('P'));
  b.onclick = alternarPausa;
  $('.recorrido').classList.toggle('pausado', E.pausado);
  if (!recorriendo()) return;
  if (pendiente && E.pausaPedida) ponerTitulo('Pausando…', false);
  else if (E.pausado) ponerTitulo('En pausa', false);
  else ponerTitulo('Revisando', false);
  pintarPastilla();
  pintarAtajos();
}

// ================================================================== cabecera
function ponerTitulo(texto, fin) {
  const t = $('#r-titulo');
  t.innerHTML = '';
  t.classList.toggle('fin', !!fin);
  t.append(el('span', 'punto'), el('span', null, texto));
}

function pintarStats() {
  // Contadores chicos; al pasar el mouse, una leyenda mínima dice qué son.
  // "Descartados" son solo los tuyos; los repetidos van aparte. Externos, errores, etc. quedan en el registro (L).
  const c = E.cuenta;
  const nuevas = c.ok + (c.autoExtra || 0) + (c.form || 0);      // en esta corrida: solas o con tus respuestas
  const rep = c.rep + E.repExtra;
  const desc = Math.max(0, c.desc + E.descN - E.recuperados);
  const caja = $('#stats');
  caja.innerHTML = '';
  for (const [cls, icono, n, tip] of [['nuevas', 'listo', nuevas, 'Nuevas postulaciones'],
                                      ['ya', 'check', c.ya + E.yaExtra, 'Ya postulados'],
                                      ['decidir', 'pregunta', E.items.length, 'Para decidir'],
                                      ['rep', 'copia', rep, 'Repetidos'],
                                      ['desc', 'x', desc, 'Descartados por vos']]) {
    const barra = {nuevas: 'lateral-nuevas', rep: 'lateral-rep', desc: 'lateral-desc'}[cls];   // abren su barra
    const t = el(barra ? 'button' : 'span', 'stat ' + cls);
    if (barra) { t.type = 'button'; t.onclick = () => alternarLateral(barra); }
    t.dataset.tip = tip;
    t.setAttribute('aria-label', `${tip}: ${n}`);
    t.append(ic(icono), el('span', null, String(n)));
    caja.append(t);
  }
}

// ================================================================== búsquedas del recorrido
function pintarBusqueda() {
  const b = $('#r-busq');
  b.innerHTML = '';
  const d = E.busqs[E.busqActiva - 1];
  if (!d) return;
  const varias = E.busqs.length > 1;
  if (varias) b.append(el('span', 'num', `${d.indice}/${E.busqs.length}`));
  b.append(el('span', 'txt', d.resumen));
  if (varias) b.append(ic('abajo'));
  b.classList.toggle('elegible', varias);
  b.onclick = varias ? alternarMenuBusquedas : null;
}

function alternarMenuBusquedas(ev) {
  if (ev) ev.stopPropagation();
  const m = $('#busq-menu');
  if (m.classList.contains('ver')) { cerrarMenuBusquedas(); return; }
  m.innerHTML = '';
  for (const d of E.busqs) {
    const activa = d.indice === E.busqActiva && !E.terminado;
    const o = el('button', 'busq-op' + (activa ? ' activa' : (!d.fin && d.total ? ' pausada' : '')));
    o.type = 'button';
    const estado = activa ? 'recorriendo' : d.fin ? 'terminada'
                 : d.total ? `pausada en ${d.hechos} de ${d.total}` : 'sin empezar';
    o.append(el('span', 'n', String(d.indice)), el('span', 't', d.resumen), el('span', 'e', estado));
    o.disabled = activa || d.fin || E.terminado;
    o.onclick = () => elegirBusqueda(d.indice);
    m.append(o);
  }
  m.classList.add('ver');
  $('#r-busq').classList.add('abierto');
}

function cerrarMenuBusquedas() {
  $('#busq-menu').classList.remove('ver');
  $('#r-busq').classList.remove('abierto');
}

function elegirBusqueda(indice) {
  // Solo se recorre una búsqueda a la vez: la actual queda pausada donde estaba y se sigue con la elegida.
  cerrarMenuBusquedas();
  E.cambioPedido = true;
  api().comando('cambiar_busqueda', {indice});
  ponerTitulo('Cambiando de búsqueda…', false);
}

document.addEventListener('click', ev => {
  if (!ev.target.closest('.busq-sel')) cerrarMenuBusquedas();
});

// ================================================================== lista
function pintarPastilla() {
  const libres = E.items.filter(x => x.libre).length;
  for (const [id, tab, nombre, n] of [['#tab-libres', 'libres', nombreLibres(), libres],
                                      ['#tab-preg', 'preg', 'Con preguntas', E.items.length - libres]]) {
    const b = $(id);
    b.querySelector('.nom').textContent = nombre;
    b.querySelector('.n').textContent = n;
    b.classList.toggle('sel', E.tab === tab);
    b.setAttribute('aria-selected', E.tab === tab);
    b.onclick = () => cambiarTab(tab);
  }
  const a = $('#btn-auto');
  a.classList.toggle('oculto', E.tab !== 'libres');
  a.classList.toggle('activo', E.auto);
  a.setAttribute('aria-checked', E.auto);
  a.onclick = alternarAuto;
  $('#auto-estado').textContent = !E.auto ? 'Desactivado: te postulás vos, de a uno'
    : E.pausado ? 'En pausa junto con el recorrido'
    : libres || E.autoGid ? 'Postulando uno por uno' : 'Activado: esperando avisos';
}

function pintarOrden() {
  const b = $('#btn-orden');
  b.classList.toggle('oculto', !E.terminado || !E.items.length);
  b.classList.toggle('activo', E.porFecha);
  b.setAttribute('aria-pressed', E.porFecha);
  b.querySelector('span').textContent = E.porFecha ? 'Ordenados: más recientes primero' : 'Ordenar por fecha de publicación';
  b.onclick = alternarOrden;
}

function alternarOrden() {
  if (E.modo !== 'lista') return;
  E.porFecha = !E.porFecha;
  api().comando('ordenar', {activo: E.porFecha});
  seleccionar(0);
}

function cambiarTab(tab) {
  if (E.modo !== 'lista' || E.tab === tab) return;
  E.tab = tab;
  seleccionar(0);
  pintarAtajos();
}

function alternarAuto() {
  if (!E.activo || E.modo !== 'lista' || E.tab !== 'libres') return;
  E.auto = !E.auto;
  api().comando('auto', {activo: E.auto});
  pintarPastilla();
}

// Si el elegido ya no está en la lista a la vista, se elige el primero.
function asegurarSel() {
  if (E.modo === 'form' || E.modo === 'cargando') return false;
  if (actual()) return false;
  const primero = visibles()[0];
  const gid = primero ? primero.gid : null;
  if (gid === E.selGid) return false;
  E.selGid = gid;
  return true;
}

function pintarLista() {
  const cambio = asegurarSel();
  const items = visibles();
  const ol = $('#lista');
  ol.innerHTML = '';
  for (const it of items) {
    const li = el('li', (it.gid === E.selGid ? 'sel' : '') + (E.nuevos.has(it.gid) ? ' nuevo' : '') +
                        (E.autoGid === it.gid ? ' postulando' : ''));
    li.append(el('span', 't', it.titulo), el('span', 'e', E.autoGid === it.gid ? 'Postulando…'
                : [it.empresa, it.publicado].filter(Boolean).join(' · ')));
    if (it.repetidos.length) {
      const r = el('span', 'rep', `×${it.repetidos.length + 1}`);
      r.title = `Publicado ${it.repetidos.length + 1} veces`;
      li.append(r);
    }
    li.title = it.titulo;
    li.onclick = () => { if (E.modo === 'lista') seleccionar(visibles().findIndex(x => x.gid === it.gid)); };
    ol.append(li);
  }
  E.nuevos.clear();
  $('#l-cant').textContent = E.items.length;
  const v = $('#lista-vacia');
  v.innerHTML = '';
  v.classList.toggle('ver', !items.length);
  if (!items.length) {
    const i = el('div', 'ic-grande');
    i.append(ic(E.terminado ? 'listo' : 'bandeja'));
    v.append(i);
    if (E.leyendo) {
      v.innerHTML = '';
      const c = el('div', 'cargando');
      c.append(el('div', 'spinner'), el('strong', null, 'Leyendo el listado de avisos…'));
      v.append(c, el('span', null, `Página ${E.leyendo.pagina} · ${E.leyendo.avisos} avisos encontrados hasta ahora`));
    } else if (E.fallo && !E.items.length) {
      v.append(el('strong', null, 'No se pudieron leer los avisos'),
               el('span', null, 'Volvé al menú (Esc) y probá de nuevo en un rato.'));
    } else if (E.terminado) {
      v.append(el('strong', null, 'No queda nada en esta lista'),
               el('span', null, E.items.length ? 'Fijate en la otra lista.' : 'Ya pasaste por todos los avisos.'));
    } else {
      v.append(el('strong', null, E.tab === 'libres' ? 'Todavía no hay avisos nuevos' : 'Todavía no hay avisos con preguntas'),
               el('span', null, 'Van a ir apareciendo acá a medida que se recorre el listado.'));
    }
  }
  const s = ol.querySelector('.sel');
  if (s) s.scrollIntoView({block: 'nearest'});
  pintarPastilla();
  pintarOrden();
  pintarStats();
  if (cambio) { pintarPanel(); pedirDetalles(); }
}

function seleccionar(i) {
  const items = visibles();
  if (!items.length) E.selGid = null;
  else E.selGid = items[Math.max(0, Math.min(i, items.length - 1))].gid;
  pintarLista();
  pintarPanel();
  pedirDetalles();
}

let tPedido;
function pedirDetalles() {
  // El aviso elegido y los dos siguientes, así al bajar ya están cargados.
  clearTimeout(tPedido);
  tPedido = setTimeout(() => {
    const i = idxSel();
    if (i < 0 || !E.activo) return;
    for (const it of visibles().slice(i, i + 3)) {
      if (!E.pedidos.has(it.gid)) {
        E.pedidos.add(it.gid);
        api().comando('detalle', {gid: it.gid});
      }
    }
  }, 150);
}

function quitarItem(gid) {
  const i = E.items.findIndex(x => x.gid === gid);
  if (i < 0) return null;
  const v = visibles().findIndex(x => x.gid === gid);
  const [it] = E.items.splice(i, 1);
  if (E.selGid === gid) {
    const quedan = visibles();
    E.selGid = quedan.length ? quedan[Math.max(0, Math.min(v, quedan.length - 1))].gid : null;
  }
  return {it, pos: i};
}

// ================================================================== barras laterales
// Se abren tocando un contador de la cabecera (o L para el registro) y se cierran con la flecha o Esc.
const lateralAbierta = () => document.querySelector('.registro.ver');
const cerrarLaterales = () => document.querySelectorAll('.registro.ver').forEach(l => l.classList.remove('ver'));

function alternarLateral(id) {
  const l = $('#' + id);
  const abierta = l.classList.contains('ver');
  cerrarLaterales();
  if (abierta) return;
  l.classList.add('ver');
  if (id === 'lateral-desc') pintarDescartados();
  if (id === 'lateral-nuevas') pintarNuevas();
  if (id === 'lateral-rep') pintarRepetidos();
}

function verEnLaWeb(url) {
  const b = el('button', 'btn chico', 'Ver en la web');
  b.onclick = () => api().abrir_url(url);
  return b;
}

function tarjetaAviso(x, ...extra) {
  const li = el('li', 'descartado');
  li.append(el('b', null, x.titulo || '(sin título)'), el('small', null, x.empresa || ''), ...extra);
  if (x.url) { const f = el('div', 'fila-botones'); f.append(verEnLaWeb(x.url)); li.append(f); }
  return li;
}

function pintarNuevas() {
  const ol = $('#lateral-nuevas-lista');
  ol.innerHTML = '';
  if (!E.nuevas.length) ol.append(el('li', 'descartado tenue', 'Todavía no te postulaste a ningún aviso en este recorrido.'));
  for (const x of E.nuevas) {
    const resp = x.respuestas || [];
    const extra = [el('span', 'etiqueta' + (resp.length ? ' preg' : ''), resp.length ? 'Con preguntas' : 'Sin preguntas')];
    if (resp.length) {
      const ul = el('ul', 'respuestas');
      for (const q of resp) {
        const it = el('li');
        it.append(el('span', null, q.pregunta), el('strong', null, q.respuesta || '—'));
        ul.append(it);
      }
      extra.push(ul);
    }
    if (x.sin_respuestas) extra.push(el('p', 'error', 'Las respuestas no se guardaron: completalas en la web.'));
    ol.append(tarjetaAviso(x, ...extra));
  }
}

function pintarRepetidos() {
  const ol = $('#lateral-rep-lista');
  ol.innerHTML = '';
  if (!E.repetidos.length) ol.append(el('li', 'descartado tenue', 'No hubo avisos repetidos en este recorrido.'));
  for (const x of E.repetidos) {
    ol.append(tarjetaAviso(x, ...(x.de ? [el('p', 'repite', `Repite uno al que ya te postulaste: ${x.de}`)] : [])));
  }
}

async function pintarDescartados() {
  const ol = $('#lateral-desc-lista');
  if (!ol.children.length) ol.append(el('li', 'descartado tenue', 'Cargando…'));
  const r = await api().descartados();
  ol.innerHTML = '';
  if (!r.ok) { ol.append(el('li', 'descartado', 'No pude leer los descartados: ' + r.error)); return; }
  const items = (r.bolsas || {})[E.plataformaId] || [];
  $('#lateral-desc-sub').textContent = `Todos los que descartaste en ${E.plataforma} (${items.length}). Los restaurados no los toca Auto.`;
  if (!items.length) ol.append(el('li', 'descartado tenue', 'No tenés avisos descartados.'));
  for (const x of items) {
    const li = el('li', 'descartado');
    const botones = el('div', 'fila-botones');
    const restaurar = el('button', 'btn chico', 'Restaurar');
    restaurar.onclick = () => { restaurar.disabled = true; restaurar.textContent = 'Restaurando…'; api().comando('recuperar', {id: x.id}); };
    botones.append(restaurar);
    if (x.url) {
      const ver = el('button', 'btn chico', 'Ver en la web');
      ver.onclick = () => api().abrir_url(x.url);
      botones.append(ver);
    }
    li.append(el('b', null, x.titulo || '(sin título)'),
              el('small', null, [x.empresa, (x.fecha || '').slice(0, 10)].filter(Boolean).join(' · ')), botones);
    ol.append(li);
  }
}

// ================================================================== descripción del aviso
// El texto llega plano (de cualquier bolsa): acá se reconocen subtítulos, viñetas y párrafos.
const VINETA = /^(?:[•·▪●◦‣➢➤►✔✓✅*]\s*|[-–—]\s*(?=\D)|\d{1,2}[.)]\s+)/;
const TITULOS = /^(requisitos|requerimientos|funciones|tareas|responsabilidades|principales|beneficios|ofrecemos|qu[eé] ofrecemos|se ofrece|competencias|perfil|descripci[oó]n|sobre |condiciones|conocimientos|excluyentes?|deseables?)[^.,;]{0,40}$/i;

function descripcion(texto) {
  const caja = el('div', 'det-texto');
  let ul = null, sueltaVineta = false;
  for (const cruda of texto.split('\n')) {
    let linea = cruda.trim();
    if (!linea) continue;
    const m = linea.match(VINETA);
    if (m && !linea.slice(m[0].length).trim()) { sueltaVineta = true; continue; }   // viñeta sola: el texto viene abajo
    if (m || sueltaVineta) {
      if (m) linea = linea.slice(m[0].length).trim();
      sueltaVineta = false;
      if (!ul) { ul = el('ul'); caja.append(ul); }
      ul.append(el('li', null, linea));
      continue;
    }
    // oración cortada en dos líneas ("…en Finanzas y" / "Compras."): se une a la viñeta de arriba
    if (ul && /( y| o| e| de| en| con|,)$/.test(ul.lastChild.textContent)) { ul.lastChild.textContent += ' ' + linea; continue; }
    ul = null;
    if (linea.length <= 70 && (linea.endsWith(':') || /^[^\wÁÉÍÓÚ]*¿.*\?$/.test(linea) || TITULOS.test(linea))) {
      caja.append(el('h3', null, linea.replace(/:$/, '')));
      continue;
    }
    const p = el('p');
    const par = linea.match(/^([^:.]{2,30}):\s+(.+)$/);          // "Modalidad: Híbrido"
    if (par) p.append(el('b', null, par[1] + ': '), par[2]); else p.textContent = linea;
    caja.append(p);
  }
  return caja;
}

// ================================================================== panel
function cabeceraAviso(p, it) {
  const cab = el('div', 'det-cab');
  const txt = el('div');
  const m = el('div', 'det-meta');
  if (it.empresa) m.append(ic('empresa'), el('span', null, it.empresa));
  if (it.publicado) m.append(el('span', null, '  '), ic('reloj'), el('span', null, it.publicado));
  txt.append(el('h2', null, it.titulo), m);
  if (it.busqueda && E.busqueda && E.busqueda.total > 1) {
    const b = el('div', 'det-busq');
    b.append(ic('buscar'), el('span', null, it.busqueda));
    txt.append(b);
  }
  // logo de la empresa (llega con la descripción); sin logo, o si no carga, la inicial
  const avatar = el('div', 'avatar', inicial(it.empresa));
  const logo = (E.detalles[it.gid] || {}).logo;
  if (logo && logo.startsWith('https://')) {
    const img = el('img');
    img.alt = '';
    img.referrerPolicy = 'no-referrer';
    img.onload = () => { avatar.textContent = ''; avatar.classList.add('con-logo'); avatar.append(img); };
    img.src = logo;
  }
  cab.append(avatar, txt);
  p.append(cab);
}

let vistaPanel = null;   // qué muestra el panel (aviso o formulario de tal aviso)

function pintarPanel() {
  const p = $('#panel');
  const esForm = E.modo === 'form' && E.form;
  const it = actual();
  // Al cambiar de aviso (o entre aviso y formulario) el panel arranca desde arriba;
  // si es el mismo (llegó la descripción, se eligió una opción) se respeta el scroll.
  const vista = esForm ? 'form:' + E.form.gid : 'aviso:' + (it ? it.gid : '');
  if (vista !== vistaPanel) { vistaPanel = vista; p.scrollTop = 0; }
  p.innerHTML = '';
  if (esForm) return pintarForm(p);
  if (!it) {
    const v = el('div', 'vacio');
    v.append(el('div', null, visibles().length ? 'Elegí un aviso de la lista.' : ''));
    p.append(v);
    return;
  }
  cabeceraAviso(p, it);

  if (E.modo === 'cargando' && E.cargandoGid === it.gid) {
    const c = el('div', 'cargando');
    c.append(el('div', 'spinner'),
             el('span', null, (it.libre ? 'Postulándote… Si tiene preguntas, te las muestro.' : 'Abriendo las preguntas…') +
                              ' Si justo se está revisando otro aviso, tarda unos segundos más.'));
    p.append(c);
  } else if (E.autoGid === it.gid) {
    const c = el('div', 'cargando');
    c.append(el('div', 'spinner'), el('span', null, 'Auto se está postulando a este aviso…'));
    p.append(c);
  } else {
    const acc = el('div', 'acciones');
    acc.append(boton('Postularme', 'S', 'si', postular),
               boton('Descartar para siempre', 'N', 'no', descartar),
               boton('Ver en la web', 'O', '', () => api().abrir_url(it.url)));
    p.append(acc);
    if (it.libre) p.append(el('p', 'nota-libre', sinAnticipo()
      ? 'Al apretar Postularme quedás postulado en el acto, salvo que tenga preguntas (ahí te las muestro).'
      : 'No tiene preguntas: al apretar Postularme quedás postulado en el acto.'));
  }

  if (it.repetidos.length) {
    const r = el('div', 'repetidos');
    r.append(el('strong', null, `Publicado ${it.repetidos.length + 1} veces.`),
             el('span', 'tenue', ' Lo que decidas vale para todas.'));
    const ul = el('ul');
    for (const x of it.repetidos) ul.append(el('li', null, x.titulo));
    r.append(ul);
    p.append(r);
  }

  const d = E.detalles[it.gid];
  if (!d) {
    const sk = el('div', 'esqueleto');
    for (let k = 0; k < 10; k++) sk.append(el('i'));
    p.append(sk);
    return;
  }
  if (d.tags && d.tags.length) {
    const t = el('div', 'tags');
    for (const x of d.tags) t.append(el('span', 'tag', x));
    p.append(t);
  }
  if (d.error) p.append(el('p', 'error', d.error));
  if (d.texto) p.append(descripcion(d.texto));
  if (d.requisitos && d.requisitos.length) {        // siempre al final, y solo si la bolsa los informa
    const r = el('div', 'requisitos');
    const ul = el('ul');
    for (const x of d.requisitos) {
      const li = el('li');
      li.append(ic('check'), el('span', null, x));
      ul.append(li);
    }
    r.append(el('h3', null, 'Requerimientos'), ul);
    p.append(r);
  }
}

function boton(texto, tecla, cls, fn) {
  // La tecla se muestra solo con una plataforma corriendo (pedido del usuario: en el menú, Ajustes
  // y el editor de búsquedas no se ven atajos; igual funcionan).
  const b = el('button', 'btn ' + cls);
  b.append(el('span', null, texto));
  if (E.activo) b.append(kbd(tecla));
  b.onclick = fn;
  return b;
}

// ================================================================== acciones
function postular() {
  const it = actual();
  if (!it || E.autoGid === it.gid) return;
  E.modo = 'cargando';
  E.cargandoGid = it.gid;
  api().comando('abrir_form', {gid: it.gid});
  pintarPanel();
  pintarAtajos();
}

function descartar() {
  const it = actual();
  if (!it || E.autoGid === it.gid) return;
  // Se quita al instante; el motor lo registra en cuanto termina lo que está haciendo.
  E.descartados.push(quitarItem(it.gid));
  E.descN++;
  api().comando('descartar', {gid: it.gid});
  if ($('#lateral-desc').classList.contains('ver')) setTimeout(pintarDescartados, 800);
  toast(`Descartado para siempre: ${it.titulo}. Z para deshacer.`, 'descarte');
  pintarLista();
  pintarPanel();
  pedirDetalles();
}

function deshacer() {
  const q = E.descartados.pop();
  if (!q) { toast('No hay nada para deshacer.'); return; }
  E.items.splice(Math.min(q.pos, E.items.length), 0, q.it);
  E.descN = Math.max(0, E.descN - 1);
  api().comando('deshacer', {});
  toast(`Vuelve a la lista: ${q.it.titulo}`, 'ok');
  E.tab = q.it.libre ? 'libres' : 'preg';
  seleccionar(visibles().findIndex(x => x.gid === q.it.gid));
  pintarAtajos();
}

// ================================================================== formulario
const respondida = q => {
  const v = E.form.resp[q.indice];
  return v != null && String(v).trim() !== '';
};

function abrirForm(d) {
  const f = {gid: d.gid, preguntas: d.preguntas, resp: {}, activa: 0, enviando: false, error: null};
  for (const q of d.preguntas) if (q.precarga) f.resp[q.indice] = q.precarga;
  E.form = f;
  E.modo = 'form';
  E.cargandoGid = null;
  pintarPanel();
  pintarAtajos();
}

function cerrarForm() {
  E.form = null;
  E.cargandoGid = null;
  E.modo = 'lista';
  pintarPanel();
  pintarAtajos();
}

function pintarForm(p) {
  const f = E.form;
  const it = E.items.find(x => x.gid === f.gid) || {titulo: '', empresa: ''};
  cabeceraAviso(p, it);
  p.append(el('div', 'form-sub', `${f.preguntas.length === 1 ? 'Una pregunta' : f.preguntas.length + ' preguntas'} de la empresa. Respondé y enviá tu postulación.`));

  if (f.preguntas.some(q => !q.soportada)) {
    p.append(el('p', 'error', 'Este formulario tiene un tipo de pregunta que la app no sabe completar. Postulate desde la web.'));
    const acc = el('div', 'acciones');
    acc.append(boton('Ver en la web', 'O', 'si', () => api().abrir_url(it.url)), boton('Volver', 'Esc', '', cerrarForm));
    p.append(acc);
    return;
  }

  f.preguntas.forEach((q, k) => {
    const card = el('div', 'q' + (k === f.activa ? ' activa' : '') + (respondida(q) ? ' lista-ok' : ''));
    const t = el('div', 'q-titulo');
    t.append(el('span', 'q-num', String(k + 1)), el('span', null, (q.titulo || '').trim()));
    card.append(t);
    if (q.abierta) {
      const ta = el('textarea');
      ta.value = f.resp[q.indice] || '';
      ta.maxLength = q.maxlen || 500;
      ta.dataset.k = k;
      ta.oninput = () => {
        f.resp[q.indice] = ta.value;
        card.classList.toggle('lista-ok', respondida(q));
      };
      ta.onfocus = () => { if (f.activa !== k) activar(k); };
      const precargado = {sueldo: 'Precargué tu sueldo bruto pretendido', sueldo_neto: 'Pregunta el neto: precargué tu sueldo neto estimado',
                          zona: 'Precargué tu zona de residencia'}[q.precarga_tipo];
      card.append(ta, el('div', 'ayuda', precargado
        ? precargado + ' (se cambia en Ajustes). Enter para seguir.'
        : 'Enter para seguir · Shift+Enter para una línea nueva'));
    } else {
      q.opciones.forEach((o, j) => {
        const op = el('div', 'op' + (f.resp[q.indice] === o.valor ? ' sel' : ''));
        op.append(el('span', 'n', String(j + 1)), el('span', null, o.texto));
        op.onclick = ev => { ev.stopPropagation(); elegirOpcion(k, j, true); };
        card.append(op);
      });
      card.append(el('div', 'ayuda', 'Apretá el número de la opción (o ↑ ↓ y Enter)'));
    }
    card.onclick = ev => { if (ev.target.tagName !== 'TEXTAREA') activar(k); };
    p.append(card);
  });

  const pie = el('div', 'form-pie');
  const env = boton(f.enviando ? 'Enviando…' : 'Enviar postulación', 'Ctrl+Enter', 'si', enviar);
  env.id = 'btn-enviar';
  if (f.activa === f.preguntas.length) env.classList.add('listo');
  pie.append(env, boton('Cancelar', 'Esc', '', cerrarForm));
  if (f.enviando) pie.append(el('div', 'spinner'));
  p.append(pie);
  if (f.error) p.append(el('p', 'error', f.error));
  p.append(el('div', 'form-espacio'));   // deja centrar también la última pregunta y Enviar
  enfocar();
}

function activar(k) {
  const f = E.form;
  f.activa = Math.max(0, Math.min(k, f.preguntas.length));
  pintarPanel();
}

function enfocar() {
  const f = E.form;
  const ta = document.querySelector(`textarea[data-k="${f.activa}"]`);
  if (ta) {
    if (document.activeElement !== ta) {
      ta.focus({preventScroll: true});
      ta.setSelectionRange(ta.value.length, ta.value.length);
    }
  } else if (f.activa === f.preguntas.length) {
    $('#btn-enviar') && $('#btn-enviar').focus({preventScroll: true});
  } else if (document.activeElement && document.activeElement.blur) {
    document.activeElement.blur();
  }
  centrarEnPanel(document.querySelector('.q.activa') || $('.form-pie'));
}

// Lleva el elemento al centro del panel (si es más alto que el panel, lo deja arriba).
function centrarEnPanel(elem) {
  if (!elem) return;
  const p = $('#panel');
  const rp = p.getBoundingClientRect(), re = elem.getBoundingClientRect();
  const delta = re.height > rp.height - 48
    ? re.top - rp.top - 24
    : (re.top + re.height / 2) - (rp.top + rp.height / 2);
  if (Math.abs(delta) > 2) p.scrollBy({top: delta, behavior: 'smooth'});
}

function elegirOpcion(k, j, avanzar) {
  const f = E.form;
  const q = f.preguntas[k];
  f.resp[q.indice] = q.opciones[j].valor;
  f.activa = avanzar ? k + 1 : k;
  pintarPanel();
}

function enviar() {
  const f = E.form;
  if (!f || f.enviando) return;
  const falta = f.preguntas.findIndex(q => !respondida(q));
  if (falta >= 0) {
    toast(`Falta responder la pregunta ${falta + 1}.`, 'error');
    activar(falta);
    return;
  }
  f.enviando = true;
  f.error = null;
  api().comando('enviar', {gid: f.gid, respuestas: f.preguntas.map(q => ({
    indice: q.indice, tipo: q.abierta ? 'texto' : 'radio', valor: f.resp[q.indice]}))});
  pintarPanel();
}

function teclaForm(ev) {
  const f = E.form;
  if (ev.key === 'Escape') { cerrarForm(); return true; }
  if (f.enviando) return true;
  if (ev.key === 'Enter' && ev.ctrlKey) { enviar(); return true; }
  if (f.preguntas.some(q => !q.soportada)) {
    if (ev.key.toLowerCase() === 'o') { const it = actual(); if (it) api().abrir_url(it.url); return true; }
    return false;
  }
  if (ev.key === 'Tab') { activar(f.activa + (ev.shiftKey ? -1 : 1)); return true; }
  if (f.activa === f.preguntas.length) {           // parado en "Enviar"
    if (ev.key === 'Enter') { enviar(); return true; }
    if (ev.key === 'ArrowUp') { activar(f.activa - 1); return true; }
    return false;
  }
  const q = f.preguntas[f.activa];
  if (q.abierta) {
    if (ev.key === 'Enter' && !ev.shiftKey) {
      if (respondida(q)) activar(f.activa + 1);
      else toast('Escribí una respuesta (o Esc para cancelar).');
      return true;
    }
    return false;                                    // escribir normalmente
  }
  const j = q.opciones.findIndex(o => o.valor === f.resp[q.indice]);
  if (ev.key === 'ArrowDown') { elegirOpcion(f.activa, Math.min(j + 1, q.opciones.length - 1), false); return true; }
  if (ev.key === 'ArrowUp') {
    if (j <= 0 && f.activa > 0) activar(f.activa - 1);
    else elegirOpcion(f.activa, Math.max(j - 1, 0), false);
    return true;
  }
  if (/^[1-9]$/.test(ev.key) && +ev.key <= q.opciones.length) { elegirOpcion(f.activa, +ev.key - 1, true); return true; }
  if (ev.key === 'Enter') {
    if (j >= 0) activar(f.activa + 1);
    else toast('Elegí una opción.');
    return true;
  }
  return false;
}

// ================================================================== atajos, velo
function pintarAtajos() {
  const a = $('#atajos');
  a.innerHTML = '';
  const lista = {
    lista: [['↑ ↓', 'Moverse'], ['← →', 'Cambiar de lista'], ...(E.tab === 'libres' ? [['A', 'Auto']] : []),
            ['S', 'Postularme'], ['N', 'Descartar para siempre'], ['Z', 'Deshacer'],
            ['O', 'Ver en la web'], ['L', 'Registro']],
    cargando: [['Esc', 'Volver a la lista']],
    form: [['1-9', 'Elegir opción'], ['Enter', 'Siguiente'], ['Tab', 'Cambiar de pregunta'],
           ['Ctrl+Enter', 'Enviar'], ['Esc', 'Cancelar']],
  }[E.modo] || [];
  for (const [k, t] of lista) {
    const s = el('span');
    for (const parte of k.split(' ')) s.append(kbd(parte));
    s.append(t);
    a.append(s);
  }
  if (E.modo === 'lista' && recorriendo()) {
    const s = el('span');
    s.append(kbd('P'), (E.pausaPedida ?? E.pausado) ? 'Seguir el recorrido' : 'Pausar el recorrido');
    a.append(s);
  }
  if (E.modo === 'lista') {
    const s = el('span', 'der');
    s.append(kbd('Esc'), 'Volver al menú');
    a.append(s);
  }
}

function velo(titulo, texto, extra, tipo) {
  if (E.modo !== 'velo') E.veloPrevio = E.modo;
  E.modo = 'velo';
  E.veloTipo = tipo;
  const c = $('#velo-caja');
  c.innerHTML = '';
  if (titulo) c.append(el('h2', null, titulo));
  if (texto) c.append(el('p', null, texto));
  if (extra) c.append(extra);
  $('#velo').classList.add('ver');
}

function cerrarVelo() {
  $('#velo').classList.remove('ver');
  E.modo = E.veloPrevio || 'lista';
  E.veloTipo = null;
  pintarAtajos();
}

function pintarTodo() {
  pintarLista();
  pintarPanel();
  pintarAtajos();
}

// ================================================================== eventos del motor
const handlers = {
  estado(d) { if (!E.hayTotal) ponerTitulo(d.texto, false); },

  login() {
    const s = el('div', 'cargando');
    s.append(el('div', 'spinner'), el('span', null, 'Esperando que inicies sesión…'));
    velo(`Iniciá sesión en ${E.plataforma}`,
         'Se abrió una ventana de Edge con la página de login. Cuando entres, la app sigue sola. (Esc para volver al menú)', s, 'login');
  },
  login_ok() { cerrarVelo(); },

  usuario(d) {
    // la cuenta con la que entraste: queda como leyenda del logo de la bolsa
    if (d.mail) $('#t-icono').title = `${E.plataforma} · ${d.mail}`;
  },

  busquedas(d) {
    E.busqs = d.items.map(x => ({...x, hechos: 0, total: 0, fin: false}));
  },

  busqueda(d) {
    E.busqueda = d;
    E.busqActiva = d.indice;
    if (!E.busqs.length) E.busqs = [{indice: d.indice, resumen: d.resumen, hechos: 0, total: 0, fin: false}];
    pintarBusqueda();
    $('#r-barra').classList.add('indeterminado');
    $('#r-barra').style.width = '0';
    $('#r-cuenta').textContent = '';
    if (d.total > 1) {
      const li = el('li', 'sep', `Búsqueda ${d.indice} de ${d.total}: ${d.resumen}`);
      $('#registro-lista').prepend(li);
      const previa = E.busqs[d.indice - 1];
      if (previa && previa.total && previa.hechos && !E.cambioPedido) {
        toast(`Vuelvo a «${d.resumen}» donde la dejaste (${previa.hechos} de ${previa.total}).`, 'info', 5000);
      } else if (!E.cambioPedido && d.indice > 1) toast(`Sigo con la búsqueda ${d.indice} de ${d.total}: ${d.resumen}`, 'info', 4000);
    }
    E.cambioPedido = false;
  },
  busqueda_fin(d) {
    const b = E.busqs[d.indice - 1];
    if (b) b.fin = true;
    // Los avisos que ya revisaste en otras corridas se saltean al instante: si no hay nuevos, una
    // búsqueda termina en un segundo. Se avisa para que no parezca que se cortó.
    if (d.total === undefined) return;
    const txt = !d.total ? `«${d.resumen}» no trajo avisos.`
      : d.abiertos ? `Terminé «${d.resumen}»: ${d.abiertos} ${d.abiertos === 1 ? 'aviso nuevo' : 'avisos nuevos'} de ${d.total}.`
      : `«${d.resumen}»: no hay avisos nuevos (los ${d.total} ya los habías revisado).`;
    toast(txt, 'info', 6000);
  },

  leyendo(d) {
    E.leyendo = d;
    ponerTitulo('Leyendo avisos…', false);
    $('#r-cuenta').textContent = `pág. ${d.pagina} · ${d.avisos}`;
    pintarLista();
  },

  listado(d) {
    E.hayTotal = true;
    E.leyendo = null;
    $('#r-barra').classList.remove('indeterminado');
    const b = E.busqs[E.busqActiva - 1];
    if (b) { b.total = d.total; b.hechos = d.retoma || 0; }
    $('#r-barra').style.width = d.total ? (100 * (d.retoma || 0) / d.total) + '%' : '0';
    $('#r-cuenta').textContent = `${d.retoma || 0}/${d.total}`;
    if (d.en_otras) toast(`${d.en_otras} avisos de esta búsqueda ya estaban en otra: no se repiten.`, 'info', 4000);
    pintarPausa();
    pintarLista();
  },

  pausa(d) {
    E.pausado = d.pausado;
    if (E.pausaPedida === d.pausado) E.pausaPedida = null;
    pintarPausa();
    toast(d.pausado ? 'Recorrido en pausa. P para seguir.' : 'El recorrido sigue.', 'info', 2500);
  },

  grupos(d) {
    E.items = d.items;
    seleccionar(0);
  },
  recuperado(d) {
    if (d.contado) E.recuperados++;
    if (d.gid_deshacer) E.descartados = E.descartados.filter(q => q.it.gid !== d.gid_deshacer);   // ya no hay qué deshacer
    pintarStats();
    toast(d.lista ? `Restaurado: volvió a «${d.lista === 'libres' ? nombreLibres() : 'Con preguntas'}».`
                  : 'Restaurado: va a aparecer cuando el recorrido lo encuentre.', 'ok');
    pintarDescartados();
  },
  auto(d) {
    E.auto = d.activo;
    pintarPastilla();
  },
  auto_en(d) {
    E.autoGid = d.gid;
    pintarLista();
    if (E.selGid === d.gid && E.modo === 'lista') pintarPanel();
  },
  grupo_nuevo(it) {
    if (E.items.some(x => x.gid === it.gid)) return;
    E.items.push(it);
    E.nuevos.add(it.gid);
    if (!E.selGid) seleccionar(0); else pintarLista();
  },
  grupo_act(it) {
    const i = E.items.findIndex(x => x.gid === it.gid);
    if (i < 0) return;
    E.items[i] = it;
    // lo estabas postulando y resultó tener preguntas: se pasa a esa lista para mostrar el formulario
    if (E.cargandoGid === it.gid && !it.libre) E.tab = 'preg';
    pintarLista();
    if (it.gid === E.selGid && E.modo !== 'form') pintarPanel();
  },
  grupo_quitado(d) {
    if (d.motivo === 'descartado') return;           // ya se quitó al apretar N
    const eraElElegido = E.selGid === d.gid;
    quitarItem(d.gid);
    if (E.autoGid === d.gid) E.autoGid = null;
    if (d.motivo === 'postulado') {
      if (d.postulacion) E.nuevas.unshift(d.postulacion);
      if (d.con_form) E.cuenta.form = (E.cuenta.form || 0) + 1;
      else E.cuenta.autoExtra = (E.cuenta.autoExtra || 0) + 1;
    } else if (d.motivo === 'ya_postulado') E.yaExtra++;
    else if (d.motivo === 'repetido') { E.repExtra++; E.repetidos.unshift({titulo: d.titulo, empresa: d.empresa, url: d.url, de: d.de}); }
    if (d.auto) {
      const res = {postulado: 'ok', ya_postulado: 'ya', preguntas: 'preg', externo: 'ext', repetido: 'rep'}[d.motivo] || 'err';
      const li = el('li');
      li.append(el('span', 'punto-c c-' + RESULTADO[res].cat), el('span', 't', d.titulo), el('span', 'que', RESULTADO[res].texto));
      $('#registro-lista').prepend(li);
    }
    const eraElAbierto = (E.form && E.form.gid === d.gid) || E.cargandoGid === d.gid;
    if (eraElAbierto) {
      E.form = null;
      E.cargandoGid = null;
      E.modo = 'lista';
    }
    if (d.motivo !== 'preguntas') toast(`${d.texto || ''} ${d.titulo}`.trim(), ['error', 'externo'].includes(d.motivo) ? 'error' : 'ok');
    if ($('#lateral-nuevas').classList.contains('ver')) pintarNuevas();
    if ($('#lateral-rep').classList.contains('ver')) pintarRepetidos();
    pintarLista();
    // con Auto andando, no se repinta el panel de otro aviso (no molesta si estás completando un formulario)
    if (eraElElegido || eraElAbierto) pintarPanel();
    pintarAtajos();
    pedirDetalles();
  },
  deshecho(d) {
    if (!E.items.some(x => x.gid === d.item.gid)) {
      E.items.splice(Math.min(d.pos, E.items.length), 0, d.item);
      pintarLista();
    }
  },

  detalle(d) {
    E.detalles[d.gid] = d;
    if (d.gid === E.selGid && E.modo !== 'form') pintarPanel();
  },

  form(d) {
    if (E.modo !== 'cargando' || E.cargandoGid !== d.gid) return;   // lo cancelaste mientras cargaba
    abrirForm(d);
  },
  form_error(d) {
    if (E.form && E.form.gid === d.gid) {
      E.form.enviando = false;
      E.form.error = d.texto;
      pintarPanel();
    } else if (E.cargandoGid === d.gid) {
      E.cargandoGid = null;
      E.modo = 'lista';
      pintarTodo();
    }
    toast(d.texto, 'error', 7000);
  },

  progreso(d) {
    // Las postulaciones hechas desde la lista (con formulario, o que se resolvieron solas al apretar S)
    // se cuentan aparte en grupo_quitado: acá solo se actualiza lo del recorrido.
    E.cuenta = {...d, form: E.cuenta.form || 0, autoExtra: E.cuenta.autoExtra || 0};
    $('#r-barra').style.width = (100 * d.hechos / d.total) + '%';
    $('#r-cuenta').textContent = `${d.hechos}/${d.total}`;
    const b = E.busqs[(d.busqueda || E.busqActiva) - 1];
    if (b) { b.hechos = d.hechos; b.total = d.total; }
    const u = d.ultimo;
    if (u && u.res === 'rep') {
      E.repetidos.unshift(u);
      if ($('#lateral-rep').classList.contains('ver')) pintarRepetidos();
    }
    if (u) {
      const r = RESULTADO[u.res] || RESULTADO.err;
      const li = el('li');
      li.append(el('span', 'punto-c c-' + r.cat), el('span', 't', `${u.titulo} — ${u.empresa}`), el('span', 'que', r.texto));
      $('#registro-lista').prepend(li);
    }
    pintarStats();
  },
  fase1_fin(d) {
    E.fallo = !!d.fallo;
    E.terminado = true;
    E.pausado = false;
    E.pausaPedida = null;
    pintarPausa();
    pintarAtajos();
    $('#r-barra').classList.remove('indeterminado');
    $('#r-barra').style.width = '100%';
    const nuevos = E.cuenta.ok + (E.cuenta.autoExtra || 0) + (E.cuenta.form || 0);
    // cuántos quedan para decidir ya lo dice la lista: arriba no se repite
    ponerTitulo(nuevos === 1 ? 'Listo · 1 postulación nueva'
              : nuevos ? `Listo · ${nuevos} postulaciones nuevas`
              : E.items.length ? 'Listo' : E.fallo ? 'No se pudo leer la búsqueda' : 'Listo · sin avisos nuevos', true);
    cerrarMenuBusquedas();
    pintarLista();
  },

  aviso(d) { toast(d.texto, d.tipo || 'info', 6000); },

  fatal(d) {
    if (E.veloTipo === 'cerrando') return;   // ya se está volviendo al menú
    const pre = el('pre', null, d.texto);
    velo('Ocurrió un error',
         'Apretá Esc para volver al menú y probá de nuevo. El detalle quedó guardado en app/errores.log.', pre, 'fatal');
  },
};

window.app = {evento: (tipo, datos) => {
  if (eventosCuenta[tipo]) { eventosCuenta[tipo](datos || {}); return; }
  if (!E.activo) return;                            // eventos que llegan después de volver al menú
  const h = handlers[tipo];
  if (h) h(datos || {});
}};

// ================================================================== teclado
document.addEventListener('keydown', ev => {
  if (ev.altKey) return;
  let usado = false;
  const k = ev.key;
  const kl = k.length === 1 ? k.toLowerCase() : k;

  if (k === 'Escape' && lateralAbierta() && E.modo !== 'velo') { cerrarLaterales(); ev.preventDefault(); return; }
  if (k === 'Escape' && $('#busq-menu').classList.contains('ver')) { cerrarMenuBusquedas(); ev.preventDefault(); return; }
  if (k === 'Escape' && $('#cuenta-menu').classList.contains('ver')) { cerrarMenuCuenta(); ev.preventDefault(); return; }
  if (E.modo === 'inicio') {
    // las flechas saltean las bolsas que todavía no se pueden usar
    const mover = paso => { let i = platSel; do { i = (i + paso + PLATAFORMAS.length) % PLATAFORMAS.length; } while (!PLATAFORMAS[i].activa); platSel = i; pintarInicio(); };
    if (k === 'ArrowRight' || k === 'ArrowDown') { mover(1); usado = true; }
    if (k === 'ArrowLeft' || k === 'ArrowUp') { mover(-1); usado = true; }
    if (k === 'Enter') { elegirPlataforma(); usado = true; }
    if (kl === 'b' && !ev.ctrlKey) { editarBusqueda(); usado = true; }
    if (kl === 'a' && !ev.ctrlKey) { abrirAjustes(); usado = true; }
  } else if (E.modo === 'ajustes') {
    if (k === 'Escape') { cerrarAjustes(); usado = true; }
    if (kl === 'e' && !ev.ctrlKey) { exportarDatos(); usado = true; }
    if (kl === 'i' && !ev.ctrlKey) { importarDatos(); usado = true; }
  } else if (E.modo === 'velo') {
    if (E.veloTipo === 'confirmar') {
      if (k === 'Enter') { volverAlMenu(true); usado = true; }
      if (k === 'Escape') { cerrarVelo(); usado = true; }
    } else if (E.veloTipo === 'busqueda') {
      if (k === 'Escape') { cerrarVelo(); usado = true; }
    } else if (E.veloTipo === 'descartados') {
      if (k === 'Escape') { cerrarVelo(); usado = true; }
    } else if (E.veloTipo === 'borrar') {
      if (k === 'Escape') { cerrarVelo(); usado = true; }
      if (kl === 'e' && ev.ctrlKey) { exportarDatos(); usado = true; }
    } else if (k === 'Escape' && ['login', 'fatal'].includes(E.veloTipo)) {
      volverAlMenu(true);
      usado = true;
    }
  } else if (E.modo === 'lista') {
    if (ev.ctrlKey && kl !== 'z') return;
    // dejar la tecla apretada no puede postular ni descartar en cadena
    if (ev.repeat && ['s', 'n', 'a', 'Enter', 'Delete'].includes(kl)) { ev.preventDefault(); return; }
    const i = idxSel();
    if (k === 'Escape') {
      if (lateralAbierta()) cerrarLaterales();
      else volverAlMenu();
      usado = true;
    }
    else if (k === 'ArrowDown' || kl === 'j') { seleccionar(i + 1); usado = true; }
    else if (k === 'ArrowUp' || kl === 'k') { seleccionar(i - 1); usado = true; }
    else if (k === 'PageDown') { seleccionar(i + 10); usado = true; }
    else if (k === 'PageUp') { seleccionar(i - 10); usado = true; }
    else if (k === 'Home') { seleccionar(0); usado = true; }
    else if (k === 'End') { seleccionar(visibles().length - 1); usado = true; }
    else if (k === 'ArrowLeft') { cambiarTab('libres'); usado = true; }
    else if (k === 'ArrowRight') { cambiarTab('preg'); usado = true; }
    else if (kl === 'a') { alternarAuto(); usado = true; }
    else if (kl === 's' || k === 'Enter') { postular(); usado = true; }
    else if (kl === 'n' || k === 'Delete') { descartar(); usado = true; }
    else if (kl === 'z') { deshacer(); usado = true; }
    else if (kl === 'o') { const it = actual(); if (it) api().abrir_url(it.url); usado = true; }
    else if (kl === 'l') { alternarLateral('registro'); usado = true; }
    else if (kl === 'p') { alternarPausa(); usado = true; }
  } else if (E.modo === 'cargando') {
    if (k === 'Escape') { cerrarForm(); usado = true; }
  } else if (E.modo === 'form') {
    usado = teclaForm(ev);
  }
  if (usado) ev.preventDefault();
});

pintarInicio();
prepararDatos();
document.querySelectorAll('.registro .lateral-volver').forEach(b => { b.onclick = cerrarLaterales; });
document.getElementById('version').textContent = 'v' + VERSION;
// window.pywebview.api aparece un instante después de cargar la página.
const alListo = () => { cargarDatos(); cargarBusquedas(); };
if (api()) alListo(); else window.addEventListener('pywebviewready', alListo);
