import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.graphics.barcode import code128

def crear_factura_pdf_mock(datos):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Constantes
    margin_x = 1.5 * cm
    margin_y = 1.5 * cm
    
    # ------------------ SECCION SUPERIOR ------------------
    # Caja RUC (Derecha)
    c.rect(width/2 + 0.5*cm, height - 8.5*cm, width/2 - 2*cm, 7*cm)
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(width/2 + 1*cm, height - 2*cm, "RUC:        0000000000001")
    c.drawString(width/2 + 1*cm, height - 2.5*cm, "Tipo:       FACTURA")
    c.drawString(width/2 + 1*cm, height - 3*cm, f"Número:  {datos.get('numero', '001-001-000000001')}")
    
    c.setFont("Helvetica", 9)
    c.drawString(width/2 + 1*cm, height - 4*cm, "Ambiente:   PRODUCCION")
    c.drawString(width/2 + 1*cm, height - 4.4*cm, "Emisión:    NORMAL")
    c.drawString(width/2 + 1*cm, height - 4.8*cm, f"Fecha y Hora: {datos.get('fecha')} 12:00")
    
    c.drawString(width/2 + 1*cm, height - 5.5*cm, "Número Autorización / Clave de Acceso:")
    clave_acceso = "1208202001179247719000120011000000000080000000111"
    c.drawString(width/2 + 1*cm, height - 5.9*cm, clave_acceso)
    
    # Barcode
    barcode = code128.Code128(clave_acceso, barHeight=1.2*cm, barWidth=0.8)
    barcode.drawOn(c, width/2 + 1*cm, height - 7.5*cm)
    
    # Caja Empresa (Izquierda)
    c.rect(margin_x, height - 8.5*cm, width/2 - 1.5*cm, 7*cm)
    # Mock logo
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin_x + 0.5*cm, height - 2.5*cm, "TECHSTORE 360")
    
    c.setFont("Helvetica-Bold", 8)
    c.drawString(margin_x + 0.5*cm, height - 4.5*cm, "RAZON SOCIAL: TechStore 360 S.A.")
    c.drawString(margin_x + 0.5*cm, height - 5.5*cm, "DIRECCIÓN: Av. Principal y Secundaria")
    c.drawString(margin_x + 0.5*cm, height - 6.5*cm, "OBLIGADO A LLEVAR CONTABILIDAD: SI")
    
    # ------------------ INFO CLIENTE ------------------
    y_cliente = height - 10.5*cm
    c.rect(margin_x, y_cliente, width - 3*cm, 1.8*cm)
    c.setFont("Helvetica", 9)
    c.drawString(margin_x + 0.2*cm, y_cliente + 1.2*cm, f"RAZÓN SOCIAL/NOMBRES: {datos['cliente']['nombre']}")
    c.drawString(margin_x + 0.2*cm, y_cliente + 0.7*cm, f"IDENTIFICACIÓN: {datos['cliente']['cedula_ruc']}")
    c.drawString(margin_x + 0.2*cm, y_cliente + 0.2*cm, f"DIRECCIÓN: {datos['cliente']['direccion']}")
    
    c.drawString(width - 7*cm, y_cliente + 1.2*cm, f"FECHA EMISIÓN: {datos['fecha']}")
    
    # ------------------ DETALLE PRODUCTOS ------------------
    y_table = y_cliente - 1*cm
    c.rect(margin_x, y_table - 6*cm, width - 3*cm, 6*cm) # Box for table
    
    # Headers
    c.setFont("Helvetica-Bold", 8)
    c.drawString(margin_x + 0.2*cm, y_table - 0.4*cm, "CÓDIGO")
    c.drawString(margin_x + 2*cm, y_table - 0.4*cm, "CANT")
    c.drawString(margin_x + 3.5*cm, y_table - 0.4*cm, "DESCRIPCIÓN")
    c.drawString(width - 5.5*cm, y_table - 0.4*cm, "PVP")
    c.drawString(width - 4*cm, y_table - 0.4*cm, "DESC")
    c.drawString(width - 2.5*cm, y_table - 0.4*cm, "TOTAL")
    
    c.line(margin_x, y_table - 0.6*cm, width - 1.5*cm, y_table - 0.6*cm)
    
    y = y_table - 1.2*cm
    c.setFont("Helvetica", 8)
    subtotal_general = 0
    for i, item in enumerate(datos["productos"]):
        cantidad = float(item["cantidad"])
        precio_unitario = float(item["precio_unitario"])
        subtotal = cantidad * precio_unitario
        subtotal_general += subtotal
        
        c.drawString(margin_x + 0.2*cm, y, f"PROD-{i+1}")
        c.drawString(margin_x + 2*cm, y, f"{cantidad:.2f}")
        c.drawString(margin_x + 3.5*cm, y, str(item["nombre"])[:45])
        c.drawString(width - 5.5*cm, y, f"{precio_unitario:.2f}")
        c.drawString(width - 4*cm, y, "0.00")
        c.drawString(width - 2.5*cm, y, f"{subtotal:.2f}")
        y -= 0.6*cm
        
    # ------------------ TOTALES ------------------
    y_totals = y_table - 6.5*cm
    
    # Info Adicional Izquierda
    c.rect(margin_x, y_totals - 3*cm, width/2, 2.5*cm)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(margin_x + 0.2*cm, y_totals - 0.8*cm, "Información Adicional")
    c.setFont("Helvetica", 8)
    c.drawString(margin_x + 0.2*cm, y_totals - 1.3*cm, f"Email: {datos['cliente']['correo']}")
    c.drawString(margin_x + 0.2*cm, y_totals - 1.8*cm, f"Teléfono: {datos['cliente']['telefono']}")
    
    # Totales Derecha
    x_totales = width - 7*cm
    w_totales = 5.5*cm
    c.rect(x_totales, y_totals - 3*cm, w_totales, 2.5*cm)
    
    iva = subtotal_general * 0.15
    total = subtotal_general + iva
    
    c.drawString(x_totales + 0.2*cm, y_totals - 0.8*cm, "SUBTOTAL 15%")
    c.drawString(x_totales + 4*cm, y_totals - 0.8*cm, f"{subtotal_general:.2f}")
    
    c.drawString(x_totales + 0.2*cm, y_totals - 1.3*cm, "SUBTOTAL 0%")
    c.drawString(x_totales + 4*cm, y_totals - 1.3*cm, "0.00")
    
    c.drawString(x_totales + 0.2*cm, y_totals - 1.8*cm, "IVA 15%")
    c.drawString(x_totales + 4*cm, y_totals - 1.8*cm, f"{iva:.2f}")
    
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x_totales + 0.2*cm, y_totals - 2.8*cm, "VALOR TOTAL")
    c.drawString(x_totales + 4*cm, y_totals - 2.8*cm, f"{total:.2f}")
    
    # Forma de pago
    c.rect(margin_x, y_totals - 4.5*cm, width - 3*cm, 1*cm)
    c.setFont("Helvetica", 8)
    c.drawString(margin_x + 0.2*cm, y_totals - 4*cm, "FORMA DE PAGO: Otros con Utilización del Sistema Financiero")
    c.drawString(width - 5.5*cm, y_totals - 4*cm, f"TOTAL: {total:.2f}")
    
    c.save()
    
    with open("test.pdf", "wb") as f:
        f.write(buffer.getvalue())
    print("PDF generado con éxito en test.pdf")

if __name__ == "__main__":
    mock_data = {
      "numero": "001-100-000000008",
      "fecha": "2020-08-12",
      "cliente": {
        "nombre": "Marlon Guevara",
        "cedula_ruc": "000000588555",
        "correo": "correo@ejemplo.com",
        "direccion": "PICHINCHA",
        "telefono": "2996500"
      },
      "productos": [
        {
          "nombre": "VIAJES QUITO GUAYAQUIL",
          "cantidad": 6,
          "precio_unitario": 656.00
        },
        {
          "nombre": "VIAJES QUITO GUAYAQUIL",
          "cantidad": 1,
          "precio_unitario": 666.00
        },
        {
          "nombre": "VIAJES LOCALES",
          "cantidad": 3,
          "precio_unitario": 52.00
        }
      ]
    }
    crear_factura_pdf_mock(mock_data)
