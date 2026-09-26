from datetime import datetime
from io import BytesIO
from flask import Flask, render_template, redirect, url_for, request, flash, send_file, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

app = Flask(__name__)
app.config["SECRET_KEY"] = "cimafrut-clave-secreta"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///cimafrut.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# -----------------------------
# MODELOS EXISTENTES
# -----------------------------

class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class Productor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    dni = db.Column(db.String(30), unique=True, nullable=False)
    telefono = db.Column(db.String(50))
    email = db.Column(db.String(100))
    localidad = db.Column(db.String(100))
    activo = db.Column(db.Boolean, default=True, nullable=False)

    vales = db.relationship("Vale", back_populates="productor")
    liquidaciones = db.relationship("Liquidacion", back_populates="productor")
    ingresos = db.relationship("IngresoFruta", back_populates="productor")


class Precio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fruta = db.Column(db.String(100), nullable=False)
    variedad = db.Column(db.String(100), nullable=False)
    calidad = db.Column(db.String(50), nullable=False)
    precio_kg = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Liquidacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    productor_id = db.Column(db.Integer, db.ForeignKey("productor.id"), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    subtotal = db.Column(db.Float, default=0, nullable=False)
    bonificacion = db.Column(db.Float, default=0, nullable=False)
    descuento = db.Column(db.Float, default=0, nullable=False)
    adelanto = db.Column(db.Float, default=0, nullable=False)
    total = db.Column(db.Float, default=0, nullable=False)
    estado = db.Column(db.String(50), default="Pendiente", nullable=False)

    productor = db.relationship("Productor", back_populates="liquidaciones")
    vales = db.relationship("Vale", back_populates="liquidacion")


class Vale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), unique=True, nullable=False)
    productor_id = db.Column(db.Integer, db.ForeignKey("productor.id"), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    fruta = db.Column(db.String(100), nullable=False)
    variedad = db.Column(db.String(100), nullable=False)
    kilos = db.Column(db.Float, nullable=False)
    calidad = db.Column(db.String(50), nullable=False)
    precio_kg = db.Column(db.Float, nullable=False)
    importe = db.Column(db.Float, nullable=False)
    estado = db.Column(db.String(50), default="Pendiente", nullable=False)
    liquidacion_id = db.Column(db.Integer, db.ForeignKey("liquidacion.id"))

    productor = db.relationship("Productor", back_populates="vales")
    liquidacion = db.relationship("Liquidacion", back_populates="vales")


# -----------------------------
# NUEVA PARTE UNIFICADA
# -----------------------------

class IngresoFruta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    productor_id = db.Column(db.Integer, db.ForeignKey("productor.id"), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    fruta = db.Column(db.String(100), nullable=False)
    variedad = db.Column(db.String(100), default="", nullable=False)
    kilos_brutos = db.Column(db.Float, default=0, nullable=False)
    tara = db.Column(db.Float, default=0, nullable=False)
    kilos_netos = db.Column(db.Float, default=0, nullable=False)
    jaulas = db.Column(db.Integer, default=0)
    bins = db.Column(db.Integer, default=0)
    pallets = db.Column(db.Integer, default=0)
    observaciones = db.Column(db.Text, default="")
    calidad = db.Column(db.String(50), default="")
    puntuacion = db.Column(db.Integer, default=0)
    estado = db.Column(db.String(50), default="Pendiente de calidad", nullable=False)

    productor = db.relationship("Productor", back_populates="ingresos")


@login_manager.user_loader
def cargar_usuario(user_id):
    return db.session.get(Usuario, int(user_id))


@app.template_filter("moneda")
def moneda(v):
    return f"${float(v or 0):,.2f}"


@app.template_filter("kg")
def kg(v):
    return f"{float(v or 0):,.2f} kg"


# -----------------------------
# DATOS DE CALIDAD
# -----------------------------

PRODUCTOS = [
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
    "Tomate deshidratado en polvo",
]

CRITERIOS_DESHIDRATADOS = [
    "Color", "Aspecto", "Humedad", "Uniformidad",
    "Apelmazamiento", "Partículas extrañas"
]

CRITERIOS_MITADES = [
    "Tamaño", "Color", "Aspecto", "Uniformidad",
    "Roturas o deformaciones", "Golpes", "Picaduras", "Daños por granizo"
]

CRITERIOS_CON_CAROZO = [
    "Tamaño", "Color", "Aspecto", "Estado del carozo",
    "Golpes", "Picaduras", "Daños por granizo"
]

CRITERIOS_SIN_CAROZO = [
    "Tamaño", "Color", "Aspecto", "Ausencia de carozo",
    "Golpes", "Picaduras", "Daños por granizo"
]

CRITERIOS_GENERALES = ["Tamaño", "Color", "Aspecto", "Estado"]

OPCIONES = ["Excelente", "Buena", "Regular", "Rechazo"]
PUNTOS = {
    "Excelente": 100,
    "Buena": 85,
    "Regular": 65,
    "Rechazo": 30,
    "Extra": 100,
    "Grande": 90,
    "Mediano": 70,
    "Pequeño": 45,
}


def obtener_criterios(producto):
    nombre = (producto or "").lower()

    if "deshidratado" in nombre:
        return CRITERIOS_DESHIDRATADOS
    if "mitades" in nombre:
        return CRITERIOS_MITADES
    if "con carozo" in nombre:
        return CRITERIOS_CON_CAROZO
    if "sin carozo" in nombre:
        return CRITERIOS_SIN_CAROZO
    return CRITERIOS_GENERALES


def calcular_calidad(respuestas):
    valores = [PUNTOS.get(valor, 0) for valor in respuestas.values() if valor]
    if not valores:
        return 0
    return round(sum(valores) / len(valores))


def etiqueta_calidad(puntuacion):
    if puntuacion >= 90:
        return "Excelente"
    if puntuacion >= 75:
        return "Buena"
    if puntuacion >= 50:
        return "Regular"
    return "Rechazo"


# -----------------------------
# AUTENTICACIÓN
# -----------------------------

@app.route("/", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "")
        admin = Usuario.query.filter_by(usuario=usuario).first()

        if admin and check_password_hash(admin.password, password):
            login_user(admin)
            return redirect(url_for("dashboard"))

        flash("Usuario o contraseña incorrectos.", "error")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# -----------------------------
# PANEL PRINCIPAL
# -----------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    total_pendiente = (
        db.session.query(db.func.sum(Liquidacion.total))
        .filter_by(estado="Pendiente")
        .scalar() or 0
    )

    total_kilos = db.session.query(db.func.sum(Vale.kilos)).scalar() or 0

    return render_template(
        "dashboard.html",
        productores=Productor.query.filter_by(activo=True).count(),
        vales=Vale.query.count(),
        liquidaciones=Liquidacion.query.count(),
        total_pendiente=total_pendiente,
        total_kilos=total_kilos,
    )


# -----------------------------
# INGRESO DE FRUTA
# -----------------------------

@app.route("/ingreso-fruta", methods=["GET", "POST"])
@login_required
def ingreso_fruta():
    productores = Productor.query.filter_by(activo=True).order_by(
        Productor.apellido, Productor.nombre
    ).all()

    if request.method == "POST":
        try:
            productor_id = int(request.form["productor_id"])
            kilos_brutos = float(request.form.get("kilos_brutos", "0").replace(",", ".") or 0)
            tara = float(request.form.get("tara", "0").replace(",", ".") or 0)
            jaulas = int(request.form.get("jaulas", "0") or 0)
            bins = int(request.form.get("bins", "0") or 0)
            pallets = int(request.form.get("pallets", "0") or 0)
        except (ValueError, TypeError):
            flash("Revisá los datos numéricos ingresados.", "error")
            return redirect(url_for("ingreso_fruta"))

        kilos_netos = kilos_brutos - tara

        if kilos_netos <= 0:
            flash("Los kilos netos deben ser mayores que cero.", "error")
            return redirect(url_for("ingreso_fruta"))

        productor = db.session.get(Productor, productor_id)
        if not productor:
            flash("Productor no encontrado.", "error")
            return redirect(url_for("ingreso_fruta"))

        ingreso = IngresoFruta(
            productor_id=productor_id,
            fruta=request.form.get("fruta", "").strip(),
            variedad=request.form.get("variedad", "").strip(),
            kilos_brutos=kilos_brutos,
            tara=tara,
            kilos_netos=kilos_netos,
            jaulas=jaulas,
            bins=bins,
            pallets=pallets,
            observaciones=request.form.get("observaciones", "").strip(),
        )

        if not ingreso.fruta:
            flash("Seleccioná el tipo de fruta.", "error")
            return redirect(url_for("ingreso_fruta"))

        db.session.add(ingreso)
        db.session.commit()

        session["ingreso_actual_id"] = ingreso.id
        return redirect(url_for("control_calidad", ingreso_id=ingreso.id))

    return render_template(
        "ingreso_fruta.html",
        productores=productores,
        productos=PRODUCTOS,
    )


@app.route("/api/productor/<int:productor_id>")
@login_required
def api_productor(productor_id):
    productor = db.session.get(Productor, productor_id)
    if not productor:
        return jsonify({})
    return jsonify({
        "nombre": f"{productor.apellido}, {productor.nombre}",
        "dni": productor.dni,
        "telefono": productor.telefono or "",
        "email": productor.email or "",
        "localidad": productor.localidad or "",
    })


# -----------------------------
# CONTROL DE CALIDAD
# -----------------------------

@app.route("/control-calidad/<int:ingreso_id>", methods=["GET", "POST"])
@login_required
def control_calidad(ingreso_id):
    ingreso = db.session.get(IngresoFruta, ingreso_id)

    if not ingreso:
        flash("Ingreso no encontrado.", "error")
        return redirect(url_for("ingreso_fruta"))

    criterios = obtener_criterios(ingreso.fruta)

    if request.method == "POST":
        respuestas = {
            criterio: request.form.get(f"criterio_{i}", "")
            for i, criterio in enumerate(criterios)
        }

        if any(not valor for valor in respuestas.values()):
            flash("Completá todos los criterios de calidad.", "error")
            return redirect(url_for("control_calidad", ingreso_id=ingreso.id))

        puntuacion = calcular_calidad(respuestas)
        calidad = etiqueta_calidad(puntuacion)

        ingreso.puntuacion = puntuacion
        ingreso.calidad = calidad
        ingreso.estado = "Calificado"
        db.session.commit()

        # El precio se busca por fruta, variedad y calidad.
        precio = (
            Precio.query
            .filter_by(
                fruta=ingreso.fruta,
                variedad=ingreso.variedad,
                calidad=calidad
            )
            .order_by(Precio.fecha.desc())
            .first()
        )

        # Compatibilidad con precios antiguos del proyecto original.
        if not precio:
            calidad_legacy = {
                "Excelente": "Bueno",
                "Buena": "Bueno",
                "Regular": "Aceptable",
                "Rechazo": "Malo",
            }.get(calidad)

            if calidad_legacy:
                precio = (
                    Precio.query
                    .filter_by(
                        fruta=ingreso.fruta,
                        variedad=ingreso.variedad,
                        calidad=calidad_legacy
                    )
                    .order_by(Precio.fecha.desc())
                    .first()
                )

        precio_kg = precio.precio_kg if precio else 0
        importe = ingreso.kilos_netos * precio_kg
        numero = "V-" + datetime.now().strftime("%Y%m%d%H%M%S%f")

        vale = Vale(
            numero=numero,
            productor_id=ingreso.productor_id,
            fecha=ingreso.fecha,
            fruta=ingreso.fruta,
            variedad=ingreso.variedad,
            kilos=ingreso.kilos_netos,
            calidad=calidad,
            precio_kg=precio_kg,
            importe=importe,
        )

        db.session.add(vale)
        db.session.commit()

        return render_template(
            "resultado_calidad.html",
            ingreso=ingreso,
            respuestas=respuestas,
            vale=vale,
            precio_configurado=bool(precio),
        )

    return render_template(
        "control_calidad.html",
        ingreso=ingreso,
        criterios=criterios,
        opciones=OPCIONES,
    )


# -----------------------------
# PRODUCTORES
# -----------------------------

@app.route("/productores")
@login_required
def productores():
    return render_template(
        "productores.html",
        productores=Productor.query.order_by(Productor.apellido, Productor.nombre).all()
    )


@app.route("/productores/nuevo", methods=["GET", "POST"])
@login_required
def nuevo_productor():
    if request.method == "POST":
        dni = request.form["dni"].strip()

        if Productor.query.filter_by(dni=dni).first():
            flash("Ya existe un productor con ese DNI.", "error")
            return redirect(url_for("nuevo_productor"))

        db.session.add(Productor(
            nombre=request.form["nombre"].strip(),
            apellido=request.form["apellido"].strip(),
            dni=dni,
            telefono=request.form.get("telefono", "").strip(),
            email=request.form.get("email", "").strip(),
            localidad=request.form.get("localidad", "").strip()
        ))
        db.session.commit()

        flash("Productor creado correctamente.", "success")
        return redirect(url_for("productores"))

    return render_template("productor_form.html", productor=None)


@app.route("/productores/<int:id>")
@login_required
def detalle_productor(id):
    productor = db.session.get(Productor, id)
    if not productor:
        flash("Productor no encontrado.", "error")
        return redirect(url_for("productores"))

    return render_template(
        "productor_detalle.html",
        productor=productor,
        vales=Vale.query.filter_by(productor_id=id).order_by(Vale.fecha.desc()).all(),
        liquidaciones=Liquidacion.query.filter_by(productor_id=id).order_by(Liquidacion.fecha.desc()).all()
    )


@app.route("/productores/<int:id>/editar", methods=["GET", "POST"])
@login_required
def editar_productor(id):
    productor = db.session.get(Productor, id)
    if not productor:
        flash("Productor no encontrado.", "error")
        return redirect(url_for("productores"))

    if request.method == "POST":
        dni = request.form["dni"].strip()

        if Productor.query.filter(
            Productor.dni == dni, Productor.id != id
        ).first():
            flash("Ese DNI ya pertenece a otro productor.", "error")
            return redirect(url_for("editar_productor", id=id))

        productor.nombre = request.form["nombre"].strip()
        productor.apellido = request.form["apellido"].strip()
        productor.dni = dni
        productor.telefono = request.form.get("telefono", "").strip()
        productor.email = request.form.get("email", "").strip()
        productor.localidad = request.form.get("localidad", "").strip()

        db.session.commit()
        flash("Productor actualizado correctamente.", "success")
        return redirect(url_for("detalle_productor", id=id))

    return render_template("productor_form.html", productor=productor)


@app.route("/productores/<int:id>/estado")
@login_required
def cambiar_estado_productor(id):
    productor = db.session.get(Productor, id)
    if productor:
        productor.activo = not productor.activo
        db.session.commit()
        flash("Estado actualizado.", "success")
    return redirect(url_for("productores"))


# -----------------------------
# PRECIOS
# -----------------------------

@app.route("/precios")
@login_required
def precios():
    return render_template(
        "precios.html",
        precios=Precio.query.order_by(
            Precio.fruta, Precio.variedad, Precio.calidad
        ).all()
    )


@app.route("/precios/nuevo", methods=["GET", "POST"])
@login_required
def nuevo_precio():
    if request.method == "POST":
        try:
            valor = float(request.form["precio_kg"].replace(",", "."))
        except ValueError:
            flash("Precio inválido.", "error")
            return redirect(url_for("nuevo_precio"))

        db.session.add(Precio(
            fruta=request.form["fruta"].strip(),
            variedad=request.form["variedad"].strip(),
            calidad=request.form["calidad"].strip(),
            precio_kg=valor
        ))
        db.session.commit()
        flash("Precio registrado correctamente.", "success")
        return redirect(url_for("precios"))

    return render_template("precio_form.html", precio=None)


@app.route("/precios/<int:id>/editar", methods=["GET", "POST"])
@login_required
def editar_precio(id):
    precio = db.session.get(Precio, id)
    if not precio:
        flash("Precio no encontrado.", "error")
        return redirect(url_for("precios"))

    if request.method == "POST":
        try:
            precio.precio_kg = float(request.form["precio_kg"].replace(",", "."))
        except ValueError:
            flash("Precio inválido.", "error")
            return redirect(url_for("editar_precio", id=id))

        precio.fruta = request.form["fruta"].strip()
        precio.variedad = request.form["variedad"].strip()
        precio.calidad = request.form["calidad"].strip()
        precio.fecha = datetime.utcnow()

        db.session.commit()
        flash("Precio actualizado correctamente.", "success")
        return redirect(url_for("precios"))

    return render_template("precio_form.html", precio=precio)


@app.route("/precios/<int:id>/eliminar")
@login_required
def eliminar_precio(id):
    precio = db.session.get(Precio, id)
    if precio:
        db.session.delete(precio)
        db.session.commit()
        flash("Precio eliminado.", "success")
    return redirect(url_for("precios"))


# -----------------------------
# VALES
# -----------------------------

@app.route("/vales")
@login_required
def vales():
    return render_template(
        "vales.html",
        vales=Vale.query.order_by(Vale.fecha.desc(), Vale.id.desc()).all()
    )


@app.route("/vales/nuevo", methods=["GET", "POST"])
@login_required
def nuevo_vale():
    productores = Productor.query.filter_by(activo=True).order_by(Productor.apellido).all()
    precios = Precio.query.order_by(Precio.fruta, Precio.variedad, Precio.calidad).all()

    if request.method == "POST":
        try:
            productor_id = int(request.form["productor_id"])
            kilos = float(request.form["kilos"].replace(",", "."))
        except (ValueError, KeyError):
            flash("Datos del vale inválidos.", "error")
            return redirect(url_for("nuevo_vale"))

        precio = (
            Precio.query
            .filter_by(
                fruta=request.form["fruta"],
                variedad=request.form["variedad"],
                calidad=request.form["calidad"]
            )
            .order_by(Precio.fecha.desc())
            .first()
        )

        if kilos <= 0 or not precio:
            flash("Revisá los kilos y que exista un precio configurado.", "error")
            return redirect(url_for("nuevo_vale"))

        numero = "V-" + datetime.now().strftime("%Y%m%d%H%M%S%f")

        db.session.add(Vale(
            numero=numero,
            productor_id=productor_id,
            fruta=request.form["fruta"],
            variedad=request.form["variedad"],
            kilos=kilos,
            calidad=request.form["calidad"],
            precio_kg=precio.precio_kg,
            importe=kilos * precio.precio_kg
        ))

        db.session.commit()
        flash("Vale creado correctamente.", "success")
        return redirect(url_for("vales"))

    return render_template(
        "vale_form.html",
        productores=productores,
        precios=precios
    )


@app.route("/vales/<int:id>/anular")
@login_required
def anular_vale(id):
    vale = db.session.get(Vale, id)
    if vale and vale.estado == "Pendiente":
        vale.estado = "Anulado"
        db.session.commit()
        flash("Vale anulado.", "success")
    return redirect(url_for("vales"))


# -----------------------------
# LIQUIDACIONES
# -----------------------------

@app.route("/liquidaciones")
@login_required
def liquidaciones():
    return render_template(
        "liquidaciones.html",
        liquidaciones=Liquidacion.query.order_by(Liquidacion.fecha.desc()).all(),
        productores=Productor.query.filter_by(activo=True).order_by(Productor.apellido).all()
    )


@app.route("/liquidaciones/nueva/<int:productor_id>", methods=["GET", "POST"])
@login_required
def nueva_liquidacion(productor_id):
    productor = db.session.get(Productor, productor_id)

    if not productor:
        flash("Productor no encontrado.", "error")
        return redirect(url_for("liquidaciones"))

    vales = Vale.query.filter_by(
        productor_id=productor_id,
        estado="Pendiente"
    ).order_by(Vale.fecha).all()

    if not vales:
        flash("El productor no tiene vales pendientes.", "error")
        return redirect(url_for("detalle_productor", id=productor_id))

    subtotal = sum(v.importe for v in vales)

    if request.method == "POST":
        try:
            bonificacion = float(request.form.get("bonificacion", "0").replace(",", ".") or 0)
            descuento = float(request.form.get("descuento", "0").replace(",", ".") or 0)
            adelanto = float(request.form.get("adelanto", "0").replace(",", ".") or 0)
        except ValueError:
            flash("Importes inválidos.", "error")
            return redirect(url_for("nueva_liquidacion", productor_id=productor_id))

        total = subtotal + bonificacion - descuento - adelanto

        if min(bonificacion, descuento, adelanto) < 0 or total < 0:
            flash("Los importes no son válidos.", "error")
            return redirect(url_for("nueva_liquidacion", productor_id=productor_id))

        liquidacion = Liquidacion(
            productor_id=productor_id,
            subtotal=subtotal,
            bonificacion=bonificacion,
            descuento=descuento,
            adelanto=adelanto,
            total=total
        )

        db.session.add(liquidacion)
        db.session.flush()

        for vale in vales:
            vale.estado = "Liquidado"
            vale.liquidacion_id = liquidacion.id

        db.session.commit()
        flash("Liquidación generada correctamente.", "success")
        return redirect(url_for("detalle_liquidacion", id=liquidacion.id))

    return render_template(
        "liquidacion_nueva.html",
        productor=productor,
        vales=vales,
        subtotal=subtotal
    )


@app.route("/liquidaciones/<int:id>")
@login_required
def detalle_liquidacion(id):
    liquidacion = db.session.get(Liquidacion, id)
    if not liquidacion:
        flash("Liquidación no encontrada.", "error")
        return redirect(url_for("liquidaciones"))
    return render_template("liquidacion.html", liquidacion=liquidacion)


@app.route("/liquidaciones/<int:id>/pagar")
@login_required
def pagar_liquidacion(id):
    liquidacion = db.session.get(Liquidacion, id)
    if liquidacion:
        liquidacion.estado = "Pagada"
        db.session.commit()
        flash("Pago registrado correctamente.", "success")
    return redirect(url_for("liquidaciones"))


@app.route("/liquidaciones/<int:id>/pdf")
@login_required
def pdf_liquidacion(id):
    liquidacion = db.session.get(Liquidacion, id)
    if not liquidacion:
        return redirect(url_for("liquidaciones"))

    buf = BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    pdf.setFillColor(colors.HexColor("#171c63"))
    pdf.rect(0, height - 70, width, 70, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(45, height - 45, "CIMAFRUT")

    y = height - 100
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(45, y, f"Liquidación N° {liquidacion.id}")

    y -= 20
    pdf.setFont("Helvetica", 10)
    pdf.drawString(
        45, y,
        f"Productor: {liquidacion.productor.nombre} {liquidacion.productor.apellido}"
    )
    y -= 16
    pdf.drawString(45, y, f"DNI: {liquidacion.productor.dni}")
    y -= 16
    pdf.drawString(45, y, f"Fecha: {liquidacion.fecha.strftime('%d/%m/%Y %H:%M')}")

    y -= 30
    pdf.setFont("Helvetica-Bold", 9)

    for x, title in [
        (45, "Vale"), (105, "Fruta"), (185, "Variedad"),
        (275, "Calidad"), (380, "Kg"), (440, "$/Kg"), (510, "Importe")
    ]:
        pdf.drawString(x, y, title)

    y -= 15
    pdf.setFont("Helvetica", 8)

    for vale in liquidacion.vales:
        pdf.drawString(45, y, vale.numero[-10:])
        pdf.drawString(105, y, vale.fruta[:12])
        pdf.drawString(185, y, vale.variedad[:13])
        pdf.drawString(275, y, vale.calidad[:12])
        pdf.drawRightString(405, y, f"{vale.kilos:.2f}")
        pdf.drawRightString(480, y, f"${vale.precio_kg:.2f}")
        pdf.drawRightString(555, y, f"${vale.importe:.2f}")
        y -= 15

        if y < 100:
            pdf.showPage()
            y = height - 60

    y -= 10
    pdf.setFont("Helvetica-Bold", 10)

    for label, value in [
        ("Subtotal", liquidacion.subtotal),
        ("Bonificación", liquidacion.bonificacion),
        ("Descuento", liquidacion.descuento),
        ("Adelanto", liquidacion.adelanto),
        ("TOTAL", liquidacion.total),
    ]:
        pdf.drawRightString(480, y, label + ":")
        pdf.drawRightString(555, y, f"${value:.2f}")
        y -= 18

    pdf.save()
    buf.seek(0)

    return send_file(
        buf,
        as_attachment=False,
        download_name=f"liquidacion_{id}.pdf",
        mimetype="application/pdf"
    )


# -----------------------------
# INFORMES
# -----------------------------

@app.route("/informes")
@login_required
def informes():
    vales = Vale.query.filter(Vale.estado != "Anulado").all()

    total_kilos = sum(v.kilos for v in vales)
    total_liquidado = sum(
        l.total for l in Liquidacion.query.filter_by(estado="Pagada").all()
    )
    productores_activos = Productor.query.filter_by(activo=True).count()

    por_fruta = {}
    for vale in vales:
        por_fruta[vale.fruta] = por_fruta.get(vale.fruta, 0) + vale.kilos

    total_fruta = sum(por_fruta.values()) or 1
    frutas = sorted(
        [
            {
                "nombre": nombre,
                "kilos": kilos,
                "porcentaje": round((kilos / total_fruta) * 100, 1),
            }
            for nombre, kilos in por_fruta.items()
        ],
        key=lambda x: x["kilos"],
        reverse=True
    )

    return render_template(
        "informes.html",
        total_kilos=total_kilos,
        total_liquidado=total_liquidado,
        productores_activos=productores_activos,
        frutas=frutas,
    )


# -----------------------------
# INICIALIZACIÓN
# -----------------------------

with app.app_context():
    db.create_all()

    if not Usuario.query.filter_by(usuario="admin").first():
        db.session.add(
            Usuario(
                usuario="admin",
                password=generate_password_hash("admin123")
            )
        )
        db.session.commit()


if __name__ == "__main__":
    app.run(debug=True)
