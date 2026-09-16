<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Python como backend</title>

    <link rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css">
</head>

<body>

    <div class="container-fluid">

        Hola: <span id="divRespuesta"></span>

        <form id="frmSaludo" class="mt-3">

            <div class="row">
                <div class="col-6">

                    <input
                        placeholder="Email"
                        name="txtEmailCliente"
                        id="txtEmailCliente"
                        class="form-control"
                        type="text">

                </div>
            </div>

            <div class="row mt-3">
                <div class="col">

                    <select
                        name="cboTipo"
                        id="cboTipo"
                        class="form-select">

                        <option value="">Seleccione</option>
                        <option value="1">Cliente</option>
                        <option value="2">Proveedor</option>
                        <option value="3">Empleado</option>

                    </select>

                </div>
            </div>

            <button class="btn btn-primary mt-3" type="submit">
                Saludar
            </button>

        </form>

    </div>

    <script>

        const frmSaludo = document.getElementById("frmSaludo");
        const txtEmailCliente = document.getElementById("txtEmailCliente");
        const divRespuesta = document.getElementById("divRespuesta");

        frmSaludo.onsubmit = function(e) {

            e.preventDefault();

            fetch(`/saludo?nombre=${txtEmailCliente.value}`)
                .then(response => response.text())
                .then(data => {

                    divRespuesta.innerHTML = data;

                });

        };

    </script>

</body>

</html>