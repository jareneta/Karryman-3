"""Karryman · selección del régimen de evaluación (docs/V24_REGIMEN_2015.md).
Variable de entorno V24_REGIMEN: 'legacy' (periodos A 2010-2020 y B 1997-2009 con 2021-2026 bloqueado) o '2015' (2015-01-01 a 2026-10-31 en dos tramos)."""
import os

ACTIVE = os.environ.get('V24_REGIMEN', 'legacy').strip() or 'legacy'
if ACTIVE not in ('legacy', '2015'):
    raise ValueError(f'V24_REGIMEN no válido: {ACTIVE}')

END_2015 = '2026-10-31'
S1 = ('2015-01-01', '2020-12-31')
S2 = ('2021-01-01', END_2015)
FULL_2015 = ('2015-01-01', END_2015)


def period_list(legacy, k):
    """Lista de periodos (nombre, inicio de carga, fin de carga, tramos, nivel de confianza) según el régimen."""
    if ACTIVE == '2015':
        return [('N_2015_2026', '2013-06-01', END_2015, [('S1_2015_2020', S1), ('S2_2021_2026', S2)], 1 - 0.05 / k)]
    return list(legacy)
