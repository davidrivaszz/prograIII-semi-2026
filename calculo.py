"""
Cálculo del Impuesto a las Actividades Económicas.
Usa Decimal (nunca float) como exige la sección 11 de la guía.
Este módulo NO toca la base de datos: solo recibe datos y devuelve resultados.
"""
from datetime import timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

FORMULA_ACTUAL = "v2_bloques"         # CEIL por bloques de mil (sección 10.1)
FORMULA_HISTORICA = "v1_proporcional"  # fórmula anterior (sección 12)

MSG_SIN_TARIFA = "No existe una tarifa configurada para el balance indicado."
MSG_TARIFAS_DUPLICADAS = "Existe más de una tarifa aplicable. Corrija la tabla tarifaria."

MIL = Decimal("1000")
CENTAVO = Decimal("0.01")
SEIS_DECIMALES = Decimal("0.000001")


def dec(valor):
    """Convierte a Decimal pasando por texto (evita errores de float)."""
    return valor if isinstance(valor, Decimal) else Decimal(str(valor))


def redondear2(valor):
    return dec(valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def redondear6(valor):
    return dec(valor).quantize(SEIS_DECIMALES, rounding=ROUND_HALF_UP)


def seleccionar_tarifa(tarifas, balance, fecha):
    """RF 10 a RF 12: busca UNA tarifa con TarifaDesde <= balance <= TarifaHasta
    que esté vigente en 'fecha'. Devuelve (tarifa, mensaje_de_error)."""
    balance = dec(balance)
    candidatas = []
    for t in tarifas:
        if not (dec(t["desde"]) <= balance <= dec(t["hasta"])):
            continue
        if t["vigente_desde"] > fecha:
            continue
        if t.get("vigente_hasta") is not None and fecha >= t["vigente_hasta"]:
            continue
        candidatas.append(t)
    if not candidatas:
        return None, MSG_SIN_TARIFA          # RF 11 y RF 13 (no usa precio general)
    if len(candidatas) > 1:
        return None, MSG_TARIFAS_DUPLICADAS  # RF 12
    return candidatas[0], None


def calcular_impuesto(balance, tarifa, formula=FORMULA_ACTUAL):
    """Devuelve un diccionario con todo el detalle del cálculo (RF 18)."""
    balance = dec(balance)
    desde = dec(tarifa["desde"])
    base = dec(tarifa["precio_base"])
    adicional = dec(tarifa["adicional"])
    porcentaje = dec(tarifa["porcentaje"])

    excedente = Decimal("0")
    bloques = Decimal("0")

    if porcentaje > 0:
        # Sección 10.4: Balance x Porcentaje / 100 (el porcentaje NO se trunca)
        precio = balance * porcentaje / 100
        expresion = f"{balance} x {porcentaje.normalize():f} / 100 = {redondear2(precio)}"
    elif formula == FORMULA_HISTORICA:
        # Sección 12: 1.50 + ((700.00 - 500.00) / 1,000 x 3.00)
        inicio = desde - CENTAVO
        excedente = balance - inicio
        precio = base + (excedente / MIL * adicional)
        expresion = (f"{base} + (({balance} - {inicio}) / 1,000 x {adicional}) "
                     f"= {redondear2(precio)}")
    else:
        # Sección 10.1: Excedente, Bloques = CEIL(Excedente / 1000)
        excedente = balance - desde
        bloques = (excedente / MIL).to_integral_value(rounding=ROUND_CEILING)
        precio = base + (bloques * adicional)
        expresion = f"{base} + ({bloques} x {adicional}) = {redondear2(precio)}"

    return {
        "balance": balance,
        "rango_desde": desde,
        "rango_hasta": dec(tarifa["hasta"]),
        "precio_base": base,
        "excedente": excedente,
        "bloques": bloques,
        "adicional": adicional,
        "porcentaje": porcentaje,
        "precio": redondear6(precio),           # interno, 6 decimales
        "precio_mostrado": redondear2(precio),  # mostrado/cobrado, 2 decimales
        "formula": formula,
        "version_tarifa": tarifa.get("version", 1),
        "idTarifa": tarifa.get("idTarifa"),
        "expresion": expresion,
    }


def calcular_subtotal(cantidad, precio):
    """Subtotal = Cantidad x Precio, redondeado a 2 decimales al final."""
    return redondear2(dec(cantidad) * dec(precio))


def meses_aplicables(inicio, fin):
    """Cantidad de meses calendario que toca el intervalo [inicio, fin).
    Ejemplo: [2025-01-01, 2026-01-01) -> 12."""
    if inicio >= fin:
        return 0
    ultimo_dia = fin - timedelta(days=1)
    return (ultimo_dia.year - inicio.year) * 12 + (ultimo_dia.month - inicio.month) + 1