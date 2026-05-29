# 既存の /close コマンドはそのまま残して、以下を追加・修正

@tree.command(name="close", description="チケットを閉じる / Close the ticket")
async def close(interaction: discord.Interaction):
    await close_ticket(interaction)

# 新しく追加： !close も使えるようにする
@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if message.content.lower() == "!close":
        # チケットチャンネル判定
        if "ticket" in message.channel.name.lower():
            await close_ticket(message)
        else:
            await message.channel.send("このチャンネルはチケットではありません。", delete_after=10)

    # 他のメッセージ処理があればここに追加
    await client.process_commands(message)  # 必要に応じて


# 共通の閉じる処理
async def close_ticket(ctx):
    """チケットを閉じる共通関数"""
    channel = ctx.channel if isinstance(ctx, discord.Message) else ctx.channel
    user = ctx.author if isinstance(ctx, discord.Message) else ctx.user

    await channel.send("✅ 30秒後にチケットを閉じ、ログを保存します...")

    # ログ保存処理（そのまま）
    messages = [message async for message in channel.history(limit=None)]
    log_content = f"Ticket Log - {channel.name}\nClosed at: {datetime.now()}\nClosed by: {user}\n\n"
    for msg in reversed(messages):
        log_content += f"[{msg.created_at}] {msg.author}: {msg.content}\n"

    log_channel = discord.utils.get(channel.guild.text_channels, name="ticket-logs")
    if not log_channel:
        log_channel = await channel.guild.create_text_channel("ticket-logs")

    await log_channel.send(f"**Closed Ticket:** {channel.name}", file=discord.File(
        fp=discord.utils._io.BytesIO(log_content.encode('utf-8')),
        filename=f"{channel.name}-log.txt"
    ))

    await asyncio.sleep(30)
    await channel.delete()
