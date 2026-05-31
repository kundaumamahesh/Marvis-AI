class CacheManager:

    CACHE = {}

    @staticmethod
    def get(key):

        return CacheManager.CACHE.get(key)

    @staticmethod
    def set(key, value):

        CacheManager.CACHE[key] = value
