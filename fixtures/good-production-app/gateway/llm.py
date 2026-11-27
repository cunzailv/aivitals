class ModelGateway:
    def __init__(self, key_pool, redis):
        self.key_pool = key_pool
        self.redis = redis
    async def ainvoke(self, tenant_id, messages, budget=None):
        usage = {"tenant_id": tenant_id, "tokens": len(messages)}
        self.redis.incr(f"usage:{tenant_id}")
        return usage
