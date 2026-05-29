import discord
from discord import app_commands
from discord.ui import Select, View
import asyncio
import os
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# クールダウン管理
cooldown = {}

class TicketSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="HWID Reset", description="HWIDのリセット申請 / HWID Reset Request", emoji="🔑"),
            discord.SelectOption(label="Products", description="商品に関する質問 / Product Inquiry", emoji="🛒"),
            discord.SelectOption(label="Support", description="その他のサポート / Other Support", emoji="❓"),
        ]
        super().__init__(placeholder="チケットの種類を選択 / Select ticket type...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        now = datetime.now().timestamp()

        # クールダウン（30秒）
        if user_id in cooldown and now - cooldown[user_id] < 30:
            remaining = int(30 - (now - cooldown[user_id]))
            return await interaction.response.send_message(f"⏳ クールダウン中です。あと{remaining}秒お待ちください / Cooldown active. Please wait {remaining} seconds.", ephemeral=True)

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
            f"{ticket_type.lower().replace(' ', '-')}-{interaction.user.name}",
            overwrites=overwrites
        )

        embed = discord.Embed(
            title=f"📩 新しいチケット - {ticket_type}",
            description=f"{interaction.user.mention} さんがチケットを作成しました。\n\n**内容**: {ticket_type}",
            color=0x5865F2
        )
        embed.add_field(name="閉じる方法 / How to close", value="`!close` と入力してください", inline=False)

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
        description="下のメニューから用件を選択してください / Select your request below.",
        color=0x5865F2
    )
    view = TicketView()
    await interaction.response.send_message(embed=embed, view=view)


@tree.command(name="close", description="チケットを閉じる / Close the ticket")
async def close(interaction: discord.Interaction):
    if "ticket" not in interaction.channel.name.lower():
        return await interaction.response.send_message("このチャンネルはチケットではありません / This is not a ticket channel.", ephemeral=True)

    await interaction.response.send_message("✅ 30秒後にチケットを閉じ、ログを保存します... / Closing ticket and saving log in 30 seconds...")

    # ログ保存
    messages = [message async for message in interaction.channel.history(limit=None)]
    log_content = f"Ticket Log - {interaction.channel.name}\nClosed at: {datetime.now()}\n\n"
    for msg in reversed(messages):
        log_content += f"[{msg.created_at}] {msg.author}: {msg.content}\n"

    # ログチャンネルに送信（"ticket-logs" というチャンネルがなければ自動作成）
    log_channel = discord.utils.get(interaction.guild.text_channels, name="ticket-logs")
    if not log_channel:
        log_channel = await interaction.guild.create_text_channel("ticket-logs")

    await log_channel.send(f"**Closed Ticket:** {interaction.channel.name}", file=discord.File(
        fp=discord.utils._io.BytesIO(log_content.encode('utf-8')),
        filename=f"{interaction.channel.name}-log.txt"
    ))

    await asyncio.sleep(30)
    await interaction.channel.delete()


@client.event
async def on_ready():
    await tree.sync()
    print(f"Bot is ready! {client.user} | 多言語・ログ保存対応")


client.run(os.getenv("TOKEN"))
