# Sistema de Gerenciamento de Propostas Comerciais

Sistema web completo desenvolvido em Python com Flask para importar, processar e gerenciar propostas comerciais em formato PDF.

## 📋 Funcionalidades

- ✅ **Upload de PDF**: Interface intuitiva para importar propostas comerciais
- ✅ **Extração Automática**: Leitura e extração automática de dados do PDF usando regex
- ✅ **Banco de Dados**: Armazenamento em SQLite com SQLAlchemy
- ✅ **Listagem com Filtros**: Busca por Razão Social, CNPJ ou ID da Proposta
- ✅ **Detalhes Completos**: Visualização organizada de todos os dados extraídos
- ✅ **Prevenção de Duplicidade**: Sistema não permite importar a mesma proposta duas vezes
- ✅ **Interface Moderna**: Design responsivo com Bootstrap 5
- ✅ **API REST**: Endpoints JSON para integração

## 🗂️ Estrutura do Projeto

```
proposta_system/
├── app.py                  # Aplicação Flask principal
├── models.py               # Modelos do banco de dados (SQLAlchemy)
├── pdf_reader.py           # Módulo de extração de dados do PDF
├── requirements.txt        # Dependências do projeto
├── README.md              # Este arquivo
├── database.db            # Banco de dados SQLite (criado automaticamente)
├── templates/             # Templates HTML
│   ├── base.html          # Template base
│   ├── upload.html        # Página de upload
│   ├── listagem.html      # Página de listagem
│   └── detalhes.html      # Página de detalhes
├── static/                # Arquivos estáticos (CSS, JS, imagens)
│   └── css/
└── uploads/               # Diretório para PDFs importados
```

## 📊 Campos Extraídos do PDF

O sistema extrai automaticamente os seguintes campos:

### Dados da Proposta
- ID da Proposta
- Data de Emissão
- Validade
- Valor Total

### Dados do Cliente
- Razão Social
- Nome Fantasia
- CNPJ
- Telefone
- Celular
- E-mail
- Pessoa de Contato

### Itens da Proposta
- Número do Item
- Descrição
- Quantidade
- Valor Unitário
- Valor Total

## 🚀 Como Rodar o Sistema

### Pré-requisitos

- Python 3.11 ou superior
- pip (gerenciador de pacotes Python)

### Instalação

1. **Clone ou baixe o projeto**

```bash
cd proposta_system
```

2. **Instale as dependências**

```bash
pip install -r requirements.txt
```

Ou, se preferir usar pip3:

```bash
pip3 install -r requirements.txt
```

3. **Execute a aplicação**

```bash
python app.py
```

Ou:

```bash
python3 app.py
```

4. **Acesse o sistema**

Abra seu navegador e acesse:

```
http://localhost:5000
```

## 📝 Como Usar

### 1. Importar Proposta

1. Clique em **"Importar PDF"** no menu
2. Selecione o arquivo PDF da proposta comercial
3. Clique em **"Importar Proposta"**
4. O sistema irá:
   - Extrair todos os dados automaticamente
   - Salvar no banco de dados
   - Redirecionar para a página de detalhes

### 2. Listar Propostas

1. Clique em **"Listagem"** no menu
2. Visualize todas as propostas importadas
3. Use os filtros para buscar:
   - Por Razão Social
   - Por CNPJ
   - Por ID da Proposta
4. Clique em **"Ver Detalhes"** para visualizar uma proposta específica

### 3. Ver Detalhes

- Visualize todos os dados extraídos organizados em cards
- Veja a tabela completa de itens com valores
- Opção para deletar a proposta

### 4. Deletar Proposta

- Na listagem ou página de detalhes, clique no botão **"Deletar"**
- Confirme a exclusão no modal
- A proposta e seus itens serão removidos do banco de dados

## 🔧 Configurações

### Banco de Dados

Por padrão, o sistema usa SQLite (`database.db`). Para usar MySQL:

1. Instale o driver MySQL:

```bash
pip install pymysql
```

2. Altere a configuração em `app.py`:

```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://usuario:senha@localhost/nome_banco'
```

### Tamanho Máximo de Upload

Por padrão, o limite é 16MB. Para alterar, edite em `app.py`:

```python
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB
```

### Chave Secreta

⚠️ **IMPORTANTE**: Antes de usar em produção, altere a chave secreta em `app.py`:

```python
app.config['SECRET_KEY'] = 'sua-chave-secreta-super-segura-aqui'
```

## 🌐 API REST

O sistema oferece endpoints JSON para integração:

### Listar todas as propostas

```
GET /api/propostas
```

Retorna array JSON com todas as propostas.

### Obter detalhes de uma proposta

```
GET /api/proposta/<id>
```

Retorna JSON com dados completos da proposta, incluindo itens.

## 🛠️ Tecnologias Utilizadas

- **Backend**: Python 3.11, Flask 3.0
- **Banco de Dados**: SQLite com SQLAlchemy
- **Extração de PDF**: pdfplumber
- **Frontend**: HTML5, Bootstrap 5, Bootstrap Icons
- **Segurança**: Werkzeug para upload seguro de arquivos

## 📦 Dependências

- `Flask==3.0.0` - Framework web
- `Flask-SQLAlchemy==3.1.1` - ORM para banco de dados
- `pdfplumber==0.11.9` - Extração de texto de PDFs
- `Werkzeug==3.0.1` - Utilitários WSGI

## 🔒 Segurança

- Upload apenas de arquivos PDF
- Nomes de arquivo sanitizados (secure_filename)
- Prevenção de duplicidade por ID da proposta
- Validação de campos no backend

## 🐛 Solução de Problemas

### Erro ao instalar dependências

```bash
# Tente atualizar o pip
pip install --upgrade pip

# Ou use pip3
pip3 install -r requirements.txt
```

### Porta 5000 já está em uso

Altere a porta em `app.py`:

```python
app.run(debug=True, host='0.0.0.0', port=8000)
```

### Erro ao extrair dados do PDF

- Verifique se o PDF está no formato correto (mesmo layout da proposta exemplo)
- Verifique se o arquivo não está corrompido
- Consulte os logs no terminal para detalhes do erro

## 📄 Licença

Este projeto foi desenvolvido para uso interno. Todos os direitos reservados.

## 👨‍💻 Suporte

Para dúvidas ou problemas, consulte a documentação ou entre em contato com o desenvolvedor.

---

**Versão**: 1.0.0  
**Data**: Janeiro 2025  
**Desenvolvido com**: ❤️ e Python
# propostas-system
