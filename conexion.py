import mysql.connector
from mysql.connector import Error


class Conexion:
    def __init__(self):
        self.host = "localhost"
        self.user = "root"
        self.password = ""
        self.database = "db_sistema_impuestos"
        self.conexion = None
        print("Conectando a la base de datos...")

        try:
            # autocommit=True: cada consulta ve siempre los datos más recientes.
            # Las transacciones se controlan a mano en ejecutar_transaccion().
            self.conexion = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                autocommit=True
            )
            if self.conexion.is_connected():
                print("Conexion exitosa")
            else:
                print("No se pudo conectar a la base de datos")
        except Error as e:
            print(f"Error al conectar a la base de datos: {e}")

    def _asegurar_conexion(self):
        """Reconecta si MySQL cerró la conexión por inactividad."""
        self.conexion.ping(reconnect=True, attempts=3, delay=1)

    def consultar(self, sql, params=None):
        try:
            self._asegurar_conexion()
            cursor = self.conexion.cursor(dictionary=True)
            cursor.execute(sql, params)
            filas = cursor.fetchall()
            cursor.close()
            return filas
        except Error as e:
            print(f"Error al consultar la base de datos: {e}")
            return None

    def ejecutar(self, sql, datos):
        try:
            self._asegurar_conexion()
            cursor = self.conexion.cursor()
            cursor.execute(sql, datos)
            self.conexion.commit()
            cursor.close()
            return 'ok'
        except Error as e:
            print(f"Error al ejecutar la consulta: {e}")
            return f'Error: {e}'

    def ejecutar_transaccion(self, operaciones):
        """Ejecuta varias sentencias [(sql, datos), ...] como una sola unidad.
        Si una falla, se deshace todo (sección 17 de la guía)."""
        try:
            self._asegurar_conexion()
            self.conexion.start_transaction()
            cursor = self.conexion.cursor()
            for sql, datos in operaciones:
                cursor.execute(sql, datos)
            self.conexion.commit()
            cursor.close()
            return 'ok'
        except Error as e:
            print(f"Error en la transaccion: {e}")
            try:
                self.conexion.rollback()
            except Error:
                pass
            return f'Error: {e}'