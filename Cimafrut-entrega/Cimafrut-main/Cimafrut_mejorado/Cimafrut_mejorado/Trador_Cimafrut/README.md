# CIMAFRUT unificado — versión mejorada

## Cambios principales
- Control de calidad con **una sola selección por criterio** (radio buttons) y botón bloqueado hasta completar todos.
- Frutas principales: Ciruela, Durazno, Pera, Damasco, Uva y Tomate.
- Variedad dependiente de la fruta mediante desplegables.
- Configuración de tipos de envase y peso vacío.
- Cálculo: **peso bruto del camión − tara del camión − tara total de envases = kilos netos**.
- Usuarios con roles: Administrador, General, Báscula/Ingreso, Precios, Control de calidad y Liquidaciones.
- El administrador puede crear y editar usuarios desde `/usuarios`.
- Se conserva la base SQLite del proyecto original y se agrega migración automática para los nuevos campos del usuario.

## Instalación en Windows PowerShell
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```
Abrir `http://127.0.0.1:5000`.

Usuario inicial: `admin` / `admin123`.

## Variedades
El catálogo inicial se armó como una base regional para Mendoza, priorizando referencias documentadas para el oasis Sur. Debe tomarse como catálogo inicial configurable, no como un censo exhaustivo de cada finca.


## Ajustes de esta versión
- Número de lote obligatorio y único en cada ingreso, heredado por el vale.
- El vale muestra precio por kg e importe y conserva ambos valores al momento de la calificación.
- No se finaliza un ingreso si no existe un precio válido (> 0) para fruta + variedad + calidad.
- PDF del vale con marca CIMAFRUT, lote y datos del productor (nombre, DNI/CUIT, teléfono, email y localidad).
- Descarga del PDF y compartir por WhatsApp; en dispositivos compatibles se comparte el PDF como archivo y, como alternativa, se abre WhatsApp con el enlace al PDF.
- Productores editables con validación de DNI/CUIT, email y teléfono.
- Listado de vales con lote, $/kg, importe, estado y descarga PDF.
- Liquidaciones con selección individual de vales; solo los seleccionados pasan a estado Liquidado.
- Validaciones de servidor y de formulario para impedir combinaciones o valores inválidos.
- Migración automática y migración incluida de la SQLite existente para los nuevos campos de lote.
