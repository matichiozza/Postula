"""
Estimación del sueldo neto (en mano) a partir del bruto mensual, empleado en relación de
dependencia en Argentina. Supone: soltero, sin hijos, sin otras deducciones de Ganancias
(alquiler, prepaga, etc.) y sin cuota sindical.

Cálculo:
  1. Aportes del empleado: 11% jubilación + 3% PAMI (ley 19.032) + 3% obra social = 17%,
     sobre el bruto con tope (base imponible máxima del SIPA).
  2. Impuesto a las Ganancias (4ta categoría): se anualiza (13 sueldos: 12 + aguinaldo),
     se restan los aportes, la ganancia no imponible y la deducción especial, se aplica la
     escala del art. 94 y el impuesto se reparte en los 13 sueldos.

VALORES A ACTUALIZAR (cambian seguido):
  - TOPE_APORTES: ANSES lo actualiza todos los meses (Res. ANSES 304/2026: noviembre 2026).
  - Deducciones y escala: valores anuales 2026 de ARCA (se actualizan cada semestre).
    Ojo: la prensa suele calcular el piso de Ganancias con 12 sueldos (~$3,5 M bruto);
    acá se usan 13 porque el aguinaldo también paga, así que el piso da algo más bajo (~$3,24 M).
"""

VIGENCIA = "noviembre 2026"

TOPE_APORTES = 4_861_685.38          # base imponible máxima SIPA, nov-2026
APORTES = {"Jubilación": 0.11, "PAMI": 0.03, "Obra social": 0.03}

GANANCIA_NO_IMPONIBLE = 6_019_671.36   # art. 30 inc. a, anual 2026
DEDUCCION_ESPECIAL = 28_894_422.56     # art. 30 inc. c ap. 2 (relación de dependencia), anual 2026

# Escala art. 94, anual 2026: (desde, monto fijo, alícuota)
ESCALA = [
    (0.00, 0.00, 0.05),
    (2_336_953.69, 116_847.68, 0.09),
    (4_673_907.36, 327_173.52, 0.12),
    (7_010_861.05, 607_607.96, 0.15),
    (10_516_291.59, 1_133_422.54, 0.19),
    (21_032_583.18, 3_131_517.94, 0.23),
    (31_548_874.77, 5_550_265.01, 0.27),
    (47_323_312.16, 9_809_363.10, 0.31),
    (70_984_968.25, 17_144_476.49, 0.35),
]
SUELDOS_POR_ANIO = 13   # 12 + aguinaldo (el SAC también paga Ganancias)


def impuesto_escala(base):
    if base <= 0:
        return 0.0
    for desde, fijo, tasa in reversed(ESCALA):
        if base > desde:
            return fijo + (base - desde) * tasa
    return 0.0


def calcular(bruto):
    """-> {"bruto", "aportes": {nombre: monto}, "ganancias", "neto", "vigencia"} (montos mensuales)."""
    bruto = max(0.0, float(bruto or 0))
    base_aportes = min(bruto, TOPE_APORTES)
    aportes = {k: round(base_aportes * t, 2) for k, t in APORTES.items()}
    total_aportes = sum(aportes.values())

    neta_anual = (bruto - total_aportes) * SUELDOS_POR_ANIO
    sujeta = neta_anual - GANANCIA_NO_IMPONIBLE - DEDUCCION_ESPECIAL
    ganancias = round(impuesto_escala(sujeta) / SUELDOS_POR_ANIO, 2)

    return {
        "bruto": round(bruto, 2),
        "aportes": aportes,
        "con_tope": bruto > TOPE_APORTES,
        "ganancias": ganancias,
        "neto": round(bruto - total_aportes - ganancias, 2),
        "vigencia": VIGENCIA,
    }
