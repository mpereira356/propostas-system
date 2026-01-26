# 🚀 Guia Rápido - Sistema de Propostas

## Instalação e Execução

### 1. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 2. Executar o Sistema

```bash
python app.py
```

### 3. Acessar no Navegador

```
http://localhost:5000
```

## Como Usar

### 📤 Importar Proposta

1. Acesse a página inicial ou clique em **"Importar PDF"**
2. Clique em **"Choose File"** e selecione o PDF
3. Clique em **"Importar Proposta"**
4. Aguarde o processamento (alguns segundos)
5. Você será redirecionado para a página de detalhes

### 📋 Ver Todas as Propostas

1. Clique em **"Listagem"** no menu
2. Visualize todas as propostas em formato de tabela
3. Use os filtros para buscar propostas específicas

### 🔍 Filtrar Propostas

Na página de listagem, você pode filtrar por:

- **Razão Social**: Digite parte do nome da empresa
- **CNPJ**: Digite parte ou completo do CNPJ
- **ID da Proposta**: Digite o código da proposta (ex: BA.0012/2025)

Clique em **"Filtrar"** para aplicar.

Para limpar os filtros, clique em **"Limpar Filtros"**.

### 👁️ Ver Detalhes

1. Na listagem, clique no botão **azul com ícone de olho**
2. Visualize todos os dados organizados:
   - Informações Gerais
   - Dados do Cliente
   - Tabela de Itens com valores

### 🗑️ Deletar Proposta

1. Na listagem ou página de detalhes, clique no botão **vermelho com ícone de lixeira**
2. Confirme a exclusão no modal
3. A proposta será removida permanentemente

## ⚠️ Importante

- **Formato do PDF**: O sistema foi desenvolvido para PDFs de propostas no mesmo formato do exemplo fornecido
- **Duplicidade**: O sistema não permite importar a mesma proposta duas vezes (verifica pelo ID da Proposta)
- **Tamanho**: Limite de 16MB por arquivo
- **Tipo**: Apenas arquivos PDF são aceitos

## 📊 Dados Extraídos

O sistema extrai automaticamente:

✅ ID da Proposta  
✅ Data de Emissão  
✅ Validade  
✅ Razão Social  
✅ Nome Fantasia  
✅ CNPJ  
✅ Telefone  
✅ Celular  
✅ E-mail  
✅ Pessoa de Contato  
✅ Itens (descrição, quantidade, valores)  
✅ Valor Total  

## 🔧 Configurações

### Alterar Porta

Edite `app.py` na última linha:

```python
app.run(debug=True, host='0.0.0.0', port=8000)  # Mude 5000 para 8000
```

### Usar MySQL

1. Instale o driver:
```bash
pip install pymysql
```

2. Edite `app.py`:
```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://usuario:senha@localhost/banco'
```

## 📞 Suporte

Para problemas ou dúvidas:

1. Verifique se todas as dependências foram instaladas
2. Verifique se o PDF está no formato correto
3. Consulte o arquivo `README.md` para mais detalhes
4. Verifique os logs no terminal para mensagens de erro

## 🎯 Dicas

- **Importe diariamente**: Use o botão "Importar PDF" sempre que receber novas propostas
- **Use os filtros**: Encontre rapidamente propostas por CNPJ ou razão social
- **Backup**: Faça backup regular do arquivo `instance/database.db`
- **Organização**: O sistema mantém histórico de todas as importações com data e hora

---

**Versão**: 1.0.0  
**Desenvolvido com**: Python + Flask + Bootstrap
