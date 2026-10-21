document.getElementById("btnLogin").addEventListener("click", login);
document.getElementById("clave").addEventListener("keydown", function (e) {
    if (e.key === "Enter") login();
});

async function login() {
    const datos = {
        usuario: document.getElementById("usuario").value.trim(),
        clave: document.getElementById("clave").value
    };
    const msg = document.getElementById("msg");

    if (datos.usuario === "" || datos.clave === "") {
        msg.textContent = "Ingrese usuario y clave";
        return;
    }

    const respuesta = await fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(datos)
    });
    const r = await respuesta.json();

    if (r.ok) {
        window.location.href = "/usuarios.html";
    } else {
        msg.textContent = r.msg;
    }
}