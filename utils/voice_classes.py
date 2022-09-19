from asyncio import get_event_loop, AbstractEventLoop
from urllib.parse import quote

import youtube_dl
from discord import PCMVolumeTransformer, FFmpegPCMAudio

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {'options': '-vn'}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


__all__ = ('YouTubeData', 'TTSData', 'AudioSource')


class YouTubeData:
    title: str
    source_url: str
    url: str
    duration: int
    thumbnail_url: str
    channel: str

    __slots__ = ('title', 'source_url', 'url', 'duration', 'thumbnail_url', 'channel')

    def __init__(self, data: dict):
        self.title = data.get('title')
        self.source_url = data.get('url')
        self.url = data.get('webpage_url')
        self.duration = data.get('duration')
        self.thumbnail_url = data.get('thumbnail')
        self.channel = data.get('channel')

    @classmethod
    async def from_query(cls, query: str, *, loop: AbstractEventLoop = None) -> 'YouTubeData':
        loop = loop or get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        assert data

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        return cls(data)


class TTSData:
    text: str
    source_url: str

    __slots__ = ('text', 'source_url')

    def __init__(self, query: str):
        self.text = query
        self.source_url = f'https://api.streamelements.com/kappa/v2/speech?voice=Brian&text={quote(query)}'


class AudioSource(PCMVolumeTransformer):
    def __init__(self, data: YouTubeData | TTSData):
        super().__init__(FFmpegPCMAudio(data.source_url, **ffmpeg_options), 0.5)
