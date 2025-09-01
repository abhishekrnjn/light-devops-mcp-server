import uuid
from datetime import datetime, timezone
from app.domain.entities.rollback import Rollback

class RollbackClient:
    async def rollback_deployment(self, deployment_id: str, reason: str) -> Rollback:
        # Mock rollback
        return Rollback(
            rollback_id=str(uuid.uuid4()),
            deployment_id=deployment_id,
            status="SUCCESS",
            reason=reason,
            timestamp=datetime.now(timezone.utc)
        )
    
    async def get_rollbacks(self) -> list[Rollback]:
        # Mock recent rollbacks
        reasons = ["Performance issues", "Bug found", "Security concern"]
        statuses = ["SUCCESS", "FAILED", "IN_PROGRESS"]
        
        return [
            Rollback(
                rollback_id=str(uuid.uuid4()),
                deployment_id=str(uuid.uuid4()),
                status=statuses[i % len(statuses)],
                reason=reasons[i % len(reasons)],
                timestamp=datetime.now(timezone.utc)
            )
            for i in range(3)
        ]
