import random

from .indexed import Indexed
from .random import Random
from .recommender import Recommender


class MyRec(Recommender):
    def __init__(self, tracks_redis, recommendations_redis, catalog, highlyranked, used):
        self.random = Random(tracks_redis)
        self.tracks_redis = tracks_redis
        self.catalog = catalog
        self.recommendations_redis = recommendations_redis
        self.fallback = Indexed(tracks_redis, recommendations_redis, catalog)
        self.highlyranked = highlyranked
        self.used = used

    def recommend_next(self, user: int, prev_track: int, prev_track_time: float) -> int:
        if user not in self.used:
            self.used[user] = []
        self.used[user].append(prev_track)
        if user not in self.highlyranked:
            self.highlyranked[user] = {}
        if prev_track_time > 0.9:  # found the best value
            if prev_track not in self.highlyranked[user]:
                self.highlyranked[user][prev_track] = 1
            else:
                self.highlyranked[user][prev_track] = self.highlyranked[user][prev_track] + 1
            good_track = prev_track
        else:
            if len(self.highlyranked[user]) > 0:
                good_track, num = random.choice(list(self.highlyranked[user].items()))
                self.highlyranked[user][good_track] = num + 1
            else:
                return self.fallback.recommend_next(user, prev_track, prev_track_time)
        previous_track = self.tracks_redis.get(good_track)
        if previous_track is None:
            return self.fallback.recommend_next(user, prev_track, prev_track_time)

        previous_track = self.catalog.from_bytes(previous_track)
        recommendations = previous_track.recommendations
        if not recommendations:
            return self.fallback.recommend_next(user, prev_track, prev_track_time)

        unshuffled = list(recommendations)
        for i in range(0, len(unshuffled)):
            if not unshuffled[i] in self.used[user]:
                return unshuffled[i]
        return unshuffled[0]
