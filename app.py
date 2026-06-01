from flask import Flask, request, Response, jsonify
from flask_cors import CORS
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os

app = Flask(__name__)
CORS(app)

IVA_PORCENTAJE = 0.15

# Asegurar que exista la carpeta para guardar las facturas generadas
FACTURAS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "facturas")
os.makedirs(FACTURAS_DIR, exist_ok=True)

@app.route("/")
def inicio():
    return jsonify({
        "success": True,
        "message": "Servicio de Facturación REST de TechStore 360 listo y funcionando",
        "facturas_guardadas_dir": FACTURAS_DIR
    }), 200

def validar_datos(datos):
    errores = []

    if datos is None:
        errores.append({
            "campo": "body",
            "error": "No se recibió un JSON válido."
        })
        return errores

    if not datos.get("numero"):
        errores.append({
            "campo": "numero",
            "error": "El número de factura es obligatorio."
        })

    if not datos.get("fecha"):
        errores.append({
            "campo": "fecha",
            "error": "La fecha es obligatoria."
        })

    cliente = datos.get("cliente")

    if not isinstance(cliente, dict):
        errores.append({
            "campo": "cliente",
            "error": "Los datos del cliente son obligatorios."
        })
    else:
        if not cliente.get("nombre"):
            errores.append({
                "campo": "cliente.nombre",
                "error": "El nombre del cliente es obligatorio."
            })

        if not cliente.get("cedula_ruc"):
            errores.append({
                "campo": "cliente.cedula_ruc",
                "error": "La cédula o RUC es obligatorio."
            })

        if not cliente.get("correo"):
            errores.append({
                "campo": "cliente.correo",
                "error": "El correo es obligatorio."
            })

        if not cliente.get("direccion"):
            errores.append({
                "campo": "cliente.direccion",
                "error": "La dirección es obligatoria."
            })

    productos = datos.get("productos")

    if not isinstance(productos, list) or len(productos) == 0:
        errores.append({
            "campo": "productos",
            "error": "Debe existir al menos un producto."
        })
    else:
        for i, producto in enumerate(productos, start=1):
            if not producto.get("nombre"):
                errores.append({
                    "campo": f"productos[{i}].nombre",
                    "error": "El nombre del producto es obligatorio."
                })

            # Validar cantidad
            try:
                cantidad = float(producto.get("cantidad", 0))
                if cantidad <= 0:
                    errores.append({
                        "campo": f"productos[{i}].cantidad",
                        "error": "La cantidad debe ser mayor a 0."
                    })
            except (ValueError, TypeError):
                errores.append({
                    "campo": f"productos[{i}].cantidad",
                    "error": "La cantidad debe ser numérica."
                })

            # Validar precio unitario
            try:
                precio_unitario = float(producto.get("precio_unitario", 0))
                if precio_unitario <= 0:
                    errores.append({
                        "campo": f"productos[{i}].precio_unitario",
                        "error": "El precio unitario debe ser mayor a 0."
                    })
            except (ValueError, TypeError):
                errores.append({
                    "campo": f"productos[{i}].precio_unitario",
                    "error": "El precio unitario debe ser numérico."
                })

    return errores

def formatear_xml(elemento):
    xml_sin_formato = ET.tostring(elemento, encoding="utf-8")
    xml_formateado = minidom.parseString(xml_sin_formato).toprettyxml(indent="  ")
    return xml_formateado

def crear_factura_xml(datos):
    factura = ET.Element("Factura")
    cabecera = ET.SubElement(factura, "Cabecera")
    ET.SubElement(cabecera, "Numero").text = str(datos["numero"])
    ET.SubElement(cabecera, "Fecha").text = str(datos["fecha"])
    
    cliente = ET.SubElement(factura, "Cliente")
    ET.SubElement(cliente, "Nombre").text = datos["cliente"]["nombre"]
    ET.SubElement(cliente, "CedulaRUC").text = datos["cliente"]["cedula_ruc"]
    ET.SubElement(cliente, "Correo").text = datos["cliente"]["correo"]
    ET.SubElement(cliente, "Direccion").text = datos["cliente"]["direccion"]
    
    detalle = ET.SubElement(factura, "Detalle")
    subtotal_general = 0
    for item in datos["productos"]:
        cantidad = float(item["cantidad"])
        precio_unitario = float(item["precio_unitario"])
        subtotal_producto = cantidad * precio_unitario
        subtotal_general += subtotal_producto
        
        producto = ET.SubElement(detalle, "Producto")
        ET.SubElement(producto, "Nombre").text = item["nombre"]
        ET.SubElement(producto, "Cantidad").text = str(item["cantidad"])
        ET.SubElement(producto, "PrecioUnitario").text = f"{precio_unitario:.2f}"
        ET.SubElement(producto, "Subtotal").text = f"{subtotal_producto:.2f}"
        
    iva = subtotal_general * IVA_PORCENTAJE
    total = subtotal_general + iva
    
    totales = ET.SubElement(factura, "Totales")
    ET.SubElement(totales, "Subtotal").text = f"{subtotal_general:.2f}"
    ET.SubElement(totales, "IVA").text = f"{iva:.2f}"
    ET.SubElement(totales, "Total").text = f"{total:.2f}"
    
    ET.SubElement(factura, "Estado").text = "Generada"
    return formatear_xml(factura)

@app.route("/api/factura", methods=["POST"])
def generar_factura():
    datos = request.get_json(silent=True)
    errores = validar_datos(datos)
    if errores:
        return jsonify({
            "estado": "error",
            "mensaje": "Datos inválidos. No se pudo generar la factura.",
            "errores": errores
        }), 400
        
    xml_factura = crear_factura_xml(datos)
    
    # Escribir el archivo XML físicamente en la carpeta 'facturas/'
    numero_factura = datos.get("numero", "F000-000000").replace("/", "-").replace("\\", "-")
    file_path = os.path.join(FACTURAS_DIR, f"factura_{numero_factura}.xml")
    
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(xml_factura)
        print(f"Factura guardada físicamente en: {file_path}")
    except Exception as e:
        print(f"Error al guardar el archivo de factura: {e}")
        
    return Response(xml_factura, mimetype="application/xml; charset=utf-8")

if __name__ == "__main__":
    # Lee el puerto de las variables de entorno (requerido por Render) o usa el 5002 por defecto
    port = int(os.environ.get("PORT", 5002))
    app.run(host="0.0.0.0", port=port, debug=True)
