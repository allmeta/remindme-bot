from discord.ext import commands
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import re


class Job():
    def __init__(self, user, ctx):
        self.user = user
        self.desc = "placeholder"
        self.date = False
        self.ctx = ctx


class Remind(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.frmt = "%d/%m/%Y %H:%M:%S"
        self.scheduler = AsyncIOScheduler(timezone="Europe/Oslo")
        self.scheduler.start()
        # go over jobs in config and add jobs

        self.waiting = {
            # stage 0: nothing
            # stage 1: waiting for desc
            # stage 2: waiting for desc
            # stage 3: waiting for time
            'stage': 0,
            'user': 0
        }
        self.jobs = {
            # user: [job1,job2] etc
            # link to apscheduler
        }
        # current job in the making
        self.cc_job = None

    def set_waiting_stage(self, s):
        self.waiting['stage'] = s

    def set_waiting_user(self, s):
        self.waiting['user'] = s

    @commands.command(
        name="remindme",
        description="Remindme date command",
        aliases=['rd']
    )
    async def remindme(self, ctx):
        # add user to query dict
        if not self.waiting['stage'] == 0:
            return(
                await ctx.send(
                    "I CANT HANDLE MORE THAN ONE REQUEST"))
        self.set_waiting_stage(1)
        self.set_waiting_user(ctx.author.id)
        self.cc_job = Job(ctx.author.id, ctx.channel)

        await ctx.channel.send(
            "Enter a desc for your remind_me!")

        desc = await self.bot.wait_for('message')
        print(desc.content)

        self.cc_job.desc = desc.content

        time = await self.prompt_time(ctx)
        while not time:
            await ctx.channel.send(
                "Date is in wrong format. Try again!")
            time = await self.prompt_time(ctx)

        await ctx.channel.send(
            "You will get an @ on {.date} saying: {.desc}"
            .format(self.cc_job, self.cc_job))

        # create job and reset stuff
        self.set_waiting_stage(0)
        self.set_waiting_user(0)
        self.add_job(self.cc_job)
        self.cc_job = None

    def add_job(self, job):
        self.scheduler.add_job(func=self.remind, trigger='date', next_run_time=job.date, args=[
                               job.user, job.desc, job.ctx])

    async def remind(self, user, desc, ctx):
        return await ctx.send("<@{}> {}".format(user, desc))

    async def prompt_time(self, ctx):

        def check(m):
            return (m.author.id == ctx.author.id and
                    m.channel == ctx.channel)

        await ctx.channel.send(
            "Enter a time in the format `{}`".format(self.frmt))
        m = await self.bot.wait_for('message', check=check)
        return self.validate_pattern(m)

    def validate_time(self, t, frmt):
        try:
            d = datetime.strptime(t, frmt)
            # check if after current date
            if datetime.now() < d:
                # set current job date to *d*

                self.cc_job.date = d
                return True
            else:
                return False
        except ValueError:
            return False

    def validate_pattern(self, message):
        t = message.content

        regex_date_time = r"^\d+\/\d+\/\d+ \d+\:\d+\:\d+$"
        #regex_time = r"^\d+\:\d+\:\d+$"
        if re.match(regex_date_time, t):
            return self.validate_time(t, self.frmt)
        # elif re.match(regex_time, t):
        #     return validate_time(t, frmt.split(" ")[1])
        else:
            return False


def setup(bot):
    bot.add_cog(Remind(bot))
