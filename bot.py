import discord
from discord import app_commands
from discord.ui import Select, View
import asyncio
import os
from datetime import datetime
import io

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

cooldown = {}

class TicketSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="HWID Reset", description="HWIDリセット申請 / HWID Reset Request", emoji="🔑"),
            discord.SelectOption(label="Products", description="商品に関する問い合わせ / Product Inquiry", emoji="🛒"),
            discord.SelectOption(label="Support", description="その他のサポート / Other Support", emoji="❓"),
        ]
        super().__init__(placeholder="チケットの種類を選択 / Select ticket type...", options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        now = datetime.now().timestamp()
        if user_id in cooldown and now - cooldown[user_id] < 30:
            remain = int(30 - (now - cooldown[user_id]))
            return await interaction.response.send_message(f"⏳ あと{remain}秒待ってください / Please wait {remain} seconds.", ephemeral=True)
        
        cooldown[user_id] = now

        ticket_type = self.values[0]
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="Tickets") or await guild.create_category("Tickets")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        channel = await category.create_text_channel(
            f"ticket-{ticket_type.lower().replace(' ', '-')}-{interaction.user.name}",
            overwrites=overwrites
        )

        # 共通の挨拶
        embed = discord.Embed(
            title=f"📩 新しいチケット - {ticket_type}",
            description=f"{interaction.user.mention} さんがチケットを作成しました。\n\n**Please provide the following information:**",
            color=0x5865F2
        )

        if ticket_type == "HWID Reset":
            embed.add_field(
                name="必要な情報 / Required Information",
                value="• ライセンスキー / License Key\n• HWID Resetをしたい理由 / Reason for HWID Reset",
                inline=False
            )
        elif ticket_type == "Products":
            embed.add_field(
                name="必要な情報 / Required Information",
                value="• どの商品についての問い合わせですか？ / Which product is this inquiry about?",
                inline=False
            )
        elif ticket_type == "Support":
            embed.add_field(
                name="必要な情報 / Required Information",
                value="• サポートが必要な理由を詳しく書いてください / Please describe your issue in detail",
                inline=False
            )

        embed.add_field(name="閉じる方法 / How to close", value="`!close` または `/close` と入力", inline=False)

        await channel.send(embed=embed, content=interaction.user.mention)
        await interaction.response.send_message(f"✅ チケットを作成しました → {channel.mention}", ephemeral=True)


class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


@tree.command(name="ticketpanel", description="チケットパネルを表示 / Show ticket panel")
@app_commands.default_permissions(administrator=True)
async def ticketpanel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛠️ サポートチケット / Support Ticket",
        description="下のメニューから用件を選択してください / Please select your request below.",
        color=0x5865F2
    )
    await interaction.response.send_message(embed=embed, view=TicketView())


async def close_ticket(ctx):
    channel = ctx.channel
    if "ticket" not in channel.name.lower():
        return await channel.send("このチャンネルはチケットではありません / This is not a ticket channel.")

    await channel.send("✅ 30秒後にチケットを閉じ、ログを保存します... / Closing ticket and saving log in 30 seconds...")

    messages = [msg async for msg in channel.history(limit=None)]
    log_content = f"Ticket Log: {channel.name}\nClosed at: {datetime.now()}\n\n"
    for msg in reversed(messages):
        log_content += f"[{msg.created_at}] {msg.author}: {msg.content}\n"

    log_channel = discord.utils.get(channel.guild.text_channels, name="ticket-logs")
    if not log_channel:
        log_channel = await channel.guild.create_text_channel("ticket-logs")

    await log_channel.send(
        f"**Closed Ticket:** {channel.name}",
        file=discord.File(fp=io.BytesIO(log_content.encode('utf-8')), filename=f"{channel.name}-log.txt")
    )

    await asyncio.sleep(30)
    await channel.delete()


@tree.command(name="close", description="チケットを閉じる / Close ticket")
async def close_slash(interaction: discord.Interaction):
    await close_ticket(interaction)


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if message.content.lower().strip() == "!close":
        await close_ticket(message)


@client.event
async def on_ready():
    await tree.sync()
    print(f"Bot is ready! {client.user} | 詳細情報要求対応済み")


client.run(os.getenv("TOKEN"))
