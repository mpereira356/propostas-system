"""
Aplicação Flask para gerenciamento de propostas comerciais
"""
import os
import io
import re
from datetime import datetime, timedelta, date
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename
from models import db, Proposta, ItemProposta, Cliente, Setor, Regiao, Visita, Contato, Equipamento, init_db
from pdf_reader import PropostaExtractor
from sqlalchemy import text, func
from openpyxl import Workbook
from openpyxl.utils import get_column_letter

# Configurações
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua-chave-secreta-aqui-mude-em-producao'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

def parse_date_br(date_str):
    """Converte data no formato dd/mm/aaaa para datetime.date."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").date()
    except Exception:
        return None


def parse_date_iso(date_str):
    """Converte data no formato aaaa-mm-dd para datetime.date."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        return None


def normalize_cnpj(cnpj):
    """Normaliza CNPJ removendo caracteres não numéricos."""
    if not cnpj:
        return None
    return re.sub(r'\D', '', cnpj)


def extract_cod_from_filename(filename):
    """Extrai o código do vendedor do nome do arquivo."""
    if not filename:
        return None
    match = re.search(r'cod\s*([A-Za-z0-9]+)', filename, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def ensure_schema():
    """Garante colunas novas no SQLite sem migração."""
    with db.engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(propostas)"))
        existing = {row[1] for row in result.fetchall()}
        if 'cod_vendedor' not in existing:
            conn.execute(text("ALTER TABLE propostas ADD COLUMN cod_vendedor VARCHAR(50)"))
        if 'data_vencimento' not in existing:
            conn.execute(text("ALTER TABLE propostas ADD COLUMN data_vencimento DATE"))
        if 'instalacao_status' not in existing:
            conn.execute(text("ALTER TABLE propostas ADD COLUMN instalacao_status VARCHAR(30)"))
        if 'qualificacoes_status' not in existing:
            conn.execute(text("ALTER TABLE propostas ADD COLUMN qualificacoes_status VARCHAR(30)"))
        if 'treinamento_status' not in existing:
            conn.execute(text("ALTER TABLE propostas ADD COLUMN treinamento_status VARCHAR(30)"))
        if 'garantia_resumo' not in existing:
            conn.execute(text("ALTER TABLE propostas ADD COLUMN garantia_resumo TEXT"))
        if 'garantia_texto' not in existing:
            conn.execute(text("ALTER TABLE propostas ADD COLUMN garantia_texto TEXT"))
        if 'observacoes' not in existing:
            conn.execute(text("ALTER TABLE propostas ADD COLUMN observacoes VARCHAR(30)"))

        # Visitas: ajustes de schema
        try:
            result_visitas = conn.execute(text("PRAGMA table_info(visitas)"))
            existing_visitas = {row[1] for row in result_visitas.fetchall()}
            if 'historico' not in existing_visitas and existing_visitas:
                conn.execute(text("ALTER TABLE visitas ADD COLUMN historico TEXT"))
            if existing_visitas and ('data' not in existing_visitas):
                if 'data_hora' in existing_visitas:
                    data_expr = "date(data_hora)"
                elif 'data_criacao' in existing_visitas:
                    data_expr = "date(data_criacao)"
                else:
                    data_expr = "date('now')"
                historico_expr = "historico" if 'historico' in existing_visitas else "NULL"
                data_criacao_expr = "data_criacao" if 'data_criacao' in existing_visitas else "NULL"

                conn.execute(text("PRAGMA foreign_keys=off"))
                conn.execute(text("""
                    CREATE TABLE visitas_new (
                        id INTEGER PRIMARY KEY,
                        cliente_id INTEGER NOT NULL,
                        data DATE NOT NULL,
                        historico TEXT,
                        data_criacao DATETIME,
                        FOREIGN KEY(cliente_id) REFERENCES clientes(id)
                    )
                """))
                conn.execute(text(f"""
                    INSERT INTO visitas_new (id, cliente_id, data, historico, data_criacao)
                    SELECT id, cliente_id, {data_expr}, {historico_expr}, {data_criacao_expr}
                    FROM visitas
                """))
                conn.execute(text("DROP TABLE visitas"))
                conn.execute(text("ALTER TABLE visitas_new RENAME TO visitas"))
                conn.execute(text("PRAGMA foreign_keys=on"))
        except Exception:
            # Tabela pode não existir ainda
            pass

        # Contatos: adicionar setor se faltar
        try:
            result_contatos = conn.execute(text("PRAGMA table_info(contatos)"))
            existing_contatos = {row[1] for row in result_contatos.fetchall()}
            if 'setor' not in existing_contatos and existing_contatos:
                conn.execute(text("ALTER TABLE contatos ADD COLUMN setor VARCHAR(100)"))
        except Exception:
            # Tabela pode não existir ainda
            pass

        # Clientes: adicionar CPM se faltar
        try:
            result_clientes = conn.execute(text("PRAGMA table_info(clientes)"))
            existing_clientes = {row[1] for row in result_clientes.fetchall()}
            if 'cpm_status' not in existing_clientes and existing_clientes:
                conn.execute(text("ALTER TABLE clientes ADD COLUMN cpm_status VARCHAR(20)"))
            if 'cpm_data' not in existing_clientes and existing_clientes:
                conn.execute(text("ALTER TABLE clientes ADD COLUMN cpm_data DATE"))
            if 'regiao' not in existing_clientes and existing_clientes:
                conn.execute(text("ALTER TABLE clientes ADD COLUMN regiao VARCHAR(50)"))
        except Exception:
            pass

# Inicializar banco de dados
db.init_app(app)
with app.app_context():
    db.create_all()
    ensure_schema()


def allowed_file(filename):
    """Verifica se o arquivo é permitido"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Página principal - redireciona para upload"""
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
def dashboard():
    """Dashboard com indicadores de propostas"""
    hoje = date.today()
    total_propostas = Proposta.query.count()
    total_ganhas = Proposta.query.filter_by(observacoes='Proposta ganha').count()
    total_perdidas = Proposta.query.filter_by(observacoes='Proposta perdida').count()
    total_abertas = Proposta.query.filter_by(observacoes='Proposta em aberto').count()
    total_vencidas = Proposta.query.filter(
        Proposta.data_vencimento.isnot(None),
        Proposta.data_vencimento < hoje
    ).count()

    return render_template(
        'dashboard.html',
        total_propostas=total_propostas,
        total_ganhas=total_ganhas,
        total_perdidas=total_perdidas,
        total_abertas=total_abertas,
        total_vencidas=total_vencidas
    )


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """Página de upload de PDF"""
    if request.method == 'POST':
        # Verificar se arquivo foi enviado
        files = request.files.getlist('pdf_files')
        if not files or (len(files) == 1 and files[0].filename == ''):
            files = request.files.getlist('pdf_file')

        if not files or all(f.filename == '' for f in files):
            flash('Nenhum arquivo foi selecionado', 'error')
            return redirect(request.url)

        def process_file(file_obj):
            if not allowed_file(file_obj.filename):
                return {'status': 'error', 'message': f'Apenas arquivos PDF são permitidos: {file_obj.filename}'}

            filename_original = file_obj.filename
            filename = secure_filename(filename_original)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file_obj.save(filepath)

            try:
                extractor = PropostaExtractor(filepath)
                dados = extractor.extract_all()
                if not dados or not dados.get('id_proposta'):
                    return {'status': 'error', 'message': f'Não foi possível extrair dados do PDF: {filename_original}'}

                cod_vendedor = extract_cod_from_filename(filename_original)
                data_emissao_date = parse_date_br(dados.get('data_emissao'))
                data_vencimento = data_emissao_date + timedelta(days=30) if data_emissao_date else None

                proposta_existente = Proposta.query.filter_by(
                    id_proposta=dados['id_proposta']
                ).first()

                if proposta_existente:
                    return {
                        'status': 'warning',
                        'message': f'Proposta {dados["id_proposta"]} já foi importada anteriormente!',
                        'proposta_id': proposta_existente.id
                    }

                proposta = Proposta(
                    razao_social=dados.get('razao_social'),
                    nome_fantasia=dados.get('nome_fantasia'),
                    id_proposta=dados.get('id_proposta'),
                    data_emissao=dados.get('data_emissao'),
                    validade=dados.get('validade'),
                    cnpj=dados.get('cnpj'),
                    telefone=dados.get('telefone'),
                    celular=dados.get('celular'),
                    email=dados.get('email'),
                    pessoa_contato=dados.get('pessoa_contato'),
                    descricao_item=dados.get('descricao_item'),
                    quantidade=dados.get('quantidade'),
                    valor_total=dados.get('valor_total'),
                    nome_arquivo_pdf=filename,
                    cod_vendedor=cod_vendedor,
                    data_vencimento=data_vencimento,
                    instalacao_status=dados.get('instalacao_status'),
                    qualificacoes_status=dados.get('qualificacoes_status'),
                    treinamento_status=dados.get('treinamento_status'),
                    garantia_resumo=dados.get('garantia_resumo'),
                    garantia_texto=dados.get('garantia_texto')
                )

                db.session.add(proposta)
                db.session.flush()

                for item_data in dados.get('itens', []):
                    item = ItemProposta(
                        proposta_id=proposta.id,
                        numero=item_data.get('numero'),
                        descricao=item_data.get('descricao'),
                        quantidade=item_data.get('quantidade'),
                        valor_unitario=item_data.get('valor_unitario'),
                        valor_total=item_data.get('valor_total')
                    )
                    db.session.add(item)

                cnpj = dados.get('cnpj')
                if cnpj:
                    cnpj_normalizado = normalize_cnpj(cnpj)
                    cliente_existente = Cliente.query.filter(
                        (Cliente.cnpj == cnpj) | (Cliente.cnpj_normalizado == cnpj_normalizado)
                    ).first()
                    if not cliente_existente:
                        nome_cliente = dados.get('razao_social') or dados.get('nome_fantasia') or 'Cliente sem nome'
                        cliente = Cliente(
                            nome=nome_cliente,
                            cnpj=cnpj,
                            cnpj_normalizado=cnpj_normalizado
                        )
                        db.session.add(cliente)

                db.session.commit()
                return {
                    'status': 'success',
                    'message': f'Proposta {dados["id_proposta"]} importada com sucesso!',
                    'proposta_id': proposta.id
                }
            except Exception as e:
                db.session.rollback()
                return {'status': 'error', 'message': f'Erro ao processar PDF ({filename_original}): {str(e)}'}

        if len(files) == 1:
            resultado = process_file(files[0])
            flash(resultado['message'], resultado['status'])
            if resultado['status'] == 'success' and resultado.get('proposta_id'):
                return redirect(url_for('detalhes', id=resultado['proposta_id']))
            if resultado['status'] == 'warning' and resultado.get('proposta_id'):
                return redirect(url_for('detalhes', id=resultado['proposta_id']))
            return redirect(request.url)

        for file_obj in files:
            if file_obj.filename == '':
                continue
            resultado = process_file(file_obj)
            flash(resultado['message'], resultado['status'])

        return redirect(url_for('listagem'))
    
    return render_template('upload.html')


@app.route('/listagem')
def listagem():
    """Página de listagem de propostas"""
    # Filtros
    razao_social = request.args.get('razao_social', '').strip()
    cnpj = request.args.get('cnpj', '').strip()
    id_proposta = request.args.get('id_proposta', '').strip()
    cod_vendedor = request.args.get('cod_vendedor', '').strip()
    
    # Query base
    query = Proposta.query
    
    # Aplicar filtros
    if razao_social:
        query = query.filter(Proposta.razao_social.ilike(f'%{razao_social}%'))
    if cnpj:
        query = query.filter(Proposta.cnpj.ilike(f'%{cnpj}%'))
    if id_proposta:
        query = query.filter(Proposta.id_proposta.ilike(f'%{id_proposta}%'))
    if cod_vendedor:
        query = query.filter(Proposta.cod_vendedor.ilike(f'%{cod_vendedor}%'))
    
    # Ordenar por ID da proposta (crescente)
    propostas = query.order_by(Proposta.id_proposta.asc()).all()

    hoje = date.today()
    limite_vencendo = hoje + timedelta(days=7)
    total_vencidas = 0
    alterou = False

    for proposta in propostas:
        # Backfill de data de vencimento se faltar
        if not proposta.data_vencimento and proposta.data_emissao:
            data_emissao_date = parse_date_br(proposta.data_emissao)
            if data_emissao_date:
                proposta.data_vencimento = data_emissao_date + timedelta(days=30)
                alterou = True
        
        # Backfill de cod pelo nome do arquivo
        if not proposta.cod_vendedor and proposta.nome_arquivo_pdf:
            cod = extract_cod_from_filename(proposta.nome_arquivo_pdf)
            if cod:
                proposta.cod_vendedor = cod
                alterou = True

        # Backfill de serviços/garantia se faltar
        needs_backfill = any([
            proposta.instalacao_status is None,
            proposta.qualificacoes_status is None,
            proposta.treinamento_status is None,
            proposta.garantia_resumo is None,
            proposta.garantia_texto is None
        ])
        if needs_backfill and proposta.nome_arquivo_pdf:
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], proposta.nome_arquivo_pdf)
            if os.path.exists(pdf_path):
                extractor = PropostaExtractor(pdf_path)
                dados = extractor.extract_all()
                if dados:
                    proposta.instalacao_status = dados.get('instalacao_status') or proposta.instalacao_status
                    proposta.qualificacoes_status = dados.get('qualificacoes_status') or proposta.qualificacoes_status
                    proposta.treinamento_status = dados.get('treinamento_status') or proposta.treinamento_status
                    proposta.garantia_resumo = dados.get('garantia_resumo') or proposta.garantia_resumo
                    proposta.garantia_texto = dados.get('garantia_texto') or proposta.garantia_texto
                    alterou = True

        # Flags para status de vencimento
        proposta.vencida = False
        proposta.vencendo = False
        if proposta.data_vencimento:
            if proposta.data_vencimento < hoje:
                proposta.vencida = True
                total_vencidas += 1
            elif proposta.data_vencimento <= limite_vencendo:
                proposta.vencendo = True

    if alterou:
        db.session.commit()
    
    return render_template('listagem.html', 
                         propostas=propostas,
                         filtros={
                             'razao_social': razao_social,
                             'cnpj': cnpj,
                             'id_proposta': id_proposta,
                             'cod_vendedor': cod_vendedor
                         },
                         total_vencidas=total_vencidas)


@app.route('/clientes')
def clientes():
    """Página de listagem de clientes"""
    clientes = Cliente.query.order_by(Cliente.nome.asc()).all()
    return render_template('clientes_listagem.html', clientes=clientes)


@app.route('/relatorio')
def relatorio():
    """Página de relatórios"""
    clientes = Cliente.query.order_by(Cliente.nome.asc()).all()
    return render_template('relatorio.html', clientes=clientes)


def _autosize_sheet(ws):
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.value is not None:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(max_len + 2, 60)


@app.route('/relatorio/export', methods=['POST'])
def relatorio_export():
    """Exporta relatório em XLSX"""
    cliente_id = request.form.get('cliente_id', '').strip()
    if not cliente_id or not cliente_id.isdigit():
        flash('Selecione um cliente para exportar.', 'error')
        return redirect(url_for('relatorio'))

    cliente = Cliente.query.get_or_404(int(cliente_id))
    contatos = Contato.query.filter_by(cliente_id=cliente.id).order_by(Contato.nome.asc()).all()
    visitas = Visita.query.filter_by(cliente_id=cliente.id).order_by(Visita.data.desc()).all()
    equipamentos = Equipamento.query.filter_by(cliente_id=cliente.id).order_by(Equipamento.nome.asc()).all()
    cnpj_normalizado = cliente.cnpj_normalizado or normalize_cnpj(cliente.cnpj)
    propostas = Proposta.query.filter(
        (Proposta.cnpj == cliente.cnpj) |
        (func.replace(func.replace(func.replace(Proposta.cnpj, '.', ''), '/', ''), '-', '') == cnpj_normalizado)
    ).order_by(Proposta.id_proposta.asc()).all()

    wb = Workbook()

    ws_info = wb.active
    ws_info.title = 'Cliente'
    ws_info.append(['Campo', 'Valor'])
    ws_info.append(['Nome', cliente.nome])
    ws_info.append(['CNPJ', cliente.cnpj])
    ws_info.append(['Contato principal', cliente.contato or ''])
    ws_info.append(['Email principal', cliente.email or ''])
    ws_info.append(['Telefone principal', cliente.telefone or ''])
    ws_info.append(['Endereço', cliente.endereco or ''])
    ws_info.append(['Região', cliente.regiao or ''])
    ws_info.append(['CPM Status', cliente.cpm_status or ''])
    if cliente.cpm_data:
        ws_info.append(['CPM Data', cliente.cpm_data.strftime('%d/%m/%Y')])
    _autosize_sheet(ws_info)

    ws_contatos = wb.create_sheet('Contatos')
    ws_contatos.append(['Nome', 'Email', 'Telefone', 'Cargo', 'Setor'])
    for c in contatos:
        ws_contatos.append([c.nome, c.email or '', c.telefone or '', c.cargo or '', c.setor or ''])
    _autosize_sheet(ws_contatos)

    ws_equip = wb.create_sheet('Parque instalado')
    ws_equip.append(['Equipamento', 'Quantidade', 'Marca', 'Modelo', 'Ano'])
    for e in equipamentos:
        ws_equip.append([
            e.nome,
            e.quantidade if e.quantidade is not None else '',
            e.marca or '',
            e.modelo or '',
            e.ano_instalacao if e.ano_instalacao is not None else ''
        ])
    _autosize_sheet(ws_equip)

    ws_visitas = wb.create_sheet('Visitas')
    ws_visitas.append(['Data', 'Histórico'])
    for v in visitas:
        ws_visitas.append([
            v.data.strftime('%d/%m/%Y') if v.data else '',
            v.historico or ''
        ])
    _autosize_sheet(ws_visitas)

    ws_propostas = wb.create_sheet('Propostas')
    ws_propostas.append(['ID Proposta', 'Razão Social', 'Data Emissão', 'Valor Total', 'Cod Vendedor'])
    for p in propostas:
        ws_propostas.append([
            p.id_proposta or '',
            p.razao_social or '',
            p.data_emissao or '',
            p.valor_total or '',
            p.cod_vendedor or ''
        ])
    _autosize_sheet(ws_propostas)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"relatorio_cliente_{cliente.id}.xlsx"
    return send_file(output, as_attachment=True, download_name=filename,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@app.route('/clientes/novo', methods=['GET', 'POST'])
def clientes_novo():
    """Cadastro de novos clientes"""
    setores = Setor.query.order_by(Setor.nome.asc()).all()
    regioes = Regiao.query.order_by(Regiao.nome.asc()).all()
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        cnpj = request.form.get('cnpj', '').strip()
        contato = request.form.get('contato', '').strip()
        email = request.form.get('email', '').strip()
        telefone = request.form.get('telefone', '').strip()
        endereco = request.form.get('endereco', '').strip()
        cpm_status = cliente.cpm_status
        cpm_data = cliente.cpm_data
        if 'cpm_status' in request.form or 'cpm_data' in request.form:
            cpm_status = request.form.get('cpm_status', '').strip()
            cpm_data_str = request.form.get('cpm_data', '').strip()
            cpm_data = parse_date_iso(cpm_data_str)
        regiao = request.form.get('regiao', '').strip()

        if not nome or not cnpj:
            flash('Nome e CNPJ são obrigatórios.', 'error')
            return redirect(request.url)

        cnpj_normalizado = normalize_cnpj(cnpj)
        existente = Cliente.query.filter(
            (Cliente.cnpj == cnpj) | (Cliente.cnpj_normalizado == cnpj_normalizado)
        ).first()
        if existente:
            flash('Já existe um cliente cadastrado com esse CNPJ.', 'warning')
            return redirect(url_for('cliente_detalhes', id=existente.id))

        cliente = Cliente(
            nome=nome,
            cnpj=cnpj,
            cnpj_normalizado=cnpj_normalizado,
            contato=contato or None,
            email=email or None,
            telefone=telefone or None,
            endereco=endereco or None,
            setor=None,
            cpm_status=cpm_status or None,
            cpm_data=cpm_data,
            regiao=regiao or None
        )
        db.session.add(cliente)
        db.session.flush()

        nomes_contatos = request.form.getlist('contato_nome[]')
        emails_contatos = request.form.getlist('contato_email[]')
        telefones_contatos = request.form.getlist('contato_telefone[]')
        cargos_contatos = request.form.getlist('contato_cargo[]')
        setores_contatos = request.form.getlist('contato_setor[]')

        for idx, nome_contato in enumerate(nomes_contatos):
            nome_contato = nome_contato.strip()
            if not nome_contato:
                continue
            contato_item = Contato(
                cliente_id=cliente.id,
                nome=nome_contato,
                email=(emails_contatos[idx].strip() if idx < len(emails_contatos) else '') or None,
                telefone=(telefones_contatos[idx].strip() if idx < len(telefones_contatos) else '') or None,
                cargo=(cargos_contatos[idx].strip() if idx < len(cargos_contatos) else '') or None,
                setor=(setores_contatos[idx].strip() if idx < len(setores_contatos) else '') or None
            )
            db.session.add(contato_item)
        db.session.commit()
        flash('Cliente criado com sucesso!', 'success')
        return redirect(url_for('cliente_detalhes', id=cliente.id))

    return render_template('cliente_novo.html', setores=setores, regioes=regioes)


@app.route('/setores/novo', methods=['POST'])
def setores_novo():
    """Cadastro rápido de setor"""
    nome = request.form.get('setor_nome', '').strip()
    if not nome:
        flash('Informe o nome do setor.', 'error')
        return redirect(request.referrer or url_for('clientes_novo'))

    existente = Setor.query.filter_by(nome=nome).first()
    if existente:
        flash('Este setor já está cadastrado.', 'warning')
        return redirect(request.referrer or url_for('clientes_novo'))

    setor = Setor(nome=nome)
    db.session.add(setor)
    db.session.commit()
    flash('Setor adicionado com sucesso!', 'success')
    return redirect(request.referrer or url_for('clientes_novo'))


@app.route('/regioes/novo', methods=['POST'])
def regioes_novo():
    """Cadastro rápido de região"""
    nome = request.form.get('regiao_nome', '').strip()
    if not nome:
        flash('Informe o nome da região.', 'error')
        return redirect(request.referrer or url_for('clientes_novo'))

    existente = Regiao.query.filter_by(nome=nome).first()
    if existente:
        flash('Esta região já está cadastrada.', 'warning')
        return redirect(request.referrer or url_for('clientes_novo'))

    regiao = Regiao(nome=nome)
    db.session.add(regiao)
    db.session.commit()
    flash('Região adicionada com sucesso!', 'success')
    return redirect(request.referrer or url_for('clientes_novo'))


@app.route('/clientes/<int:id>')
def cliente_detalhes(id):
    """Detalhes do cliente e propostas vinculadas"""
    cliente = Cliente.query.get_or_404(id)
    cnpj_normalizado = cliente.cnpj_normalizado or normalize_cnpj(cliente.cnpj)
    propostas = Proposta.query.filter(
        (Proposta.cnpj == cliente.cnpj) |
        (func.replace(func.replace(func.replace(Proposta.cnpj, '.', ''), '/', ''), '-', '') == cnpj_normalizado)
    ).order_by(Proposta.id_proposta.asc()).all()
    visitas = Visita.query.filter_by(cliente_id=cliente.id).order_by(Visita.data.desc()).all()
    setores = Setor.query.order_by(Setor.nome.asc()).all()
    contatos = Contato.query.filter_by(cliente_id=cliente.id).order_by(Contato.nome.asc()).all()
    equipamentos = Equipamento.query.filter_by(cliente_id=cliente.id).order_by(Equipamento.nome.asc()).all()

    return render_template('cliente_detalhes.html', cliente=cliente, propostas=propostas, visitas=visitas,
                           contatos=contatos, setores=setores, equipamentos=equipamentos)


@app.route('/clientes/<int:id>/cpm', methods=['POST'])
def cliente_cpm_atualizar(id):
    """Atualiza CPM do cliente na tela de detalhes"""
    cliente = Cliente.query.get_or_404(id)
    cpm_status = request.form.get('cpm_status', '').strip()
    cpm_data_str = request.form.get('cpm_data', '').strip()
    cpm_data = parse_date_iso(cpm_data_str)

    cliente.cpm_status = cpm_status or None
    cliente.cpm_data = cpm_data

    db.session.commit()
    flash('CPM atualizado com sucesso!', 'success')
    return redirect(url_for('cliente_detalhes', id=cliente.id))


@app.route('/clientes/<int:id>/editar', methods=['GET', 'POST'])
def cliente_editar(id):
    """Editar cliente"""
    cliente = Cliente.query.get_or_404(id)

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        cnpj = request.form.get('cnpj', '').strip()
        contato = request.form.get('contato', '').strip()
        email = request.form.get('email', '').strip()
        telefone = request.form.get('telefone', '').strip()
        endereco = request.form.get('endereco', '').strip()
        cpm_status = request.form.get('cpm_status', '').strip()
        cpm_data_str = request.form.get('cpm_data', '').strip()
        cpm_data = parse_date_iso(cpm_data_str)
        regiao = request.form.get('regiao', '').strip()

        if not nome or not cnpj:
            flash('Nome e CNPJ são obrigatórios.', 'error')
            return redirect(request.url)

        cnpj_normalizado = normalize_cnpj(cnpj)
        existente = Cliente.query.filter(
            ((Cliente.cnpj == cnpj) | (Cliente.cnpj_normalizado == cnpj_normalizado)) &
            (Cliente.id != cliente.id)
        ).first()
        if existente:
            flash('Já existe outro cliente com esse CNPJ.', 'warning')
            return redirect(url_for('cliente_editar', id=cliente.id))

        cliente.nome = nome
        cliente.cnpj = cnpj
        cliente.cnpj_normalizado = cnpj_normalizado
        cliente.contato = contato or None
        cliente.email = email or None
        cliente.telefone = telefone or None
        cliente.endereco = endereco or None
        cliente.setor = None
        cliente.cpm_status = cpm_status or None
        cliente.cpm_data = cpm_data
        cliente.regiao = regiao or None

        db.session.commit()
        flash('Cliente atualizado com sucesso!', 'success')
        return redirect(url_for('cliente_detalhes', id=cliente.id))

    regioes = Regiao.query.order_by(Regiao.nome.asc()).all()
    return render_template('cliente_editar.html', cliente=cliente, regioes=regioes)


@app.route('/clientes/<int:id>/contatos/novo', methods=['POST'])
def contatos_novo(id):
    """Cria um novo contato para o cliente"""
    cliente = Cliente.query.get_or_404(id)
    nome = request.form.get('nome', '').strip()
    email = request.form.get('email', '').strip()
    telefone = request.form.get('telefone', '').strip()
    cargo = request.form.get('cargo', '').strip()
    setor = request.form.get('setor', '').strip()

    if not nome:
        flash('Informe o nome do contato.', 'error')
        return redirect(url_for('cliente_detalhes', id=cliente.id))

    contato = Contato(
        cliente_id=cliente.id,
        nome=nome,
        email=email or None,
        telefone=telefone or None,
        cargo=cargo or None,
        setor=setor or None
    )
    db.session.add(contato)
    db.session.commit()
    flash('Contato adicionado com sucesso!', 'success')
    return redirect(url_for('cliente_detalhes', id=cliente.id))


@app.route('/contatos/<int:id>/editar', methods=['GET', 'POST'])
def contato_editar(id):
    """Editar contato"""
    contato = Contato.query.get_or_404(id)
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip()
        telefone = request.form.get('telefone', '').strip()
        cargo = request.form.get('cargo', '').strip()
        setor = request.form.get('setor', '').strip()

        if not nome:
            flash('Informe o nome do contato.', 'error')
            return redirect(request.url)

        contato.nome = nome
        contato.email = email or None
        contato.telefone = telefone or None
        contato.cargo = cargo or None
        contato.setor = setor or None
        db.session.commit()
        flash('Contato atualizado com sucesso!', 'success')
        return redirect(url_for('cliente_detalhes', id=contato.cliente_id))

    return render_template('contato_editar.html', contato=contato)


@app.route('/contatos/<int:id>/deletar', methods=['POST'])
def contato_deletar(id):
    """Deleta contato"""
    contato = Contato.query.get_or_404(id)
    cliente_id = contato.cliente_id
    try:
        db.session.delete(contato)
        db.session.commit()
        flash('Contato deletado com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao deletar contato: {str(e)}', 'error')
    return redirect(url_for('cliente_detalhes', id=cliente_id))


@app.route('/clientes/<int:id>/equipamentos/novo', methods=['POST'])
def equipamentos_novo(id):
    """Cria equipamentos para o cliente"""
    cliente = Cliente.query.get_or_404(id)
    nomes = request.form.getlist('equipamento_nome[]')
    quantidades = request.form.getlist('equipamento_quantidade[]')
    marcas = request.form.getlist('equipamento_marca[]')
    modelos = request.form.getlist('equipamento_modelo[]')
    anos = request.form.getlist('equipamento_ano[]')

    adicionou = False
    for idx, nome in enumerate(nomes):
        nome = nome.strip()
        if not nome:
            continue
        quantidade = (quantidades[idx].strip() if idx < len(quantidades) else '')
        ano = (anos[idx].strip() if idx < len(anos) else '')
        equipamento = Equipamento(
            cliente_id=cliente.id,
            nome=nome,
            quantidade=int(quantidade) if quantidade.isdigit() else None,
            marca=(marcas[idx].strip() if idx < len(marcas) else '') or None,
            modelo=(modelos[idx].strip() if idx < len(modelos) else '') or None,
            ano_instalacao=int(ano) if ano.isdigit() else None
        )
        db.session.add(equipamento)
        adicionou = True

    if not adicionou:
        flash('Informe ao menos o nome do equipamento.', 'error')
        return redirect(url_for('cliente_detalhes', id=cliente.id))

    db.session.commit()
    flash('Equipamento(s) adicionados com sucesso!', 'success')
    return redirect(url_for('cliente_detalhes', id=cliente.id))


@app.route('/equipamentos/<int:id>/editar', methods=['GET', 'POST'])
def equipamento_editar(id):
    """Editar equipamento"""
    equipamento = Equipamento.query.get_or_404(id)
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        quantidade = request.form.get('quantidade', '').strip()
        marca = request.form.get('marca', '').strip()
        modelo = request.form.get('modelo', '').strip()
        ano = request.form.get('ano', '').strip()

        if not nome:
            flash('Informe o nome do equipamento.', 'error')
            return redirect(request.url)

        equipamento.nome = nome
        equipamento.quantidade = int(quantidade) if quantidade.isdigit() else None
        equipamento.marca = marca or None
        equipamento.modelo = modelo or None
        equipamento.ano_instalacao = int(ano) if ano.isdigit() else None
        db.session.commit()
        flash('Equipamento atualizado com sucesso!', 'success')
        return redirect(url_for('cliente_detalhes', id=equipamento.cliente_id))

    return render_template('equipamento_editar.html', equipamento=equipamento)


@app.route('/equipamentos/<int:id>/deletar', methods=['POST'])
def equipamento_deletar(id):
    """Deleta equipamento"""
    equipamento = Equipamento.query.get_or_404(id)
    cliente_id = equipamento.cliente_id
    try:
        db.session.delete(equipamento)
        db.session.commit()
        flash('Equipamento deletado com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao deletar equipamento: {str(e)}', 'error')
    return redirect(url_for('cliente_detalhes', id=cliente_id))


@app.route('/clientes/<int:id>/deletar', methods=['POST'])
def cliente_deletar(id):
    """Deleta um cliente e seus registros relacionados"""
    cliente = Cliente.query.get_or_404(id)
    try:
        Contato.query.filter_by(cliente_id=cliente.id).delete()
        Equipamento.query.filter_by(cliente_id=cliente.id).delete()
        Visita.query.filter_by(cliente_id=cliente.id).delete()
        db.session.delete(cliente)
        db.session.commit()
        flash('Cliente deletado com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao deletar cliente: {str(e)}', 'error')
    return redirect(url_for('clientes'))


@app.route('/clientes/<int:id>/visitas/nova', methods=['POST'])
def visitas_nova(id):
    """Cria uma nova visita para o cliente"""
    cliente = Cliente.query.get_or_404(id)
    data_str = request.form.get('data', '').strip()
    historico = request.form.get('historico', '').strip()

    if not data_str:
        flash('Informe a data da visita.', 'error')
        return redirect(url_for('cliente_detalhes', id=cliente.id))

    try:
        data_visita = datetime.strptime(data_str, '%Y-%m-%d').date()
    except Exception:
        flash('Formato de data inválido.', 'error')
        return redirect(url_for('cliente_detalhes', id=cliente.id))

    visita = Visita(cliente_id=cliente.id, data=data_visita, historico=historico or None)
    db.session.add(visita)
    db.session.commit()
    flash('Visita registrada com sucesso!', 'success')
    return redirect(url_for('cliente_detalhes', id=cliente.id))


@app.route('/detalhes/<int:id>')
def detalhes(id):
    """Página de detalhes de uma proposta"""
    proposta = Proposta.query.get_or_404(id)
    itens = ItemProposta.query.filter_by(proposta_id=id).all()
    return render_template('detalhes.html', proposta=proposta, itens=itens)


@app.route('/uploads/<path:filename>')
def visualizar_pdf(filename):
    """Serve PDFs enviados para visualização no navegador."""
    safe_name = secure_filename(filename)
    if not safe_name:
        return redirect(url_for('listagem'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], safe_name, as_attachment=False)

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    """Editar proposta"""
    proposta = Proposta.query.get_or_404(id)
    if request.method == 'POST':
        proposta.id_proposta = request.form.get('id_proposta', '').strip() or proposta.id_proposta
        proposta.data_emissao = request.form.get('data_emissao', '').strip() or proposta.data_emissao
        data_vencimento_str = request.form.get('data_vencimento', '').strip()
        proposta.data_vencimento = parse_date_br(data_vencimento_str) if data_vencimento_str else proposta.data_vencimento
        proposta.validade = request.form.get('validade', '').strip() or proposta.validade
        proposta.cod_vendedor = request.form.get('cod_vendedor', '').strip() or proposta.cod_vendedor

        proposta.razao_social = request.form.get('razao_social', '').strip() or proposta.razao_social
        proposta.nome_fantasia = request.form.get('nome_fantasia', '').strip() or proposta.nome_fantasia
        proposta.cnpj = request.form.get('cnpj', '').strip() or proposta.cnpj
        proposta.telefone = request.form.get('telefone', '').strip() or proposta.telefone
        proposta.celular = request.form.get('celular', '').strip() or proposta.celular
        proposta.email = request.form.get('email', '').strip() or proposta.email
        proposta.pessoa_contato = request.form.get('pessoa_contato', '').strip() or proposta.pessoa_contato

        proposta.instalacao_status = request.form.get('instalacao_status', '').strip() or proposta.instalacao_status
        proposta.qualificacoes_status = request.form.get('qualificacoes_status', '').strip() or proposta.qualificacoes_status
        proposta.treinamento_status = request.form.get('treinamento_status', '').strip() or proposta.treinamento_status
        proposta.garantia_resumo = request.form.get('garantia_resumo', '').strip() or proposta.garantia_resumo

        db.session.commit()
        flash('Proposta atualizada com sucesso!', 'success')
        return redirect(url_for('detalhes', id=proposta.id))

    return render_template('editar.html', proposta=proposta)


@app.route('/atualizar_cod/<int:id>', methods=['POST'])
def atualizar_cod(id):
    """Atualiza o código do vendedor manualmente"""
    proposta = Proposta.query.get_or_404(id)
    cod = request.form.get('cod_vendedor', '').strip()
    proposta.cod_vendedor = cod if cod else None
    db.session.commit()
    flash('Código do vendedor atualizado com sucesso!', 'success')
    return redirect(url_for('listagem'))


@app.route('/atualizar_observacoes/<int:id>', methods=['POST'])
def atualizar_observacoes(id):
    """Atualiza observações da proposta na listagem"""
    proposta = Proposta.query.get_or_404(id)
    observacoes = request.form.get('observacoes', '').strip()
    proposta.observacoes = observacoes if observacoes else None
    db.session.commit()
    flash('Observações atualizadas com sucesso!', 'success')
    return redirect(url_for('listagem'))


@app.route('/deletar/<int:id>', methods=['POST'])
def deletar(id):
    """Deletar uma proposta"""
    proposta = Proposta.query.get_or_404(id)
    
    try:
        # Deletar arquivo PDF
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], proposta.nome_arquivo_pdf)
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # Deletar do banco (itens serão deletados em cascata)
        db.session.delete(proposta)
        db.session.commit()
        
        flash(f'Proposta {proposta.id_proposta} deletada com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao deletar proposta: {str(e)}', 'error')
        db.session.rollback()
    
    return redirect(url_for('listagem'))


@app.route('/api/propostas')
def api_propostas():
    """API para listar propostas (JSON)"""
    propostas = Proposta.query.all()
    return jsonify([p.to_dict() for p in propostas])


@app.route('/api/proposta/<int:id>')
def api_proposta(id):
    """API para obter detalhes de uma proposta (JSON)"""
    proposta = Proposta.query.get_or_404(id)
    itens = ItemProposta.query.filter_by(proposta_id=id).all()
    
    resultado = proposta.to_dict()
    resultado['itens'] = [item.to_dict() for item in itens]
    
    return jsonify(resultado)


if __name__ == '__main__':
    # Criar diretório de uploads se não existir
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    print("Banco de dados inicializado!")
    # Rodar aplicação
    app.run(debug=True, host='0.0.0.0', port=2020)
