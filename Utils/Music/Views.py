"""All Functions and modals for Music module."""

import discord, wavelink
from discord.ext import commands
from discord.ui import InputText, Modal

from Data.Localizations import Embeds
from Utils.Bot import Logger, Functions


def action_log(r: discord.Interaction, action: str):
    Logger.log("MUSIC", "INTERACTION", f'User {r.user.name} ({r.user.id}) {action}. Guild ID - {r.guild.id}')


class SongModal(Modal):
    def __init__(self, bot, ctx: commands.Context, vc: wavelink.Player, msg: discord.Message, language: str) -> None:
        self.bot = bot
        self.ctx = ctx
        self.vc = vc
        self.msg = msg
        super().__init__(
            title="Добавить песню в очередь" if language == "ru" else "Add track to the queue"
        )

        self.add_item(
            InputText(
                label="Трек" if language == "ru" else "Song",
                placeholder="Ссылка или название трека (YouTube)." if language == "ru" else "Song link or YouTube url.",
                style=discord.InputTextStyle.short,
            )
        )
    async def callback(self, r: discord.Interaction):
        try:
            vc: wavelink.Player = r.guild.voice_client
            if vc.notifications_level == 2:
                await r.response.defer()
            else:
                await r.response.defer(ephemeral=True)
                
            if vc.queue.count > 24:
                return await r.followup.send(
                    embed=Embeds.Music.premium_queue_is_full(Functions.get_locale(self.bot, r))
                )

            try:
                song = await wavelink.YouTubeTrack.search(query=self.children[0].value, return_first=True)
            except:
                return await r.followup.send(
                    embed=Embeds.Music.song_not_found(Functions.get_locale(self.bot, r))
                )

            if int(song.duration) > 3600:
                return await r.followup.send(
                    embed=Embeds.Music.song_is_too_long(Functions.get_locale(self.bot, r))
                )

            if vc.queue.is_empty and not vc.is_playing():
                await vc.play(song)
                await self.msg.edit(embed=Embeds.Music.music_player_connected(vc.language, song, self.ctx))
                if vc.notifications_level == 2:
                    return await r.followup.send(
                        embed=Embeds.Music.track_added_to_play(Functions.get_locale(self.bot, r), r, song)
                        )
                else:
                    return await r.followup.send(
                        embed=Embeds.Music.self_track_added_to_play(Functions.get_locale(self.bot, r), r, song), ephemeral=True
                        )
            else:
                await vc.queue.put_wait(song)
                if vc.notifications_level == 2:
                    return await r.followup.send(
                        embed=Embeds.Music.track_added(Functions.get_locale(self.bot, r), r, song)
                        )
                else:
                    return await r.followup.send(
                        embed=Embeds.Music.self_track_added(Functions.get_locale(self.bot, r), r, song), ephemeral=True
                    )

        except Exception as error:
            Logger.log("MUSIC", "ERROR", f"Error on track add (Modal): {error} | Guild ID: {r.guild.id}")
            Logger.log_traceback()
            return await r.followup.send(
                embed=Embeds.Music.error(Functions.get_locale(self.bot, r)), ephemeral=True
                )


class SoundModal(Modal):
    def __init__(self, bot, ctx: commands.Context, vc: wavelink.Player, language: str) -> None:
        self.bot = bot
        self.ctx = ctx
        self.vc = vc
        super().__init__(
            title="Изменить уровень громкости" if language == "ru" else "Change player volume"
        )

        self.add_item(
            InputText(
                label="Уровень громкости" if language == "ru" else "Volume",
                placeholder="Число от 0 до 200." if language == "ru" else "Integer from 0 to 200",
                style=discord.InputTextStyle.short,
            )
        )
    async def callback(self, r: discord.Interaction):
        try:
            vc: wavelink.Player = r.guild.voice_client
            volume = self.children[0].value

            if volume.isdigit() is False:
                return await r.response.send_message(
                    embed=Embeds.Music.invalid_volume(Functions.get_locale(self.bot, r)), ephemeral=True
                )

            if 0 <= int(volume) <= 200:
                await vc.set_volume(int(volume))
                if vc.notifications_level == 2:
                    return await r.response.send_message(
                        embed=Embeds.Music.volume_set(Functions.get_locale(self.bot, r), r, volume)
                    )
                else:
                    return await r.response.send_message(
                        embed=Embeds.Music.self_volume_set(Functions.get_locale(self.bot, r), volume), ephemeral=True
                    )
            else:
                return await r.response.send_message(
                    embed=Embeds.Music.invalid_volume(Functions.get_locale(self.bot, r)), ephemeral=True
                )

        except Exception as error:
            Logger.log("MUSIC", "ERROR", f"Error on volume change (Modal): {error} | Guild ID: {r.guild.id}")
            Logger.log_traceback()
            return await r.response.send_message(
                embed=Embeds.Music.error(Functions.get_locale(self.bot, r)), ephemeral=True
            )


class Player(discord.ui.View):
    def __init__(self, bot, ctx: commands.Context, msg: discord.Message, player: wavelink.Player):
        self.bot = bot
        self.ctx: commands.Context = ctx
        self.msg: discord.Message = msg
        self.player: wavelink.Player = player
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:av_previous:1028326288424964208>", style=discord.ButtonStyle.gray, custom_id="av_previous", row=0)
    async def previous(self, button: discord.Button, r: discord.Interaction):
        action_log(r, "played previous song")
        try:
            if not r.guild.voice_client:
                return await r.response.send_message(
                    embed=Embeds.Music.voice_client_not_connected(Functions.get_locale(self.bot, r)), ephemeral=True
                )
            elif not getattr(r.user.voice, "channel", None):
                return await r.response.send_message(
                    embed=Embeds.Music.join_vc(Functions.get_locale(self.bot, r)), ephemeral=True
                )
            else:
                vc: wavelink.Player = r.guild.voice_client
            
            if vc.previous_track is not None:
                if vc.loop:
                    vc.loop = False
                    for b in self.children:
                        if b.custom_id == "av_loop":
                            b.style = discord.ButtonStyle.gray
                            b.emoji = "<:av_loop:1028326291843338300>"

                track = await wavelink.YouTubeTrack.search(query=vc.track.title, return_first=True)
                previous_track = await wavelink.YouTubeTrack.search(query=vc.previous_track.title, return_first=True)

                vc.queue.put_at_front(track)
                vc.queue.put_at_front(previous_track)

                vc.previous_track = None

                postition = int(vc.track.length) * 10000
                await vc.seek(position=postition)

                if vc.notifications_level == 2:
                    await self.msg.edit(
                        embed=Embeds.Music.music_player_connected(vc.language, previous_track, self.ctx), view=self
                    )
                    await r.response.send_message(
                        embed=Embeds.Music.returned(Functions.get_locale(self.bot, r), r, False)
                    )
                elif vc.notifications_level == 1:
                    await self.msg.edit(
                        embed=Embeds.Music.music_player_connected(vc.language, previous_track, self.ctx), view=self
                    )
                    await r.response.send_message(
                        embed=Embeds.Music.returned(Functions.get_locale(self.bot, r), r, True), ephemeral=True
                    )
                else:
                    return await r.response.edit_message(
                        embed=Embeds.Music.music_player_connected(vc.language, previous_track, self.ctx), view=self
                    )
            else:
                return await r.response.send_message(
                    embed=Embeds.Music.previous_track_is_none(Functions.get_locale(self.bot, r)), ephemeral=True
                )

        except Exception as error:
            Logger.log("MUSIC", "ERROR", f"Error on previous track play (Modal): {error} | Guild ID: {r.guild.id}")
            Logger.log_traceback()
            return await r.response.send_message(
                embed=Embeds.Music.error(Functions.get_locale(self.bot, r)), ephemeral=True
            )

    @discord.ui.button(emoji="<:av_pause:1028328245227180142>", style=discord.ButtonStyle.gray, custom_id="av_pause", row=0)
    async def pause(self, button: discord.Button, r: discord.Interaction):
        action_log(r, "paused player playback")
        try:
            if not r.guild.voice_client:
                return await r.response.send_message(
                    embed=Embeds.Music.nothing_is_playing(Functions.get_locale(self.bot, r)), ephemeral=True
                )
            elif not getattr(r.user.voice, "channel", None):
                return await r.response.send_message(
                    embed=Embeds.Music.join_vc(Functions.get_locale(self.bot, r)), ephemeral=True
                )
            else:
                vc: wavelink.Player = self.ctx.voice_client

            if vc.is_playing() is False: return await r.response.send_message(
                embed=Embeds.Music.nothing_is_playing(Functions.get_locale(self.bot, r)), ephemeral=True
            )

            if vc.is_paused() == False:
                button.emoji = "<:ari_paused:963563984181661696>"
                button.style = discord.ButtonStyle.blurple
                await vc.pause()
                if vc.notifications_level == 2:
                    await self.msg.edit(view=self)
                    return await r.response.send_message(
                        embed=Embeds.Music.paused(Functions.get_locale(self.bot, r), r, False), delete_after=10
                    )
                elif vc.notifications_level == 1:
                    await self.msg.edit(view=self)
                    return await r.response.send_message(
                        embed=Embeds.Music.paused(Functions.get_locale(self.bot, r), r, True), ephemeral=True
                    )
                else:
                    return await r.response.edit_message(view=self)
            else:
                button.emoji = "<:av_pause:1028328245227180142>"
                button.style = discord.ButtonStyle.gray
                await vc.resume()
                if vc.notifications_level == 2:
                    await self.msg.edit(view=self)
                    return await r.response.send_message(
                        embed=Embeds.Music.resumed(Functions.get_locale(self.bot, r), r, False), delete_after=10
                    )
                elif vc.notifications_level == 1:
                    await self.msg.edit(view=self)
                    return await r.response.send_message(
                        embed=Embeds.Music.resumed(Functions.get_locale(self.bot, r), r, True), ephemeral=True
                    )
                else:
                    return await r.response.edit_message(view=self)

        except Exception as error:
            Logger.log("MUSIC", "ERROR", f"Error on track pause (Modal): {error} | Guild ID: {r.guild.id}")
            Logger.log_traceback()
            return await r.response.send_message(
                embed=Embeds.Music.error(Functions.get_locale(self.bot, r)), ephemeral=True
            )

    @discord.ui.button(emoji="<:av_next:1028326301901279303>", style=discord.ButtonStyle.gray, custom_id="av_next", row=0)
    async def next_song(self, button: discord.Button, r: discord.Interaction):
        action_log(r, "played next track")
        try:
            if not r.guild.voice_client:
                return await r.response.send_message(
                    embed=Embeds.Music.voice_client_not_connected(Functions.get_locale(self.bot, r)), ephemeral=True
                )
            elif not getattr(r.user.voice, "channel", None):
                return await r.response.send_message(
                    embed=Embeds.Music.join_vc(Functions.get_locale(self.bot, r)), ephemeral=True
                )
            else:
                vc: wavelink.Player = r.guild.voice_client
            
            if vc.queue.is_empty:
                return await r.response.send_message(
                    embed=Embeds.Music.queue_is_empty(Functions.get_locale(self.bot, r)), ephemeral=True
                )
            
            if vc.loop:
                vc.loop = False
                for b in self.children:
                    if b.custom_id == "av_loop":
                        b.style = discord.ButtonStyle.gray
                        b.emoji = "<:av_loop:1028326291843338300>"

            track = vc.track
            vc.previous_track = track
            
            postition = int(vc.track.length) * 10000
            await vc.seek(position=postition)
            song = vc.track

            if vc.notifications_level == 2:
                await self.msg.edit(
                    embed=Embeds.Music.music_player_connected(vc.language, song, self.ctx), view=self
                )
                await r.response.send_message(
                    embed=Embeds.Music.skipped(Functions.get_locale(self.bot, r), r, False)
                )
            elif vc.notifications_level == 1:
                await self.msg.edit(
                    embed=Embeds.Music.music_player_connected(vc.language, song, self.ctx), view=self
                )
                await r.response.send_message(
                    embed=Embeds.Music.skipped(Functions.get_locale(self.bot, r), r, True), ephemeral=True
                )
            else:
                return await r.response.edit_message(
                    embed=Embeds.Music.music_player_connected(vc.language, song, self.ctx), view=self
                )
        
        except Exception as error:
            Logger.log("MUSIC", "ERROR", f"Error on track skip (Modal): {error} | Guild ID: {r.guild.id}")
            Logger.log_traceback()
            return await r.response.send_message(
                embed=Embeds.Music.error(Functions.get_locale(self.bot, r)), ephemeral=True
            )

    @discord.ui.button(emoji="<:av_stop:1028328895218471014>", style=discord.ButtonStyle.gray, custom_id="av_stop", row=0)
    async def stop(self, button: discord.Button, r: discord.Interaction):
        action_log(r, "stopped player")
        try:
            if not r.guild.voice_client:
                return await r.response.send_message(
                    embed=Embeds.Music.stop_not_connected(Functions.get_locale(self.bot, r)), ephemeral=True
                )
            elif not getattr(r.user.voice, "channel", None):
                return await r.response.send_message(
                    embed=Embeds.Music.join_vc(Functions.get_locale(self.bot, r)), ephemeral=True
                )
            else:
                vc: wavelink.Player = r.guild.voice_client
            
            await vc.stop()
            vc.cleanup()
            await vc.disconnect()

            mes = await self.ctx.fetch_message(self.msg.id)

            for b in self.children:
                b.disabled = True
                if b.custom_id == "av_stop":
                    b.style = discord.ButtonStyle.red
                    b.emoji = "<:ari_stop_white:963813662794088568>"

            embed_to_dict = mes.embeds[0].to_dict()
            embed_to_dict["color"] = 0xdd5f65
            embed = discord.Embed.from_dict(embed_to_dict)

            await self.msg.edit(embed=embed, view=self)
            return await r.response.send_message(
                embed=Embeds.Music.stopped(Functions.get_locale(self.bot, r), r)
            )
        
        except Exception as error:
            Logger.log("MUSIC", "ERROR", f"Error on player stop (Modal): {error} | Guild ID: {r.guild.id}")
            Logger.log_traceback()
            return await r.response.send_message(
                embed=Embeds.Music.error(Functions.get_locale(self.bot, r)), ephemeral=True
            )

    @discord.ui.button(emoji="<:av_add_song:1028326304778555513>", style=discord.ButtonStyle.gray, custom_id="av_add_song", row=0)
    async def add_song(self, button: discord.Button, r: discord.Interaction):
        action_log(r, "added track to the queue")
        try:
            if not r.guild.voice_client:
                return await r.response.send_message(
                    embed=Embeds.Music.voice_client_not_connected(Functions.get_locale(self.bot, r)), ephemeral=True
                )
            elif not getattr(r.user.voice, "channel", None):
                return await r.response.send_message(
                    embed=Embeds.Music.join_vc(Functions.get_locale(self.bot, r)), ephemeral=True
                )
            else:
                vc: wavelink.Player = r.guild.voice_client

            await r.response.send_modal(SongModal(self.bot, self.ctx, vc, self.msg, Functions.get_locale(self.bot, r)))

        except Exception as error:
            Logger.log("MUSIC", "ERROR", f"Error on add track to the queue (Modal): {error} | Guild ID: {r.guild.id}")
            Logger.log_traceback()
            return await r.response.send_message(
                embed=Embeds.Music.error(Functions.get_locale(self.bot, r)), ephemeral=True
            )

    @discord.ui.button(emoji="<:av_replay:1028326290291433472>", style=discord.ButtonStyle.gray, custom_id="av_replay", row=1)
    async def replay(self, button: discord.Button, r: discord.Interaction):
        action_log(r, "replayed track")
        try:
            if not r.guild.voice_client:
                return await r.response.send_message(
                    embed=Embeds.Music.nothing_is_playing(Functions.get_locale(self.bot, r)), ephemeral=True
                )
            elif not getattr(r.user.voice, "channel", None):
                return await r.response.send_message(
                    embed=Embeds.Music.join_vc(Functions.get_locale(self.bot, r)), ephemeral=True
                )
            else:
                vc: wavelink.Player = r.guild.voice_client

            if vc.is_playing() is False: return await r.response.send_message(embed=Embeds.Music.loop_nothing_playing(Functions.get_locale(self.bot, r)), ephemeral=True)
            
            await vc.seek(0)
            if vc.notifications_level == 2:
                return await r.response.send_message(
                    embed=Embeds.Music.replay(Functions.get_locale(self.bot, r), r, False), delete_after=10
                )
            elif vc.notifications_level == 1:
                return await r.response.send_message(
                    embed=Embeds.Music.replay(Functions.get_locale(self.bot, r), r, True), ephemeral=True
                )
            else:
                return await r.response.edit_message(view=self)
        except Exception as error:
            Logger.log("MUSIC", "ERROR", f"Error on track replay (Modal): {error} | Guild ID: {r.guild.id}")
            Logger.log_traceback()
            return await r.response.send_message(
                embed=Embeds.Music.error(Functions.get_locale(self.bot, r)), ephemeral=True
            )

    @discord.ui.button(emoji="<:av_loop:1028326291843338300>", style=discord.ButtonStyle.gray, custom_id="av_loop", row=1)
    async def loop(self, button: discord.Button, r: discord.Interaction):
        action_log(r, "looped track")
        try:
            if not r.guild.voice_client:
                return await r.response.send_message(
                    embed=Embeds.Music.nothing_is_playing(Functions.get_locale(self.bot, r)), ephemeral=True
                )
            elif not getattr(r.user.voice, "channel", None):
                return await r.response.send_message(
                    embed=Embeds.Music.join_vc(Functions.get_locale(self.bot, r)), ephemeral=True
                )
            else:
                vc: wavelink.Player = r.guild.voice_client

            if vc.is_playing() is False: return await r.response.send_message(
                embed=Embeds.Music.loop_nothing_playing(Functions.get_locale(self.bot, r)), ephemeral=True
            )

            if not hasattr(vc, "loop"):
                setattr(vc, "loop", False)

            if vc.loop == False:
                vc.loop = True
                button.emoji = "<:ari_loop_white:963565579749425202>"
                button.style = discord.ButtonStyle.blurple
                if vc.notifications_level == 2:
                    await self.msg.edit(view=self)
                    return await r.response.send_message(
                        embed=Embeds.Music.loop_enabled(Functions.get_locale(self.bot, r), r, False), delete_after=10
                    )
                elif vc.notifications_level == 1:
                    await self.msg.edit(view=self)
                    return await r.response.send_message(
                        embed=Embeds.Music.loop_enabled(Functions.get_locale(self.bot, r), r, True), ephemeral=True
                    )
                else:
                    return await r.response.edit_message(view=self)
            else:
                vc.loop = False
                button.emoji = "<:av_loop:1028326291843338300>"
                button.style = discord.ButtonStyle.gray
                if vc.notifications_level == 2:
                    await self.msg.edit(view=self)
                    await r.response.send_message(
                        embed=Embeds.Music.loop_disabled(Functions.get_locale(self.bot, r), r, False), delete_after=10
                    )
                elif vc.notifications_level == 1:
                    await self.msg.edit(view=self)
                    await r.response.send_message(
                        embed=Embeds.Music.loop_disabled(Functions.get_locale(self.bot, r), r, True), ephemeral=True
                    )
                else:
                    return await r.response.edit_message(view=self)

        except Exception as error:
            Logger.log("MUSIC", "ERROR", f"Error on track loop (Modal): {error} | Guild ID: {r.guild.id}")
            Logger.log_traceback()
            return await r.response.send_message(
                embed=Embeds.Music.error(Functions.get_locale(self.bot, r)), ephemeral=True
            )

    @discord.ui.button(emoji="<:av_music_queue:1028326285690282075>", style=discord.ButtonStyle.gray, custom_id="av_queue", row=1)
    async def queue(self, button: discord.Button, r: discord.Interaction):
        action_log(r, "view tracks queue")
        try:
            if not r.guild.voice_client:
                return await r.response.send_message(
                    embed=Embeds.Music.nothing_is_playing(Functions.get_locale(self.bot, r)), ephemeral=True
                )
            elif not getattr(r.user.voice, "channel", None):
                return await r.response.send_message(
                    embed=Embeds.Music.join_vc(Functions.get_locale(self.bot, r)), ephemeral=True
                )
            else:
                vc: wavelink.Player = r.guild.voice_client

            if vc.queue.is_empty: return await r.response.send_message(
                embed=Embeds.Music.queue_is_empty_(Functions.get_locale(self.bot, r)), ephemeral=True
            )

            queue = vc.queue.copy()
            return await r.response.send_message(
                embed=Embeds.Music.queue(Functions.get_locale(self.bot, r), queue), ephemeral=True
            )

        except Exception as error:
            Logger.log("MUSIC", "ERROR", f"Error on track queue view (Modal): {error} | Guild ID: {r.guild.id}")
            Logger.log_traceback()
            return await r.response.send_message(
                embed=Embeds.Music.error(Functions.get_locale(self.bot, r)), ephemeral=True
            )

    @discord.ui.button(emoji="<:av_volume_settings:1028326298487115880>", style=discord.ButtonStyle.gray, custom_id="av_volume_settings", row=1)
    async def volume_settings(self, button: discord.Button, r: discord.Interaction):
        action_log(r, "changed player volume")
        try:
            if not r.guild.voice_client:
                return await r.response.send_message(
                    embed=Embeds.Music.voice_client_not_connected(Functions.get_locale(self.bot, r)), ephemeral=True
                )
            elif not getattr(r.user.voice, "channel", None):
                return await r.response.send_message(
                    embed=Embeds.Music.join_vc(Functions.get_locale(self.bot, r)), ephemeral=True
                )
            else:
                vc: wavelink.Player = r.guild.voice_client
            
            await r.response.send_modal(SoundModal(self.bot, self.ctx, vc, Functions.get_locale(self.bot, r)))

        except Exception as error:
            Logger.log("MUSIC", "ERROR", f"Error on player volume change (Modal): {error} | Guild ID: {r.guild.id}")
            Logger.log_traceback()
            return await r.response.send_message(
                embed=Embeds.Music.error(Functions.get_locale(self.bot, r)), ephemeral=True
            )

    @discord.ui.button(emoji="<:av_notifications_on:1028326287091179612>", style=discord.ButtonStyle.gray, custom_id="av_player_notifications", row=1)
    async def notifications(self, button: discord.Button, r: discord.Interaction):
        action_log(r, "changed player notifications level")
        try:
            if not r.guild.voice_client:
                return await r.response.send_message(
                    embed=Embeds.Music.nothing_is_playing(Functions.get_locale(self.bot, r)), ephemeral=True
                )
            elif not getattr(r.user.voice, "channel", None):
                return await r.response.send_message(
                    embed=Embeds.Music.join_vc(Functions.get_locale(self.bot, r)), ephemeral=True
                )
            else:
                vc: wavelink.Player = r.guild.voice_client

            if not hasattr(vc, "notifications_level"):
                setattr(vc, "notifications_level", 2)

            if vc.notifications_level == 2:
                vc.notifications_level = 0
                button.style = discord.ButtonStyle.red
                button.emoji = "<:ari_notifications_off:964415669582069770>"
                await self.msg.edit(view=self)
                await r.response.send_message(
                    embed=Embeds.Music.notifications(Functions.get_locale(self.bot, r), r, 0)
                )
            elif vc.notifications_level == 1:
                vc.notifications_level = 2
                button.style = discord.ButtonStyle.gray
                button.emoji = "<:av_notifications_on:1028326287091179612>"
                await self.msg.edit(view=self)
                await r.response.send_message(
                    embed=Embeds.Music.notifications(Functions.get_locale(self.bot, r), r, 2)
                )
            else:
                vc.notifications_level = 1
                button.style = discord.ButtonStyle.blurple
                button.emoji = "<:ari_notifications_white:964415669816950794>"
                await self.msg.edit(view=self)
                await r.response.send_message(
                    embed=Embeds.Music.notifications(Functions.get_locale(self.bot, r), r, 1)
                )

        except Exception as error:
            Logger.log("MUSIC", "ERROR", f"Error on player notifications level change (Modal): {error} | Guild ID: {r.guild.id}")
            Logger.log_traceback()
            return await r.response.send_message(
                embed=Embeds.Music.error(Functions.get_locale(self.bot, r)), ephemeral=True
            )

class DisabledPlayer(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:av_previous:1028326288424964208>", style=discord.ButtonStyle.gray, custom_id="av_previous", disabled=True, row=0)
    async def previous(self, button: discord.Button, r: discord.Interaction):
        return

    @discord.ui.button(emoji="<:av_pause:1028328245227180142>", style=discord.ButtonStyle.gray, custom_id="av_pause", disabled=True, row=0)
    async def pause(self, button: discord.Button, r: discord.Interaction):
        return

    @discord.ui.button(emoji="<:av_next:1028326301901279303>", style=discord.ButtonStyle.gray, custom_id="av_next", disabled=True, row=0)
    async def next_song(self, button: discord.Button, r: discord.Interaction):
        return

    @discord.ui.button(emoji="<:ari_stop_white:963813662794088568>", style=discord.ButtonStyle.red, custom_id="av_stop", disabled=True, row=0)
    async def stop(self, button: discord.Button, r: discord.Interaction):
        return

    @discord.ui.button(emoji="<:av_add_song:1028326304778555513>", style=discord.ButtonStyle.gray, custom_id="av_add_song", disabled=True, row=0)
    async def add_song(self, button: discord.Button, r: discord.Interaction):
        return

    @discord.ui.button(emoji="<:av_replay:1028326290291433472>", style=discord.ButtonStyle.gray, custom_id="av_replay", disabled=True, row=1)
    async def replay(self, button: discord.Button, r: discord.Interaction):
        return

    @discord.ui.button(emoji="<:av_loop:1028326291843338300>", style=discord.ButtonStyle.gray, custom_id="av_loop", disabled=True, row=1)
    async def loop(self, button: discord.Button, r: discord.Interaction):
        return

    @discord.ui.button(emoji="<:av_music_queue:1028326285690282075>", style=discord.ButtonStyle.gray, custom_id="av_queue", disabled=True, row=1)
    async def queue(self, button: discord.Button, r: discord.Interaction):
        return

    @discord.ui.button(emoji="<:av_volume_settings:1028326298487115880>", style=discord.ButtonStyle.gray, custom_id="av_volume_settings", disabled=True, row=1)
    async def volume_settings(self, button: discord.Button, r: discord.Interaction):
        return

    @discord.ui.button(emoji="<:av_notifications_on:1028326287091179612>", style=discord.ButtonStyle.gray, custom_id="av_player_notifications", disabled=True, row=1)
    async def notifications(self, button: discord.Button, r: discord.Interaction):
        return
