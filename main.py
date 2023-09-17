# This example requires the 'message_content' intent.
from __future__ import annotations
import asyncio

from dataclasses import dataclass
import dataclasses
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import datefinder
import discord
from discord import app_commands

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@tree.command(name = "remind-me", description = "Post a message at a later date")
async def post_command(ctx, start_at: str, period_h: int, message: str):
    parsed_start = None
    try:
        parsed_start = next(datefinder.find_dates(start_at))
    except StopIteration:
        await ctx.response.send_message(f"Could not parse date")
        return
    reminder = Reminder(
        message=message,
        period=timedelta(hours=period_h),
        send_at=parsed_start,
        channel=ctx.channel,
    )
    reminders.add(reminder)
    await ctx.response.send_message(f"Will remind at {reminder.send_at}")

@tree.command(name = "print-reminders", description = "Tell me what reminders are queued up")
async def print_reminders(ctx):
    summary_lines=[]
    global reminders
    for reminder in reminders:
        summary_lines.append(f"At {reminder.send_at}: {reminder.message}")
    await ctx.response.send_message('\n'.join(summary_lines))

@dataclass(frozen=True, eq=True)
class Reminder:
    message: str
    channel: discord.abc.TextChannel
    send_at: datetime
    period: Optional[timedelta]

    async def send(self):
        await self.channel.send(self.message)
    
    def next(self) -> Optional[Reminder]:
        if not self.period:
            return None
        return dataclasses.replace(self, send_at=datetime.now()+self.period)

# A lovely global datastructure instead of a database because we are cheap.
reminders = set()

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    global tree
    worked = await tree.sync()
    client.loop.create_task(every(timedelta(seconds=10), post_reminders))
    print(worked)

async def every(period: timedelta, func, *args, **kwargs):
    while True:
        await func(*args, **kwargs)
        await asyncio.sleep(period.total_seconds())

async def post_reminders():
    print("loop task called")
    updated_reminders = set()
    global reminders
    for reminder in reminders:
        if reminder.send_at < datetime.now():
            print("sending reminder")
            await reminder.send()
            next = reminder.next()
            if next:
                updated_reminders.add(next)
        else:
            updated_reminders.add(reminder)
    reminders = updated_reminders

if __name__ == "__main__":
    token = Path('bot_secret.txt').read_text()
    client.run(token)