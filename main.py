import discord
from discord.ext import commands
import asyncio
from quart import Quart, jsonify, request
from quart_cors import cors
import re
import os  # Importado para ler as variáveis de ambiente

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True 
bot = commands.Bot(command_prefix="!", intents=intents)

app = Quart(__name__)
app = cors(app, allow_origin="*")

# Puxa o ID da categoria das variáveis de ambiente. Se não achar, usa o padrão 0
ID_CATEGORIA_DENUNCIAS = int(os.environ.get("ID_CATEGORIA_DENUNCIAS", 0))
TICKETS_ATIVOS = {}

@bot.event
async def on_ready():
    print(f"🤖 Bot online como {bot.user}")
    # O Fly.io exige ler a porta que a plataforma fornece através da variável PORT
    porta = int(os.environ.get("PORT", 5000))
    bot.loop.create_task(app.run_task(host="0.0.0.0", port=porta))

@bot.event
async def on_guild_channel_create(channel):
    if isinstance(channel, discord.TextChannel) and channel.category_id == ID_CATEGORIA_DENUNCIAS:
        TICKETS_ATIVOS[channel.id] = {
            "id": channel.id,
            "nome": channel.name,
            "dados_formulario": {}
        }

@bot.event
async def on_message(message):
    if message.author.bot: return
    
    if message.category_id == ID_CATEGORIA_DENUNCIAS:
        if message.channel.id not in TICKETS_ATIVOS:
            TICKETS_ATIVOS[message.channel.id] = {"id": message.channel.id, "nome": message.channel.name, "dados_formulario": {}}
        
        texto = message.content
        if "Seu Nome em RP:" in texto:
            TICKETS_ATIVOS[message.channel.id]["dados_formulario"] = extrair_dados(texto)
            
    await bot.process_commands(message)

def extrair_dados(texto):
    dados = {
        "nome_rp": re.search(r"Seu Nome em RP:\s*(.*)", texto, re.IGNORECASE),
        "seu_id": re.search(r"Seu ID:\s*(\d+)", texto, re.IGNORECASE),
        "id_denunciado": re.search(r"ID do Denunciado:\s*(\d+)", texto, re.IGNORECASE),
        "motivo": re.search(r"Motivo Detalhado.*:\s*(.*)", texto, re.IGNORECASE),
        "provas": re.search(r"Provas.*:\s*(.*)", texto, re.IGNORECASE)
    }
    return {k: (v.group(1).strip() if v else "") for k, v in dados.items()}

@app.route("/tickets", methods=["GET"])
async def listar_tickets():
    for cid in list(TICKETS_ATIVOS.keys()):
        if not bot.get_channel(cid): del TICKETS_ATIVOS[cid]
    return jsonify(list(TICKETS_ATIVOS.values()))

@app.route("/membros", methods=["GET"])
async def listar_membros():
    membros = []
    for guild in bot.guilds:
        for member in guild.members:
            if not member.bot:
                membros.append({"id_discord": str(member.id), "tag": f"{member.name}#{member.discriminator}" if member.discriminator != "0" else member.name})
    return jsonify(membros)

@app.route("/enviar-acao", methods=["POST"])
async def enviar_acao():
    dados = await request.get_json()
    channel_id = int(dados.get("channel_id"))
    acao = dados.get("acao")
    canal = bot.get_channel(channel_id)
    
    if not canal: return jsonify({"status": "erro", "mensagem": "Ticket não encontrado"}), 404

    if acao == "pedir_formulario":
        msg = (
            "👤 **Seu Nome em RP:**\n🆔 **Seu ID:**\n🆔 **ID do Denunciado:**\n"
            "📅 **Data e Hora do Ocorrido:**\n🎬 **Provas (YouTube ou Medal):**\n📝 **Motivo Detalhado da Denúncia:**\n\n"
            "⚠️ **AVISO IMPORTANTE**\nPeço que ambas as partes mantenham o respeito durante o atendimento deste ticket. "
            "É totalmente proibido qualquer tipo de ofensa, provocação ou desrespeito. Caso haja, medidas administrativas serão tomadas."
        )
        await canal.send(msg)

    elif acao == "notificar_denunciado":
        membro_id = dados.get("membro_id")
        motivo = dados.get("motivo_denuncia")
        texto_customizado = dados.get("texto_customizado", "")
        
        msg = (
            f"Atenção <@{membro_id}>, você foi citado neste ticket de denúncia.\n\n"
            f"❓ **Motivo:** Você está sendo acusado de: **{motivo}**.\n"
            f"💬 **Mensagem da Staff:** {texto_customizado}\n\n"
            f"Você tem o direito de apresentar sua defesa e contraprovas aqui neste canal. Mantenha o respeito."
        )
        await canal.send(msg)

    elif acao == "decreto_aceito":
        id_jogo = dados.get("id_jogo")
        regra = dados.get("regra_infringida")
        punicao = dados.get("punicao_applied") # Corrigido pequeno erro de digitação do script anterior
        
        msg = (
            f"Análise concluída. A denúncia foi considerada **ACEITA**.\n\n"
            f"O denunciado (ID: {id_jogo}) infringiu a regra de **{regra}** e recebeu a punição de **{punicao}**.\n\n"
            f"Agradecemos o seu envio para mantermos a ordem no servidor. Este ticket será fechado."
        )
        await canal.send(msg)

    elif acao == "decreto_recusado":
        motivo_recusa = dados.get("motivo_recusa")
        
        msg = (
            f"Análise concluída. A denúncia foi considerada **RECUSADA** e será arquivada.\n\n"
            f"❌ **Motivo:** {motivo_recusa}\n\n"
            f"Agradecemos o contato. Este ticket será fechado."
        )
        await canal.send(msg)

    return jsonify({"status": "sucesso"})

# Puxa o Token das variáveis de ambiente de forma segura
TOKEN_BOT = os.environ.get("DISCORD_TOKEN")
bot.run(TOKEN_BOT)
