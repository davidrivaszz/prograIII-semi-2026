const $ = id => document.getElementById(id);

async function enviar(datos) {
    const respuesta = await fetch("/crud", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(datos)
    });
    if (respuesta.status === 401) {
        window.location.href = "/";
        return { ok: false };
    }
    return await respuesta.json();
}

function mostrar(texto, ok) {
    $("msg").style.color = ok ? "#2e7d32" : "#c62828";
    $("msg").textContent = texto;
}

function limpiar() {
    ["idUsuario", "usuario", "clave", "nombre", "direccion", "telefono"].forEach(i => $(i).value = "");
    $("btnGuardar").textContent = "Guardar";
}

// Recoge los datos del formulario y los envía a Python
async function guardar() {
    const datos = {
        accion: $("idUsuario").value === "" ? "nuevo" : "modificar",
        idUsuario: $("idUsuario").value,
        usuario: $("usuario").value.trim(),
        clave: $("clave").value,
        nombre: $("nombre").value.trim(),
        direccion: $("direccion").value.trim(),
        telefono: $("telefono").value.trim()
    };

    if (!datos.usuario || !datos.clave || !datos.nombre || !datos.direccion || !datos.telefono) {
        mostrar("Complete todos los campos", false);
        return;
    }

    const r = await enviar(datos);
    mostrar(r.msg, r.ok);
    if (r.ok) {
        limpiar();
        buscar();
    }
}

async function buscar() {
    const r = await enviar({ accion: "buscar", texto: $("txtBuscar").value.trim() });
    const tbody = $("tbody");
    tbody.innerHTML = "";
    if (!r.ok) return;

    r.datos.forEach(u => {
        const tr = document.createElement("tr");
        [u.idUsuario, u.usuario, u.nombre, u.direccion, u.telefono].forEach(valor => {
            const td = document.createElement("td");
            td.textContent = valor;
            tr.appendChild(td);
        });

        const tdAcciones = document.createElement("td");

        const btnEditar = document.createElement("button");
        btnEditar.textContent = "Editar";
        btnEditar.className = "naranja";
        btnEditar.onclick = () => editar(u);

        const btnEliminar = document.createElement("button");
        btnEliminar.textContent = "Eliminar";
        btnEliminar.className = "rojo";
        btnEliminar.onclick = () => eliminar(u);

        tdAcciones.appendChild(btnEditar);
        tdAcciones.appendChild(btnEliminar);
        tr.appendChild(tdAcciones);
        tbody.appendChild(tr);
    });
}

function editar(u) {
    $("idUsuario").value = u.idUsuario;
    $("usuario").value = u.usuario;
    $("clave").value = u.clave;
    $("nombre").value = u.nombre;
    $("direccion").value = u.direccion;
    $("telefono").value = u.telefono;
    $("btnGuardar").textContent = "Actualizar";
    window.scrollTo(0, 0);
}

async function eliminar(u) {
    if (!confirm("¿Eliminar al usuario " + u.usuario + "?")) return;
    const r = await enviar({ accion: "eliminar", idUsuario: u.idUsuario });
    mostrar(r.msg, r.ok);
    if (r.ok) buscar();
}

$("btnGuardar").addEventListener("click", guardar);
$("btnLimpiar").addEventListener("click", limpiar);
$("btnBuscar").addEventListener("click", buscar);
$("txtBuscar").addEventListener("keydown", e => {
    if (e.key === "Enter") buscar();
});

buscar();