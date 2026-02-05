#!/usr/bin/env python3
"""
Extractor v5.0 - GENÉRICO para DIGI/GOOGLE/IONOS y otros
Maneja paréntesis, EUR dispersos, espaciado irregular
"""

import argparse
import re
import pandas as pd
from pathlib import Path
import sys
from typing import Dict, Optional
from datetime import datetime

try:
    import fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

def extraer_texto_completo(pdf_path: Path) -> str:
    """Extracción robusta"""
    if not PYMUPDF_AVAILABLE: return ""
    try:
        doc = fitz.open(pdf_path)
        texto = ""
        for page in doc:
            texto += page.get_text() + "\n"
        doc.close()
        return texto
    except:
        return ""

def normalizar_numero(numero: str) -> str:
    return re.sub(r'[^\w\-]', '', str(numero).strip()) if numero else ""

def normalizar_fecha(fecha: str) -> str:
    if not fecha: return ""
    fecha = re.sub(r'[^\d/.-]', '', fecha)[:10]
    return fecha

def normalizar_importe(importe: str) -> Optional[float]:
    """Maneja 1,00€ 6,21 EUR 9.03€"""
    if not importe: return None
    # Quita EUR, €, espacios
    importe = re.sub(r'[€EUR\s€]', '', str(importe).strip())
    importe = re.sub(r'[^\d.,]', '', importe.replace(',', '.'))
    try: 
        return float(importe)
    except: 
        return None

def extraer_importes_universal(texto: str) -> Dict[str, Optional[float]]:
    """Patrones UNIVERSALES para TODOS los proveedores"""
    
    # Zona resumen amplia
    zona_resumen = texto[-3000:]
    
    # 1. TODOS los importes posibles
    todos_importes = re.findall(r'[\d.,]{3,}(?:[.,]\d{2})?', zona_resumen)
    importes_normalizados = [normalizar_importe(x) for x in todos_importes if normalizar_importe(x)]
    
    # 2. Patrones específicios MEJORADOS
    patrones_universal = [
        # TOTALES (máxima prioridad)
        (r'(?:Total\s*(?:factura|a pagar|final|en EUR)?|TOTAL|Importe total)\s*[:\-\(\)]*\s*([\d.,]+)', 'total'),
        (r'TOTAL\s*[:\-\(\)]*\s*([\d.,]+)', 'total'),
        
        # BASE IMPONIBLE
        (r'(?:Base\s*(?:imponible|imp\.?)|Subtotal|Neto?|IMPORTE\s*\(base imponible\))\s*[:\-\(\)]*\s*([\d.,]+)', 'base_imponible'),
        (r'base imponible\).*?([\d.,]+)', 'base_imponible'),
        
        # IVA
        (r'(?:IVA?|I\.V\.A\.?|IMPUESTOS\s*\(21|Impuesto|Cuota IVA)\s*[:\-\(\)]*\s*([\d.,]+)', 'iva'),
        (r'\(21(?:\.00)?%?\s*IVA?\).*?([\d.,]+)', 'iva'),
        (r'I\.V\.A\..*?([\d.,]+)', 'iva'),
    ]
    
    resultado = {'total': None, 'base_imponible': None, 'iva': None}
    
    # Buscar por patrón específico
    for patron, campo in patrones_universal:
        match = re.search(patron, zona_resumen, re.IGNORECASE | re.DOTALL)
        if match and not resultado[campo]:
            valor = normalizar_importe(match.group(1))
            if valor:
                resultado[campo] = valor
    
    # Fallback: coherencia matemática si falta algún campo
    if resultado['total'] and not resultado['base_imponible']:
        for imp in importes_normalizados:
            if 0.7 * resultado['total'] <= imp <= 0.95 * resultado['total']:
                resultado['base_imponible'] = imp
                break
    
    return resultado

def extraer_datos_factura_completo(texto: str, nombre_fichero: str) -> Dict:
    datos = {
        'numero_factura': '', 'fecha_factura': '', 'proveedor': '', 'cliente': '',
        'base_imponible': None, 'iva': None, 'total': None, 'nombre_fichero': nombre_fichero
    }
    
    # NÚMERO FACTURA (múltiples formatos)
    numero_match = (re.search(r'N(?:\.°|º)?\s*de?\s*factura\s*[:\-]?\s*(\w+)', texto) or 
                    re.search(r'Número\s*[:\-]?\s*(\w+)', texto) or
                    re.search(r'Factura[:\-]?\s*(\w+)', texto))
    datos['numero_factura'] = normalizar_numero(numero_match.group(1)) if numero_match else nombre_fichero.replace('.pdf', '')
    
    # FECHA
    fecha_match = re.search(r'Fecha\s+de?\s*(?:factura|facturación|emisión)\s*[:\-]?\s*([\d/\.-]{8,10})', texto)
    datos['fecha_factura'] = normalizar_fecha(fecha_match.group(1)) if fecha_match else ""
    
    # IMPORTES UNIVERSALES
    importes = extraer_importes_universal(texto)
    datos.update(importes)
    
    # PROVEEDOR NIF
    nif_match = re.search(r'(?:CIF|NIF|IVA:\s*)([A-Z]\d{8}[A-Z]?)', texto, re.IGNORECASE)
    datos['proveedor'] = nif_match.group(1)[:50] if nif_match else ""
    
    return datos

def main():
    parser = argparse.ArgumentParser(description='Extractor v5.0 UNIVERSAL')
    parser.add_argument('carpeta_pdf', help='Carpeta PDFs')
    parser.add_argument('-o', '--output', help='CSV salida')
    args = parser.parse_args()
    
    carpeta = Path(args.carpeta_pdf)
    print("🚀 Extractor v5.0 - UNIVERSAL (DIGI/GOOGLE/IONOS)")
    
    filas, procesados = [], 0
    for pdf_path in carpeta.glob("*.pdf"):
        print(f"  📄 {pdf_path.name}", end=" ")
        procesados += 1
        
        texto = extraer_texto_completo(pdf_path)
        if not texto.strip():
            print("❌")
            continue
        print("✅")
        
        datos = extraer_datos_factura_completo(texto, pdf_path.name)
        filas.append(datos)
    
    if not filas:
        print("❌ No PDFs válidos")
        return 1
    
    df = pd.DataFrame(filas)
    columnas = ['numero_factura', 'fecha_factura', 'proveedor', 'cliente', 
                'base_imponible', 'iva', 'total', 'nombre_fichero']
    df = df[columnas]
    
    # NOMBRE AUTOMÁTICO
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = args.output or f"facturas_universal_{timestamp}.csv"
    df.to_csv(output, index=False, encoding='utf-8-sig')
    
    print(f"\n🎉 {len(filas)}/{procesados} procesados → {output}")
    con_total = df['total'].notna().sum()
    print(f"📊 Totales detectados: {con_total}/{len(df)} ({con_total/len(df)*100:.1f}%)")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
