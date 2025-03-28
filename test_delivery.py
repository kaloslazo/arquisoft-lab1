# test_delivery.py - Script para probar el flujo de delivery según el diagrama simplificado
import requests
import json
import time

# URL base de la API
BASE_URL = "http://localhost:8000"

def test_flujo_delivery():
    """Prueba el flujo de venta para delivery según el diagrama"""
    print("\n" + "="*70)
    print("PRUEBA DE FLUJO: DELIVERY - MIFARMA")
    print("="*70)
    
    tienda_id = "tienda_virtual_1"  # Usamos la tienda virtual para delivery
    
    # Paso 1: Login como administrador para verificar stock
    print("\n➡️ PASO 1: Login como administrador")
    login_data = {
        "username": "admin1",
        "password": "admin123"
    }
    
    response = requests.post(f"{BASE_URL}/login", json=login_data)
    if response.status_code != 200:
        print(f"❌ Error en login: {response.text}")
        return
    
    admin_token = response.json()["token"]
    admin_headers = {"token": admin_token}
    
    print("✅ Login exitoso como administrador")
    
    # Paso 2: Verificar stock (GET VerificarStock)
    print("\n➡️ PASO 2: Verificar stock (GET VerificarStock)")
    response = requests.get(f"{BASE_URL}/verificar-stock/{tienda_id}", headers=admin_headers)
    if response.status_code != 200:
        print(f"❌ Error al verificar stock: {response.text}")
        return
    
    stock_tienda = response.json()
    print(f"✅ Stock verificado. Ejemplos de productos disponibles:")
    for producto_id, info in list(stock_tienda.items())[:2]:
        print(f"   📦 {info['nombre']} - Stock: {info['stock']} - Precio: S/{info['precio']}")
    
    # Paso 3: Login como cliente normal
    print("\n➡️ PASO 3: Login como cliente normal para realizar compra")
    login_data = {
        "username": "user1",
        "password": "password123"
    }
    
    response = requests.post(f"{BASE_URL}/login", json=login_data)
    if response.status_code != 200:
        print(f"❌ Error en login: {response.text}")
        return
    
    user_token = response.json()["token"]
    user_headers = {"token": user_token}
    
    print("✅ Login exitoso como cliente")
    
    # Paso 4: Agregar al carrito (Carrito de compras)
    print("\n➡️ PASO 4: Agregar producto al carrito (Carrito de compras)")
    carrito_item = {
        "producto_id": "producto_001",  # Paracetamol
        "cantidad": 2,
        "isDelivery": True,  # Activamos delivery
        "direccion_entrega": "Av. Principal 123, Lima"
    }
    
    response = requests.post(
        f"{BASE_URL}/carrito/{tienda_id}", 
        json=carrito_item,
        headers=user_headers
    )
    if response.status_code != 200:
        print(f"❌ Error al agregar al carrito: {response.text}")
        return
    
    print(f"✅ Producto agregado al carrito: {carrito_item['cantidad']} unidades de Paracetamol")
    print(f"✅ Dirección de entrega: {carrito_item['direccion_entrega']}")
    
    # Paso 5: Crear Orden de Venta con Delivery
    print("\n➡️ PASO 5: Crear Orden de Venta con Delivery")
    response = requests.post(
        f"{BASE_URL}/orden-venta/{tienda_id}", 
        headers=user_headers
    )
    if response.status_code != 200:
        print(f"❌ Error al crear orden: {response.text}")
        return
    
    orden_result = response.json()
    orden_id = orden_result["orden_id"]
    
    print(f"✅ Orden de venta creada con ID: {orden_id}")
    print(f"✅ Total a pagar (incluye delivery): S/{orden_result['total']}")
    
    # Paso 6: Procesar pago online
    print("\n➡️ PASO 6: Procesar pago online")
    pago_data = {
        "metodo": "tarjeta",
        "monto": orden_result["total"],
        "detalles": {
            "numero_tarjeta": "**** **** **** 4242",
            "fecha_vencimiento": "12/25",
            "cvv": "***"
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/pago-online/{orden_id}", 
        json=pago_data,
        headers=user_headers
    )
    if response.status_code != 200:
        print(f"❌ Error al procesar pago: {response.text}")
        return
    
    pago_result = response.json()
    print(f"✅ Pago procesado correctamente")
    print(f"✅ ID de transacción: {pago_result.get('transaccion_id', 'N/A')}")
    
    # Paso 7: Asignar Delivery
    print("\n➡️ PASO 7: Asignar Delivery")
    response = requests.post(
        f"{BASE_URL}/asignar-delivery/{orden_id}",
        headers=admin_headers
    )
    if response.status_code != 200:
        print(f"❌ Error al asignar delivery: {response.text}")
        return
    
    delivery_info = response.json()
    print(f"✅ Delivery asignado")
    print(f"✅ Repartidor: {delivery_info.get('repartidor', 'N/A')}")
    print(f"✅ Tiempo estimado: {delivery_info.get('tiempo_estimado', 'N/A')} minutos")
    
    # Paso 8: Realizar Venta
    print("\n➡️ PASO 8: Realizar Venta (RealizarVenta)")
    response = requests.post(
        f"{BASE_URL}/realizar-venta/{orden_id}", 
        headers=user_headers
    )
    if response.status_code != 200:
        print(f"❌ Error al realizar venta: {response.text}")
        return
    
    venta_result = response.json()
    venta_id = venta_result["venta_id"]
    
    print(f"✅ Venta realizada con éxito. ID de venta: {venta_id}")
    
    # Paso 9: Generar Boleta
    print("\n➡️ PASO 9: Generar Boleta")
    response = requests.post(
        f"{BASE_URL}/boleta/{venta_id}", 
        headers=user_headers
    )
    if response.status_code != 200:
        print(f"❌ Error al generar boleta: {response.text}")
        return
    
    print("✅ Boleta generada correctamente")
    
    # Paso 10: Confirmar entrega
    print("\n➡️ PASO 10: Confirmar entrega")
    response = requests.post(
        f"{BASE_URL}/confirmar-entrega/{orden_id}",
        headers=admin_headers
    )
    if response.status_code != 200:
        print(f"❌ Error al confirmar entrega: {response.text}")
        return
    
    print("✅ Entrega confirmada")
    print("\n" + "="*70)
    print("✅ PRUEBA DE DELIVERY COMPLETADA CON ÉXITO")
    print("="*70)

if __name__ == "__main__":
    test_flujo_delivery()