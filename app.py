# app.py - Implementación POC MiFarma siguiendo exactamente la estructura del diagrama
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional
import uuid
import datetime

# Inicializar FastAPI
app = FastAPI(title="MiFarma POC")

# ----- BASES DE DATOS MOCK -----
# Usuarios
USUARIOS = {
    "user1": {"id": "user1", "nombre": "Cliente Normal", "password": "password123", "es_admin": False},
    "admin1": {"id": "admin1", "nombre": "Administrador", "password": "admin123", "es_admin": True}
}

# Stock de productos (por tienda)
STOCK = {
    "tienda_fisica_1": {
        "producto_001": {"nombre": "Paracetamol", "precio": 5.50, "stock": 100},
        "producto_002": {"nombre": "Ibuprofeno", "precio": 8.75, "stock": 75},
    },
    "tienda_virtual_1": {
        "producto_001": {"nombre": "Paracetamol", "precio": 5.50, "stock": 80},
        "producto_002": {"nombre": "Ibuprofeno", "precio": 8.75, "stock": 60},
        "producto_003": {"nombre": "Aspirina", "precio": 4.20, "stock": 120}
    }
}

# Productos generales
PRODUCTOS = {
    "producto_001": {"id": "producto_001", "nombre": "Paracetamol", "descripcion": "Analgésico y antipirético"},
    "producto_002": {"id": "producto_002", "nombre": "Ibuprofeno", "descripcion": "Antiinflamatorio no esteroideo"},
    "producto_003": {"id": "producto_003", "nombre": "Aspirina", "descripcion": "Ácido acetilsalicílico"}
}

# Carritos de compra
CARRITOS = {}

# Órdenes de venta
ORDENES = []

# Ventas realizadas
VENTAS = []

# Sesiones activas
SESIONES = {}

# ----- MODELOS DE DATOS -----
class LoginData(BaseModel):
    username: str
    password: str

class ProductoCarrito(BaseModel):
    producto_id: str
    cantidad: int
    isDelivery: bool = False
    direccion_entrega: Optional[str] = None

class PagoData(BaseModel):
    metodo: str  # "efectivo" o "pasarela"
    monto: float
    detalles: Optional[Dict] = None

# ----- FUNCIONES AUXILIARES -----
def get_user_from_token(token: str = Header(...)):
    if token not in SESIONES:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
    return SESIONES[token]

def verificar_admin(user: Dict = Depends(get_user_from_token)):
    if not user["es_admin"]:
        raise HTTPException(status_code=403, detail="Se requieren permisos de administrador")
    return user

# ----- ENDPOINTS (APIS) -----

# 1. Login Service
@app.post("/login")
def login_service(datos: LoginData):
    """Login Service para autenticación"""
    if datos.username not in USUARIOS:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    
    user = USUARIOS[datos.username]
    if user["password"] != datos.password:
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")
    
    # Generar token de sesión
    token = str(uuid.uuid4())
    SESIONES[token] = user
    
    return {
        "token": token,
        "user_id": user["id"],
        "nombre": user["nombre"],
        "es_admin": user["es_admin"]
    }

# 2. Verificar si es admin
@app.get("/admin")
def verificar_es_admin(user: Dict = Depends(get_user_from_token)):
    """Verifica si el usuario es admin, según el flujo 'admin' del diagrama"""
    return {"es_admin": user["es_admin"]}

# 3. GET VerificarStock
@app.get("/verificar-stock/{tienda_id}")
def verificar_stock(tienda_id: str, producto_id: Optional[str] = None):
    """GET VerificarStock para consultar disponibilidad"""
    if tienda_id not in STOCK:
        raise HTTPException(status_code=404, detail="Tienda no encontrada")
    
    if producto_id:
        # Verificar stock de un producto específico
        if producto_id not in STOCK[tienda_id]:
            raise HTTPException(status_code=404, detail="Producto no encontrado en esta tienda")
        
        return {
            "producto": STOCK[tienda_id][producto_id],
            "disponible": STOCK[tienda_id][producto_id]["stock"] > 0
        }
    else:
        # Retornar todo el stock de la tienda
        return STOCK[tienda_id]

# 4. GET Productos
@app.get("/productos")
def get_productos():
    """GET Productos para obtener el catálogo"""
    return PRODUCTOS

# 5. Carrito de compras
@app.post("/carrito/{tienda_id}")
def agregar_al_carrito(tienda_id: str, item: ProductoCarrito, user: Dict = Depends(get_user_from_token)):
    """Agregar producto al carrito de compras"""
    if tienda_id not in STOCK:
        raise HTTPException(status_code=404, detail="Tienda no encontrada")
    
    if item.producto_id not in STOCK[tienda_id]:
        raise HTTPException(status_code=404, detail="Producto no disponible en esta tienda")
    
    # Verificar stock
    if STOCK[tienda_id][item.producto_id]["stock"] < item.cantidad:
        raise HTTPException(status_code=400, detail="Stock insuficiente")
    
    # Validar información de delivery si se solicita
    if item.isDelivery and not item.direccion_entrega:
        raise HTTPException(status_code=400, detail="Se requiere dirección de entrega para delivery")
    
    # Crear o actualizar carrito
    carrito_id = f"cart_{user['id']}_{tienda_id}"
    
    if carrito_id not in CARRITOS:
        CARRITOS[carrito_id] = {
            "user_id": user["id"],
            "tienda_id": tienda_id,
            "items": [],
            "isDelivery": item.isDelivery,
            "direccion_entrega": item.direccion_entrega if item.isDelivery else None,
            "fecha_creacion": datetime.datetime.now().isoformat()
        }
    else:
        # Actualizar información de delivery en el carrito existente
        if item.isDelivery != CARRITOS[carrito_id].get("isDelivery", False):
            CARRITOS[carrito_id]["isDelivery"] = item.isDelivery
            CARRITOS[carrito_id]["direccion_entrega"] = item.direccion_entrega
    
    # Verificar si ya existe el producto en el carrito
    for carrito_item in CARRITOS[carrito_id]["items"]:
        if carrito_item["producto_id"] == item.producto_id:
            carrito_item["cantidad"] += item.cantidad
            return {"mensaje": "Carrito actualizado", "carrito": CARRITOS[carrito_id]}
    
    # Agregar nuevo item
    CARRITOS[carrito_id]["items"].append({
        "producto_id": item.producto_id,
        "cantidad": item.cantidad,
        "precio": STOCK[tienda_id][item.producto_id]["precio"],
        "isDelivery": item.isDelivery
    })
    
    return {"mensaje": "Producto agregado al carrito", "carrito": CARRITOS[carrito_id]}

# 6. Obtener carrito actual
@app.get("/carrito/{tienda_id}")
def obtener_carrito(tienda_id: str, user: Dict = Depends(get_user_from_token)):
    """Obtener el carrito actual del usuario para una tienda"""
    carrito_id = f"cart_{user['id']}_{tienda_id}"
    
    if carrito_id not in CARRITOS or not CARRITOS[carrito_id]["items"]:
        raise HTTPException(status_code=404, detail="Carrito vacío o no existe")
    
    # Calcular total
    total = 0
    for item in CARRITOS[carrito_id]["items"]:
        total += item["precio"] * item["cantidad"]
    
    return {"carrito": CARRITOS[carrito_id], "total": total}

# 7. Orden de Venta
@app.post("/orden-venta/{tienda_id}")
def crear_orden_venta(tienda_id: str, user: Dict = Depends(get_user_from_token)):
    """Crear una orden de venta desde el carrito"""
    carrito_id = f"cart_{user['id']}_{tienda_id}"
    
    if carrito_id not in CARRITOS or not CARRITOS[carrito_id]["items"]:
        raise HTTPException(status_code=404, detail="Carrito vacío o no existe")
    
    # Obtener información del carrito
    carrito = CARRITOS[carrito_id]
    isDelivery = carrito.get("isDelivery", False)
    direccion_entrega = carrito.get("direccion_entrega")
    
    # Si es delivery, asegurarse que hay dirección
    if isDelivery and not direccion_entrega:
        raise HTTPException(status_code=400, detail="Se requiere dirección de entrega para delivery")
    
    # Verificar stock nuevamente
    for item in carrito["items"]:
        producto_id = item["producto_id"]
        cantidad = item["cantidad"]
        
        if STOCK[tienda_id][producto_id]["stock"] < cantidad:
            raise HTTPException(status_code=400, 
                               detail=f"Stock insuficiente para {PRODUCTOS[producto_id]['nombre']}")
    
    # Calcular total
    total = 0
    items = []
    for item in carrito["items"]:
        precio = item["precio"]
        cantidad = item["cantidad"]
        total += precio * cantidad
        
        items.append({
            "producto_id": item["producto_id"],
            "nombre": PRODUCTOS[item["producto_id"]]["nombre"],
            "cantidad": cantidad,
            "precio_unitario": precio,
            "subtotal": precio * cantidad,
            "isDelivery": item.get("isDelivery", False)
        })
    
    # Añadir costo de delivery si aplica
    costo_delivery = 0
    if isDelivery:
        costo_delivery = 10.00  # Costo fijo de delivery (podría ser variable según distancia, etc.)
        total += costo_delivery
    
    # Crear orden de venta
    orden_id = str(uuid.uuid4())
    orden = {
        "orden_id": orden_id,
        "user_id": user["id"],
        "tienda_id": tienda_id,
        "tienda_recojo": tienda_id if not isDelivery else None,
        "isDelivery": isDelivery,
        "direccion_entrega": direccion_entrega if isDelivery else None,
        "costo_delivery": costo_delivery if isDelivery else 0,
        "items": items,
        "total": total,
        "estado": "pendiente",
        "fecha_creacion": datetime.datetime.now().isoformat()
    }
    
    ORDENES.append(orden)
    
    return {
        "orden_id": orden_id,
        "total": total,
        "isDelivery": isDelivery,
        "costo_delivery": costo_delivery if isDelivery else 0,
        "tienda_recojo": tienda_id if not isDelivery else None,
        "direccion_entrega": direccion_entrega if isDelivery else None,
        "mensaje": "Orden de venta creada con éxito"
    }

# 8. Sistema POS (para tienda física)
@app.post("/pos/{orden_id}")
def procesar_pos(orden_id: str, pago: PagoData, user: Dict = Depends(get_user_from_token)):
    """Procesar pago a través del Sistema POS"""
    # Buscar la orden
    orden = next((o for o in ORDENES if o["orden_id"] == orden_id), None)
    
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    # Verificar si la tienda es física
    if not orden["tienda_id"].startswith("tienda_fisica"):
        raise HTTPException(status_code=400, detail="El sistema POS solo es válido para tiendas físicas")
    
    # Verificar estado
    if orden["estado"] != "pendiente":
        raise HTTPException(status_code=400, detail="La orden ya ha sido procesada")
    
    # Verificar monto
    if pago.monto < orden["total"]:
        raise HTTPException(status_code=400, detail="Monto insuficiente")
    
    # Procesar pago
    orden["estado"] = "pagada"
    orden["metodo_pago"] = "pos"
    orden["detalles_pago"] = {
        "metodo": pago.metodo,
        "monto": pago.monto,
        "cambio": pago.monto - orden["total"],
        "fecha_pago": datetime.datetime.now().isoformat()
    }
    
    return {
        "orden_id": orden_id,
        "estado": "pagada",
        "cambio": pago.monto - orden["total"],
        "mensaje": "Pago procesado correctamente por POS"
    }

# 9. Pasarela de Pagos (para tienda virtual)
@app.post("/pasarela-pagos/{orden_id}")
def procesar_pasarela(orden_id: str, pago: PagoData, user: Dict = Depends(get_user_from_token)):
    """Procesar pago a través de la Pasarela de Pagos"""
    # Buscar la orden
    orden = None
    for o in ORDENES:
        if o["orden_id"] == orden_id:
            orden = o
            break
    
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    # Verificar si la tienda es virtual
    if not orden["tienda_id"].startswith("tienda_virtual"):
        raise HTTPException(status_code=400, detail="La pasarela de pagos solo es válida para tiendas virtuales")
    
    # Verificar estado
    if orden["estado"] != "pendiente":
        raise HTTPException(status_code=400, detail="La orden ya ha sido procesada")
    
    # Verificar detalles para pasarela
    if not pago.detalles or "tarjeta" not in pago.detalles:
        raise HTTPException(status_code=400, detail="Detalles de tarjeta requeridos para pasarela")
    
    # Simular procesamiento de pasarela
    # En un sistema real, aquí se conectaría con un gateway de pago
    
    # Procesar pago
    orden["estado"] = "pagada"
    orden["metodo_pago"] = "pasarela"
    orden["detalles_pago"] = {
        "metodo": pago.metodo,
        "referencia": f"REF-{uuid.uuid4().hex[:8]}",
        "fecha_pago": datetime.datetime.now().isoformat()
    }
    
    return {
        "orden_id": orden_id,
        "estado": "pagada",
        "referencia": orden["detalles_pago"]["referencia"],
        "mensaje": "Pago procesado correctamente por pasarela"
    }

# 10. POST ActualizarStock (con rollback si es necesario)
@app.post("/actualizar-stock/{orden_id}")
def actualizar_stock(orden_id: str, user: Dict = Depends(get_user_from_token)):
    """POST ActualizarStock para actualizar inventario"""
    # Buscar la orden
    orden = None
    for o in ORDENES:
        if o["orden_id"] == orden_id:
            orden = o
            break
    
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    # Verificar estado
    if orden["estado"] != "pagada":
        raise HTTPException(status_code=400, detail="La orden debe estar pagada para actualizar stock")
    
    tienda_id = orden["tienda_id"]
    
    # Actualizar stock
    try:
        for item in orden["items"]:
            producto_id = item["producto_id"]
            cantidad = item["cantidad"]
            
            if STOCK[tienda_id][producto_id]["stock"] < cantidad:
                # Rollback - en caso de error
                raise HTTPException(status_code=400, detail=f"Stock insuficiente para {item['nombre']}")
            
            STOCK[tienda_id][producto_id]["stock"] -= cantidad
        
        # Marcar como stock actualizado
        orden["stock_actualizado"] = True
        
        return {
            "orden_id": orden_id,
            "mensaje": "Stock actualizado correctamente",
            "stock_actualizado": True
        }
    except Exception as e:
        # En caso de error, implementar rollback si es necesario
        orden["rollback"] = True
        return {
            "orden_id": orden_id,
            "mensaje": f"Error al actualizar stock: {str(e)}",
            "stock_actualizado": False
        }

# 11. Pago Online
@app.post("/pago-online/{orden_id}")
def procesar_pago_online(orden_id: str, pago: PagoData, user: Dict = Depends(get_user_from_token)):
    """Procesar pago online para una orden"""
    # Buscar la orden
    orden = next((orden for orden in ORDENES if orden["orden_id"] == orden_id), None)
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    # Verificar que el pago sea del monto correcto
    if pago.monto != orden["total"]:
        raise HTTPException(status_code=400, detail="Monto de pago incorrecto")
    
    # Simular procesamiento de pago
    transaccion_id = str(uuid.uuid4())
    
    # Actualizar estado de la orden
    orden["estado"] = "pagada"
    orden["pago"] = {
        "transaccion_id": transaccion_id,
        "metodo": pago.metodo,
        "monto": pago.monto,
        "fecha": datetime.datetime.now().isoformat()
    }
    
    return {
        "mensaje": "Pago procesado correctamente",
        "transaccion_id": transaccion_id,
        "estado": orden["estado"]
    }

# 12. Asignar Delivery
@app.post("/asignar-delivery/{orden_id}")
def asignar_delivery(orden_id: str, user: Dict = Depends(verificar_admin)):
    """Asignar un repartidor a una orden de delivery"""
    # Buscar la orden
    orden = next((orden for orden in ORDENES if orden["orden_id"] == orden_id), None)
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    # Verificar que la orden sea de delivery
    if not orden.get("isDelivery"):
        raise HTTPException(status_code=400, detail="Esta orden no es de delivery")
    
    # Verificar que la orden esté pagada
    if orden["estado"] != "pagada":
        raise HTTPException(status_code=400, detail="La orden debe estar pagada para asignar delivery")
    
    # Simular asignación de repartidor
    repartidor = {
        "id": "REP001",
        "nombre": "Juan Delivery",
        "vehiculo": "Moto",
        "telefono": "999-888-777"
    }
    
    tiempo_estimado = 30  # minutos
    
    # Actualizar orden con información de delivery
    orden["delivery"] = {
        "repartidor": repartidor,
        "tiempo_estimado": tiempo_estimado,
        "estado": "en_camino",
        "fecha_asignacion": datetime.datetime.now().isoformat()
    }
    orden["estado"] = "en_delivery"
    
    return {
        "mensaje": "Delivery asignado correctamente",
        "repartidor": repartidor["nombre"],
        "tiempo_estimado": tiempo_estimado
    }

# 13. Realizar Venta
@app.post("/realizar-venta/{orden_id}")
def realizar_venta(orden_id: str, user: Dict = Depends(get_user_from_token)):
    """Realizar la venta final"""
    # Buscar la orden
    orden = next((orden for orden in ORDENES if orden["orden_id"] == orden_id), None)
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    # Verificar estado de la orden
    if orden["estado"] not in ["pagada", "en_delivery"]:
        raise HTTPException(status_code=400, detail="La orden debe estar pagada o en delivery para realizar la venta")
    
    # Actualizar stock
    tienda_id = orden["tienda_id"]
    for item in orden["items"]:
        producto_id = item["producto_id"]
        cantidad = item["cantidad"]
        STOCK[tienda_id][producto_id]["stock"] -= cantidad
    
    # Crear registro de venta
    venta_id = str(uuid.uuid4())
    venta = {
        "venta_id": venta_id,
        "orden_id": orden_id,
        "user_id": user["id"],
        "tienda_id": tienda_id,
        "items": orden["items"],
        "total": orden["total"],
        "isDelivery": orden.get("isDelivery", False),
        "estado": "completada",
        "fecha_venta": datetime.datetime.now().isoformat()
    }
    
    VENTAS.append(venta)
    orden["estado"] = "vendida"
    
    return {
        "venta_id": venta_id,
        "mensaje": "Venta realizada con éxito"
    }

# 14. Generar Factura
@app.post("/factura/{venta_id}")
def generar_factura(venta_id: str, user: Dict = Depends(get_user_from_token)):
    """Generar factura para una venta completada"""
    # Buscar la venta
    venta = None
    for v in VENTAS:
        if v["id"] == venta_id:
            venta = v
            break
    
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    
    # Verificar estado
    if venta["estado"] != "completada":
        raise HTTPException(status_code=400, detail="La venta debe estar completada para generar factura")
    
    # Generar número de factura
    factura_numero = f"F-{uuid.uuid4().hex[:8]}"
    
    # Obtener información de delivery
    isDelivery = venta.get("isDelivery", False)
    direccion_entrega = venta.get("direccion_entrega", None)
    costo_delivery = venta.get("costo_delivery", 0)
    tienda_recojo = venta.get("tienda_recojo", venta["tienda_id"])
    
    # Crear factura
    factura = {
        "tipo": "factura",
        "numero": factura_numero,
        "venta_id": venta_id,
        "cliente": USUARIOS[venta["user_id"]]["nombre"],
        "items": venta["items"],
        "isDelivery": isDelivery,
        "tienda_recojo": tienda_recojo if not isDelivery else None,
        "direccion_entrega": direccion_entrega if isDelivery else None,
        "costo_delivery": costo_delivery,
        "subtotal": round((venta["total"] - costo_delivery) / 1.18, 2),
        "igv": round((venta["total"] - costo_delivery) * 0.18, 2),
        "total": venta["total"],
        "fecha_emision": datetime.datetime.now().isoformat()
    }
    
    # Actualizar la venta con la referencia a la factura
    venta["factura"] = factura_numero
    
    return factura

# 15. Generar Boleta
@app.post("/boleta/{venta_id}")
def generar_boleta(venta_id: str, user: Dict = Depends(get_user_from_token)):
    """Generar una boleta para una venta"""
    # Buscar la venta
    venta = next((v for v in VENTAS if v["venta_id"] == venta_id), None)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    
    # Generar boleta
    boleta = {
        "boleta_id": str(uuid.uuid4()),
        "venta_id": venta_id,
        "fecha_emision": datetime.datetime.now().isoformat(),
        "cliente": {
            "id": user["id"],
            "nombre": user["nombre"]
        },
        "items": venta["items"],
        "total": venta["total"],
        "isDelivery": venta.get("isDelivery", False)
    }
    
    return {
        "mensaje": "Boleta generada correctamente",
        "boleta": boleta
    }

# 16. Registrar Venta en BD
@app.post("/registrar-venta/{venta_id}")
def registrar_venta(venta_id: str, admin: Dict = Depends(verificar_admin)):
    """Registrar la venta en la base de datos (solo admin)"""
    # Buscar la venta
    venta = None
    for v in VENTAS:
        if v["id"] == venta_id:
            venta = v
            break
    
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    
    # Verificar que tenga factura o boleta
    if not venta.get("factura") and not venta.get("boleta"):
        raise HTTPException(status_code=400, detail="La venta debe tener factura o boleta para ser registrada")
    
    # Simular registro en BD
    # En un sistema real, aquí se guardaría en una base de datos persistente
    
    venta["registrada_bd"] = True
    venta["fecha_registro"] = datetime.datetime.now().isoformat()
    
    return {
        "venta_id": venta_id,
        "mensaje": "Venta registrada correctamente en la base de datos",
        "fecha_registro": venta["fecha_registro"]
    }

# Confirmar Entrega
@app.post("/confirmar-entrega/{orden_id}")
def confirmar_entrega(orden_id: str, user: Dict = Depends(verificar_admin)):
    """Confirmar la entrega de un pedido"""
    # Buscar la orden
    orden = next((orden for orden in ORDENES if orden["orden_id"] == orden_id), None)
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    # Verificar que la orden sea de delivery
    if not orden.get("isDelivery"):
        raise HTTPException(status_code=400, detail="Esta orden no es de delivery")
    
    # Verificar que tenga delivery asignado
    if not orden.get("delivery"):
        raise HTTPException(status_code=400, detail="La orden no tiene delivery asignado")
    
    # Verificar que esté en estado correcto
    if orden["estado"] != "vendida":
        raise HTTPException(status_code=400, detail="La orden debe estar vendida para confirmar entrega")
    
    # Actualizar estado de la orden y del delivery
    orden["estado"] = "entregado"
    orden["delivery"]["estado"] = "entregado"
    orden["delivery"]["fecha_entrega"] = datetime.datetime.now().isoformat()
    
    return {
        "mensaje": "Entrega confirmada correctamente",
        "fecha_entrega": orden["delivery"]["fecha_entrega"]
    }

# Iniciar la aplicación si se ejecuta directamente
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)