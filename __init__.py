import random
from os.path import join, dirname

import requests
from json_database import JsonStorageXDG

from ovos_utils.ocp import MediaType, PlaybackType
from ovos_workshop.decorators.ocp import ocp_search, ocp_featured_media
from ovos_workshop.skills.common_play import OVOSCommonPlaybackSkill


class CGBrosSkill(OVOSCommonPlaybackSkill):
    def __init__(self, *args, **kwargs):
        self.supported_media = [MediaType.SHORT_FILM,
                                MediaType.GENERIC]
        self.skill_icon = self.default_bg = join(dirname(__file__), "ui", "cgbros_icon.jpg")
        self.archive = JsonStorageXDG("TheCGBros", subfolder="OCP")
        super().__init__(*args, **kwargs)

    def initialize(self):
        self._sync_db()
        self.load_ocp_keywords()

    def load_ocp_keywords(self):
        titles = []
        movie_studio = []
        actors = []

        for url, data in self.archive.items():

            t = data["title"]
            if " by " in t:
                t, studio = t.split(" by ", 1)
                studio = studio.split("|")[0].replace("-", "").replace("&", ",").split("+")[0].strip()
                if "," in studio:
                    actors += [_.strip() for _ in studio.replace(" and ", ",").split(",") if _.strip()]
                else:
                    # NB: catches both movie directors and film studios
                    movie_studio.append(studio)
            if '"' in t:
                t = t.split('"')[1].strip()
                if ":" in t:
                    t, t2 = t.split(":", 1)
                    titles.append(t2)
                titles.append(t)

        self.register_ocp_keyword(MediaType.SHORT_FILM,
                                  "short_movie_name", titles)
        self.register_ocp_keyword(MediaType.SHORT_FILM,
                                  "movie_actor", actors)
        self.register_ocp_keyword(MediaType.SHORT_FILM,
                                  "film_studio", movie_studio)
        self.register_ocp_keyword(MediaType.SHORT_FILM,
                                  "movie_genre", ["3D", "shorts", "animated", "Animated Short",
                                                  "CGI", "Computer generated"])
        self.register_ocp_keyword(MediaType.SHORT_FILM,
                                  "shorts_streaming_provider",
                                  ["CGBros", "TheCGBros", "The CGBros", "CG Bros", "C G Bros"])

    def _sync_db(self):
        bootstrap = "https://github.com/JarbasSkills/skill-cgbros/raw/dev/bootstrap.json"
        data = requests.get(bootstrap).json()
        self.archive.merge(data)
        self.schedule_event(self._sync_db, random.randint(3600, 24 * 3600))

    def get_playlist(self, score=50, num_entries=50):
        pl = self.featured_media()[:num_entries]
        return {
            "match_confidence": score,
            "media_type": MediaType.SHORT_FILM,
            "playlist": pl,
            "playback": PlaybackType.VIDEO,
            "skill_icon": self.skill_icon,
            "image": self.skill_icon,
            "bg_image": self.default_bg,
            "title": "The CGBros (Movie Playlist)",
            "author": "The CGBros"
        }

    @ocp_search()
    def search_db(self, phrase, media_type):
        base_score = 25 if media_type == MediaType.SHORT_FILM else 0
        entities = self.ocp_voc_match(phrase)
        base_score += 50 * len(entities)

        title = entities.get("short_movie_name")
        film_studio = entities.get("film_studio")
        skill = "shorts_streaming_provider" in entities  # skill matched

        if skill:
            yield self.get_playlist(base_score)

        if title or film_studio:
            # only search db if user explicitly requested short films
            if title:
                base_score += 35
                candidates = [video for video in self.archive.values()
                              if title.lower() in video["title"].lower()]
            else:
                base_score += 20
                candidates = [video for video in self.archive.values()
                              if film_studio.lower() in video["title"].lower()]

            for video in candidates:
                yield {
                    "title": video["title"],
                    "artist": entities.get("film_studio") or video["author"],
                    "match_confidence": min(100, base_score),
                    "media_type": MediaType.SHORT_FILM,
                    "uri": "youtube//" + video["url"],
                    "playback": PlaybackType.VIDEO,
                    "skill_icon": self.skill_icon,
                    "skill_id": self.skill_id,
                    "image": video["thumbnail"],
                    "bg_image": self.default_bg,
                }

    @ocp_featured_media()
    def featured_media(self):
        return [{
            "title": video["title"],
            "image": video["thumbnail"],
            "match_confidence": 70,
            "media_type": MediaType.SHORT_FILM,
            "uri": "youtube//" + video["url"],
            "playback": PlaybackType.VIDEO,
            "skill_icon": self.skill_icon,
            "bg_image": video["thumbnail"],
            "skill_id": self.skill_id
        } for video in self.archive.values()]


if __name__ == "__main__":
    from ovos_utils.messagebus import FakeBus

    s = CGBrosSkill(bus=FakeBus(), skill_id="t.fake")
    for r in s.search_db("play something from Masters of Pie", MediaType.MOVIE):
        print(r)
        # {'title': 'CGI 3D Animated Short HD: "The Olympians" by - Masters of Pie', 'artist': 'Masters of Pie', 'match_confidence': 70, 'media_type': <MediaType.SHORT_FILM: 17>, 'uri': 'youtube//https://youtube.com/watch?v=0W-1TMVQh6c', 'playback': <PlaybackType.VIDEO: 1>, 'skill_icon': 'https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin/raw/master/ovos_plugin_common_play/ocp/res/ui/images/ocp.png', 'skill_id': 't.fake', 'image': 'https://i.ytimg.com/vi/0W-1TMVQh6c/sddefault.jpg', 'bg_image': '/home/miro/PycharmProjects/OCP_sprint/skills/skill-cgbros/ui/cgbros_icon.jpg'}
