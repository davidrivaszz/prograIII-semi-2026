import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import calculo
import conexion

db = conexion.Conexion()

# Mensajes exactos de la sección 16 de la guía
MSG_NO_EMPRESA = "El Impuesto a las Actividades Económicas requiere un cliente de tipo empresa."
MSG_BALANCE = "Ingrese un balance mayor que cero."
MSG_FECHAS = "La fecha Hasta debe ser posterior a la fecha Desde."
MSG_SUPERPUESTO = "El período indicado se superpone con un período existente."
MSG_PRODUCTO = "Confirme si la actividad corresponde a comercio o industria."
MSG_FACTURADO = "El período ya fue utilizado en recibos y no puede recalcularse automáticamente."


class crud_periodos:
    # ------------------------------------------------------------ utilidades
    def _fecha(self, texto):
        try:
            return datetime.strptime(str(texto), "%Y-%m-%d").date()
        except ValueError:
            return None

    def _decimal(self, valor):
        try:
            d = Decimal(str(valor).strip())
            return d if d.is_finite() else None
        except (InvalidOperation, ValueError):
            return None

    def _error(self, msg):
        return {'ok': False, 'msg': msg}

    # -------------------------------------------------------------- consultas
    def productos(self):
        return db.consultar("SELECT idProducto, codigo, nombre FROM productos ORDER BY codigo") or []

    def consultar(self, idCliente):
        filas = db.consultar("""
            SELECT p.idPeriodo, p.desde, p.hasta, p.monto, pr.codigo, p.cantidad,
                   p.precio, p.subtotal, p.formula_version, p.facturado,
                   CASE WHEN CURDATE() >= p.desde AND CURDATE() < p.hasta THEN 'Vigente según fecha'
                        WHEN p.hasta <= CURDATE() THEN 'Histórico'
                        ELSE 'Futuro' END AS estado
            FROM periodos p
            INNER JOIN productos pr ON pr.idProducto = p.idProducto
            WHERE p.idCliente = %s
            ORDER BY pr.codigo, p.desde
        """, (idCliente,)) or []
        # RF 21: el total referencial NO es la mensualidad
        total_referencial = sum((Decimal(str(f['precio'])) for f in filas), Decimal('0'))
        mensual_vigente = sum((Decimal(str(f['subtotal'])) for f in filas
                               if f['estado'] == 'Vigente según fecha'), Decimal('0'))
        return {
            'periodos': filas,
            'mensual_vigente': calculo.redondear2(mensual_vigente),
            'total_referencial': calculo.redondear2(total_referencial),
        }

    # ------------------------------------------------ validación + cálculo
    def _preparar(self, datos, requiere_fechas):
        """Valida todo y calcula. Devuelve {'ok': False, 'msg': ...} o un dict con los datos listos."""
        # Cliente empresa
        try:
            idCliente = int(datos.get('idCliente'))
        except (TypeError, ValueError):
            return self._error("Seleccione un cliente registrado.")
        cli = db.consultar("SELECT idCliente, nombre, tipo FROM clientes WHERE idCliente=%s", (idCliente,))
        if not cli:
            return self._error("Seleccione un cliente registrado.")
        if cli[0]['tipo'] != 'empresa':
            return self._error(MSG_NO_EMPRESA)

        # Producto (comercio o industria)
        prod = None
        if str(datos.get('idProducto', '')).strip() != '':
            r = db.consultar("SELECT idProducto, codigo, nombre FROM productos WHERE idProducto=%s",
                             (datos.get('idProducto'),))
            prod = r[0] if r else None
        if not prod:
            return self._error(MSG_PRODUCTO)

        # Balance > 0
        monto = self._decimal(datos.get('monto', ''))
        if monto is None or monto <= 0:
            return self._error(MSG_BALANCE)

        # Cantidad (normalmente 1.00)
        cantidad = self._decimal(datos.get('cantidad', '1')) if str(datos.get('cantidad', '')).strip() != '' else Decimal('1')
        if cantidad is None or cantidad <= 0:
            return self._error("La cantidad debe ser mayor que cero.")

        # Fechas: RF 02 y RF 03
        desde = self._fecha(datos.get('desde', ''))
        hasta = self._fecha(datos.get('hasta', ''))
        if requiere_fechas and (desde is None or hasta is None):
            return self._error("Ingrese las fechas Desde y Hasta del período.")
        if desde and hasta and desde >= hasta:
            return self._error(MSG_FECHAS)

        # Fórmula: la anterior solo se permite en períodos históricos ya terminados
        formula = calculo.FORMULA_ACTUAL
        if datos.get('formula') == calculo.FORMULA_HISTORICA:
            if hasta is None or hasta > date.today():
                return self._error("La fórmula proporcional anterior solo se permite para períodos históricos ya finalizados.")
            formula = calculo.FORMULA_HISTORICA

        # Tarifa vigente a la fecha Desde (RF 10 a RF 13, RF 20)
        fecha_ref = desde or date.today()
        tarifas = db.consultar("SELECT * FROM tarifas WHERE idProducto=%s", (prod['idProducto'],)) or []
        tarifa, err = calculo.seleccionar_tarifa(tarifas, monto, fecha_ref)
        if err:
            return self._error(err)

        calc = calculo.calcular_impuesto(monto, tarifa, formula)
        calc['cantidad'] = cantidad
        calc['subtotal'] = calculo.calcular_subtotal(cantidad, calc['precio'])
        return {'ok': True, 'idCliente': idCliente, 'producto': prod, 'desde': desde,
                'hasta': hasta, 'monto': monto, 'cantidad': cantidad, 'calc': calc}

    def calcular(self, datos):
        """Vista previa inmediata (RF 17 a RF 20). No guarda nada."""
        p = self._preparar(datos, requiere_fechas=False)
        if not p['ok']:
            return p
        return {'ok': True, 'msg': 'ok', 'detalle': p['calc']}

    # ----------------------------------------------------------- guardado
    def guardar(self, datos):
        p = self._preparar(datos, requiere_fechas=True)
        if not p['ok']:
            return p
        idCli, prod = p['idCliente'], p['producto']
        desde, hasta, calc = p['desde'], p['hasta'], p['calc']
        usuario = str(datos.get('usuario', 'admin'))[:50]

        # RF 04: los períodos de la misma empresa y producto no pueden superponerse
        # [desde, hasta) se superpone si: existente.desde < nuevo.hasta Y existente.hasta > nuevo.desde
        solapados = db.consultar("""
            SELECT idPeriodo, desde, hasta, facturado FROM periodos
            WHERE idCliente=%s AND idProducto=%s AND desde < %s AND hasta > %s
        """, (idCli, prod['idProducto'], hasta, desde))
        if solapados is None:
            return self._error("No se pudo verificar la superposición de períodos.")

        operaciones = []
        cierra = False
        if solapados:
            cerrar = bool(datos.get('cerrar_vigente'))
            # RF 07: si cambia el balance se CIERRA el período vigente (no se sobrescribe)
            if not (cerrar and len(solapados) == 1 and solapados[0]['desde'] < desde):
                return self._error(MSG_SUPERPUESTO +
                                   f" (existente: {solapados[0]['desde']} a {solapados[0]['hasta']})")
            if solapados[0]['facturado']:
                return self._error(MSG_FACTURADO)
            viejo = solapados[0]
            operaciones.append(("UPDATE periodos SET hasta=%s WHERE idPeriodo=%s", (desde, viejo['idPeriodo'])))
            operaciones.append((
                "INSERT INTO bitacora(idPeriodo,accion,usuario,detalle) VALUES(%s,'CIERRE',%s,%s)",
                (viejo['idPeriodo'], usuario,
                 f"Período cerrado: hasta pasó de {viejo['hasta']} a {desde} por nuevo período")))
            cierra = True

        # RF 06: advertir si queda un espacio sin cobertura
        aviso = []
        if not cierra:
            ant = db.consultar("""SELECT MAX(hasta) AS h FROM periodos
                                  WHERE idCliente=%s AND idProducto=%s AND hasta <= %s""",
                               (idCli, prod['idProducto'], desde))
            if ant and ant[0]['h'] and ant[0]['h'] < desde:
                aviso.append(f"Advertencia: hay un espacio sin cobertura entre {ant[0]['h']} y {desde}.")
        sig = db.consultar("""SELECT MIN(desde) AS d FROM periodos
                              WHERE idCliente=%s AND idProducto=%s AND desde >= %s""",
                           (idCli, prod['idProducto'], hasta))
        if sig and sig[0]['d'] and sig[0]['d'] > hasta:
            aviso.append(f"Advertencia: hay un espacio sin cobertura entre {hasta} y {sig[0]['d']}.")

        # Se guarda el resultado + la "foto" de la tarifa (RF 14, RF 15)
        operaciones.append(("""
            INSERT INTO periodos(idCliente,idProducto,desde,hasta,monto,cantidad,precio,subtotal,
                                 idTarifa,tarifa_detalle,formula_version,fecha_calculo,facturado,creado_por)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),0,%s)
        """, (idCli, prod['idProducto'], desde, hasta, str(p['monto']), str(p['cantidad']),
              str(calc['precio']), str(calc['subtotal']), calc['idTarifa'],
              json.dumps(calc, default=str), calc['formula'], usuario)))
        operaciones.append((
            "INSERT INTO bitacora(idPeriodo,accion,usuario,detalle) VALUES(LAST_INSERT_ID(),'CREACION',%s,%s)",
            (usuario, f"Producto {prod['codigo']}, balance {p['monto']}, precio {calc['precio_mostrado']}, "
                      f"formula {calc['formula']}, tarifa v{calc['version_tarifa']}")))

        # Todo junto en una transacción (sección 17)
        resultado = db.ejecutar_transaccion(operaciones)
        if resultado != 'ok':
            return self._error(resultado)
        return {'ok': True, 'msg': 'ok', 'aviso': " ".join(aviso), 'detalle': calc}

    # ------------------------------------------------------------- cobro
    def cobro(self, idCliente, idProducto, desde_txt, hasta_txt):
        """Sección 15: Cargo = Cantidad x Precio mensual x Meses aplicables,
        usando solo los períodos que se superponen con el rango de cobro."""
        desde, hasta = self._fecha(desde_txt), self._fecha(hasta_txt)
        if desde is None or hasta is None:
            return self._error("Ingrese las fechas Desde y Hasta del cobro.")
        if desde >= hasta:
            return self._error(MSG_FECHAS)
        filas = db.consultar("""
            SELECT idPeriodo, desde, hasta, cantidad, precio, monto FROM periodos
            WHERE idCliente=%s AND idProducto=%s AND desde < %s AND hasta > %s
            ORDER BY desde
        """, (idCliente, idProducto, hasta, desde)) or []
        detalle, total = [], Decimal('0')
        for f in filas:
            ini, fin = max(desde, f['desde']), min(hasta, f['hasta'])
            meses = calculo.meses_aplicables(ini, fin)
            cargo = calculo.redondear2(Decimal(str(f['cantidad'])) * Decimal(str(f['precio'])) * meses)
            total += cargo
            detalle.append({'desde': ini, 'hasta': fin, 'balance': f['monto'], 'cantidad': f['cantidad'],
                            'precio_mensual': calculo.redondear2(f['precio']), 'meses': meses, 'cargo': cargo})
        if not detalle:
            return self._error("No hay períodos registrados que cubran el rango de cobro.")
        return {'ok': True, 'msg': 'ok', 'detalle': detalle, 'total': calculo.redondear2(total)}
        