## Freym Boost Masivo de Freym PC
Script para extraer los totales de un masivo de facturas. 

Versión -all para extraer el proveedor con el input cliente.

sumatorio.py para obtener el total de una columna.

## Dependencias
Installar Python 3

pip install PyMuPDF pandas

## Ejecución
En ruta de facturas:

python extractor.py . -o salida.csv

python extractor-all.py .

python sumatorio.py salida.csv n

n - Indice de celda
--debug (option)

## Fuente
Desarrollado mediante perplexity.ai

