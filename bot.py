import discord
from discord import app_commands
from discord.ui import Select, View
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

class TicketSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="HWID Reset", description="HWIDのリセット申請", emoji="🔑"),
            discord.SelectOption(label="Products", description="商品に関する質問", emoji="🛒"),
            discord.SelectOption(label="Support", description="その他のサポート", emoji="❓"),
        ]
        super().__init__(placeholder="チケットの種類を選択してください...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        ticket_type = self.values[0]
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="Tickets")
        if not category:
            category = await guild.create_category("Tickets")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        channel = await category.create_text_channel(
            f"{ticket_type.replace(' ', '-').lower()}-{interaction.user.name}",
            overwrites=overwrites
        )

        embed = discord.Embed(
            title=f"📩 新しいチケット - {ticket_type}",
            description=f"{interaction.user.mention} さんがチケットを作成しました。",
            color=0x00ff00
        )
        embed.add_field(name="操作", value="チケットを閉じたい場合は `!close` と入力してください。", inline=False)

        await channel.send(embed=embed, content=interaction.user.mention)
        await interaction.response.send_message(f"✅ チケットを作成しました → {channel.mention}", ephemeral=True)

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

@tree.command(name="ticketpanel", description="チケット作成パネルを表示")
@app_commands.default_permissions(administrator=True)
async def ticketpanel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛠️ サポートチケット",
        description="下のメニューから用件を選択してチケットを作成してください。",
        color=0x5865F2
    )
    view = TicketView()
    await interaction.response.send_message(embed=embed, view=view)

@tree.command(name="close", description="現在のチケットを閉じます")
async def close(interaction: discord.Interaction):
    if "ticket" not in interaction.channel.name:
        return await interaction.response.send_message("このチャンネルはチケットではありません。", ephemeral=True)
    await interaction.response.send_message("30秒後にチケットを閉じます...")
    await asyncio.sleep(30)
    await interaction.channel.delete()

import os   # ← この行を一番上に追加（他のimportと一緒に）

@client.event
async def on_ready():
    await tree.sync()
    print(f"Bot is ready! {client.user}")

client.run(os.getenv("TOKEN"))
