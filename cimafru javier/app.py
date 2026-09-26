from flask import Flask, render_template, request, send_file, jsonify 
import qrcode 
import io 
 
app = Flask(__name__) 
 
PRODUCTORES = { 
    "101": { 
        "cliente": "Juan Perez", 
        "cuit": "20-12345678-9", 
        "domicilio": "Finca Los Olivos S/N", 
        "condicion_iva": "IVA responsable Inscripto" 
    }, 
    "102": { 
        "cliente": "Agricola del Sur S.A.", 
        "cuit": "30-98765432-1", 
        "domicilio": "Ruta Nacional 40, Km 15", 
        "condicion_iva": "IVA Sujeto Exento" 
    }, 
    "103": { 
        "cliente": "Javier francp", 
        "cuit": "20123456788", 
        "domicilio": "calle 1234", 
        "condicion_iva": "Monotributista" 
    } 
} 
 
@app.route('/') 
def index(): 
    id_productor = request.args.get('id_productor') 
    datos_autocompletar = PRODUCTORES.get(id_productor, {}) 
    return render_template('entrada_fruta.html', datos=datos_autocompletar, 
productores=PRODUCTORES) 
 
@app.route('/api/productor/<id_productor>') 
def api_productor(id_productor): 
    return jsonify(PRODUCTORES.get(id_productor, {})) 
 
@app.route('/generar_qr/<id_productor>') 
def generar_qr(id_productor): 
    url_formulario = f"http://127.0.0{id_productor}" 
     
    qr = qrcode.QRCode(version=1, box_size=10, border=5) 
    qr.add_data(url_formulario) 
    qr.make(fit=True) 
    img = qr.make_image(fill='black', back_color='white') 
     
    buf = io.BytesIO() 
    img.save(buf, format='PNG') 
    buf.seek(0) 
    return send_file(buf, mimetype='image/png') 
 
@app.route('/procesar_entrada', methods=['POST']) 
def procesar_entrada(): 
    datos = request.form 
    return f"¡Datos guardados con éxito para {datos.get('cliente')}!" 
 
if __name__ == '__main__': 
    app.run(debug=True) 