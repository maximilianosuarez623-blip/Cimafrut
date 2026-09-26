function mostrarCriterios() {

    const producto = document.getElementById("producto").value;
    const contenedor = document.getElementById("criterios");

    contenedor.innerHTML = "";

    if (producto === "") {
        contenedor.innerHTML =
            '<p class="mensaje">Seleccione un producto para comenzar la evaluación.</p>';
        return;
    }

    let criterios = [];

    if (producto.toLowerCase().includes("deshidratado")) {

        criterios = [
            "Color",
            "Aspecto",
            "Humedad",
            "Uniformidad",
            "Apelmazamiento",
            "Partículas extrañas"
        ];

    } else if (producto.toLowerCase().includes("mitades")) {

        criterios = [
            "Tamaño",
            "Color",
            "Aspecto",
            "Uniformidad",
            "Roturas o deformaciones",
            "Golpes",
            "Picaduras",
            "Daños por granizo"
        ];

    } else if (producto.toLowerCase().includes("con carozo")) {

        criterios = [
            "Tamaño",
            "Color",
            "Aspecto",
            "Estado del carozo",
            "Golpes",
            "Picaduras",
            "Daños por granizo"
        ];

    } else {

        criterios = [
            "Tamaño",
            "Color",
            "Aspecto",
            "Ausencia de carozo",
            "Golpes",
            "Picaduras",
            "Daños por granizo"
        ];
    }

    criterios.forEach(function(criterio) {

        const div = document.createElement("div");

        div.classList.add("criterio");

        div.innerHTML = `
            <label>${criterio}</label>

            <select name="${criterio}" required>
                <option value="">Seleccione</option>
                <option value="Bueno">Bueno</option>
                <option value="Aceptable">Aceptable</option>
                <option value="Malo">Malo</option>
            </select>
        `;

        contenedor.appendChild(div);
    });
}
