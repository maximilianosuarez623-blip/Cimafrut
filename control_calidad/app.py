from flask import Flask, render_template, request

app = Flask(__name__)

productos = [
    "Ciruelas sin carozo",
    "Ciruelas con carozo",
    "Ciruelas Presidente sin carozo",
    "Ciruela deshidratada en polvo",
    "Durazno en mitades",
    "Duraznos pelones con carozo",
    "Durazno descarozado en medallones",
    "Durazno deshidratado granulado",
    "Damascos enteros sin carozo",
    "Damasco deshidratado granulado",
    "Peras en mitades",
    "Pera deshidratada granulada",
    "Tomates en mitades",
    "Tomate deshidratado en polvo"
]

criterios_deshidratados = [
    "Color",
    "Aspecto",
    "Humedad",
    "Uniformidad",
    "Apelmazamiento",
    "Partículas extrañas"
]

criterios_mitades = [
    "Tamaño",
    "Color",
    "Aspecto",
    "Uniformidad",
    "Roturas o deformaciones",
    "Golpes",
    "Picaduras",
    "Daños por granizo"
]

criterios_con_carozo = [
    "Tamaño",
    "Color",
    "Aspecto",
    "Estado del carozo",
    "Golpes",
    "Picaduras",
    "Daños por granizo"
]

criterios_sin_carozo = [
    "Tamaño",
    "Color",
    "Aspecto",
    "Ausencia de carozo",
    "Golpes",
    "Picaduras",
    "Daños por granizo"
]

criterios_generales = [
    "Tamaño",
    "Color",
    "Aspecto",
    "Estado"
]


def obtener_criterios(producto):

    if "deshidratado" in producto.lower():
        return criterios_deshidratados

    if "mitades" in producto.lower():
        return criterios_mitades

    if "con carozo" in producto.lower():
        return criterios_con_carozo

    if "sin carozo" in producto.lower():
        return criterios_sin_carozo

    return criterios_generales


def calcular_calidad(respuestas):

    valores = {
        "Bueno": 100,
        "Aceptable": 70,
        "Malo": 30
    }

    if not respuestas:
        return 0

    puntos = []

    for respuesta in respuestas.values():
        puntos.append(valores.get(respuesta, 0))

    return round(sum(puntos) / len(puntos))


@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "POST":

        producto = request.form.get("producto")

        criterios = obtener_criterios(producto)

        respuestas = {}

        for criterio in criterios:
            respuestas[criterio] = request.form.get(criterio)

        puntuacion = calcular_calidad(respuestas)

        defectos = []

        for criterio, respuesta in respuestas.items():
            if respuesta == "Malo":
                defectos.append(criterio)

        if puntuacion >= 80:
            resultado = "CALIDAD BUENA"

        elif puntuacion >= 60:
            resultado = "CALIDAD A REVISAR"

        else:
            resultado = "CALIDAD NO APTA"

        return render_template(
            "resultado.html",
            producto=producto,
            puntuacion=puntuacion,
            resultado=resultado,
            defectos=defectos
        )

    return render_template(
        "index.html",
        productos=productos
    )


if __name__ == "__main__":
    app.run(debug=True)