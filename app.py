import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import requests
import json

# ─────────────────────────────────────────
# APP
# ─────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'vigilantex-spynet-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///vigilantex.db').replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login_page'

# ─────────────────────────────────────────
# MODELOS
# ─────────────────────────────────────────
class Empresa(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    nome      = db.Column(db.String(200), nullable=False)
    cnpj      = db.Column(db.String(30))
    plano     = db.Column(db.String(20), default='basico')
    zapi_inst = db.Column(db.String(100), default='')
    zapi_tok  = db.Column(db.String(200), default='')
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

class Usuario(db.Model, UserMixin):
    id         = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresa.id'), nullable=False)
    nome       = db.Column(db.String(150), nullable=False)
    matricula  = db.Column(db.String(30), default='')
    email      = db.Column(db.String(150), unique=True, nullable=False)
    senha_hash = db.Column(db.String(256))
    role       = db.Column(db.String(20), default='vigilante')
    telefone   = db.Column(db.String(20), default='')
    ativo      = db.Column(db.Boolean, default=True)
    empresa    = db.relationship('Empresa', backref='usuarios')

    def set_senha(self, s): self.senha_hash = generate_password_hash(s)
    def check_senha(self, s): return check_password_hash(self.senha_hash, s)

class Plantao(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    empresa_id   = db.Column(db.Integer, db.ForeignKey('empresa.id'))
    vigilante_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    posto_nome   = db.Column(db.String(200), default='')
    turno        = db.Column(db.String(50), default='')
    inicio       = db.Column(db.DateTime, default=datetime.utcnow)
    fim          = db.Column(db.DateTime)
    encerrado    = db.Column(db.Boolean, default=False)
    vigilante    = db.relationship('Usuario', backref='plantoes')

class Passagem(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    plantao_id    = db.Column(db.Integer, db.ForeignKey('plantao.id'))
    passou_nome   = db.Column(db.String(150), default='')
    recebeu_nome  = db.Column(db.String(150), default='')
    arm_tipo      = db.Column(db.String(50), default='')
    arm_numero    = db.Column(db.String(50), default='')
    arm_municao   = db.Column(db.Integer, default=0)
    arm_condicao  = db.Column(db.String(100), default='')
    colete        = db.Column(db.String(100), default='')
    materiais     = db.Column(db.Text, default='[]')
    verificacoes  = db.Column(db.Text, default='[]')
    veiculo_placa = db.Column(db.String(20), default='')
    veiculo_km    = db.Column(db.Integer, default=0)
    observacoes   = db.Column(db.Text, default='')
    data_hora     = db.Column(db.DateTime, default=datetime.utcnow)
    plantao       = db.relationship('Plantao', backref='passagens')

class Ocorrencia(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    plantao_id    = db.Column(db.Integer, db.ForeignKey('plantao.id'))
    tipo          = db.Column(db.String(100), default='')
    urgencia      = db.Column(db.String(20), default='media')
    local         = db.Column(db.String(200), default='')
    descricao     = db.Column(db.Text, default='')
    providencias  = db.Column(db.Text, default='')
    envolvidos    = db.Column(db.Text, default='')
    autoridade    = db.Column(db.String(100), default='')
    bo_numero     = db.Column(db.String(50), default='')
    data_hora     = db.Column(db.DateTime, default=datetime.utcnow)
    plantao       = db.relationship('Plantao', backref='ocorrencias')

class Ronda(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    plantao_id     = db.Column(db.Integer, db.ForeignKey('plantao.id'))
    inicio         = db.Column(db.DateTime, default=datetime.utcnow)
    fim            = db.Column(db.DateTime)
    duracao_seg    = db.Column(db.Integer, default=0)
    pontos         = db.Column(db.Text, default='[]')
    observacoes    = db.Column(db.Text, default='')
    encerrada      = db.Column(db.Boolean, default=False)
    plantao        = db.relationship('Plantao', backref='rondas')

class Panico(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    plantao_id     = db.Column(db.Integer, db.ForeignKey('plantao.id'))
    tipo           = db.Column(db.String(100), default='')
    vigilante_nome = db.Column(db.String(150), default='')
    posto_nome     = db.Column(db.String(200), default='')
    data_hora      = db.Column(db.DateTime, default=datetime.utcnow)
    atendido       = db.Column(db.Boolean, default=False)
    cancelado      = db.Column(db.Boolean, default=False)
    plantao        = db.relationship('Plantao', backref='panicos')

@login_manager.user_loader
def load_user(uid): return Usuario.query.get(int(uid))

# ─────────────────────────────────────────
# CRIAR TABELAS E ADMIN PADRÃO
# ─────────────────────────────────────────
with app.app_context():
    db.create_all()
    if not Empresa.query.first():
        emp = Empresa(nome='SPYNET Tecnologia Forense', cnpj='64.000.808/0001-51', plano='empresarial')
        db.session.add(emp)
        db.session.flush()
        adm = Usuario(empresa_id=emp.id, nome='Administrador', email='admin@vigilantex.com',
                      role='admin', matricula='0001')
        adm.set_senha('admin123')
        db.session.add(adm)
        db.session.commit()
        print('✅ Admin criado: admin@vigilantex.com / admin123')

# ─────────────────────────────────────────
# PÁGINAS
# ─────────────────────────────────────────
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('painel'))
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/painel')
@login_required
def painel():
    return render_template('painel.html', usuario=current_user)

# ─────────────────────────────────────────
# API — AUTH
# ─────────────────────────────────────────
@app.route('/api/login', methods=['POST'])
def api_login():
    d = request.get_json()
    u = Usuario.query.filter_by(email=d.get('email','').lower().strip(), ativo=True).first()
    if not u or not u.check_senha(d.get('senha','')):
        return jsonify({'erro': 'Email ou senha incorretos'}), 401
    login_user(u, remember=True)
    return jsonify({'ok': True, 'usuario': {'id': u.id, 'nome': u.nome,
        'matricula': u.matricula, 'role': u.role, 'empresa_id': u.empresa_id}})

@app.route('/api/logout', methods=['POST'])
def api_logout():
    logout_user()
    return jsonify({'ok': True})

@app.route('/api/me')
@login_required
def api_me():
    return jsonify({'id': current_user.id, 'nome': current_user.nome,
        'matricula': current_user.matricula, 'role': current_user.role,
        'empresa_id': current_user.empresa_id, 'telefone': current_user.telefone})

@app.route('/api/usuarios', methods=['GET'])
@login_required
def api_usuarios():
    if current_user.role not in ('admin','gestor','supervisor'):
        return jsonify({'erro': 'Sem permissão'}), 403
    us = Usuario.query.filter_by(empresa_id=current_user.empresa_id, ativo=True).all()
    return jsonify([{'id':u.id,'nome':u.nome,'matricula':u.matricula,'role':u.role,'email':u.email,'telefone':u.telefone} for u in us])

@app.route('/api/usuarios', methods=['POST'])
@login_required
def api_criar_usuario():
    if current_user.role not in ('admin','gestor'):
        return jsonify({'erro': 'Sem permissão'}), 403
    d = request.get_json()
    if Usuario.query.filter_by(email=d.get('email','')).first():
        return jsonify({'erro': 'Email já cadastrado'}), 400
    u = Usuario(empresa_id=current_user.empresa_id, nome=d['nome'],
                matricula=d.get('matricula',''), email=d['email'],
                role=d.get('role','vigilante'), telefone=d.get('telefone',''))
    u.set_senha(d.get('senha','123456'))
    db.session.add(u); db.session.commit()
    return jsonify({'ok': True, 'id': u.id})

@app.route('/api/senha', methods=['POST'])
@login_required
def api_senha():
    d = request.get_json()
    if not current_user.check_senha(d.get('senha_atual','')):
        return jsonify({'erro': 'Senha atual incorreta'}), 400
    current_user.set_senha(d['nova_senha'])
    db.session.commit()
    return jsonify({'ok': True})

# ─────────────────────────────────────────
# API — PLANTÃO
# ─────────────────────────────────────────
def plantao_ativo():
    return Plantao.query.filter_by(vigilante_id=current_user.id, encerrado=False)\
                        .order_by(Plantao.inicio.desc()).first()

@app.route('/api/plantao/abrir', methods=['POST'])
@login_required
def api_abrir():
    d = request.get_json()
    ant = plantao_ativo()
    if ant: ant.encerrado=True; ant.fim=datetime.utcnow()
    p = Plantao(empresa_id=current_user.empresa_id, vigilante_id=current_user.id,
                posto_nome=d.get('posto_nome',''), turno=d.get('turno',''))
    db.session.add(p); db.session.commit()
    return jsonify({'ok': True, 'plantao_id': p.id})

@app.route('/api/plantao/encerrar', methods=['POST'])
@login_required
def api_encerrar():
    p = plantao_ativo()
    if not p: return jsonify({'erro': 'Sem plantão ativo'}), 404
    p.encerrado=True; p.fim=datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/plantao/ativo')
@login_required
def api_ativo():
    p = plantao_ativo()
    if not p: return jsonify({'plantao': None})
    return jsonify({'plantao': {'id':p.id,'posto':p.posto_nome,'turno':p.turno,
        'inicio':p.inicio.strftime('%d/%m/%Y %H:%M'),
        'n_passagens':len(p.passagens),'n_rondas':len(p.rondas),
        'n_ocorr':len(p.ocorrencias),'n_panicos':len(p.panicos)}})

@app.route('/api/plantao/historico')
@login_required
def api_historico():
    if current_user.role in ('supervisor','gestor','admin'):
        ps = Plantao.query.filter_by(empresa_id=current_user.empresa_id)\
                          .order_by(Plantao.inicio.desc()).limit(50).all()
    else:
        ps = Plantao.query.filter_by(vigilante_id=current_user.id)\
                          .order_by(Plantao.inicio.desc()).limit(30).all()
    return jsonify([{'id':p.id,'posto':p.posto_nome,'turno':p.turno,
        'vigilante':p.vigilante.nome,'inicio':p.inicio.strftime('%d/%m/%Y %H:%M'),
        'encerrado':p.encerrado,'n_ocorr':len(p.ocorrencias),'n_rondas':len(p.rondas)} for p in ps])

# ─────────────────────────────────────────
# API — PASSAGEM
# ─────────────────────────────────────────
@app.route('/api/passagem', methods=['POST'])
@login_required
def api_passagem():
    p = plantao_ativo()
    if not p: return jsonify({'erro': 'Abra um plantão primeiro'}), 400
    d = request.get_json()
    pas = Passagem(plantao_id=p.id, passou_nome=d.get('passou_nome',''),
        recebeu_nome=d.get('recebeu_nome', current_user.nome),
        arm_tipo=d.get('arm_tipo',''), arm_numero=d.get('arm_numero',''),
        arm_municao=int(d.get('arm_municao',0) or 0),
        arm_condicao=d.get('arm_condicao',''), colete=d.get('colete',''),
        materiais=json.dumps(d.get('materiais',[]),ensure_ascii=False),
        verificacoes=json.dumps(d.get('verificacoes',[]),ensure_ascii=False),
        veiculo_placa=d.get('veiculo_placa',''),
        veiculo_km=int(d.get('veiculo_km',0) or 0),
        observacoes=d.get('observacoes',''))
    db.session.add(pas); db.session.commit()
    return jsonify({'ok': True, 'id': pas.id})

@app.route('/api/passagens')
@login_required
def api_passagens():
    p = plantao_ativo()
    if not p: return jsonify([])
    return jsonify([{'id':x.id,'passou_nome':x.passou_nome,'recebeu_nome':x.recebeu_nome,
        'arm_tipo':x.arm_tipo,'arm_numero':x.arm_numero,'arm_municao':x.arm_municao,
        'colete':x.colete,'materiais':json.loads(x.materiais or '[]'),
        'verificacoes':json.loads(x.verificacoes or '[]'),
        'veiculo_placa':x.veiculo_placa,'veiculo_km':x.veiculo_km,
        'observacoes':x.observacoes,'data_hora':x.data_hora.strftime('%d/%m/%Y %H:%M:%S')}
        for x in p.passagens])

# ─────────────────────────────────────────
# API — OCORRÊNCIA
# ─────────────────────────────────────────
@app.route('/api/ocorrencia', methods=['POST'])
@login_required
def api_ocorrencia():
    p = plantao_ativo()
    if not p: return jsonify({'erro': 'Abra um plantão primeiro'}), 400
    d = request.get_json()
    oc = Ocorrencia(plantao_id=p.id, tipo=d.get('tipo',''),
        urgencia=d.get('urgencia','media'), local=d.get('local',''),
        descricao=d.get('descricao',''), providencias=d.get('providencias',''),
        envolvidos=d.get('envolvidos',''), autoridade=d.get('autoridade',''),
        bo_numero=d.get('bo_numero',''))
    db.session.add(oc); db.session.commit()
    if d.get('notificar') or d.get('urgencia') in ('alta','critica'):
        _whatsapp(current_user.empresa_id,
            f"🚨 *OCORRÊNCIA {d.get('urgencia','').upper()}*\n"
            f"Posto: {p.posto_nome}\nVigilante: {current_user.nome}\n"
            f"Tipo: {d.get('tipo')}\nLocal: {d.get('local','—')}\n"
            f"Hora: {datetime.now().strftime('%H:%M:%S')}")
    return jsonify({'ok': True, 'id': oc.id})

@app.route('/api/ocorrencias')
@login_required
def api_ocorrencias():
    p = plantao_ativo()
    if not p: return jsonify([])
    return jsonify([{'id':x.id,'tipo':x.tipo,'urgencia':x.urgencia,'local':x.local,
        'descricao':x.descricao,'providencias':x.providencias,'autoridade':x.autoridade,
        'bo_numero':x.bo_numero,'data_hora':x.data_hora.strftime('%d/%m/%Y %H:%M:%S')}
        for x in p.ocorrencias])

@app.route('/api/ocorrencias/todas')
@login_required
def api_ocorrencias_todas():
    if current_user.role not in ('supervisor','gestor','admin'):
        return jsonify({'erro': 'Sem permissão'}), 403
    ocs = Ocorrencia.query.join(Plantao).filter(
        Plantao.empresa_id==current_user.empresa_id)\
        .order_by(Ocorrencia.data_hora.desc()).limit(100).all()
    return jsonify([{'id':x.id,'tipo':x.tipo,'urgencia':x.urgencia,'local':x.local,
        'descricao':x.descricao,'vigilante':x.plantao.vigilante.nome,
        'posto':x.plantao.posto_nome,'data_hora':x.data_hora.strftime('%d/%m/%Y %H:%M:%S')}
        for x in ocs])

# ─────────────────────────────────────────
# API — RONDA
# ─────────────────────────────────────────
@app.route('/api/ronda/iniciar', methods=['POST'])
@login_required
def api_iniciar_ronda():
    p = plantao_ativo()
    if not p: return jsonify({'erro': 'Sem plantão ativo'}), 400
    ant = Ronda.query.filter_by(plantao_id=p.id, encerrada=False).first()
    if ant: ant.encerrada=True; ant.fim=datetime.utcnow()
    r = Ronda(plantao_id=p.id)
    db.session.add(r); db.session.commit()
    return jsonify({'ok': True, 'ronda_id': r.id})

@app.route('/api/ronda/encerrar', methods=['POST'])
@login_required
def api_encerrar_ronda():
    d = request.get_json()
    p = plantao_ativo()
    if not p: return jsonify({'erro': 'Sem plantão'}), 400
    r = Ronda.query.filter_by(id=d.get('ronda_id'), plantao_id=p.id).first()
    if not r: return jsonify({'erro': 'Ronda não encontrada'}), 404
    r.fim=datetime.utcnow()
    r.duracao_seg=int((r.fim-r.inicio).total_seconds())
    r.pontos=json.dumps(d.get('pontos',[]),ensure_ascii=False)
    r.observacoes=d.get('observacoes','')
    r.encerrada=True
    db.session.commit()
    return jsonify({'ok': True, 'duracao_seg': r.duracao_seg})

@app.route('/api/rondas')
@login_required
def api_rondas():
    p = plantao_ativo()
    if not p: return jsonify([])
    return jsonify([{'id':x.id,'inicio':x.inicio.strftime('%H:%M:%S'),
        'fim':x.fim.strftime('%H:%M:%S') if x.fim else None,
        'duracao':f"{x.duracao_seg//60}min {x.duracao_seg%60}s" if x.duracao_seg else '—',
        'pontos':json.loads(x.pontos or '[]'),'obs':x.observacoes,'encerrada':x.encerrada}
        for x in p.rondas])

# ─────────────────────────────────────────
# API — PÂNICO
# ─────────────────────────────────────────
@app.route('/api/panico/acionar', methods=['POST'])
@login_required
def api_panico():
    p = plantao_ativo()
    if not p: return jsonify({'erro': 'Sem plantão ativo'}), 400
    d = request.get_json()
    pan = Panico(plantao_id=p.id, tipo=d.get('tipo','Emergência'),
                 vigilante_nome=current_user.nome, posto_nome=p.posto_nome)
    db.session.add(pan); db.session.commit()
    enviado = _whatsapp(current_user.empresa_id,
        f"🆘🆘 *ALERTA DE PÂNICO* 🆘🆘\n\n"
        f"*Tipo:* {pan.tipo}\n"
        f"*Vigilante:* {current_user.nome} (Mat. {current_user.matricula or '—'})\n"
        f"*Posto:* {p.posto_nome}\n"
        f"*Hora:* {datetime.now().strftime('%H:%M:%S — %d/%m/%Y')}\n\n"
        f"⚠️ Acesse o painel VIGILANTEX PRO para confirmar.")
    return jsonify({'ok': True, 'panico_id': pan.id, 'whatsapp': enviado})

@app.route('/api/panico/cancelar', methods=['POST'])
@login_required
def api_cancelar_panico():
    d = request.get_json()
    pan = Panico.query.get(d.get('panico_id'))
    if not pan: return jsonify({'erro': 'Não encontrado'}), 404
    pan.cancelado=True; db.session.commit()
    _whatsapp(current_user.empresa_id,
        f"✅ *PÂNICO CANCELADO — FALSO ALARME*\n"
        f"Vigilante: {current_user.nome}\nPosto: {pan.posto_nome}\n"
        f"Hora: {datetime.now().strftime('%H:%M:%S')}")
    return jsonify({'ok': True})

@app.route('/api/panico/atender', methods=['POST'])
@login_required
def api_atender_panico():
    if current_user.role not in ('supervisor','gestor','admin'):
        return jsonify({'erro': 'Sem permissão'}), 403
    d = request.get_json()
    pan = Panico.query.get(d.get('panico_id'))
    if not pan: return jsonify({'erro': 'Não encontrado'}), 404
    pan.atendido=True; db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/panico/ativos')
@login_required
def api_panicos_ativos():
    if current_user.role not in ('supervisor','gestor','admin'):
        return jsonify({'erro': 'Sem permissão'}), 403
    pans = Panico.query.join(Plantao).filter(
        Plantao.empresa_id==current_user.empresa_id,
        Panico.atendido==False, Panico.cancelado==False).all()
    return jsonify([{'id':p.id,'tipo':p.tipo,'vigilante':p.vigilante_nome,
        'posto':p.posto_nome,'hora':p.data_hora.strftime('%H:%M:%S')} for p in pans])

# ─────────────────────────────────────────
# API — FEED SUPERVISOR
# ─────────────────────────────────────────
@app.route('/api/feed')
@login_required
def api_feed():
    if current_user.role not in ('supervisor','gestor','admin'):
        return jsonify({'erro': 'Sem permissão'}), 403
    plantoes = Plantao.query.filter_by(empresa_id=current_user.empresa_id, encerrado=False).all()
    return jsonify([{
        'plantao_id':p.id,'vigilante':p.vigilante.nome,'matricula':p.vigilante.matricula,
        'posto':p.posto_nome,'turno':p.turno,'inicio':p.inicio.strftime('%d/%m/%Y %H:%M'),
        'n_passagens':len(p.passagens),'n_rondas':len(p.rondas),
        'n_ocorr':len(p.ocorrencias),'n_panicos':len(p.panicos),
        'ronda_ativa':any(not r.encerrada for r in p.rondas),
        'panico_ativo':any(not r.atendido and not r.cancelado for r in p.panicos),
    } for p in plantoes])

# ─────────────────────────────────────────
# API — ADMIN
# ─────────────────────────────────────────
@app.route('/api/admin/dashboard')
@login_required
def api_dashboard():
    if current_user.role not in ('admin','gestor'):
        return jsonify({'erro': 'Sem permissão'}), 403
    from sqlalchemy import func
    emp_id = current_user.empresa_id
    return jsonify({
        'total_vigilantes': Usuario.query.filter_by(empresa_id=emp_id,role='vigilante',ativo=True).count(),
        'plantoes_ativos' : Plantao.query.filter_by(empresa_id=emp_id,encerrado=False).count(),
        'total_ocorrencias': Ocorrencia.query.join(Plantao).filter(Plantao.empresa_id==emp_id).count(),
        'total_panicos'   : Panico.query.join(Plantao).filter(Plantao.empresa_id==emp_id).count(),
    })

@app.route('/api/admin/zapi', methods=['POST'])
@login_required
def api_zapi():
    if current_user.role not in ('admin','gestor'):
        return jsonify({'erro': 'Sem permissão'}), 403
    d = request.get_json()
    emp = Empresa.query.get(current_user.empresa_id)
    emp.zapi_inst=d.get('instance',''); emp.zapi_tok=d.get('token','')
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/admin/reset-senha', methods=['POST'])
@login_required
def api_reset_senha():
    if current_user.role not in ('admin','gestor'):
        return jsonify({'erro': 'Sem permissão'}), 403
    d = request.get_json()
    u = Usuario.query.get(d.get('user_id'))
    if not u or u.empresa_id!=current_user.empresa_id:
        return jsonify({'erro': 'Usuário não encontrado'}), 404
    u.set_senha(d.get('nova_senha','123456'))
    db.session.commit()
    return jsonify({'ok': True})

# ─────────────────────────────────────────
# WHATSAPP Z-API
# ─────────────────────────────────────────
def _whatsapp(empresa_id, mensagem):
    try:
        emp = Empresa.query.get(empresa_id)
        if not emp or not emp.zapi_inst or not emp.zapi_tok:
            return False
        sups = Usuario.query.filter(
            Usuario.empresa_id==empresa_id,
            Usuario.role.in_(['supervisor','gestor','admin']),
            Usuario.telefone!='', Usuario.ativo==True).all()
        url = f"https://api.z-api.io/instances/{emp.zapi_inst}/token/{emp.zapi_tok}/send-text"
        ok = False
        for s in sups:
            tel = s.telefone.replace('+','').replace('-','').replace(' ','').replace('(','').replace(')','')
            if not tel.startswith('55'): tel='55'+tel
            r = requests.post(url, json={'phone':tel,'message':mensagem}, timeout=8)
            if r.status_code==200: ok=True
        return ok
    except Exception as e:
        print(f'WhatsApp erro: {e}')
        return False

# ─────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────
@app.route('/health')
def health():
    return jsonify({'status':'ok','sistema':'VIGILANTEX PRO','versao':'2026'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
