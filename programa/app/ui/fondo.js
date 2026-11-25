'use strict';
// Fondo animado del menú y de Ajustes: diseño A "Corrientes". Tres luces con los colores de la bolsa
// elegida (PLATAFORMAS y platSel son de app.js), que recorren la pantalla.
const VELOCIDAD_FONDO = 0.6;    // elegida por el usuario en el artefacto de diseños (de 0.3 a 2.5)

(() => {
  const lienzo = document.getElementById('fondo-lienzo');
  const g = lienzo.getContext('2d');
  const quieto = matchMedia('(prefers-reduced-motion: reduce)');
  const rgb = hex => { const n = parseInt(hex.slice(1), 16); return [n >> 16, (n >> 8) & 255, n & 255]; };
  let color = PLATAFORMAS[platSel].colores.map(rgb);   // se acerca de a poco al de la bolsa elegida
  let t = 3, antes = null;

  function luz(x, y, r, [rojo, verde, azul], a) {
    const gr = g.createRadialGradient(x, y, 0, x, y, r);
    gr.addColorStop(0, `rgba(${rojo}, ${verde}, ${azul}, ${a})`);
    gr.addColorStop(1, `rgba(${rojo}, ${verde}, ${azul}, 0)`);
    g.fillStyle = gr;
    g.fillRect(x - r, y - r, r * 2, r * 2);
  }

  function cuadro(ahora) {
    requestAnimationFrame(cuadro);
    const dt = antes === null ? 0 : Math.min(.05, (ahora - antes) / 1000);
    antes = ahora;
    // en la pantalla de trabajo el fondo está tapado: no se dibuja
    if (document.getElementById('trabajo').classList.contains('activa')) return;
    if (!quieto.matches) t += dt * VELOCIDAD_FONDO;
    const paso = Math.min(1, dt * 3);                  // transición de color de ~1 s al cambiar de bolsa
    const meta = PLATAFORMAS[platSel].colores.map(rgb);
    color = color.map((c, i) => c.map((v, k) => v + (meta[i][k] - v) * paso));
    // son manchas suaves: alcanza con dibujar a media resolución
    const w = Math.max(1, Math.round(lienzo.clientWidth / 2)), h = Math.max(1, Math.round(lienzo.clientHeight / 2));
    if (lienzo.width !== w || lienzo.height !== h) { lienzo.width = w; lienzo.height = h; }
    g.clearRect(0, 0, w, h);
    const m = Math.max(w, h);
    const [c1, c2, c3] = color.map(c => c.map(Math.round));
    luz(w * (.22 + .24 * Math.sin(t * .45)), h * (.2 + .22 * Math.cos(t * .37)), m * .48, c1, .62);
    luz(w * (.78 + .2 * Math.cos(t * .4)), h * (.78 + .22 * Math.sin(t * .52)), m * .42, c2, .44);
    luz(w * (.5 + .38 * Math.sin(t * .3 + 2)), h * (.55 + .32 * Math.sin(t * .6)), m * .34, c3, .55);
  }
  requestAnimationFrame(cuadro);
})();
