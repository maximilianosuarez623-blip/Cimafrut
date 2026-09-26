document.addEventListener("DOMContentLoaded", () => {
    const brutos = document.getElementById("kilos_brutos");
    const tara = document.getElementById("tara");
    const netos = document.getElementById("netos");
    const total = document.getElementById("total_final");
    const fecha = document.getElementById("fecha_actual");

    function calcularNeto() {
        if (!brutos || !tara) return;
        const b = parseFloat(brutos.value) || 0;
        const t = parseFloat(tara.value) || 0;
        const n = Math.max(b - t, 0);

        if (netos) netos.value = n.toFixed(2);
        if (total) total.textContent = n.toFixed(2);
    }

    if (brutos) brutos.addEventListener("input", calcularNeto);
    if (tara) tara.addEventListener("input", calcularNeto);

    if (fecha && !fecha.value) {
        const hoy = new Date();
        hoy.setMinutes(hoy.getMinutes() - hoy.getTimezoneOffset());
        fecha.value = hoy.toISOString().slice(0, 10);
    }

    const productor = document.getElementById("productor_id");
    if (productor) {
        productor.addEventListener("change", async () => {
            if (!productor.value) return;
            try {
                const response = await fetch(`/api/productor/${productor.value}`);
                const data = await response.json();
                document.body.dataset.productor = data.nombre || "";
            } catch (error) {
                console.error("No se pudo cargar el productor.", error);
            }
        });
    }

    calcularNeto();
});
