from app.infrastructure.rollback.rollback_client import RollbackClient

class RollbackService:
    def __init__(self, client: RollbackClient):
        self.client = client

    async def rollback(self, deployment_id: str, reason: str, environment: str = "staging"):
        rollback = await self.client.rollback_deployment(deployment_id, reason, environment)
        # business rule: validate reason length (as example)
        if len(reason.strip()) < 5:
            raise ValueError("Rollback reason must be at least 5 characters")
        return rollback
    
    async def get_recent_rollbacks(self):
        rollbacks = await self.client.get_rollbacks()
        # business rule: only show successful rollbacks (as example)
        return [rb for rb in rollbacks if rb.status == "SUCCESS"]
