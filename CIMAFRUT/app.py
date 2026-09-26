
from flask import Flask, render_template, redirect, url_for, request, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4 # type: ignore
from reportlab.pdfgen import canvas # type: ignore
from reportlab.lib import colors # type: ignore

app = Flask(__name__)
app.config["SECRET_KEY"] = "cimafrut-clave-secreta"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///cimafrut.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

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

@login_manager.user_loader
def cargar_usuario(user_id):
    return db.session.get(Usuario, int(user_id))

@app.template_filter("moneda")
def moneda(v):
    return f"${float(v or 0):,.2f}"

@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form.get("usuario","").strip()
        p = request.form.get("password","")
        admin = Usuario.query.filter_by(usuario=u).first()
        if admin and check_password_hash(admin.password,p):
            login_user(admin)
            return redirect(url_for("dashboard"))
        flash("Usuario o contraseña incorrectos","error")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html",
        productores=Productor.query.filter_by(activo=True).count(),
        vales=Vale.query.count(),
        liquidaciones=Liquidacion.query.count(),
        total_pendiente=db.session.query(db.func.sum(Liquidacion.total)).filter_by(estado="Pendiente").scalar() or 0)

@app.route("/productores")
@login_required
def productores():
    return render_template("productores.html", productores=Productor.query.order_by(Productor.apellido,Productor.nombre).all())

@app.route("/productores/nuevo", methods=["GET","POST"])
@login_required
def nuevo_productor():
    if request.method=="POST":
        dni=request.form["dni"].strip()
        if Productor.query.filter_by(dni=dni).first():
            flash("Ya existe un productor con ese DNI.","error")
            return redirect(url_for("nuevo_productor"))
        db.session.add(Productor(
            nombre=request.form["nombre"].strip(), apellido=request.form["apellido"].strip(),
            dni=dni, telefono=request.form.get("telefono","").strip(),
            email=request.form.get("email","").strip(), localidad=request.form.get("localidad","").strip()))
        db.session.commit()
        flash("Productor creado correctamente.","success")
        return redirect(url_for("productores"))
    return render_template("productor_form.html", productor=None)

@app.route("/productores/<int:id>")
@login_required
def detalle_productor(id):
    p=db.session.get(Productor,id)
    if not p:
        flash("Productor no encontrado.","error"); return redirect(url_for("productores"))
    return render_template("productor_detalle.html", productor=p,
        vales=Vale.query.filter_by(productor_id=id).order_by(Vale.fecha.desc()).all(),
        liquidaciones=Liquidacion.query.filter_by(productor_id=id).order_by(Liquidacion.fecha.desc()).all())

@app.route("/productores/<int:id>/editar", methods=["GET","POST"])
@login_required
def editar_productor(id):
    p=db.session.get(Productor,id)
    if not p:
        flash("Productor no encontrado.","error"); return redirect(url_for("productores"))
    if request.method=="POST":
        dni=request.form["dni"].strip()
        if Productor.query.filter(Productor.dni==dni,Productor.id!=id).first():
            flash("Ese DNI ya pertenece a otro productor.","error")
            return redirect(url_for("editar_productor",id=id))
        p.nombre=request.form["nombre"].strip(); p.apellido=request.form["apellido"].strip(); p.dni=dni
        p.telefono=request.form.get("telefono","").strip(); p.email=request.form.get("email","").strip()
        p.localidad=request.form.get("localidad","").strip()
        db.session.commit(); flash("Productor actualizado correctamente.","success")
        return redirect(url_for("detalle_productor",id=id))
    return render_template("productor_form.html", productor=p)

@app.route("/productores/<int:id>/estado")
@login_required
def cambiar_estado_productor(id):
    p=db.session.get(Productor,id)
    if p: p.activo=not p.activo; db.session.commit(); flash("Estado actualizado.","success")
    return redirect(url_for("productores"))

@app.route("/precios")
@login_required
def precios():
    return render_template("precios.html", precios=Precio.query.order_by(Precio.fruta,Precio.variedad,Precio.calidad).all())

@app.route("/precios/nuevo", methods=["GET","POST"])
@login_required
def nuevo_precio():
    if request.method=="POST":
        try: valor=float(request.form["precio_kg"].replace(",","."))
        except ValueError:
            flash("Precio inválido.","error"); return redirect(url_for("nuevo_precio"))
        db.session.add(Precio(fruta=request.form["fruta"].strip(),variedad=request.form["variedad"].strip(),
            calidad=request.form["calidad"].strip(),precio_kg=valor))
        db.session.commit(); flash("Precio registrado correctamente.","success")
        return redirect(url_for("precios"))
    return render_template("precio_form.html",precio=None)

@app.route("/precios/<int:id>/editar", methods=["GET","POST"])
@login_required
def editar_precio(id):
    p=db.session.get(Precio,id)
    if not p: flash("Precio no encontrado.","error"); return redirect(url_for("precios"))
    if request.method=="POST":
        try: p.precio_kg=float(request.form["precio_kg"].replace(",","."))
        except ValueError:
            flash("Precio inválido.","error"); return redirect(url_for("editar_precio",id=id))
        p.fruta=request.form["fruta"].strip(); p.variedad=request.form["variedad"].strip(); p.calidad=request.form["calidad"].strip(); p.fecha=datetime.utcnow()
        db.session.commit(); flash("Precio actualizado correctamente.","success"); return redirect(url_for("precios"))
    return render_template("precio_form.html",precio=p)

@app.route("/precios/<int:id>/eliminar")
@login_required
def eliminar_precio(id):
    p=db.session.get(Precio,id)
    if p: db.session.delete(p); db.session.commit(); flash("Precio eliminado.","success")
    return redirect(url_for("precios"))

@app.route("/vales")
@login_required
def vales():
    return render_template("vales.html",vales=Vale.query.order_by(Vale.fecha.desc(),Vale.id.desc()).all())

@app.route("/vales/nuevo", methods=["GET","POST"])
@login_required
def nuevo_vale():
    productores=Productor.query.filter_by(activo=True).order_by(Productor.apellido).all()
    precios=Precio.query.order_by(Precio.fruta,Precio.variedad,Precio.calidad).all()
    if request.method=="POST":
        try: productor_id=int(request.form["productor_id"]); kilos=float(request.form["kilos"].replace(",","."))
        except (ValueError,KeyError):
            flash("Datos del vale inválidos.","error"); return redirect(url_for("nuevo_vale"))
        p=Precio.query.filter_by(fruta=request.form["fruta"],variedad=request.form["variedad"],calidad=request.form["calidad"]).order_by(Precio.fecha.desc()).first()
        if kilos<=0 or not p:
            flash("Revisá los kilos y que exista un precio configurado para esa fruta, variedad y calidad.","error")
            return redirect(url_for("nuevo_vale"))
        numero="V-"+datetime.now().strftime("%Y%m%d%H%M%S%f")
        db.session.add(Vale(numero=numero,productor_id=productor_id,fruta=request.form["fruta"],
            variedad=request.form["variedad"],kilos=kilos,calidad=request.form["calidad"],
            precio_kg=p.precio_kg,importe=kilos*p.precio_kg))
        db.session.commit(); flash("Vale creado correctamente.","success"); return redirect(url_for("vales"))
    return render_template("vale_form.html",productores=productores,precios=precios)

@app.route("/vales/<int:id>/anular")
@login_required
def anular_vale(id):
    v=db.session.get(Vale,id)
    if v and v.estado=="Pendiente": v.estado="Anulado"; db.session.commit(); flash("Vale anulado.","success")
    return redirect(url_for("vales"))

@app.route("/liquidaciones")
@login_required
def liquidaciones():
    return render_template("liquidaciones.html",
        liquidaciones=Liquidacion.query.order_by(Liquidacion.fecha.desc()).all(),
        productores=Productor.query.filter_by(activo=True).order_by(Productor.apellido).all())

@app.route("/liquidaciones/nueva/<int:productor_id>",methods=["GET","POST"])
@login_required
def nueva_liquidacion(productor_id):
    p=db.session.get(Productor,productor_id)
    if not p: flash("Productor no encontrado.","error"); return redirect(url_for("liquidaciones"))
    vales=Vale.query.filter_by(productor_id=productor_id,estado="Pendiente").order_by(Vale.fecha).all()
    if not vales:
        flash("El productor no tiene vales pendientes.","error"); return redirect(url_for("detalle_productor",id=productor_id))
    subtotal=sum(v.importe for v in vales)
    if request.method=="POST":
        try:
            b=float(request.form.get("bonificacion","0").replace(",",".") or 0)
            d=float(request.form.get("descuento","0").replace(",",".") or 0)
            a=float(request.form.get("adelanto","0").replace(",",".") or 0)
        except ValueError:
            flash("Importes inválidos.","error"); return redirect(url_for("nueva_liquidacion",productor_id=productor_id))
        total=subtotal+b-d-a
        if min(b,d,a)<0 or total<0:
            flash("Los importes no son válidos.","error"); return redirect(url_for("nueva_liquidacion",productor_id=productor_id))
        l=Liquidacion(productor_id=productor_id,subtotal=subtotal,bonificacion=b,descuento=d,adelanto=a,total=total)
        db.session.add(l); db.session.flush()
        for v in vales: v.estado="Liquidado"; v.liquidacion_id=l.id
        db.session.commit(); flash("Liquidación generada correctamente.","success")
        return redirect(url_for("detalle_liquidacion",id=l.id))
    return render_template("liquidacion_nueva.html",productor=p,vales=vales,subtotal=subtotal)

@app.route("/liquidaciones/<int:id>")
@login_required
def detalle_liquidacion(id):
    l=db.session.get(Liquidacion,id)
    if not l: flash("Liquidación no encontrada.","error"); return redirect(url_for("liquidaciones"))
    return render_template("liquidacion.html",liquidacion=l)

@app.route("/liquidaciones/<int:id>/pagar")
@login_required
def pagar_liquidacion(id):
    l=db.session.get(Liquidacion,id)
    if l: l.estado="Pagada"; db.session.commit(); flash("Pago registrado correctamente.","success")
    return redirect(url_for("liquidaciones"))

@app.route("/liquidaciones/<int:id>/pdf")
@login_required
def pdf_liquidacion(id):
    l=db.session.get(Liquidacion,id)
    if not l: return redirect(url_for("liquidaciones"))
    buf=BytesIO(); pdf=canvas.Canvas(buf,pagesize=A4); w,h=A4
    pdf.setFillColor(colors.HexColor("#123c28")); pdf.rect(0,h-70,w,70,fill=1,stroke=0)
    pdf.setFillColor(colors.white); pdf.setFont("Helvetica-Bold",22); pdf.drawString(45,h-45,"CIMAFRUT")
    y=h-100; pdf.setFillColor(colors.black); pdf.setFont("Helvetica-Bold",12); pdf.drawString(45,y,f"Liquidación N° {l.id}")
    y-=20; pdf.setFont("Helvetica",10); pdf.drawString(45,y,f"Productor: {l.productor.nombre} {l.productor.apellido}"); y-=16
    pdf.drawString(45,y,f"DNI: {l.productor.dni}"); y-=16; pdf.drawString(45,y,f"Fecha: {l.fecha.strftime('%d/%m/%Y %H:%M')}")
    y-=30; pdf.setFont("Helvetica-Bold",9)
    for x,t in [(45,"Vale"),(105,"Fruta"),(185,"Variedad"),(275,"Calidad"),(380,"Kg"),(440,"$/Kg"),(510,"Importe")]: pdf.drawString(x,y,t)
    y-=15; pdf.setFont("Helvetica",8)
    for v in l.vales:
        pdf.drawString(45,y,v.numero[-10:]); pdf.drawString(105,y,v.fruta[:12]); pdf.drawString(185,y,v.variedad[:13]); pdf.drawString(275,y,v.calidad[:12])
        pdf.drawRightString(405,y,f"{v.kilos:.2f}"); pdf.drawRightString(480,y,f"${v.precio_kg:.2f}"); pdf.drawRightString(555,y,f"${v.importe:.2f}"); y-=15
        if y<100: pdf.showPage(); y=h-60
    y-=10; pdf.setFont("Helvetica-Bold",10)
    for label,val in [("Subtotal",l.subtotal),("Bonificación",l.bonificacion),("Descuento",l.descuento),("Adelanto",l.adelanto),("TOTAL",l.total)]:
        pdf.drawRightString(480,y,label+":"); pdf.drawRightString(555,y,f"${val:.2f}"); y-=18
    pdf.save(); buf.seek(0)
    return send_file(buf,as_attachment=False,download_name=f"liquidacion_{id}.pdf",mimetype="application/pdf")

with app.app_context():
    db.create_all()
    if not Usuario.query.filter_by(usuario="admin").first():
        db.session.add(Usuario(usuario="admin",password=generate_password_hash("admin123"))); db.session.commit()

if __name__=="__main__":
    app.run(debug=True)
