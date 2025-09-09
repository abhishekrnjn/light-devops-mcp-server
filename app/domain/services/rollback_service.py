from typing import Tuple, Dict, Any
from app.infrastructure.rollback.rollback_client import RollbackClient
from app.domain.entities.rollback import Rollback

class RollbackService:
    def __init__(self, client: RollbackClient):
        self.client = client

    async def rollback(self, deployment_id: str, reason: str, environment: str = "staging") -> Tuple[Rollback, int, Dict[str, Any]]:
        # business rule: validate reason length (as example)
        if len(reason.strip()) < 5:
            raise ValueError("Rollback reason must be at least 5 characters")
        
        rollback, http_status, json_response = await self.client.rollback_deployment(deployment_id, reason, environment)
        return rollback, http_status, json_response
    
    async def get_recent_rollbacks(self) -> Tuple[list[Rollback], int, Dict[str, Any]]:
        rollbacks, http_status, json_response = await self.client.get_rollbacks()
        # business rule: only show successful rollbacks (as example)
        successful_rollbacks = [rb for rb in rollbacks if rb.status == "SUCCESS"]
        
        # Update JSON response to reflect filtered results
        json_response["rollbacks"] = [rb.dict() for rb in successful_rollbacks]
        json_response["count"] = len(successful_rollbacks)
        json_response["message"] = f"Retrieved {len(successful_rollbacks)} successful rollbacks"
        json_response["metadata"]["total_rollbacks"] = len(successful_rollbacks)
        json_response["metadata"]["status_summary"]["success"] = len(successful_rollbacks)
        json_response["metadata"]["status_summary"]["failed"] = 0
        json_response["metadata"]["status_summary"]["in_progress"] = 0
        
        return successful_rollbacks, http_status, json_response
