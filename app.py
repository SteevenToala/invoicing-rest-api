from flask import Flask, request, Response, jsonify
from flask_cors import CORS
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os
from dotenv import load_dotenv
from twilio.rest import Client
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from infrastructure.soap_service import procesar_peticion_soap, obtener_wsdl
from werkzeug.exceptions import HTTPException

load_dotenv()

app = Flask(__name__)
CORS(app)

@app.errorhandler(Exception)
def handle_exception(e):
    # Registrar el error completo en la consola del servidor (útil para Render/Gunicorn logs)
    app.logger.error(f"Error detectado: {e}", exc_info=True)
    
    # Si es una excepción HTTP estándar (como 404, 405), devolver su código y descripción en JSON
    if isinstance(e, HTTPException):
        return jsonify({
            "error": e.description,
            "code": e.code
        }), e.code
        
    # Para cualquier otro error interno del servidor, devolver 500 con el mensaje de la excepción en JSON
    return jsonify({
        "error": str(e),
        "code": 500
    }), 500

@app.route("/soap", methods=["GET", "POST"])
def soap_endpoint():
    if request.method == "GET":
        if "wsdl" in request.args:
            host_url = request.host_url.rstrip("/") + "/soap"
            wsdl_content = obtener_wsdl(host_url)
            return Response(wsdl_content, mimetype="application/xml; charset=utf-8")
        else:
            return "Endpoint SOAP activo. Añade ?wsdl a la URL para ver el contrato.", 200
            
    elif request.method == "POST":
        xml_request = request.data.decode('utf-8')
        if not xml_request:
            return Response("Petición vacía", status=400)
            
        xml_response = procesar_peticion_soap(xml_request)
        return Response(xml_response, mimetype="application/xml; charset=utf-8")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")

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

        if not cliente.get("telefono"):
            errores.append({
                "campo": "cliente.telefono",
                "error": "El teléfono es obligatorio."
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

def enviar_notificacion_twilio(datos):
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        print("Credenciales de Twilio no configuradas.")
        return

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        numero_factura = datos.get("numero")
        nombre_cliente = datos["cliente"]["nombre"]
        telefono_destino = datos["cliente"]["telefono"]
        
        # Twilio requiere el prefijo 'whatsapp:' para mensajes de WhatsApp
        from_whatsapp = f"whatsapp:{TWILIO_PHONE_NUMBER}"
        
        # Asegurar que el teléfono de destino tenga un prefijo '+' si no lo tiene
        if not telefono_destino.startswith('+'):
            telefono_destino = f"+{telefono_destino}"
            
        to_whatsapp = f"whatsapp:{telefono_destino}"
        
        mensaje = f"Hola {nombre_cliente}, tu factura {numero_factura} ha sido generada con éxito en TechStore 360."
        
        message = client.messages.create(
            from_=from_whatsapp,
            body=mensaje,
            to=to_whatsapp
        )
        print(f"Notificación de Twilio enviada exitosamente. SID: {message.sid}")
    except Exception as e:
        print(f"Error al enviar notificación de Twilio: {e}")

def enviar_notificacion_correo(datos, file_path):
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print("Credenciales de SMTP (Brave Email) no configuradas. Omitiendo envío de correo.")
        return

    try:
        numero_factura = datos.get("numero")
        nombre_cliente = datos["cliente"]["nombre"]
        correo_destino = datos["cliente"]["correo"]
        
        # Crear el mensaje multipart
        mensaje = MIMEMultipart()
        mensaje["From"] = SMTP_FROM_EMAIL
        mensaje["To"] = correo_destino
        mensaje["Subject"] = f"TechStore 360 - Factura Generada: {numero_factura}"
        
        cuerpo = f"""
        Hola {nombre_cliente},
        
        Tu factura {numero_factura} ha sido generada exitosamente.
        Adjunto encontrarás el archivo XML correspondiente a tu compra.
        
        Gracias por preferir TechStore 360.
        """
        mensaje.attach(MIMEText(cuerpo, "plain"))
        
        # Adjuntar archivo XML
        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as adjunto:
                parte = MIMEBase("application", "octet-stream")
                parte.set_payload(adjunto.read())
            
            encoders.encode_base64(parte)
            parte.add_header(
                "Content-Disposition",
                f"attachment; filename=factura_{numero_factura}.xml",
            )
            mensaje.attach(parte)
        
        # Conexión al servidor SMTP
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        texto = mensaje.as_string()
        server.sendmail(SMTP_FROM_EMAIL, correo_destino, texto)
        server.quit()
        
        print(f"Notificación de correo (Brave Email) enviada exitosamente a {correo_destino}.")
    except Exception as e:
        print(f"Error al enviar notificación de correo: {e}")

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
        
        # Enviar notificación por Twilio (WhatsApp)
        enviar_notificacion_twilio(datos)
        
        # Enviar notificación por Brave Email (SMTP)
        enviar_notificacion_correo(datos, file_path)
        
    except Exception as e:
        print(f"Error al guardar el archivo de factura: {e}")
        
    return Response(xml_factura, mimetype="application/xml; charset=utf-8")

if __name__ == "__main__":
    # Lee el puerto de las variables de entorno (requerido por Render) o usa el 5002 por defecto
    port = int(os.environ.get("PORT", 5002))
    print(f"Iniciando servidor en el puerto {port}")
    print(f"Ruta REST API: http://localhost:{port}/api/factura")
    print(f"Ruta SOAP WSDL: http://localhost:{port}/soap?wsdl")
    app.run(host="0.0.0.0", port=port, debug=True)

