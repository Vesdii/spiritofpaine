import discord
from discord.ext import commands
import json
import os
# todo: have choice between channelled or borderless voting
wd = os.path.dirname(os.path.realpath(__file__)) + '/'
bot = commands.Bot(None, activity=discord.Game('Freedom Simulator 1776'))
bot.config = {}
bot.votes = {}
try:
    with open(wd+'config.json') as cfg:
        for key, value in json.load(cfg).items():
            bot.config[int(key)] = value
except OSError:
    with open(wd+'config.json', 'w') as cfg:
        cfg.write('{}')
except:
    exit()
async def get_prefix(bot, message):
    pre = bot.config[message.guild.id]['prefix']
    return commands.when_mentioned_or(pre)(bot, message)
bot.command_prefix = get_prefix
numbers = ['1\u20e3', '2\u20e3', '3\u20e3', '4\u20e3', '5\u20e3', '6\u20e3',\
    '7\u20e3', '8\u20e3', '9\u20e3', '🔟']

def ucfg():
    """Update configuration."""
    with open(wd+'config.json', 'w') as cfg:
        json.dump(bot.config, cfg, indent=4)

@bot.event
async def on_ready():
    for guild in bot.guilds:
        if guild.id not in bot.config.keys():
            bot.config[guild.id] = {
                "prefix": ";",
                'oprole': 0,
                'channels': []
            }
    g2d = []
    for guild in bot.config.keys():
        if guild not in [g.id for g in bot.guilds]:
            g2d.append(guild)
    for guild in g2d:
        del bot.config[guild]
    ucfg()

@bot.event
async def on_guild_join(guild):
    bot.config[guild.id] = {
        "prefix": ";",
        'oprole': 0,
        'channels': []
    }
    print(f'Added {guild} ({guild.id})')

@bot.check
async def in_channel(ctx):
    return ctx.channel.id in bot.config[ctx.guild.id]['channels']\
            or ctx.author.guild_permissions.administrator

def is_op():
    async def predicate(ctx):
        return ctx.guild.get_role(bot.config[ctx.guild.id]['oprole']) in ctx.author.roles\
                or ctx.author.guild_permissions.administrator
    return commands.check(predicate)

def is_admin():
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)

@bot.event
async def on_reaction_add(reaction, user):
    if reaction.message.channel.id not in bot.votes\
            or user == bot.user:
        return
    elif user.id not in bot.votes[reaction.message.channel.id]['voters']\
            and reaction.emoji in numbers:
        bot.votes[reaction.message.channel.id]['voters'].append(user.id)
        em = reaction.message.embeds[0]
        index = numbers.index(reaction.emoji)
        field_name = em.fields[index].name
        ct = int(em.fields[index].value)
        em.set_field_at(index, name=field_name, value=ct+1)
        await reaction.message.edit(embed=em)

##########
# CONFIG #
##########

@bot.command()
@is_admin()
async def prefix(ctx, *, prefix = None):
    if not prefix:
        await ctx.send('`' + bot.config[ctx.guild.id]['prefix'] + '` is the command prefix.')
        return
    bot.config[ctx.guild.id]['prefix'] = prefix
    ucfg()
    await ctx.send(f'`{prefix}` is now the command prefix.')

@bot.command()
@is_admin()
async def oprole(ctx, *, role: discord.Role = None):
    """
    If <role> is provided, sets it as the operator role. Members with this
    role can call votes. If not provided, prints the current op role.
    """
    if not role:
        if bot.config[ctx.guild.id]['oprole'] == 0:
            await ctx.send('There is currently no op role.')
        else:
            r = ctx.guild.get_role(bot.config[ctx.guild.id]['oprole'])
            if not r:
                bot.config[ctx.guild.id]['oprole'] = 0
                ucfg()
                await ctx.send('There is currently no op role.')
                return
            await ctx.send(f'{r} is the op role.')
        return
    bot.config[ctx.guild.id]['oprole'] = role.id
    ucfg()
    await ctx.send(f'{role} is now the op role.')

@oprole.error
async def oprole_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send('Invalid role.')

@bot.command()
@is_op()
async def channels(ctx):
    """Prints all registered voting channels."""
    if len(bot.config[ctx.guild.id]['channels']) == 0:
        await ctx.send('There are currently no voting channels.')
        return
    output = 'Registered voting channels:\n'
    ch2rm = []
    for x in bot.config[ctx.guild.id]['channels']:
        channel = ctx.guild.get_channel(x)
        if not channel:
            ch2rm.append(x)
            continue
        output += f'{channel.mention}\n'
    for x in ch2rm:
        bot.config[ctx.guild.id]['channels'].remove(x)
    ucfg()
    await ctx.send(output)

@bot.command()
@is_admin()
async def addchannel(ctx, channel: discord.TextChannel):
    """Enables <channel> to hold votes."""
    if channel.id in bot.config[ctx.guild.id]['channels']:
        await ctx.send(f'{channel} is already registered.')
        return
    bot.config[ctx.guild.id]['channels'].append(channel.id)
    ucfg()
    await ctx.send(f'{channel} is now a voting channel.')

@addchannel.error
async def addchannel_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send('Invalid channel.')

@bot.command()
@is_admin()
async def removechannel(ctx, channel: discord.TextChannel):
    """Disables <channel>'s ability to hold votes."""
    if channel.id not in bot.config[ctx.guild.id]['channels']:
        await ctx.send(f'{channel} is not registered.')
        return
    bot.config[ctx.guild.id]['channels'].remove(channel.id)
    ucfg()
    await ctx.send(f'{channel} is no longer a voting channel.')

@removechannel.error
async def removechannel_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send('Invalid channel.')

##########
# VOTING #
##########

@bot.command()
@is_op()
async def call(ctx, prompt, *, options = 'Yes|No'):
    if ctx.channel.id in bot.votes:
        return
    prompt = prompt.strip()
    if len(prompt) < 2:
        await ctx.send('Prompt must be at least two characters.')
        return
    options = [x.strip() for x in options.split('|')]
    options = set(options)
    if len(options) == 1:
        await ctx.send('A minimum of two options is required.')
        return
    if len(options) > 10:
        await ctx.send('A maximum of ten options is allowed.')
        return
    em = discord.Embed(title=prompt, color=discord.Color.gold())
    em.set_footer(text='Active')
    ct = 0
    for x in options:
        em.add_field(name=f'{numbers[ct]} {x}', value='0')
        ct += 1
    msg = await ctx.send(None, embed=em)
    bot.votes[ctx.channel.id] = {'message': msg.id, 'voters': []}
    for x in range(ct):
        await msg.add_reaction(numbers[x])
    try: await ctx.message.delete()
    except: pass

@bot.command()
@is_op()
async def cancel(ctx):
    """Cancels the active vote in the current channel."""
    if ctx.channel.id not in bot.votes:
        return
    (await ctx.fetch_message(bot.votes[ctx.channel.id]['message'])).delete()
    await ctx.message.delete()

@bot.command()
@is_op()
async def end(ctx):
    """Ends the active vote in the current channel."""
    if ctx.channel.id not in bot.votes:
        return
    msg = await ctx.fetch_message(bot.votes[ctx.channel.id]['message'])
    try: await msg.clear_reactions()
    except: pass
    em = msg.embeds[0]
    total = 0
    for x in em.fields:
        total += int(x.value)
    results = []
    for x in em.fields:
        x.name = x.name[x.name.index(' ')+1:]
        if x.value != '0':
            x.value = (total / int(x.value)) * 100
            x.value = f'{x.value:.4g}'
        results.append([x.name, x.value + '%'])
    results.sort(key=lambda pair: pair[1], reverse=True)
    em.clear_fields()
    for x in results:
        em.add_field(name=x[0], value=x[1])
    em.color = discord.Color.green()
    em.set_footer(text='Ended')
    del bot.votes[ctx.channel.id]
    await msg.edit(embed=em)
    try: await ctx.message.delete()
    except: pass

with open(wd+'token') as f:
    bot.token = f.read()
bot.run(bot.token)
