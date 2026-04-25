from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

# =====================================================
# EMPRESA
# =====================================================
class Empresa(db.Model):
    __tablename__ = 'empresas'
    id          = db.Column(db.Integer, primary_key=True)
    nome        = db.Column(db.String(200), nullable=False)
    cnpj        = db.Column(db.String(20), unique=True)
    plano       = db.Column(db.String(20), default='basico')  # basico/pro/empresarial
    ativo       = db.Column(db.Boolean, default=True)
    criado_em   = db.Column(db.DateTime, default=datetime.utcnow)
    # Z-API
    zapi_instance = db.Column(db.String(100))
    zapi_token    = db.Column(db.String(200))
    # Relacionamentos
    usuarios    = db.relationship('Usuario', backref='empresa', lazy=True)
    postos      = db.relationship('Posto', backref='empresa', lazy=True)

# =====================================================
# USUÁRIO (vigilante, supervisor, gestor)
# =====================================================
class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    id          = db.Column(db.Integer, primary_key=True)
    empresa_id  = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    nome        = db.Column(db.String(150), nullable=False)
    matricula   = db.Column(db.String(30))
    email       = db.Column(db.String(150), unique=True)
    senha_hash  = db.Column(db.String(256))
    role        = db.Column(db.String(20), default='vigilante')  # vigilante/supervisor/gestor/admin
    telefone    = db.Column(db.String(20))   # para receber alertas WhatsApp
    ativo       = db.Column(db.Boolean, default=True)
    criado_em   = db.Column(db.DateTime, default=datetime.utcnow)

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'matricula': self.matricula,
            'role': self.role,
            'empresa_id': self.empresa_id,
        }

# =====================================================
# POSTO DE TRABALHO
# =====================================================
class Posto(db.Model):
    __tablename__ = 'postos'
    id          = db.Column(db.Integer, primary_key=True)
    empresa_id  = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    nome        = db.Column(db.String(200), nullable=False)
    endereco    = db.Column(db.String(300))
    descricao   = db.Column(db.Text)
    ativo       = db.Column(db.Boolean, default=True)
    criado_em   = db.Column(db.DateTime, default=datetime.utcnow)
    # QR codes dos pontos de ronda
    pontos_ronda = db.relationship('PontoRonda', backref='posto', lazy=True)

class PontoRonda(db.Model):
    __tablename__ = 'pontos_ronda'
    id          = db.Column(db.Integer, primary_key=True)
    posto_id    = db.Column(db.Integer, db.ForeignKey('postos.id'), nullable=False)
    nome        = db.Column(db.String(100), nullable=False)
    qr_code     = db.Column(db.String(100), unique=True)  # código único para QR
    ativo       = db.Column(db.Boolean, default=True)

# =====================================================
# PLANTÃO
# =====================================================
class Plantao(db.Model):
    __tablename__ = 'plantoes'
    id            = db.Column(db.Integer, primary_key=True)
    empresa_id    = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    posto_id      = db.Column(db.Integer, db.ForeignKey('postos.id'), nullable=True)
    posto_nome    = db.Column(db.String(200))  # nome livre digitado
    vigilante_id  = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    turno         = db.Column(db.String(50))
    inicio        = db.Column(db.DateTime, default=datetime.utcnow)
    fim           = db.Column(db.DateTime)
    encerrado     = db.Column(db.Boolean, default=False)
    # Relacionamentos
    vigilante     = db.relationship('Usuario', foreign_keys=[vigilante_id])
    passagens     = db.relationship('Passagem', backref='plantao', lazy=True)
    ocorrencias   = db.relationship('Ocorrencia', backref='plantao', lazy=True)
    rondas        = db.relationship('Ronda', backref='plantao', lazy=True)
    panicos       = db.relationship('Panico', backref='plantao', lazy=True)

# =====================================================
# PASSAGEM DE SERVIÇO
# =====================================================
class Passagem(db.Model):
    __tablename__ = 'passagens'
    id              = db.Column(db.Integer, primary_key=True)
    plantao_id      = db.Column(db.Integer, db.ForeignKey('plantoes.id'), nullable=False)
    passou_nome     = db.Column(db.String(150))   # quem passou
    recebeu_nome    = db.Column(db.String(150))   # quem recebeu
    arm_tipo        = db.Column(db.String(50))
    arm_numero      = db.Column(db.String(50))
    arm_municao     = db.Column(db.Integer, default=0)
    arm_condicao    = db.Column(db.String(100))
    colete          = db.Column(db.String(100))
    materiais       = db.Column(db.Text)           # JSON string
    verificacoes    = db.Column(db.Text)           # JSON string
    veiculo_placa   = db.Column(db.String(20))
    veiculo_km      = db.Column(db.Integer)
    veiculo_cond    = db.Column(db.String(100))
    observacoes     = db.Column(db.Text)
    data_hora       = db.Column(db.DateTime, default=datetime.utcnow)

# =====================================================
# OCORRÊNCIA
# =====================================================
class Ocorrencia(db.Model):
    __tablename__ = 'ocorrencias'
    id              = db.Column(db.Integer, primary_key=True)
    plantao_id      = db.Column(db.Integer, db.ForeignKey('plantoes.id'), nullable=False)
    tipo            = db.Column(db.String(100), nullable=False)
    urgencia        = db.Column(db.String(20), default='media')
    local           = db.Column(db.String(200))
    descricao       = db.Column(db.Text, nullable=False)
    providencias    = db.Column(db.Text)
    envolvidos      = db.Column(db.Text)
    autoridade      = db.Column(db.String(100))
    bo_numero       = db.Column(db.String(50))
    foto_url        = db.Column(db.String(500))    # foto anexada
    notificado_sup  = db.Column(db.Boolean, default=False)
    data_hora       = db.Column(db.DateTime, default=datetime.utcnow)

# =====================================================
# RONDA
# =====================================================
class Ronda(db.Model):
    __tablename__ = 'rondas'
    id              = db.Column(db.Integer, primary_key=True)
    plantao_id      = db.Column(db.Integer, db.ForeignKey('plantoes.id'), nullable=False)
    inicio          = db.Column(db.DateTime, default=datetime.utcnow)
    fim             = db.Column(db.DateTime)
    duracao_seg     = db.Column(db.Integer)
    pontos_marcados = db.Column(db.Text)   # JSON string
    observacoes     = db.Column(db.Text)
    encerrada       = db.Column(db.Boolean, default=False)

class VerificacaoQR(db.Model):
    """Cada scan de QR Code na ronda"""
    __tablename__ = 'verificacoes_qr'
    id          = db.Column(db.Integer, primary_key=True)
    ronda_id    = db.Column(db.Integer, db.ForeignKey('rondas.id'), nullable=False)
    ponto_id    = db.Column(db.Integer, db.ForeignKey('pontos_ronda.id'), nullable=False)
    data_hora   = db.Column(db.DateTime, default=datetime.utcnow)
    ponto       = db.relationship('PontoRonda')

# =====================================================
# PÂNICO
# =====================================================
class Panico(db.Model):
    __tablename__ = 'panicos'
    id              = db.Column(db.Integer, primary_key=True)
    plantao_id      = db.Column(db.Integer, db.ForeignKey('plantoes.id'), nullable=False)
    tipo            = db.Column(db.String(100), nullable=False)
    vigilante_nome  = db.Column(db.String(150))
    posto_nome      = db.Column(db.String(200))
    data_hora       = db.Column(db.DateTime, default=datetime.utcnow)
    atendido        = db.Column(db.Boolean, default=False)
    atendido_em     = db.Column(db.DateTime)
    cancelado       = db.Column(db.Boolean, default=False)
    whatsapp_enviado = db.Column(db.Boolean, default=False)
