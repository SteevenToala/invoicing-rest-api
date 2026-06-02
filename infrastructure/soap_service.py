import xml.etree.ElementTree as ET
from application.use_cases import FacturacionUseCases
from core.entities import RespuestaFactura

def generar_respuesta_soap(operacion: str, resultado: RespuestaFactura) -> str:
    """Genera un XML de respuesta SOAP estándar basándose en el resultado de la operación."""
    
    clave_xml = f"\n                <ClaveAcceso>{resultado.clave_acceso}</ClaveAcceso>" if resultado.clave_acceso else ""
    
    xml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:fac="http://techstore360.com/facturacion">
    <soapenv:Body>
        <fac:{operacion}Response>
            <RespuestaFactura>
                <Estado>{resultado.estado}</Estado>
                <Mensaje>{resultado.mensaje}</Mensaje>{clave_xml}
            </RespuestaFactura>
        </fac:{operacion}Response>
    </soapenv:Body>
</soapenv:Envelope>"""
    return xml_response

def procesar_peticion_soap(xml_request: str) -> str:
    """Parsea una petición SOAP XML y enruta al caso de uso correspondiente."""
    try:
        # Parseamos el XML
        root = ET.fromstring(xml_request)
        
        # En SOAP, el primer hijo usualmente es el Header o el Body
        # Buscamos el Body, ignorando namespaces usando una búsqueda genérica
        body = root.find('.//*{http://schemas.xmlsoap.org/soap/envelope/}Body')
        if body is None:
            # Intentar sin namespace estricto
            for child in root:
                if 'Body' in child.tag:
                    body = child
                    break
        
        if body is None or len(body) == 0:
            return _generar_error_soap("Cuerpo SOAP (Body) vacío o inválido")
            
        operacion_node = body[0]
        # El nombre de la operación puede incluir namespace ej: {http://techstore...}ValidarFactura
        operacion = operacion_node.tag.split('}')[-1] if '}' in operacion_node.tag else operacion_node.tag
        
        if operacion == "ValidarFactura":
            # Extraer xmlFactura
            xml_factura_node = operacion_node.find('.//*xmlFactura')
            if xml_factura_node is None and len(operacion_node) > 0:
                xml_factura_node = operacion_node[0] # Fallback al primer argumento
            
            xml_factura = xml_factura_node.text if xml_factura_node is not None else ""
            resultado = FacturacionUseCases.validar_factura(xml_factura)
            return generar_respuesta_soap("ValidarFactura", resultado)
            
        elif operacion == "GenerarFacturaXML":
            id_compra_node = operacion_node.find('.//*idCompra')
            if id_compra_node is None and len(operacion_node) > 0:
                id_compra_node = operacion_node[0]
                
            id_compra = id_compra_node.text if id_compra_node is not None else ""
            resultado = FacturacionUseCases.generar_factura_xml(id_compra)
            return generar_respuesta_soap("GenerarFacturaXML", resultado)
            
        elif operacion == "ConsultarComprobante":
            id_compra_node = operacion_node.find('.//*idCompra')
            if id_compra_node is None and len(operacion_node) > 0:
                id_compra_node = operacion_node[0]
                
            id_compra = id_compra_node.text if id_compra_node is not None else ""
            resultado = FacturacionUseCases.consultar_comprobante(id_compra)
            return generar_respuesta_soap("ConsultarComprobante", resultado)
            
        else:
            return _generar_error_soap(f"Operación '{operacion}' no soportada")
            
    except Exception as e:
        return _generar_error_soap(f"Error parseando el XML SOAP: {str(e)}")

def _generar_error_soap(mensaje: str) -> str:
    """Genera un SOAP Fault en caso de error"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
    <soapenv:Body>
        <soapenv:Fault>
            <faultcode>soapenv:Client</faultcode>
            <faultstring>{mensaje}</faultstring>
        </soapenv:Fault>
    </soapenv:Body>
</soapenv:Envelope>"""

def obtener_wsdl(host_url: str) -> str:
    """Retorna un WSDL estático simple para el servicio."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<definitions name="FacturacionService"
             targetNamespace="http://techstore360.com/facturacion"
             xmlns:tns="http://techstore360.com/facturacion"
             xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
             xmlns="http://schemas.xmlsoap.org/wsdl/">
    <message name="ValidarFacturaRequest">
        <part name="xmlFactura" type="xsd:string"/>
    </message>
    <message name="ValidarFacturaResponse">
        <part name="RespuestaFactura" type="xsd:anyType"/>
    </message>
    
    <message name="GenerarFacturaXMLRequest">
        <part name="idCompra" type="xsd:string"/>
    </message>
    <message name="GenerarFacturaXMLResponse">
        <part name="RespuestaFactura" type="xsd:anyType"/>
    </message>
    
    <message name="ConsultarComprobanteRequest">
        <part name="idCompra" type="xsd:string"/>
    </message>
    <message name="ConsultarComprobanteResponse">
        <part name="RespuestaFactura" type="xsd:anyType"/>
    </message>

    <portType name="FacturacionPortType">
        <operation name="ValidarFactura">
            <input message="tns:ValidarFacturaRequest"/>
            <output message="tns:ValidarFacturaResponse"/>
        </operation>
        <operation name="GenerarFacturaXML">
            <input message="tns:GenerarFacturaXMLRequest"/>
            <output message="tns:GenerarFacturaXMLResponse"/>
        </operation>
        <operation name="ConsultarComprobante">
            <input message="tns:ConsultarComprobanteRequest"/>
            <output message="tns:ConsultarComprobanteResponse"/>
        </operation>
    </portType>

    <binding name="FacturacionBinding" type="tns:FacturacionPortType">
        <soap:binding style="rpc" transport="http://schemas.xmlsoap.org/soap/http"/>
        <operation name="ValidarFactura">
            <soap:operation soapAction="ValidarFactura"/>
            <input><soap:body use="literal"/></input>
            <output><soap:body use="literal"/></output>
        </operation>
        <operation name="GenerarFacturaXML">
            <soap:operation soapAction="GenerarFacturaXML"/>
            <input><soap:body use="literal"/></input>
            <output><soap:body use="literal"/></output>
        </operation>
        <operation name="ConsultarComprobante">
            <soap:operation soapAction="ConsultarComprobante"/>
            <input><soap:body use="literal"/></input>
            <output><soap:body use="literal"/></output>
        </operation>
    </binding>

    <service name="FacturacionService">
        <port name="FacturacionPort" binding="tns:FacturacionBinding">
            <soap:address location="{host_url}"/>
        </port>
    </service>
</definitions>"""
