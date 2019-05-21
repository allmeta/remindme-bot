from discord.ext import commands
from discord import Embed, Colour
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import re
import sys
import signal
import json
import uuid


class Job():
    """
    Just a struct to store temp data... only used by remindme
    """

    def __init__(self, user, ctx, desc="", date=False):
        self.user = user
        self.desc = desc
        self.date = date
        self.ctx = ctx


class Remind(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.frmt = "%d-%m-%Y %H:%M:%S"
        self.dfrmt = "%Y-%m-%d %H:%M:%S"
        self.scheduler = AsyncIOScheduler(timezone="Europe/Oslo")
        self.scheduler.start()
        # signal.signal(signal.SIGINT, self.close_handler)
        # go over jobs in config and add jobs
        with open("jobs.json") as f:
            jobs = json.loads(f.read())
        for userid, userjobs in jobs.items():
            for jobid, job in userjobs.items():
                self.scheduler.add_job(func=self.remind,
                                       trigger='date',
                                       next_run_time=datetime.strptime(
                                           job["date"],
                                           self.dfrmt),
                                       args=[
                                           userid,
                                           job["desc"],
                                           self.bot.get_channel(
                                               job["channel"]),
                                           jobid])
        f.close()

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

    def close_handler(self, sig, frame):
        print("You closed program nice!")
        sys.exit(0)

    def set_waiting_stage(self, s):
        self.waiting['stage'] = s

    def set_waiting_user(self, s):
        self.waiting['user'] = s

    @commands.command(
        name="remove",
        description="Remove a reminder",
        aliases=["rr"]
    )
    async def remove(self, ctx):
        with open("jobs.json") as f:
            jobs = json.loads(f.read())
        f.close()
        jobs_remove_array = []

        if (not str(ctx.author.id) in jobs
                or not bool(jobs[str(ctx.author.id)])):
            return await ctx.send("You have no reminders!")

        reminders_list = jobs[str(ctx.author.id)]

        embed = Embed(
            title="Remove reminder:",
            colour=Colour.blue()
        )
        for key, job in reminders_list.items():
            embed.add_field(
                name=("`"+str(len(jobs_remove_array))+"`"),
                value=(job["desc"])
            )
            jobs_remove_array.append(key)
        embed.set_footer(
            text="type any number to select, type cancel to exit")

        await ctx.send(embed=embed)

        def check(m): return (m.author.id ==
                              ctx.author.id and m.channel == ctx.channel)
        resp = await self.bot.wait_for('message', check=check)
        res = resp.content
        if res == "cancel":
            return await ctx.send(':white_check_mark:')
        elif re.match(r'[0-9]', res) and int(res) < len(jobs_remove_array):
            # remove job here
            res = int(res)
            k = jobs_remove_array[res]
            jobs[str(ctx.author.id)].pop(k)
            self.save_json(jobs)
            self.scheduler.remove_job(k)
            return await ctx.send(':white_check_mark: Entry deleted.')
        else:
            return await ctx.send(':x: No match found.')

    @commands.command(
        name="reminders",
        description="List all reminders of yourself or a mentioned user",
        aliases=['rm']
    )
    async def reminders(self, ctx):
        with open("jobs.json") as f:
            jobs = json.loads(f.read())
        f.close()
        usr = ctx.message.mentions[0].id if bool(
            ctx.message.mentions) else ctx.author.id
        await self.send_reminders(ctx=ctx, usr=usr, jobs=jobs)

    async def send_reminders(self, ctx, usr, jobs):
        if (not str(usr) in jobs
                or not bool(jobs[str(usr)])):
            return await ctx.send("You have no reminders!")
        reminders_list = jobs[str(usr)]
        embed = Embed(
            title="{}'s current reminders".format(
                self.bot.get_user(usr).display_name),
            colour=Colour.blue()
        )
        for key, job in reminders_list.items():  # dict btw oof
            embed.add_field(
                name="{}".format(job["desc"]),
                value="{}".format(job["date"])
            )
        return await ctx.send(embed=embed)

    @commands.command(
        name="remindme",
        description="on a certain date",
        aliases=['r']
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

        def check(m): return (m.author.id ==
                              ctx.author.id and m.channel == ctx.channel)

        desc = await self.bot.wait_for('message', check=check)

        self.cc_job.desc = desc.content

        time = await self.prompt_time(ctx)
        while not bool(time):
            await ctx.channel.send(
                "Date is in wrong format. Try again!")
            time = await self.prompt_time(ctx)
        # cancel
        if time == "cancel":
            self.set_waiting_stage(0)
            self.set_waiting_user(0)
            self.cc_job = None
            return await ctx.send(':white_check_mark:')

        await ctx.channel.send(
            "You will get an @ on {.date} saying: {.desc}"
            .format(self.cc_job, self.cc_job))

        # create job and reset stuff
        self.set_waiting_stage(0)
        self.set_waiting_user(0)
        self.add_job(self.cc_job)
        self.cc_job = None

    def add_job(self, job):
        # todo save job to file
        jobid = str(uuid.uuid4())
        self.scheduler.add_job(func=self.remind, trigger='date', next_run_time=job.date,
                               id=jobid, args=[job.user, job.desc, job.ctx, jobid])
        with open("jobs.json") as f:
            jobs = json.loads(f.read())
        f.close()
        j = {
            "desc": job.desc,
            "date": str(job.date),
            "channel": job.ctx.id
        }
        if not str(job.user) in jobs:
            jobs[str(job.user)] = {}
        jobs[str(job.user)][jobid] = j
        self.save_json(jobs)
        print("Added {} to {.user}"
              .format(jobid, job))

    def save_json(self, jobs):
        with open('jobs.json', 'w') as f:
            json.dump(jobs, f, indent=4, sort_keys=True)
        f.close()

    async def remind(self, user, desc, ctx, jobid):
        with open("jobs.json") as f:
            jobs = json.loads(f.read())
        jobs[str(user)].pop(jobid)
        self.save_json(jobs)
        print("Removed {} from {}"
              .format(jobid, user))

        return await ctx.send("<@{}> {}".format(user, desc))

    async def prompt_time(self, ctx):

        def check(m):
            return (m.author.id == ctx.author.id and
                    m.channel == ctx.channel)

        await ctx.channel.send(
            "Enter a time in the format `{}`, `cancel` to exit.".format(self.frmt))
        m = await self.bot.wait_for('message', check=check)
        if m.content == "cancel":
            return "cancel"
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

        regex_date_time = r"^\d+\-\d+\-\d+ \d+\:\d+\:\d+$"
        #regex_time = r"^\d+\:\d+\:\d+$"
        if re.match(regex_date_time, t):
            return self.validate_time(t, self.frmt)
        # elif re.match(regex_time, t):
        #     return validate_time(t, frmt.split(" ")[1])
        else:
            print("Wrong format from regex")
            return False


def setup(bot):
    bot.add_cog(Remind(bot))
