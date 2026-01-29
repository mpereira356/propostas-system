"""
Modelos de banco de dados para o sistema de propostas
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Proposta(db.Model):
    """Modelo para armazenar propostas comerciais"""
    
    __tablename__ = 'propostas'
    
    id = db.Column(db.Integer, primary_key=True)
    razao_social = db.Column(db.String(255))
    nome_fantasia = db.Column(db.String(255))
    id_proposta = db.Column(db.String(50), unique=True, nullable=False)
    data_emissao = db.Column(db.String(20))
    validade = db.Column(db.String(50))
    cnpj = db.Column(db.String(20))
    telefone = db.Column(db.String(50))
    celular = db.Column(db.String(50))
    email = db.Column(db.String(100))
    pessoa_contato = db.Column(db.String(255))
    descricao_item = db.Column(db.Text)
    quantidade = db.Column(db.String(20))
    valor_total = db.Column(db.String(50))
    nome_arquivo_pdf = db.Column(db.String(255))
    cod_vendedor = db.Column(db.String(50))
    data_vencimento = db.Column(db.Date)
    instalacao_status = db.Column(db.String(30))
    qualificacoes_status = db.Column(db.String(30))
    treinamento_status = db.Column(db.String(30))
    garantia_resumo = db.Column(db.Text)
    garantia_texto = db.Column(db.Text)
    observacoes = db.Column(db.String(30))
    id_proposta_base = db.Column(db.String(50))
    versao = db.Column(db.String(5))
    data_importacao = db.Column(db.DateTime, default=datetime.now)
    
    # Relacionamento com itens
    itens = db.relationship('ItemProposta', backref='proposta', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Proposta {self.id_proposta}>'
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'razao_social': self.razao_social,
            'nome_fantasia': self.nome_fantasia,
            'id_proposta': self.id_proposta,
            'data_emissao': self.data_emissao,
            'validade': self.validade,
            'cnpj': self.cnpj,
            'telefone': self.telefone,
            'celular': self.celular,
            'email': self.email,
            'pessoa_contato': self.pessoa_contato,
            'descricao_item': self.descricao_item,
            'quantidade': self.quantidade,
            'valor_total': self.valor_total,
            'nome_arquivo_pdf': self.nome_arquivo_pdf,
            'cod_vendedor': self.cod_vendedor,
            'data_vencimento': self.data_vencimento.strftime('%d/%m/%Y') if self.data_vencimento else None,
            'instalacao_status': self.instalacao_status,
            'qualificacoes_status': self.qualificacoes_status,
            'treinamento_status': self.treinamento_status,
            'garantia_resumo': self.garantia_resumo,
            'garantia_texto': self.garantia_texto,
            'observacoes': self.observacoes,
            'id_proposta_base': self.id_proposta_base,
            'versao': self.versao,
            'data_importacao': self.data_importacao.strftime('%d/%m/%Y %H:%M:%S') if self.data_importacao else None
        }


class ItemProposta(db.Model):
    """Modelo para armazenar itens individuais de cada proposta"""
    
    __tablename__ = 'itens_proposta'
    
    id = db.Column(db.Integer, primary_key=True)
    proposta_id = db.Column(db.Integer, db.ForeignKey('propostas.id'), nullable=False)
    numero = db.Column(db.String(10))
    descricao = db.Column(db.Text)
    quantidade = db.Column(db.String(20))
    valor_unitario = db.Column(db.String(50))
    valor_total = db.Column(db.String(50))
    
    def __repr__(self):
        return f'<ItemProposta {self.numero}>'
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'numero': self.numero,
            'descricao': self.descricao,
            'quantidade': self.quantidade,
            'valor_unitario': self.valor_unitario,
            'valor_total': self.valor_total
        }


class Cliente(db.Model):
    """Modelo para armazenar clientes"""

    __tablename__ = 'clientes'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    cnpj = db.Column(db.String(20), unique=True, nullable=False)
    cnpj_normalizado = db.Column(db.String(20), index=True)
    contato = db.Column(db.String(255))
    email = db.Column(db.String(100))
    telefone = db.Column(db.String(50))
    endereco = db.Column(db.String(255))
    setor = db.Column(db.String(100))
    data_criacao = db.Column(db.DateTime, default=datetime.now)
    cpm_status = db.Column(db.String(20))
    cpm_data = db.Column(db.Date)
    regiao = db.Column(db.String(50))

    def __repr__(self):
        return f'<Cliente {self.cnpj}>'

    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'nome': self.nome,
            'cnpj': self.cnpj,
            'contato': self.contato,
            'email': self.email,
            'telefone': self.telefone,
            'endereco': self.endereco,
            'setor': self.setor,
            'data_criacao': self.data_criacao.strftime('%d/%m/%Y %H:%M:%S') if self.data_criacao else None
        }


class Setor(db.Model):
    """Modelo para armazenar setores cadastrados"""

    __tablename__ = 'setores'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f'<Setor {self.nome}>'


class Regiao(db.Model):
    """Modelo para armazenar regiões cadastradas"""

    __tablename__ = 'regioes'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f'<Regiao {self.nome}>'


class Visita(db.Model):
    """Modelo para armazenar visitas de clientes"""

    __tablename__ = 'visitas'

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    data = db.Column(db.Date, nullable=False)
    historico = db.Column(db.Text)
    data_criacao = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f'<Visita {self.id} Cliente {self.cliente_id}>'


class Contato(db.Model):
    """Modelo para armazenar contatos de clientes"""

    __tablename__ = 'contatos'

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    nome = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100))
    telefone = db.Column(db.String(50))
    cargo = db.Column(db.String(100))
    setor = db.Column(db.String(100))
    data_criacao = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f'<Contato {self.nome} Cliente {self.cliente_id}>'


class Equipamento(db.Model):
    """Modelo para armazenar equipamentos do parque instalado"""

    __tablename__ = 'equipamentos'

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    nome = db.Column(db.String(255), nullable=False)
    quantidade = db.Column(db.Integer)
    marca = db.Column(db.String(100))
    modelo = db.Column(db.String(100))
    ano_instalacao = db.Column(db.Integer)
    data_criacao = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f'<Equipamento {self.nome} Cliente {self.cliente_id}>'


def init_db(app):
    """Inicializa o banco de dados"""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        print("Banco de dados criado com sucesso!")
