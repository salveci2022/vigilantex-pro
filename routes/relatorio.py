import json
import io
from flask import Blueprint, request, jsonify, send_file, make_response
from flask_login import login_required, current_user
from models import db, Plantao, Passagem, Ocorrencia, Ronda, Panico
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

relatorio_bp = Blueprint('relatorio', __name__)

# Cores
AZUL       = colors.HexColor('#0088dd')
AZUL_ESC   = colors.HexColor('#004488')
PRETO      = colors.HexColor('#0a0f1e')
CINZA_ESC  = colors.HexColor('#2a3a4a')
CINZA      = colors.HexColor('#607080')
VERDE      = colors.HexColor('#00aa55')
VERMELHO   = colors.HexColor('#dd2244')
AMARELO    = colors.HexColor('#cc9900')
LARANJA    = colors.HexColor('#dd6600')
BRANCO     = colors.white
FUNDO_HDR  = colors.HexColor('#04070f')
FUNDO_LIN  = colors.HexColor('#f0f5fa')

@relatorio_bp.route('/pdf/<int:plantao_id>')
@login_required
def gerar_pdf(plantao_id):
    plantao = Plantao.query.get_or_404(plantao_id)
    if plantao.empresa_id != current_user.empresa_id:
        return jsonify({'erro': 'Sem permissão'}), 403

    buf = io.BytesIO()
    _gerar_pdf_plantao(buf, plantao)
    buf.seek(0)

    nome = f"Relatorio_Plantao_{plantao_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True, download_name=nome)

@relatorio_bp.route('/pdf/atual')
@login_required
def pdf_atual():
    plantao = Plantao.query.filter_by(
        vigilante_id=current_user.id
    ).order_by(Plantao.inicio.desc()).first()
    if not plantao:
        return jsonify({'erro': 'Nenhum plantão encontrado'}), 404

    buf = io.BytesIO()
    _gerar_pdf_plantao(buf, plantao)
    buf.seek(0)

    nome = f"Relatorio_Plantao_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True, download_name=nome)


def _gerar_pdf_plantao(buf, plantao):
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=20*mm
    )
    story = []
    W = A4[0] - 30*mm

    # ── ESTILOS ──────────────────────────────────
    def estilo(nome, **kw):
        base = getSampleStyleSheet()['Normal']
        return ParagraphStyle(nome, parent=base, **kw)

    sT = estilo('titulo', fontSize=20, fontName='Helvetica-Bold', textColor=BRANCO,
                alignment=TA_CENTER, spaceAfter=2)
    sSub = estilo('sub', fontSize=9, fontName='Helvetica', textColor=AZUL,
                  alignment=TA_CENTER, spaceAfter=2)
    sSecao = estilo('secao', fontSize=10, fontName='Helvetica-Bold', textColor=AZUL,
                    spaceBefore=8, spaceAfter=4)
    sNorm = estilo('norm', fontSize=8, fontName='Helvetica', textColor=CINZA_ESC,
                   leading=13)
    sLabel = estilo('lbl', fontSize=7, fontName='Helvetica-Bold', textColor=CINZA)
    sValor = estilo('val', fontSize=8, fontName='Helvetica', textColor=PRETO)
    sAlerta = estilo('alerta', fontSize=8, fontName='Helvetica-Bold', textColor=VERMELHO)
    sObs = estilo('obs', fontSize=8, fontName='Helvetica-Oblique', textColor=CINZA_ESC,
                  leftIndent=8)

    def linha_hr(cor=AZUL, espessura=0.5):
        return HRFlowable(width='100%', thickness=espessura, color=cor, spaceAfter=4)

    # ── CABEÇALHO ────────────────────────────────
    hdr_data = [
        [Paragraph('VIGILANTEX PRO', sT),
         Paragraph('RELATÓRIO OFICIAL DE PLANTÃO<br/>Sistema de Gestão de Segurança Patrimonial · v2026', sSub)]
    ]
    hdr = Table(hdr_data, colWidths=[W*0.4, W*0.6])
    hdr.setStyle(TableStyle([
        ('BACKGROUND',   (0,0), (-1,-1), FUNDO_HDR),
        ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
        ('ROWPADDING',   (0,0), (-1,-1), 12),
        ('TOPPADDING',   (0,0), (-1,-1), 14),
        ('BOTTOMPADDING',(0,0), (-1,-1), 14),
        ('LEFTPADDING',  (0,0), (0,-1),  10),
        ('LINEAFTER',    (0,0), (0,-1),  0.5, AZUL),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 6))

    # ── IDENTIFICAÇÃO ────────────────────────────
    story.append(Paragraph('IDENTIFICAÇÃO DO PLANTÃO', sSecao))
    story.append(linha_hr())

    def campo(label, valor):
        return [Paragraph(label, sLabel), Paragraph(str(valor or '—'), sValor)]

    ini = plantao.inicio.strftime('%d/%m/%Y às %H:%M:%S')
    fim = plantao.fim.strftime('%d/%m/%Y às %H:%M:%S') if plantao.fim else 'Em andamento'
    dur = ''
    if plantao.fim:
        d = int((plantao.fim - plantao.inicio).total_seconds())
        dur = f"{d//3600}h {(d%3600)//60}min"

    id_data = [
        campo('Posto / Local de Trabalho:', plantao.posto_nome),
        campo('Vigilante Responsável:', f"{plantao.vigilante.nome} — Mat. {plantao.vigilante.matricula or '—'}"),
        campo('Turno:', plantao.turno),
        campo('Início do Plantão:', ini),
        campo('Encerramento:', fim),
        campo('Duração Total:', dur or '—'),
        campo('Relatório Gerado em:', datetime.now().strftime('%d/%m/%Y às %H:%M:%S')),
    ]
    id_tbl = Table(id_data, colWidths=[W*0.35, W*0.65])
    id_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), FUNDO_LIN),
        ('ROWPADDING', (0,0), (-1,-1), 5),
        ('LINEBELOW',  (0,0), (-1,-1), 0.3, colors.HexColor('#d0dde8')),
        ('VALIGN',     (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(id_tbl)
    story.append(Spacer(1, 10))

    # ── KPIs ─────────────────────────────────────
    kpi_data = [[
        _kpi_cell('PASSAGENS',  len(plantao.passagens),  AZUL),
        _kpi_cell('RONDAS',     len(plantao.rondas),     VERDE),
        _kpi_cell('OCORRÊNCIAS',len(plantao.ocorrencias),VERMELHO),
        _kpi_cell('PÂNICOS',    len(plantao.panicos),    AMARELO),
    ]]
    kpi_tbl = Table(kpi_data, colWidths=[W/4]*4)
    kpi_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), FUNDO_HDR),
        ('ROWPADDING', (0,0), (-1,-1), 10),
        ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
        ('LINEAFTER',  (0,0), (2,-1),  0.5, CINZA),
    ]))
    story.append(kpi_tbl)
    story.append(Spacer(1, 12))

    # ── PASSAGENS ────────────────────────────────
    if plantao.passagens:
        story.append(Paragraph('PASSAGENS DE SERVIÇO', sSecao))
        story.append(linha_hr())
        for i, pas in enumerate(plantao.passagens):
            mats = json.loads(pas.materiais or '[]')
            vers = json.loads(pas.verificacoes or '[]')
            p_data = [
                [Paragraph(f'[{i+1:02d}] {pas.data_hora.strftime("%d/%m/%Y às %H:%M:%S")}',
                           estilo('ph', fontSize=9, fontName='Helvetica-Bold', textColor=AZUL))],
                campo('Passou o serviço:', pas.passou_nome),
                campo('Recebeu o serviço:', pas.recebeu_nome),
                campo('Armamento:', f'{pas.arm_tipo or "Desarmado"} Nº {pas.arm_numero or "—"} | Munição: {pas.arm_municao}'),
                campo('Condição da arma:', pas.arm_condicao),
                campo('Colete balístico:', pas.colete),
                campo('Materiais recebidos:', ', '.join(mats) if mats else '—'),
                campo('Verificações do posto:', ', '.join(vers) if vers else '—'),
            ]
            if pas.veiculo_placa:
                p_data.append(campo('Veículo:', f'{pas.veiculo_placa} | KM: {pas.veiculo_km or "—"}'))
            if pas.observacoes:
                p_data.append([Paragraph('Observações:', sLabel),
                               Paragraph(pas.observacoes, sObs)])

            tbl = Table(p_data, colWidths=[W*0.35, W*0.65])
            tbl.setStyle(TableStyle([
                ('SPAN',       (0,0), (-1,0)),
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e8f0f8')),
                ('BACKGROUND', (0,1), (0,-1), FUNDO_LIN),
                ('ROWPADDING', (0,0), (-1,-1), 5),
                ('LINEBELOW',  (0,0), (-1,-1), 0.3, colors.HexColor('#d0dde8')),
                ('VALIGN',     (0,0), (-1,-1), 'TOP'),
            ]))
            story.append(tbl)
            story.append(Spacer(1, 6))
        story.append(Spacer(1, 6))

    # ── RONDAS ───────────────────────────────────
    if plantao.rondas:
        story.append(Paragraph('HISTÓRICO DE RONDAS', sSecao))
        story.append(linha_hr(AMARELO))
        r_rows = [['Nº', 'Início', 'Término', 'Duração', 'Pontos', 'Obs']]
        for i, r in enumerate(plantao.rondas):
            dur_s = r.duracao_seg or 0
            pontos = json.loads(r.pontos_marcados or '[]')
            r_rows.append([
                str(i+1),
                r.inicio.strftime('%H:%M:%S'),
                r.fim.strftime('%H:%M:%S') if r.fim else '—',
                f"{dur_s//60}min {dur_s%60}s",
                ', '.join(pontos) if pontos else '—',
                r.observacoes or '—',
            ])
        r_tbl = Table(r_rows, colWidths=[8*mm, 22*mm, 22*mm, 20*mm, 55*mm, None])
        r_tbl.setStyle(TableStyle([
            ('BACKGROUND',   (0,0), (-1,0), colors.HexColor('#fff8e0')),
            ('FONTNAME',     (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',     (0,0), (-1,-1), 7),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[BRANCO, FUNDO_LIN]),
            ('GRID',         (0,0), (-1,-1), 0.3, colors.HexColor('#d0dde8')),
            ('ROWPADDING',   (0,0), (-1,-1), 4),
            ('VALIGN',       (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(r_tbl)
        story.append(Spacer(1, 10))

    # ── OCORRÊNCIAS ──────────────────────────────
    if plantao.ocorrencias:
        story.append(Paragraph('OCORRÊNCIAS REGISTRADAS', sSecao))
        story.append(linha_hr(VERMELHO))
        urgCores = {'baixa': VERDE, 'media': AMARELO, 'alta': LARANJA, 'critica': VERMELHO}
        for i, oc in enumerate(plantao.ocorrencias):
            cor_urg = urgCores.get(oc.urgencia, CINZA)
            oc_data = [
                [Paragraph(f'[{i+1:02d}] {oc.urgencia.upper()} — {oc.tipo} — {oc.data_hora.strftime("%d/%m/%Y %H:%M:%S")}',
                           estilo('oh', fontSize=9, fontName='Helvetica-Bold', textColor=cor_urg))],
                campo('Local:', oc.local),
                [Paragraph('Descrição:', sLabel), Paragraph(oc.descricao or '—', sNorm)],
            ]
            if oc.providencias:
                oc_data.append([Paragraph('Providências:', sLabel), Paragraph(oc.providencias, sNorm)])
            if oc.envolvidos:
                oc_data.append(campo('Envolvidos:', oc.envolvidos))
            if oc.autoridade and oc.autoridade != 'Nenhuma acionada':
                oc_data.append(campo('Autoridade acionada:', f'{oc.autoridade}{" | BO: "+oc.bo_numero if oc.bo_numero else ""}'))

            tbl = Table(oc_data, colWidths=[W*0.35, W*0.65])
            tbl.setStyle(TableStyle([
                ('SPAN',       (0,0), (-1,0)),
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#fff0f2')),
                ('BACKGROUND', (0,1), (0,-1), FUNDO_LIN),
                ('ROWPADDING', (0,0), (-1,-1), 5),
                ('LINEBELOW',  (0,0), (-1,-1), 0.3, colors.HexColor('#d0dde8')),
                ('VALIGN',     (0,0), (-1,-1), 'TOP'),
            ]))
            story.append(tbl)
            story.append(Spacer(1, 6))
        story.append(Spacer(1, 6))

    # ── PÂNICOS ──────────────────────────────────
    if plantao.panicos:
        story.append(Paragraph('ALERTAS DE PÂNICO', sSecao))
        story.append(linha_hr(VERMELHO))
        pan_rows = [['Nº', 'Tipo', 'Hora', 'Status', 'Atendido em']]
        for i, p in enumerate(plantao.panicos):
            status = 'CANCELADO' if p.cancelado else ('ATENDIDO' if p.atendido else 'PENDENTE')
            pan_rows.append([
                str(i+1), p.tipo, p.data_hora.strftime('%H:%M:%S'), status,
                p.atendido_em.strftime('%H:%M:%S') if p.atendido_em else '—',
            ])
        pan_tbl = Table(pan_rows, colWidths=[8*mm, 55*mm, 25*mm, 30*mm, 30*mm])
        pan_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,0), colors.HexColor('#fff0f0')),
            ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',      (0,0), (-1,-1), 7),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[BRANCO, FUNDO_LIN]),
            ('GRID',          (0,0), (-1,-1), 0.3, colors.HexColor('#d0dde8')),
            ('ROWPADDING',    (0,0), (-1,-1), 4),
        ]))
        story.append(pan_tbl)
        story.append(Spacer(1, 10))

    # ── TERMO DE ENCERRAMENTO ────────────────────
    story.append(Spacer(1, 6))
    story.append(linha_hr())
    story.append(Paragraph('TERMO DE ENCERRAMENTO', sSecao))

    total = len(plantao.passagens)+len(plantao.rondas)+len(plantao.ocorrencias)+len(plantao.panicos)
    termo = (
        f"O presente relatório contém os registros oficiais do plantão de segurança patrimonial do posto "
        f"'{plantao.posto_nome}', sob responsabilidade do vigilante {plantao.vigilante.nome} "
        f"(Matrícula: {plantao.vigilante.matricula or '—'}), gerado eletronicamente pelo sistema "
        f"VIGILANTEX PRO em {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}, contendo "
        f"{len(plantao.passagens)} passagem(ns) de serviço, {len(plantao.rondas)} ronda(s), "
        f"{len(plantao.ocorrencias)} ocorrência(s) e {len(plantao.panicos)} alerta(s) de pânico — "
        f"total de {total} registro(s)."
    )
    story.append(Paragraph(termo, sNorm))
    story.append(Spacer(1, 20))

    ass_data = [
        [Paragraph('Assinatura do Vigilante:', sLabel),
         Paragraph('Assinatura do Supervisor/Gestor:', sLabel)],
        [Paragraph('_' * 40, sNorm), Paragraph('_' * 40, sNorm)],
        [Paragraph(f'{plantao.vigilante.nome} — Mat. {plantao.vigilante.matricula or "—"}', sLabel),
         Paragraph('Nome / Matrícula: ________________', sLabel)],
    ]
    ass_tbl = Table(ass_data, colWidths=[W/2, W/2])
    ass_tbl.setStyle(TableStyle([
        ('ROWPADDING', (0,0), (-1,-1), 6),
        ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
    ]))
    story.append(ass_tbl)

    # ── RODAPÉ ───────────────────────────────────
    def rodape(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 6)
        canvas.setFillColor(CINZA)
        txt = f"VIGILANTEX PRO — {plantao.posto_nome} — {datetime.now().strftime('%d/%m/%Y')} — Pág. {doc.page}"
        canvas.drawString(15*mm, 12*mm, txt)
        canvas.setStrokeColor(AZUL)
        canvas.setLineWidth(0.3)
        canvas.line(15*mm, 15*mm, A4[0]-15*mm, 15*mm)
        canvas.restoreState()

    doc.build(story, onFirstPage=rodape, onLaterPages=rodape)


def _kpi_cell(label, valor, cor):
    s_val = ParagraphStyle('kv', fontName='Helvetica-Bold', fontSize=22,
                           textColor=cor, alignment=TA_CENTER)
    s_lbl = ParagraphStyle('kl', fontName='Helvetica', fontSize=7,
                           textColor=colors.HexColor('#607080'), alignment=TA_CENTER)
    return [Paragraph(str(valor), s_val), Paragraph(label, s_lbl)]
