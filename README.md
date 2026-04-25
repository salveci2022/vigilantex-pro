# VIGILANTEX PRO — Sistema de Gestão de Plantão
### Segurança Patrimonial Profissional · v2026

---

## 🚀 DEPLOY NO RENDER (passo a passo)

### 1. Banco de dados PostgreSQL
- Acesse render.com → New → PostgreSQL
- Nome: `vigilantex-db`
- Copie a **Internal Database URL**

### 2. Web Service
- New → Web Service → conecte seu GitHub
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2`

### 3. Variáveis de Ambiente no Render
```
SECRET_KEY          = (gere uma chave aleatória)
DATABASE_URL        = (cole a URL do PostgreSQL)
```

### 4. Primeiro acesso
- URL: `https://seu-app.onrender.com`
- Email: `admin@vigilantex.com`
- Senha: `admin123`
- **Troque a senha imediatamente!**

---

## 👤 CRIAR USUÁRIOS

Acesse o painel Admin → Usuários → Novo Usuário

Perfis disponíveis:
- `vigilante` — acessa plantão, ocorrências, ronda
- `supervisor` — vê todos os postos em tempo real
- `gestor` — acesso total + relatórios
- `admin` — configurações do sistema

---

## 📱 INSTALAR COMO APP (PWA)

### No Android (Chrome):
1. Acesse o link do sistema
2. Toque nos 3 pontos → "Adicionar à tela inicial"
3. Confirme → ícone aparece como app

### No iPhone (Safari):
1. Acesse o link
2. Toque em Compartilhar → "Adicionar à Tela de Início"

---

## 📲 CONFIGURAR WHATSAPP (Z-API)

1. Acesse o painel Admin → Configurações → WhatsApp
2. Preencha:
   - **Instance ID:** (da sua conta Z-API)
   - **Token:** (da sua conta Z-API)
3. Cadastre o telefone dos supervisores em seus perfis

**Alertas automáticos enviados:**
- 🆘 Pânico acionado
- 🔴 Ocorrência CRÍTICA
- 🟠 Ocorrência ALTA
- ✅ Pânico atendido/cancelado

---

## 📄 RELATÓRIO PDF

Gerado automaticamente com:
- Capa com dados do plantão
- KPIs coloridos
- Passagens de serviço completas
- Histórico de rondas com tabela
- Ocorrências com nível de urgência
- Alertas de pânico
- Termo de encerramento com assinatura
- Rodapé com paginação

---

## 🏗️ ESTRUTURA DO PROJETO

```
vigilantex-sistema/
├── app.py              ← Flask + configuração
├── models.py           ← Banco de dados (SQLAlchemy)
├── routes/
│   ├── auth.py         ← Login, usuários, postos
│   ├── plantao.py      ← Passagem, ronda, ocorrência
│   ├── panico.py       ← Pânico + WhatsApp Z-API
│   ├── relatorio.py    ← PDF com ReportLab
│   └── admin.py        ← Dashboard, configurações
├── templates/
│   └── index.html      ← Frontend completo (SPA)
├── static/
│   ├── manifest.json   ← PWA
│   └── sw.js           ← Offline (Service Worker)
├── requirements.txt
├── Procfile            ← Deploy Render
└── .env.example        ← Variáveis de ambiente
```

---

## 💰 MODELO DE NEGÓCIO

| Plano | Postos | Usuários | Preço/mês |
|-------|--------|----------|-----------|
| Básico | 1 | até 5 | R$ 97 |
| Profissional | até 5 | até 20 | R$ 247 |
| Empresarial | ilimitado | ilimitado | R$ 497 |
| Implantação | — | — | R$ 500 único |

**Mercado Brasília:** 400+ empresas de vigilância registradas.

---

## 📞 SUPORTE
SPYNET Tecnologia Forense & Soluções Digitais Ltda
CNPJ: 64.000.808/0001-51
spynetintelligence@proton.me
