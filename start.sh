#!/bin/bash
# Script de inicialização do Sistema de Propostas

echo "========================================="
echo "Sistema de Propostas Comerciais"
echo "========================================="
echo ""
echo "Verificando dependências..."

# Verificar se as dependências estão instaladas
if ! python3.11 -c "import flask" 2>/dev/null; then
    echo "Instalando dependências..."
    pip3 install -r requirements.txt
fi

echo ""
echo "Iniciando servidor Flask..."
echo ""
echo "Acesse o sistema em: http://localhost:5000"
echo ""
echo "Pressione Ctrl+C para parar o servidor"
echo ""

python3.11 app.py
