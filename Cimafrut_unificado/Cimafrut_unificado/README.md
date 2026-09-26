# CIMAFRUT — Proyecto unificado

Este proyecto une las tres partes del repositorio original:

- `CIMAFRUT`: autenticación, productores, precios, vales y liquidaciones.
- `cimafru javier`: carga/entrada de fruta y cálculo de kilos netos.
- `control_calidad`: criterios dinámicos de calidad según el producto.

## Flujo principal

Login → Inicio → Ingreso de fruta → Control de calidad → Ingreso registrado → Liquidación → Informes.

## Instalación

1. Crear un entorno virtual:

```bash
python -m venv venv
```

2. Activarlo en Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

3. Instalar dependencias:

```bash
pip install -r requirements.txt
```

4. Ejecutar:

```bash
python app.py
```

5. Abrir:

`http://127.0.0.1:5000`

## Usuario inicial

- Usuario: `admin`
- Contraseña: `admin123`

## Importante

La base SQLite original se conserva en `instance/cimafrut.db`. Al iniciar, Flask crea las nuevas tablas que no existían.

Para producción conviene cambiar `SECRET_KEY` y la contraseña inicial.
