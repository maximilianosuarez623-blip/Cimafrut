from datetime import datetime
from functools import wraps
from io import BytesIO
from flask import Flask, render_template, redirect, url_for, request, flash, send_file, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

app=Flask(__name__)
app.config['SECRET_KEY']='cimafrut-clave-secreta-cambiar-en-produccion'
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///cimafrut.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
db=SQLAlchemy(app)
login_manager=LoginManager(app); login_manager.login_view='login'

# Catálogo inicial: especies y variedades usadas en Mendoza, con foco en el oasis Sur.
# La aplicación permite ampliarlas desde el backend en futuras versiones.
VARIEDADES={
    'Ciruela':['D’Agen','D’Agen 707','President','Stanley','Sugar','Santa Rosa','Linda Rosa'],
    'Durazno':['Elegant Lady','O’Henry','Bowen','Amarillo industrial'],
    'Pera':['Williams','Packham’s Triumph','Beurré D’Anjou','Red Bartlett'],
    'Damasco':['Royal','Tilton','Bandera Española','Royal Brillante'],
    'Uva':['Malbec','Bonarda','Cabernet Sauvignon','Syrah','Criolla Grande','Pedro Giménez'],
    'Tomate':['Roma','Perita','Redondo','Industria'],
}
FRUTAS=list(VARIEDADES.keys())
ROLES={
    'administrador':'Administrador',
    'general':'Usuario general',
    'bascula':'Báscula / Ingreso',
    'precios':'Precios',
    'calidad':'Control de calidad',
    'liquidaciones':'Liquidaciones',
}

class Usuario(UserMixin,db.Model):
    id=db.Column(db.Integer,primary_key=True); usuario=db.Column(db.String(100),unique=True,nullable=False)
    password=db.Column(db.String(200),nullable=False); nombre=db.Column(db.String(120),default='')
    rol=db.Column(db.String(30),default='general',nullable=False); activo=db.Column(db.Boolean,default=True,nullable=False)

class Productor(db.Model):
    id=db.Column(db.Integer,primary_key=True); nombre=db.Column(db.String(100),nullable=False); apellido=db.Column(db.String(100),nullable=False)
    dni=db.Column(db.String(30),unique=True,nullable=False); telefono=db.Column(db.String(50)); email=db.Column(db.String(100)); localidad=db.Column(db.String(100)); activo=db.Column(db.Boolean,default=True,nullable=False)
    vales=db.relationship('Vale',back_populates='productor'); liquidaciones=db.relationship('Liquidacion',back_populates='productor'); ingresos=db.relationship('IngresoFruta',back_populates='productor')

class Precio(db.Model):
    id=db.Column(db.Integer,primary_key=True); fruta=db.Column(db.String(100),nullable=False); variedad=db.Column(db.String(100),nullable=False); calidad=db.Column(db.String(50),nullable=False); precio_kg=db.Column(db.Float,nullable=False); fecha=db.Column(db.DateTime,default=datetime.utcnow,nullable=False)

class Liquidacion(db.Model):
    id=db.Column(db.Integer,primary_key=True); productor_id=db.Column(db.Integer,db.ForeignKey('productor.id'),nullable=False); fecha=db.Column(db.DateTime,default=datetime.utcnow,nullable=False)
    subtotal=db.Column(db.Float,default=0,nullable=False); bonificacion=db.Column(db.Float,default=0,nullable=False); descuento=db.Column(db.Float,default=0,nullable=False); adelanto=db.Column(db.Float,default=0,nullable=False); total=db.Column(db.Float,default=0,nullable=False); estado=db.Column(db.String(50),default='Pendiente',nullable=False)
    productor=db.relationship('Productor',back_populates='liquidaciones'); vales=db.relationship('Vale',back_populates='liquidacion')

class Vale(db.Model):
    id=db.Column(db.Integer,primary_key=True); numero=db.Column(db.String(50),unique=True,nullable=False); productor_id=db.Column(db.Integer,db.ForeignKey('productor.id'),nullable=False); fecha=db.Column(db.DateTime,default=datetime.utcnow,nullable=False)
    fruta=db.Column(db.String(100),nullable=False); variedad=db.Column(db.String(100),nullable=False); kilos=db.Column(db.Float,nullable=False); calidad=db.Column(db.String(50),nullable=False); precio_kg=db.Column(db.Float,nullable=False); importe=db.Column(db.Float,nullable=False); estado=db.Column(db.String(50),default='Pendiente',nullable=False); liquidacion_id=db.Column(db.Integer,db.ForeignKey('liquidacion.id'))
    productor=db.relationship('Productor',back_populates='vales'); liquidacion=db.relationship('Liquidacion',back_populates='vales')

class Envase(db.Model):
    id=db.Column(db.Integer,primary_key=True); nombre=db.Column(db.String(80),unique=True,nullable=False); peso_vacio=db.Column(db.Float,nullable=False); activo=db.Column(db.Boolean,default=True,nullable=False)

class IngresoFruta(db.Model):
    id=db.Column(db.Integer,primary_key=True); productor_id=db.Column(db.Integer,db.ForeignKey('productor.id'),nullable=False); fecha=db.Column(db.DateTime,default=datetime.utcnow,nullable=False)
    fruta=db.Column(db.String(100),nullable=False); variedad=db.Column(db.String(100),nullable=False); peso_bruto_camion=db.Column(db.Float,default=0,nullable=False); tara_camion=db.Column(db.Float,default=0,nullable=False); tara_envases=db.Column(db.Float,default=0,nullable=False); kilos_netos=db.Column(db.Float,default=0,nullable=False)
    observaciones=db.Column(db.Text,default=''); calidad=db.Column(db.String(50),default=''); puntuacion=db.Column(db.Integer,default=0); estado=db.Column(db.String(50),default='Pendiente de calidad',nullable=False)
    productor=db.relationship('Productor',back_populates='ingresos'); envases=db.relationship('IngresoEnvase',back_populates='ingreso',cascade='all,delete-orphan')

class IngresoEnvase(db.Model):
    id=db.Column(db.Integer,primary_key=True); ingreso_id=db.Column(db.Integer,db.ForeignKey('ingreso_fruta.id'),nullable=False); envase_id=db.Column(db.Integer,db.ForeignKey('envase.id'),nullable=False); cantidad=db.Column(db.Integer,default=0,nullable=False); peso_total=db.Column(db.Float,default=0,nullable=False)
    ingreso=db.relationship('IngresoFruta',back_populates='envases'); envase=db.relationship('Envase')

@login_manager.user_loader
def cargar_usuario(uid): return db.session.get(Usuario,int(uid))

@app.template_filter('moneda')
def moneda(v): return f'${float(v or 0):,.2f}'
@app.template_filter('kg')
def kg(v): return f'{float(v or 0):,.2f} kg'

@app.context_processor
def globals_template(): return {'ROLES':ROLES,'FRUTAS':FRUTAS,'VARIEDADES':VARIEDADES}

def roles_requeridos(*roles):
    def deco(view):
        @wraps(view)
        def wrapped(*args,**kwargs):
            if not current_user.is_authenticated: return login_manager.unauthorized()
            if not current_user.activo: logout_user(); flash('Usuario desactivado.','error'); return redirect(url_for('login'))
            if current_user.rol not in roles and current_user.rol!='administrador': abort(403)
            return view(*args,**kwargs)
        return wrapped
    return deco

@app.before_request
def bloquear_inactivos():
    if current_user.is_authenticated and not current_user.activo and request.endpoint not in ('logout','login','static'):
        logout_user(); return redirect(url_for('login'))

@app.route('/',methods=['GET','POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('dashboard'))
    if request.method=='POST':
        u=request.form.get('usuario','').strip(); p=request.form.get('password',''); user=Usuario.query.filter_by(usuario=u).first()
        if user and user.activo and check_password_hash(user.password,p): login_user(user); return redirect(url_for('dashboard'))
        flash('Usuario o contraseña incorrectos.','error')
    return render_template('login.html')
@app.route('/logout')
@login_required
def logout(): logout_user(); return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html',productores=Productor.query.filter_by(activo=True).count(),vales=Vale.query.count(),liquidaciones=Liquidacion.query.count(),total_kilos=db.session.query(db.func.sum(Vale.kilos)).scalar() or 0)

@app.route('/api/variedades/<fruta>')
@login_required
def api_variedades(fruta): return jsonify(VARIEDADES.get(fruta,[]))

# -------- INGRESO Y TARA --------
@app.route('/ingreso-fruta',methods=['GET','POST'])
@roles_requeridos('bascula','general')
def ingreso_fruta():
    productores=Productor.query.filter_by(activo=True).order_by(Productor.apellido,Productor.nombre).all(); envases=Envase.query.filter_by(activo=True).order_by(Envase.nombre).all()
    if request.method=='POST':
        try:
            productor_id=int(request.form['productor_id']); bruto=float(request.form.get('peso_bruto_camion','0').replace(',','.')); tara_camion=float(request.form.get('tara_camion','0').replace(',','.'))
        except (ValueError,KeyError): flash('Revisá los datos de la báscula.','error'); return redirect(url_for('ingreso_fruta'))
        fruta=request.form.get('fruta','').strip(); variedad=request.form.get('variedad','').strip()
        if fruta not in VARIEDADES or variedad not in VARIEDADES[fruta]: flash('Seleccioná una fruta y una variedad válidas.','error'); return redirect(url_for('ingreso_fruta'))
        productor=db.session.get(Productor,productor_id)
        if not productor or bruto<=0 or tara_camion<0: flash('Los datos de peso no son válidos.','error'); return redirect(url_for('ingreso_fruta'))
        ingreso=IngresoFruta(productor_id=productor_id,fruta=fruta,variedad=variedad,peso_bruto_camion=bruto,tara_camion=tara_camion,observaciones=request.form.get('observaciones','').strip())
        total_envases=0.0
        for env in envases:
            raw=request.form.get(f'envase_{env.id}','0') or '0'
            try: cantidad=int(raw)
            except ValueError: cantidad=0
            if cantidad<0: cantidad=0
            peso=cantidad*env.peso_vacio
            if cantidad: ingreso.envases.append(IngresoEnvase(envase=env,cantidad=cantidad,peso_total=peso))
            total_envases+=peso
        neto=bruto-tara_camion-total_envases
        if neto<=0: flash('La tara del camión y de los envases no puede superar el peso bruto.','error'); return redirect(url_for('ingreso_fruta'))
        ingreso.tara_envases=total_envases; ingreso.kilos_netos=neto; db.session.add(ingreso); db.session.commit()
        return redirect(url_for('control_calidad',ingreso_id=ingreso.id))
    return render_template('ingreso_fruta.html',productores=productores,envases=envases)

@app.route('/envases')
@roles_requeridos('bascula','general')
def envases(): return render_template('envases.html',envases=Envase.query.order_by(Envase.nombre).all())
@app.route('/envases/nuevo',methods=['GET','POST'])
@roles_requeridos('bascula','general')
def nuevo_envase():
    if request.method=='POST':
        nombre=request.form['nombre'].strip()
        try: peso=float(request.form['peso_vacio'].replace(',','.'))
        except ValueError: flash('Peso inválido.','error'); return redirect(url_for('nuevo_envase'))
        if not nombre or peso<0: flash('Completá correctamente los datos.','error'); return redirect(url_for('nuevo_envase'))
        if Envase.query.filter_by(nombre=nombre).first(): flash('Ese tipo de envase ya existe.','error'); return redirect(url_for('nuevo_envase'))
        db.session.add(Envase(nombre=nombre,peso_vacio=peso)); db.session.commit(); flash('Envase guardado.','success'); return redirect(url_for('envases'))
    return render_template('envase_form.html',envase=None)
@app.route('/envases/<int:id>/editar',methods=['GET','POST'])
@roles_requeridos('bascula','general')
def editar_envase(id):
    e=db.session.get(Envase,id)
    if not e: abort(404)
    if request.method=='POST':
        try: e.peso_vacio=float(request.form['peso_vacio'].replace(',','.'))
        except ValueError: flash('Peso inválido.','error'); return redirect(url_for('editar_envase',id=id))
        e.nombre=request.form['nombre'].strip(); e.activo='activo' in request.form; db.session.commit(); flash('Envase actualizado.','success'); return redirect(url_for('envases'))
    return render_template('envase_form.html',envase=e)

# -------- CALIDAD --------
CALIDAD=['Excelente','Buena','Regular','Rechazo']; PUNTOS={'Excelente':100,'Buena':85,'Regular':65,'Rechazo':30,'Extra':100,'Grande':90,'Mediano':70,'Pequeño':45}
def criterios_para(fruta,variedad):
    if fruta=='Uva': return ['Calibre','Color','Aspecto','Racimo','Granos dañados','Daños por granizo']
    if fruta=='Tomate': return ['Tamaño','Color','Firmeza','Aspecto','Golpes','Picaduras','Daños']
    if fruta in ('Ciruela','Damasco'): return ['Tamaño','Color','Aspecto','Estado del carozo','Golpes','Picaduras','Daños por granizo']
    if fruta=='Durazno': return ['Tamaño','Color','Aspecto','Firmeza','Golpes','Picaduras','Daños por granizo']
    if fruta=='Pera': return ['Tamaño','Color','Aspecto','Firmeza','Golpes','Picaduras','Daños']
    return ['Tamaño','Color','Aspecto','Estado']

@app.route('/calidad')
@roles_requeridos('calidad','general')
def cola_calidad():
    ingresos=IngresoFruta.query.filter_by(estado='Pendiente de calidad').order_by(IngresoFruta.fecha.desc()).all()
    return render_template('cola_calidad.html', ingresos=ingresos)

@app.route('/control-calidad/<int:ingreso_id>',methods=['GET','POST'])
@roles_requeridos('calidad','general')
def control_calidad(ingreso_id):
    ingreso=db.session.get(IngresoFruta,ingreso_id)
    if not ingreso: abort(404)
    criterios=criterios_para(ingreso.fruta,ingreso.variedad)
    if request.method=='POST':
        respuestas={c:request.form.get(f'criterio_{i}','') for i,c in enumerate(criterios)}
        if any(v not in CALIDAD for v in respuestas.values()): flash('Tenés que seleccionar una sola opción en cada criterio antes de continuar.','error'); return render_template('control_calidad.html',ingreso=ingreso,criterios=criterios,calidad=CALIDAD,error=True)
        puntuacion=round(sum(PUNTOS[v] for v in respuestas.values())/len(respuestas)); etiqueta='Excelente' if puntuacion>=90 else 'Buena' if puntuacion>=75 else 'Regular' if puntuacion>=50 else 'Rechazo'
        ingreso.puntuacion=puntuacion; ingreso.calidad=etiqueta; ingreso.estado='Calificado'
        precio=Precio.query.filter_by(fruta=ingreso.fruta,variedad=ingreso.variedad,calidad=etiqueta).order_by(Precio.fecha.desc()).first()
        precio_kg=precio.precio_kg if precio else 0; importe=ingreso.kilos_netos*precio_kg
        vale=Vale(numero='V-'+datetime.now().strftime('%Y%m%d%H%M%S%f'),productor_id=ingreso.productor_id,fecha=ingreso.fecha,fruta=ingreso.fruta,variedad=ingreso.variedad,kilos=ingreso.kilos_netos,calidad=etiqueta,precio_kg=precio_kg,importe=importe)
        db.session.add(vale); db.session.commit()
        return render_template('resultado_calidad.html',ingreso=ingreso,respuestas=respuestas,vale=vale,precio_configurado=bool(precio))
    return render_template('control_calidad.html',ingreso=ingreso,criterios=criterios,calidad=CALIDAD)

# -------- USUARIOS --------
@app.route('/usuarios')
@roles_requeridos('administrador')
def usuarios(): return render_template('usuarios.html',usuarios=Usuario.query.order_by(Usuario.usuario).all())
@app.route('/usuarios/nuevo',methods=['GET','POST'])
@roles_requeridos('administrador')
def nuevo_usuario():
    if request.method=='POST':
        usuario=request.form['usuario'].strip(); nombre=request.form.get('nombre','').strip(); rol=request.form['rol']; password=request.form['password']
        if rol not in ROLES or not usuario or len(password)<6: flash('Completá usuario, rol y una contraseña de al menos 6 caracteres.','error'); return redirect(url_for('nuevo_usuario'))
        if Usuario.query.filter_by(usuario=usuario).first(): flash('Ese usuario ya existe.','error'); return redirect(url_for('nuevo_usuario'))
        db.session.add(Usuario(usuario=usuario,nombre=nombre,rol=rol,password=generate_password_hash(password),activo=True)); db.session.commit(); flash('Usuario creado correctamente.','success'); return redirect(url_for('usuarios'))
    return render_template('usuario_form.html',usuario=None)
@app.route('/usuarios/<int:id>/editar',methods=['GET','POST'])
@roles_requeridos('administrador')
def editar_usuario(id):
    u=db.session.get(Usuario,id)
    if not u: abort(404)
    if request.method=='POST':
        u.nombre=request.form.get('nombre','').strip(); u.rol=request.form['rol']; u.activo='activo' in request.form
        if request.form.get('password'): u.password=generate_password_hash(request.form['password'])
        db.session.commit(); flash('Usuario actualizado.','success'); return redirect(url_for('usuarios'))
    return render_template('usuario_form.html',usuario=u)

# -------- PRODUCTORES --------
@app.route('/productores')
@roles_requeridos('general','bascula')
def productores(): return render_template('productores.html',productores=Productor.query.order_by(Productor.apellido,Productor.nombre).all())
@app.route('/productores/nuevo',methods=['GET','POST'])
@roles_requeridos('general','bascula')
def nuevo_productor():
    if request.method=='POST':
        dni=request.form['dni'].strip()
        if Productor.query.filter_by(dni=dni).first(): flash('Ya existe un productor con ese DNI.','error'); return redirect(url_for('nuevo_productor'))
        db.session.add(Productor(nombre=request.form['nombre'].strip(),apellido=request.form['apellido'].strip(),dni=dni,telefono=request.form.get('telefono','').strip(),email=request.form.get('email','').strip(),localidad=request.form.get('localidad','').strip())); db.session.commit(); flash('Productor creado.','success'); return redirect(url_for('productores'))
    return render_template('productor_form.html',productor=None)
@app.route('/productores/<int:id>')
@roles_requeridos('general','bascula')
def detalle_productor(id):
    p=db.session.get(Productor,id)
    if not p: abort(404)
    return render_template('productor_detalle.html',productor=p,vales=Vale.query.filter_by(productor_id=id).order_by(Vale.fecha.desc()).all(),liquidaciones=Liquidacion.query.filter_by(productor_id=id).order_by(Liquidacion.fecha.desc()).all())

# -------- PRECIOS --------
@app.route('/precios')
@roles_requeridos('precios','general')
def precios(): return render_template('precios.html',precios=Precio.query.order_by(Precio.fruta,Precio.variedad,Precio.calidad).all())
@app.route('/precios/nuevo',methods=['GET','POST'])
@roles_requeridos('precios','general')
def nuevo_precio():
    if request.method=='POST':
        try: valor=float(request.form['precio_kg'].replace(',','.'))
        except ValueError: flash('Precio inválido.','error'); return redirect(url_for('nuevo_precio'))
        fruta=request.form['fruta']; variedad=request.form['variedad']; calidad=request.form['calidad']
        if fruta not in VARIEDADES or variedad not in VARIEDADES[fruta] or calidad not in CALIDAD: flash('Datos de precio inválidos.','error'); return redirect(url_for('nuevo_precio'))
        db.session.add(Precio(fruta=fruta,variedad=variedad,calidad=calidad,precio_kg=valor)); db.session.commit(); flash('Precio registrado.','success'); return redirect(url_for('precios'))
    return render_template('precio_form.html',precio=None)
@app.route('/precios/<int:id>/editar',methods=['GET','POST'])
@roles_requeridos('precios','general')
def editar_precio(id):
    p=db.session.get(Precio,id)
    if not p: abort(404)
    if request.method=='POST':
        try: p.precio_kg=float(request.form['precio_kg'].replace(',','.'))
        except ValueError: flash('Precio inválido.','error'); return redirect(url_for('editar_precio',id=id))
        p.fruta=request.form['fruta']; p.variedad=request.form['variedad']; p.calidad=request.form['calidad']; p.fecha=datetime.utcnow(); db.session.commit(); flash('Precio actualizado.','success'); return redirect(url_for('precios'))
    return render_template('precio_form.html',precio=p)

# -------- LIQUIDACIONES --------
@app.route('/liquidaciones')
@roles_requeridos('liquidaciones','general')
def liquidaciones(): return render_template('liquidaciones.html',liquidaciones=Liquidacion.query.order_by(Liquidacion.fecha.desc()).all(),productores=Productor.query.filter_by(activo=True).all())
@app.route('/liquidaciones/nueva/<int:productor_id>',methods=['GET','POST'])
@roles_requeridos('liquidaciones','general')
def nueva_liquidacion(productor_id):
    p=db.session.get(Productor,productor_id); vales=Vale.query.filter_by(productor_id=productor_id,estado='Pendiente').all() if p else []
    if not p: abort(404)
    if not vales: flash('El productor no tiene ingresos pendientes.','error'); return redirect(url_for('liquidaciones'))
    subtotal=sum(v.importe for v in vales)
    if request.method=='POST':
        try: b=float(request.form.get('bonificacion','0').replace(',','.')); d=float(request.form.get('descuento','0').replace(',','.')); a=float(request.form.get('adelanto','0').replace(',','.'))
        except ValueError: flash('Importes inválidos.','error'); return redirect(url_for('nueva_liquidacion',productor_id=productor_id))
        total=subtotal+b-d-a
        if min(b,d,a)<0 or total<0: flash('Los importes no son válidos.','error'); return redirect(url_for('nueva_liquidacion',productor_id=productor_id))
        l=Liquidacion(productor_id=productor_id,subtotal=subtotal,bonificacion=b,descuento=d,adelanto=a,total=total); db.session.add(l); db.session.flush()
        for v in vales: v.estado='Liquidado'; v.liquidacion_id=l.id
        db.session.commit(); flash('Liquidación generada.','success'); return redirect(url_for('detalle_liquidacion',id=l.id))
    return render_template('liquidacion_nueva.html',productor=p,vales=vales,subtotal=subtotal)
@app.route('/liquidaciones/<int:id>')
@roles_requeridos('liquidaciones','general')
def detalle_liquidacion(id):
    l=db.session.get(Liquidacion,id)
    if not l: abort(404)
    return render_template('liquidacion.html',liquidacion=l)
@app.route('/liquidaciones/<int:id>/pagar')
@roles_requeridos('liquidaciones','general')
def pagar_liquidacion(id):
    l=db.session.get(Liquidacion,id)
    if l: l.estado='Pagada'; db.session.commit(); flash('Pago registrado.','success')
    return redirect(url_for('liquidaciones'))

@app.route('/informes')
@login_required
def informes():
    vales=Vale.query.filter(Vale.estado!='Anulado').all(); total=sum(v.kilos for v in vales); por={}
    for v in vales: por[v.fruta]=por.get(v.fruta,0)+v.kilos
    total2=sum(por.values()) or 1; frutas=[{'nombre':k,'kilos':v,'porcentaje':round(v/total2*100,1)} for k,v in por.items()]; frutas.sort(key=lambda x:x['kilos'],reverse=True)
    return render_template('informes.html',total_kilos=total,total_liquidado=sum(l.total for l in Liquidacion.query.filter_by(estado='Pagada').all()),productores_activos=Productor.query.filter_by(activo=True).count(),frutas=frutas)

@app.route('/liquidaciones/<int:id>/pdf')
@roles_requeridos('liquidaciones','general')
def pdf_liquidacion(id):
    l=db.session.get(Liquidacion,id)
    if not l: abort(404)
    buf=BytesIO(); pdf=canvas.Canvas(buf,pagesize=A4); w,h=A4; pdf.setFillColor(colors.HexColor('#171c63')); pdf.rect(0,h-70,w,70,fill=1,stroke=0); pdf.setFillColor(colors.white); pdf.setFont('Helvetica-Bold',22); pdf.drawString(45,h-45,'CIMAFRUT')
    y=h-100; pdf.setFillColor(colors.black); pdf.setFont('Helvetica-Bold',12); pdf.drawString(45,y,f'Liquidación N° {l.id}'); y-=20; pdf.setFont('Helvetica',10); pdf.drawString(45,y,f'Productor: {l.productor.apellido}, {l.productor.nombre}'); y-=16; pdf.drawString(45,y,f'DNI: {l.productor.dni}'); y-=30; pdf.setFont('Helvetica-Bold',9)
    for x,t in [(45,'Vale'),(120,'Fruta'),(205,'Variedad'),(300,'Calidad'),(390,'Kg'),(445,'$/Kg'),(510,'Importe')]: pdf.drawString(x,y,t)
    y-=15; pdf.setFont('Helvetica',8)
    for v in l.vales:
        pdf.drawString(45,y,v.numero[-10:]); pdf.drawString(120,y,v.fruta[:12]); pdf.drawString(205,y,v.variedad[:13]); pdf.drawString(300,y,v.calidad[:10]); pdf.drawRightString(420,y,f'{v.kilos:.2f}'); pdf.drawRightString(480,y,f'${v.precio_kg:.2f}'); pdf.drawRightString(555,y,f'${v.importe:.2f}'); y-=15
    y-=10; pdf.setFont('Helvetica-Bold',10)
    for label,val in [('Subtotal',l.subtotal),('Bonificación',l.bonificacion),('Descuento',l.descuento),('Adelanto',l.adelanto),('TOTAL',l.total)]: pdf.drawRightString(480,y,label+':'); pdf.drawRightString(555,y,f'${val:.2f}'); y-=18
    pdf.save(); buf.seek(0); return send_file(buf,as_attachment=False,download_name=f'liquidacion_{id}.pdf',mimetype='application/pdf')

with app.app_context():
    db.create_all()
    # Migration for the existing Usuario table from the original project.
    cols={r[1] for r in db.session.execute(db.text('PRAGMA table_info(usuario)')).fetchall()}
    if 'rol' not in cols: db.session.execute(db.text("ALTER TABLE usuario ADD COLUMN rol VARCHAR(30) NOT NULL DEFAULT 'general'"))
    if 'nombre' not in cols: db.session.execute(db.text("ALTER TABLE usuario ADD COLUMN nombre VARCHAR(120) DEFAULT ''"))
    if 'activo' not in cols: db.session.execute(db.text("ALTER TABLE usuario ADD COLUMN activo BOOLEAN NOT NULL DEFAULT 1"))
    db.session.commit()
    admin=Usuario.query.filter_by(usuario='admin').first()
    if not admin:
        db.session.add(Usuario(usuario='admin',nombre='Administrador',rol='administrador',activo=True,password=generate_password_hash('admin123'))); db.session.commit()
    elif admin.rol!='administrador': admin.rol='administrador'; admin.activo=True; db.session.commit()
    # Useful initial containers; editable from the system.
    if Envase.query.count()==0:
        db.session.add_all([Envase(nombre='Cajón plástico',peso_vacio=2.5),Envase(nombre='Bin',peso_vacio=60),Envase(nombre='Pallet',peso_vacio=25)]); db.session.commit()

if __name__=='__main__': app.run(debug=True)
