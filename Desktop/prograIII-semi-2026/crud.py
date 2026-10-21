import mysql.connector


class Crud:
    def conectar(self):
        return mysql.connector.connect(
            host="127.0.0.1",
            user="root",
            password="",
            database="db_academica"
        )

    # Procesa los datos enviados por el cliente y los guarda en la tabla
    def crud_usuarios_usss002025(self, datos):
        accion = datos.get("accion")
        con = self.conectar()
        cur = con.cursor(dictionary=True)
        try:
            if accion == "nuevo":
                cur.execute(
                    "INSERT INTO usuarios_usss002025 (usuario, clave, nombre, direccion, telefono) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (datos["usuario"], datos["clave"], datos["nombre"],
                     datos["direccion"], datos["telefono"])
                )
                con.commit()
                return {"ok": True, "msg": "Usuario registrado"}

            if accion == "modificar":
                cur.execute(
                    "UPDATE usuarios_usss002025 SET usuario=%s, clave=%s, nombre=%s, "
                    "direccion=%s, telefono=%s WHERE idUsuario=%s",
                    (datos["usuario"], datos["clave"], datos["nombre"],
                     datos["direccion"], datos["telefono"], datos["idUsuario"])
                )
                con.commit()
                return {"ok": True, "msg": "Usuario modificado"}

            if accion == "eliminar":
                cur.execute("DELETE FROM usuarios_usss002025 WHERE idUsuario=%s",
                            (datos["idUsuario"],))
                con.commit()
                return {"ok": True, "msg": "Usuario eliminado"}

            if accion == "buscar":
                texto = "%" + datos.get("texto", "") + "%"
                cur.execute(
                    "SELECT * FROM usuarios_usss002025 "
                    "WHERE usuario LIKE %s OR nombre LIKE %s OR direccion LIKE %s OR telefono LIKE %s "
                    "ORDER BY idUsuario",
                    (texto, texto, texto, texto)
                )
                return {"ok": True, "datos": cur.fetchall()}

            return {"ok": False, "msg": "Acción no válida"}
        except Exception as e:
            return {"ok": False, "msg": "Error: " + str(e)}
        finally:
            cur.close()
            con.close()

    # Revisa en la base de datos si el usuario y la clave existen
    def validar_login(self, usuario, clave):
        con = self.conectar()
        cur = con.cursor()
        try:
            cur.execute(
                "SELECT idUsuario FROM usuarios_usss002025 WHERE usuario=%s AND clave=%s",
                (usuario, clave)
            )
            return cur.fetchone() is not None
        finally:
            cur.close()
            con.close()