import discord
import random
from discord import app_commands
from datetime import datetime, timedelta
from typing import Optional, Dict
from discord.ext import commands
# Cooldown tracking dictionaries
random_cooldowns: Dict[int, datetime] = {}
answer_cooldowns: Dict[int, datetime] = {}


def cooldown_check(cooldown_dict: Dict[int, datetime]):

    def predicate(
            interaction: discord.Interaction
    ) -> Optional[app_commands.Cooldown]:
        user_id = interaction.user.id
        now = datetime.now()
        if user_id in cooldown_dict:
            remaining = (cooldown_dict[user_id] - now).total_seconds()
            if remaining > 0:
                return app_commands.Cooldown(rate=1, per=10)
        cooldown_dict[user_id] = now + timedelta(seconds=10)
        return None

    return predicate


intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Clan role IDs and their display names
CLAN_ROLES = {
    1364663712698339409: "Ghosts",
    1361790329371492653: "a non-terrorist organization",
    1364663704305795233: "DAMU",
    1362530600657092820: "SOS",
    1361784473800151272: "Sip Happens",
    1361784471359324367: "STJ",
    1361784452468183141: "Lwd058"
}

# Channel IDs
LOG_CHANNEL_ID = 1362496341103612155
FEEDBACK_CHANNEL_ID = 1368186661682544751
REPORT_CHANNEL_ID = 1368186794805559376

# Fun message dictionaries
MENTION_MESSAGES = [
    "Did you know the first video game easter egg was in *Adventure* (1980)?",
    "Fun fact: Creepers in Minecraft were a coding error.",
    "Summoned like a Final Fantasy summon—what's the mission?",
    "Press 'A' to interact... oh wait, I already did.",
    "I respond faster than a speedrunner skipping dialogue.",
    "Ever heard of the Konami Code? Up up down down... never mind.",
    "Respawned just to answer your call!",
    "Warning: low on mana, but high on motivation!",
    "Pro tip: Pinging the bot gives you +10 charisma (temporarily).",
    "I've joined the party. Time to roll initiative?"
]

REPLY_ANSWERS = [
    "the stars say yes!", "my magic 8-ball says no.",
    "that only time will tell.", "absolutely, without a doubt!",
    "I wouldn't count on it.", "the answer is blowing in the wind.",
    "yes, but with consequences.", "please don't ask me, I'm just a bot."
]


class ClanInviteView(discord.ui.View):

    def __init__(self, inviter: discord.Member, invited: discord.Member,
                 clan_role: discord.Role):
        super().__init__(timeout=60.0)
        self.inviter = inviter
        self.invited = invited
        self.clan_role = clan_role

    async def log_result(self, result: str) -> None:
        if not self.clan_role or not self.inviter or not self.invited:
            return
        log_channel = self.inviter.guild.get_channel(
            LOG_CHANNEL_ID) if self.inviter.guild else None
        if isinstance(log_channel, discord.TextChannel):
            try:
                await log_channel.send(
                    f"{self.inviter.mention} invited {self.invited.mention} to {self.clan_role.mention}; used {result}"
                )
            except discord.HTTPException:
                pass

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction,
                     button: discord.ui.Button):
        if interaction.user != self.invited:
            await interaction.response.send_message(
                "Hey, that won't be fair now, you're not the invited user!",
                ephemeral=True)
            return

        try:
            if self.clan_role and isinstance(interaction.guild, discord.Guild):
                await self.invited.add_roles(self.clan_role)
                await self.log_result("accepted")
                await interaction.response.send_message(
                    f"🎉 Welcome to {self.clan_role.mention}!", ephemeral=False)
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to add role: {e}", ephemeral=True)
        self.stop()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction,
                      button: discord.ui.Button):
        if interaction.user != self.invited:
            await interaction.response.send_message(
                "Hey, that won't be fair now, you're not the invited user!",
                ephemeral=True)
            return

        await self.log_result("declined")
        await interaction.response.send_message("❌ Invitation declined.",
                                                ephemeral=False)
        self.stop()


@bot.tree.command(name="invite", description="Invite a member to your clan")
async def invite(interaction: discord.Interaction, invited: discord.Member):
    if not interaction.guild or not isinstance(interaction.user,
                                               discord.Member):
        await interaction.response.send_message(
            "This command can only be used in servers.", ephemeral=True)
        return

    inviter_clan_role = None
    for role_id in CLAN_ROLES.keys():
        if role_id in [role.id for role in interaction.user.roles]:
            inviter_clan_role = interaction.guild.get_role(role_id)
            break

    if not inviter_clan_role:
        await interaction.response.send_message(
            "❌ You don't belong to any clan!", ephemeral=True)
        return

    try:
        await interaction.response.send_message(
            f"Greetings {invited.mention}, you received an invitation to {inviter_clan_role.mention} from {interaction.user.mention}!",
            view=ClanInviteView(inviter=interaction.user,
                                invited=invited,
                                clan_role=inviter_clan_role),
            allowed_mentions=discord.AllowedMentions(users=True, roles=True))
    except discord.HTTPException as e:
        await interaction.followup.send(f"Failed to send invitation: {e}",
                                        ephemeral=True)


@bot.tree.command(name="random", description="Get a random mention message")
@app_commands.checks.dynamic_cooldown(cooldown_check(random_cooldowns))
async def random_cmd(interaction: discord.Interaction):
    try:
        random_message = random.choice(MENTION_MESSAGES)
        await interaction.response.send_message(random_message)
    except Exception as e:
        await interaction.response.send_message(
            "❌ Failed to get a random message!", ephemeral=True)
        print(f"Random command error: {e}")


@bot.tree.command(name="answer",
                  description="Get a random answer to your message")
@app_commands.checks.dynamic_cooldown(cooldown_check(answer_cooldowns))
async def answer(interaction: discord.Interaction, message: str):
    try:
        if not message or len(message) > 200:
            await interaction.response.send_message(
                "❌ Please provide a valid message (under 200 characters)!",
                ephemeral=True)
            return

        random_answer = random.choice(REPLY_ANSWERS)
        response = f"Well, to your '{message}', {random_answer}"
        await interaction.response.send_message(response)
    except Exception as e:
        await interaction.response.send_message(
            "❌ Failed to generate an answer!", ephemeral=True)
        print(f"Answer command error: {e}")


@random_cmd.error
@answer.error
async def command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"⏳ Please wait {error.retry_after:.1f} seconds before using this command again!",
            ephemeral=True)


@bot.tree.command(name="feedback", description="Send feedback to the admins")
async def feedback(interaction: discord.Interaction, message: str):
    try:
        if interaction.guild:
            feedback_channel = interaction.guild.get_channel(
                FEEDBACK_CHANNEL_ID)
            if isinstance(feedback_channel, discord.TextChannel):
                await feedback_channel.send(
                    f"Feedback from {interaction.user.mention}: {message}")
                await interaction.response.send_message(
                    "✅ Your feedback has been sent!", ephemeral=True)
                return
        await interaction.response.send_message(
            "❌ Feedback channel not found!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Failed to send feedback: {e}",
                                        ephemeral=True)


@bot.tree.command(name="report", description="Report an issue to the admins")
async def report(interaction: discord.Interaction, message: str):
    try:
        if interaction.guild:
            report_channel = interaction.guild.get_channel(REPORT_CHANNEL_ID)
            if isinstance(report_channel, discord.TextChannel):
                await report_channel.send(
                    f"Report from {interaction.user.mention}: {message}")
                await interaction.response.send_message(
                    "✅ Your report has been sent!", ephemeral=True)
                return
        await interaction.response.send_message("❌ Report channel not found!",
                                                ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Failed to send report: {e}",
                                        ephemeral=True)


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Bot is ready as {bot.user}")
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


bot.run(os.environ["DISCORD_TOKEN"])
