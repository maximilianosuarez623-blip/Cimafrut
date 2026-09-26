document.addEventListener('DOMContentLoaded', function() {
    const inputBrutos = document.getElementById('kilos_brutos');
    const inputTara = document.getElementById('tara');
    const inputNetos = document.getElementById('netos');
    const inputTotalFinal = document.getElementById('total_final');

    function calcularNeto() {
        const brutos = parseFloat(inputBrutos.value) || 0;
        const tara = parseFloat(inputTara.value) || 0;
        const netos = brutos - tara;

        const resultadoFinal = netos > 0 ? netos.toFixed(2) : 0;
        inputNetos.value = resultadoFinal;
        inputTotalFinal.value = resultadoFinal;
    }

    if (inputBrutos && inputTara) {
        inputBrutos.addEventListener('input', calcularNeto);
        inputTara.addEventListener('input', calcularNeto);
    }

    const inputFecha = document.getElementById('fecha_actual');
    if (inputFecha) {
        const hoy = new Date().toISOString().split('T')[0];
        inputFecha.value = hoy;
    }
});