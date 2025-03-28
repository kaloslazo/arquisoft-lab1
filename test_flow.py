# test_flow.py - Script para probar el flujo de venta según el diagrama simplificado
import requests
import json
import time

# URL base de la API
BASE_URL = "http://localhost:8000"

def test_flujo_tienda_fisica():
    """Prueba el flujo de venta para tienda física según el diagrama"""
    print("\n" + "="*70)
    print("PRUEBA DE FLUJO: TIENDA FÍSICA - MIFARMA")
    print("="*70)
    
    tienda_id = "tienda_fisica_1"
    
    # Paso 1: Login como administrador
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
    
    # Paso 2: Verificar que es admin (nodo "admin" del diagrama)
    print("\n➡️ PASO 2: Verificar si es admin (condición 'admin' del diagrama)")
    response = requests.get(f"{BASE_URL}/admin", headers=admin_headers)
    if response.status_code != 200:
        print(f"❌ Error al verificar admin: {response.text}")
        return
    
    es_admin = response.json()["es_admin"]
    if not es_admin:
        print("❌ El usuario no es administrador")
        return
    
    print("✅ Verificado que el usuario es administrador")
    
    # Paso 3: Verificar stock (GET VerificarStock)
    print("\n➡️ PASO 3: Verificar stock (GET VerificarStock)")
    response = requests.get(f"{BASE_URL}/verificar-stock/{tienda_id}", headers=admin_headers)
    if response.status_code != 200:
        print(f"❌ Error al verificar stock: {response.text}")
        return
    
    stock_tienda = response.json()
    print(f"✅ Stock verificado. Ejemplos de productos disponibles:")
    for producto_id, info in list(stock_tienda.items())[:2]:
        print(f"   📦 {info['nombre']} - Stock: {info['stock']} - Precio: S/{info['precio']}")
    
    # Paso 4: Login como cliente normal
    print("\n➡️ PASO 4: Login como cliente normal para realizar compra")
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
    
    # Paso 5: Agregar al carrito (Carrito de compras)
    print("\n➡️ PASO 5: Agregar producto al carrito (Carrito de compras)")
    carrito_item = {
        "producto_id": "producto_001",  # Paracetamol
        "cantidad": 3,
        "isDelivery": False  # Recoger en tienda
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
    
    # Paso 6: Crear Orden de Venta
    print("\n➡️ PASO 6: Crear Orden de Venta")
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
    print(f"✅ Total a pagar: S/{orden_result['total']}")
    
    # Paso 7: Procesar pago por Sistema POS
    print("\n➡️ PASO 7: Procesar pago por Sistema POS")
    pago_data = {
        "metodo": "efectivo",
        "monto": orden_result["total"] + 10,  # Pago con efectivo extra para recibir cambio
        "detalles": {}
    }
    
    response = requests.post(
        f"{BASE_URL}/pos/{orden_id}", 
        json=pago_data,
        headers=user_headers
    )
    if response.status_code != 200:
        print(f"❌ Error al procesar pago: {response.text}")
        return
    
    pago_result = response.json()
    print(f"✅ Pago procesado correctamente mediante POS")
    print(f"✅ Cambio: S/{pago_result['cambio']}")
    
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
    print("\n" + "="*70)
    print("✅ PRUEBA COMPLETADA CON ÉXITO")
    print("="*70)

if __name__ == "__main__":
    test_flujo_tienda_fisica()