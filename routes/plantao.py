import json
import os
import base64
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, Plantao, Passagem, Ocorrencia, Ronda
from datetime import datetime

plantao_bp = Blueprint('plantao', __name__)

# ════════════════════════════════════════════════
# PLANTÃO
# ════════════════════════════════════════════════

@plantao_bp.route('/abrir', methods=['POST'])
@login_required
def abrir_plantao():
    data = request.get_json()
    # Encerra plantão anterior aberto deste vigilante
    ant = Plantao.query.filter_by(
        vigilante_id=current_user.id, encerrado=False
    ).first()
    if ant:
        ant.encerrado = True
        ant.fim = datetime.utcnow()

    p = Plantao(
        empresa_id   = current_user.empresa_id,
        vigilante_id = current_user.id,
        posto_nome   = data.get('posto_nome', ''),
        turno        = data.get('turno', ''),
    )
    db.session.add(p)
    db.session.commit()
    return jsonify({'ok': True, 'plantao_id': p.id})

@plantao_bp.route('/encerrar', methods=['POST'])
@login_required
def encerrar_plantao():
    p = _plantao_ativo()
    if not p:
        return jsonify({'erro': 'Nenhum plantão ativo'}), 404
    p.encerrado = True
    p.fim = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True})

@plantao_bp.route('/ativo')
@login_required
def plantao_ativo():
    p = _plantao_ativo()
    if not p:
        return jsonify({'plantao': None})
    return jsonify({'plantao': _plantao_dict(p)})

@plantao_bp.route('/historico')
@login_required
def historico():
    limit = int(request.args.get('limit', 30))
    if current_user.role in ('supervisor', 'gestor', 'admin'):
        plantoes = Plantao.query.filter_by(
            empresa_id=current_user.empresa_id
        ).order_by(Plantao.inicio.desc()).limit(limit).all()
    else:
        plantoes = Plantao.query.filter_by(
            vigilante_id=current_user.id
        ).order_by(Plantao.inicio.desc()).limit(limit).all()
    return jsonify([_plantao_dict(p) for p in plantoes])

# ════════════════════════════════════════════════
# PASSAGEM DE SERVIÇO
# ════════════════════════════════════════════════

@plantao_bp.route('/passagem', methods=['POST'])
@login_required
def registrar_passagem():
    p = _plantao_ativo()
    if not p:
        return jsonify({'erro': 'Abra um plantão primeiro'}), 400
    data = request.get_json()
    pas = Passagem(
        plantao_id    = p.id,
        passou_nome   = data.get('passou_nome', ''),
        recebeu_nome  = data.get('recebeu_nome', current_user.nome),
        arm_tipo      = data.get('arm_tipo', ''),
        arm_numero    = data.get('arm_numero', ''),
        arm_municao   = int(data.get('arm_municao', 0)),
        arm_condicao  = data.get('arm_condicao', ''),
        colete        = data.get('colete', ''),
        materiais     = json.dumps(data.get('materiais', []), ensure_ascii=False),
        verificacoes  = json.dumps(data.get('verificacoes', []), ensure_ascii=False),
        veiculo_placa = data.get('veiculo_placa', ''),
        veiculo_km    = int(data.get('veiculo_km', 0) or 0),
        veiculo_cond  = data.get('veiculo_cond', ''),
        observacoes   = data.get('observacoes', ''),
    )
    db.session.add(pas)
    db.session.commit()
    return jsonify({'ok': True, 'id': pas.id})

@plantao_bp.route('/passagens')
@login_required
def listar_passagens():
    p = _plantao_ativo()
    if not p:
        return jsonify([])
    return jsonify([_passagem_dict(x) for x in p.passagens])

# ════════════════════════════════════════════════
# OCORRÊNCIAS
# ════════════════════════════════════════════════

@plantao_bp.route('/ocorrencia', methods=['POST'])
@login_required
def registrar_ocorrencia():
    p = _plantao_ativo()
    if not p:
        return jsonify({'erro': 'Abra um plantão primeiro'}), 400
    data = request.get_json()

    foto_url = None
    # Foto em base64 → salva em disco
    if data.get('foto_base64'):
        foto_url = _salvar_foto(data['foto_base64'], p.id)

    oc = Ocorrencia(
        plantao_id     = p.id,
        tipo           = data.get('tipo', ''),
        urgencia       = data.get('urgencia', 'media'),
        local          = data.get('local', ''),
        descricao      = data.get('descricao', ''),
        providencias   = data.get('providencias', ''),
        envolvidos     = data.get('envolvidos', ''),
        autoridade     = data.get('autoridade', ''),
        bo_numero      = data.get('bo_numero', ''),
        foto_url       = foto_url,
        notificado_sup = data.get('notificar_supervisor', False),
    )
    db.session.add(oc)
    db.session.commit()

    # Notifica supervisor via WhatsApp se urgente
    if data.get('notificar_supervisor') or data.get('urgencia') in ('alta', 'critica'):
        from routes.panico import _enviar_whatsapp
        msg = (
            f"🚨 *OCORRÊNCIA {data.get('urgencia','').upper()}*\n"
            f"Posto: {p.posto_nome}\n"
            f"Vigilante: {current_user.nome}\n"
            f"Tipo: {data.get('tipo')}\n"
            f"Local: {data.get('local','—')}\n"
            f"Descrição: {data.get('descricao','')}\n"
            f"Hora: {datetime.now().strftime('%H:%M:%S')}"
        )
        _enviar_whatsapp(current_user.empresa_id, msg)

    return jsonify({'ok': True, 'id': oc.id})

@plantao_bp.route('/ocorrencias')
@login_required
def listar_ocorrencias():
    p = _plantao_ativo()
    if not p:
        return jsonify([])
    return jsonify([_ocorrencia_dict(x) for x in p.ocorrencias])

@plantao_bp.route('/ocorrencias/todas')
@login_required
def todas_ocorrencias():
    if current_user.role not in ('supervisor', 'gestor', 'admin'):
        return jsonify({'erro': 'Sem permissão'}), 403
    ocs = (Ocorrencia.query
           .join(Plantao)
           .filter(Plantao.empresa_id == current_user.empresa_id)
           .order_by(Ocorrencia.data_hora.desc())
           .limit(100).all())
    return jsonify([_ocorrencia_dict(x) for x in ocs])

# ════════════════════════════════════════════════
# RONDA
# ════════════════════════════════════════════════

@plantao_bp.route('/ronda/iniciar', methods=['POST'])
@login_required
def iniciar_ronda():
    p = _plantao_ativo()
    if not p:
        return jsonify({'erro': 'Abra um plantão primeiro'}), 400
    # Encerra ronda anterior se aberta
    ant = Ronda.query.filter_by(plantao_id=p.id, encerrada=False).first()
    if ant:
        ant.encerrada = True
        ant.fim = datetime.utcnow()
    r = Ronda(plantao_id=p.id)
    db.session.add(r)
    db.session.commit()
    return jsonify({'ok': True, 'ronda_id': r.id})

@plantao_bp.route('/ronda/encerrar', methods=['POST'])
@login_required
def encerrar_ronda():
    data = request.get_json()
    ronda_id = data.get('ronda_id')
    p = _plantao_ativo()
    if not p:
        return jsonify({'erro': 'Sem plantão ativo'}), 400
    r = Ronda.query.filter_by(id=ronda_id, plantao_id=p.id).first()
    if not r:
        return jsonify({'erro': 'Ronda não encontrada'}), 404
    r.fim          = datetime.utcnow()
    r.duracao_seg  = int((r.fim - r.inicio).total_seconds())
    r.pontos_marcados = json.dumps(data.get('pontos', []), ensure_ascii=False)
    r.observacoes  = data.get('observacoes', '')
    r.encerrada    = True
    db.session.commit()
    return jsonify({'ok': True, 'duracao_seg': r.duracao_seg})

@plantao_bp.route('/rondas')
@login_required
def listar_rondas():
    p = _plantao_ativo()
    if not p:
        return jsonify([])
    return jsonify([_ronda_dict(x) for x in p.rondas])

# ════════════════════════════════════════════════
# FEED SUPERVISOR (todos os plantões ativos)
# ════════════════════════════════════════════════

@plantao_bp.route('/feed')
@login_required
def feed_supervisor():
    if current_user.role not in ('supervisor', 'gestor', 'admin'):
        return jsonify({'erro': 'Sem permissão'}), 403
    plantoes_ativos = Plantao.query.filter_by(
        empresa_id=current_user.empresa_id, encerrado=False
    ).all()
    resultado = []
    for p in plantoes_ativos:
        resultado.append({
            'plantao_id' : p.id,
            'vigilante'  : p.vigilante.nome,
            'matricula'  : p.vigilante.matricula,
            'posto'      : p.posto_nome,
            'turno'      : p.turno,
            'inicio'     : p.inicio.strftime('%d/%m/%Y %H:%M'),
            'n_passagens': len(p.passagens),
            'n_rondas'   : len(p.rondas),
            'n_ocorr'    : len(p.ocorrencias),
            'n_panicos'  : len(p.panicos),
            'ronda_ativa': any(not r.encerrada for r in p.rondas),
            'panico_ativo': any(not r.atendido and not r.cancelado for r in p.panicos),
        })
    return jsonify(resultado)

# ════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════

def _plantao_ativo():
    return Plantao.query.filter_by(
        vigilante_id=current_user.id, encerrado=False
    ).order_by(Plantao.inicio.desc()).first()

def _plantao_dict(p):
    return {
        'id'        : p.id,
        'posto'     : p.posto_nome,
        'turno'     : p.turno,
        'vigilante' : p.vigilante.nome if p.vigilante else '—',
        'inicio'    : p.inicio.strftime('%d/%m/%Y %H:%M'),
        'fim'       : p.fim.strftime('%d/%m/%Y %H:%M') if p.fim else None,
        'encerrado' : p.encerrado,
        'n_passagens': len(p.passagens),
        'n_rondas'  : len(p.rondas),
        'n_ocorr'   : len(p.ocorrencias),
    }

def _passagem_dict(x):
    return {
        'id'          : x.id,
        'passou_nome' : x.passou_nome,
        'recebeu_nome': x.recebeu_nome,
        'arm_tipo'    : x.arm_tipo,
        'arm_numero'  : x.arm_numero,
        'arm_municao' : x.arm_municao,
        'arm_condicao': x.arm_condicao,
        'colete'      : x.colete,
        'materiais'   : json.loads(x.materiais or '[]'),
        'verificacoes': json.loads(x.verificacoes or '[]'),
        'veiculo_placa': x.veiculo_placa,
        'veiculo_km'  : x.veiculo_km,
        'observacoes' : x.observacoes,
        'data_hora'   : x.data_hora.strftime('%d/%m/%Y %H:%M:%S'),
    }

def _ocorrencia_dict(x):
    return {
        'id'          : x.id,
        'tipo'        : x.tipo,
        'urgencia'    : x.urgencia,
        'local'       : x.local,
        'descricao'   : x.descricao,
        'providencias': x.providencias,
        'envolvidos'  : x.envolvidos,
        'autoridade'  : x.autoridade,
        'bo_numero'   : x.bo_numero,
        'foto_url'    : x.foto_url,
        'data_hora'   : x.data_hora.strftime('%d/%m/%Y %H:%M:%S'),
    }

def _ronda_dict(x):
    dur = x.duracao_seg or 0
    return {
        'id'      : x.id,
        'inicio'  : x.inicio.strftime('%H:%M:%S'),
        'fim'     : x.fim.strftime('%H:%M:%S') if x.fim else None,
        'duracao' : f"{dur//60}min {dur%60}s",
        'pontos'  : json.loads(x.pontos_marcados or '[]'),
        'obs'     : x.observacoes,
        'encerrada': x.encerrada,
    }

def _salvar_foto(b64, plantao_id):
    try:
        pasta = f'static/fotos/{plantao_id}'
        os.makedirs(pasta, exist_ok=True)
        nome = f"{int(datetime.utcnow().timestamp())}.jpg"
        caminho = f"{pasta}/{nome}"
        with open(caminho, 'wb') as f:
            f.write(base64.b64decode(b64.split(',')[-1]))
        return f'/{caminho}'
    except Exception as e:
        print(f'Erro ao salvar foto: {e}')
        return None
