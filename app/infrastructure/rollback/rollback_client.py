import uuid
import random
from datetime import datetime, timezone
from typing import Dict, Any, Tuple
from app.domain.entities.rollback import Rollback

class RollbackClient:
    async def rollback_deployment(self, deployment_id: str, reason: str, environment: str = "staging") -> Tuple[Rollback, int, Dict[str, Any]]:
        """Rollback deployment with different responses based on request parameters."""
        
        rollback_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)
        
        # Different statuses based on reason content and environment
        reason_lower = reason.lower()
        
        if "critical" in reason_lower or "urgent" in reason_lower or "security" in reason_lower:
            # Critical rollbacks have higher success rate
            status = random.choices(["SUCCESS", "FAILED"], weights=[90, 10])[0]
            http_status = 200 if status == "SUCCESS" else 500
        elif "test" in reason_lower or "demo" in reason_lower:
            # Test rollbacks always succeed
            status = "SUCCESS"
            http_status = 200
        elif "experimental" in reason_lower or "beta" in reason_lower:
            # Experimental rollbacks have higher failure rate
            status = random.choices(["SUCCESS", "FAILED", "IN_PROGRESS"], weights=[70, 25, 5])[0]
            if status == "IN_PROGRESS":
                http_status = 202  # Accepted - processing
            elif status == "FAILED":
                http_status = 500  # Internal Server Error
            else:
                http_status = 200  # Success
        else:
            # Default behavior - mostly successful
            status = random.choices(["SUCCESS", "FAILED"], weights=[80, 20])[0]
            http_status = 200 if status == "SUCCESS" else 500
        
        # Environment-specific behavior
        if environment == "production":
            # Production rollbacks are more critical and have higher success rate
            if status == "FAILED":
                status = random.choices(["SUCCESS", "IN_PROGRESS"], weights=[85, 15])[0]
                if status == "IN_PROGRESS":
                    http_status = 202
                else:
                    http_status = 200
        elif environment == "staging":
            # Staging rollbacks might be in progress
            if status == "FAILED":
                status = random.choices(["SUCCESS", "IN_PROGRESS"], weights=[75, 25])[0]
                if status == "IN_PROGRESS":
                    http_status = 202
                else:
                    http_status = 200
        
        # Enhanced reason with environment context
        enhanced_reason = f"{reason} (Environment: {environment}, Rollback ID: {rollback_id[:8]})"
        
        # Create rollback object
        rollback = Rollback(
            rollback_id=rollback_id,
            deployment_id=deployment_id,
            status=status,
            reason=enhanced_reason,
            environment=environment,
            timestamp=timestamp
        )
        
        # Create JSON response
        json_response = {
            "success": status in ["SUCCESS", "IN_PROGRESS"],
            "rollback": rollback.dict(),
            "message": self._get_rollback_message(status, deployment_id, environment),
            "metadata": {
                "rollback_id": rollback_id,
                "deployment_id": deployment_id,
                "timestamp": timestamp.isoformat(),
                "environment": environment,
                "reason_type": self._get_reason_type(reason)
            }
        }
        
        return rollback, http_status, json_response
    
    def _get_rollback_message(self, status: str, deployment_id: str, environment: str) -> str:
        """Generate appropriate message based on rollback status."""
        if status == "SUCCESS":
            return f"✅ Successfully rolled back deployment {deployment_id} in {environment}"
        elif status == "FAILED":
            return f"❌ Failed to rollback deployment {deployment_id} in {environment}. Check logs for details."
        elif status == "IN_PROGRESS":
            return f"⏳ Rollback of deployment {deployment_id} in {environment} is in progress..."
        else:
            return f"🔄 Rollback status for deployment {deployment_id} in {environment}: {status}"
    
    def _get_reason_type(self, reason: str) -> str:
        """Determine reason type based on content."""
        reason_lower = reason.lower()
        if "critical" in reason_lower or "urgent" in reason_lower or "security" in reason_lower:
            return "critical"
        elif "test" in reason_lower or "demo" in reason_lower:
            return "test"
        elif "experimental" in reason_lower or "beta" in reason_lower:
            return "experimental"
        else:
            return "standard"
    
    async def get_rollbacks(self) -> Tuple[list[Rollback], int, Dict[str, Any]]:
        """Get recent rollbacks with varied realistic data."""
        # More diverse rollback reasons
        reasons = [
            "Performance issues detected", "Critical bug found in production",
            "Security vulnerability discovered", "Test rollback for validation",
            "Urgent hotfix required", "Demo rollback for presentation",
            "Experimental feature causing issues", "Critical core service failure",
            "Database connection problems", "Memory leak in staging"
        ]
        environments = ["dev", "staging", "production"]
        
        rollbacks = []
        base_time = datetime.now(timezone.utc)
        
        for i in range(6):  # More rollbacks for better variety
            reason = reasons[i % len(reasons)]
            environment = environments[i % len(environments)]
            
            # Apply same logic as rollback_deployment for consistency
            reason_lower = reason.lower()
            
            if "critical" in reason_lower or "urgent" in reason_lower or "security" in reason_lower:
                status = random.choices(["SUCCESS", "FAILED"], weights=[90, 10])[0]
            elif "test" in reason_lower or "demo" in reason_lower:
                status = "SUCCESS"
            elif "experimental" in reason_lower or "beta" in reason_lower:
                status = random.choices(["SUCCESS", "FAILED", "IN_PROGRESS"], weights=[70, 25, 5])[0]
            else:
                status = random.choices(["SUCCESS", "FAILED"], weights=[80, 20])[0]
            
            # Environment-specific behavior
            if environment == "production":
                if status == "FAILED":
                    status = random.choices(["SUCCESS", "IN_PROGRESS"], weights=[85, 15])[0]
            elif environment == "staging":
                if status == "FAILED":
                    status = random.choices(["SUCCESS", "IN_PROGRESS"], weights=[75, 25])[0]
            
            # Add time variation (more recent rollbacks first)
            time_offset = i * 3  # 3 hours between rollbacks
            timestamp = base_time.replace(hour=(base_time.hour - time_offset) % 24)
            
            rollback_id = str(uuid.uuid4())
            enhanced_reason = f"{reason} (Environment: {environment}, Rollback ID: {rollback_id[:8]})"
            
            rollbacks.append(Rollback(
                rollback_id=rollback_id,
                deployment_id=str(uuid.uuid4()),
                status=status,
                reason=enhanced_reason,
                environment=environment,
                timestamp=timestamp
            ))
        
        # Sort by timestamp (most recent first)
        sorted_rollbacks = sorted(rollbacks, key=lambda x: x.timestamp, reverse=True)
        
        # Create JSON response
        json_response = {
            "success": True,
            "rollbacks": [rollback.dict() for rollback in sorted_rollbacks],
            "count": len(sorted_rollbacks),
            "message": f"Retrieved {len(sorted_rollbacks)} recent rollbacks",
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_rollbacks": len(sorted_rollbacks),
                "environments": list(set(rb.environment for rb in sorted_rollbacks)),
                "status_summary": {
                    "success": len([r for r in sorted_rollbacks if r.status == "SUCCESS"]),
                    "failed": len([r for r in sorted_rollbacks if r.status == "FAILED"]),
                    "in_progress": len([r for r in sorted_rollbacks if r.status == "IN_PROGRESS"])
                }
            }
        }
        
        return sorted_rollbacks, 200, json_response
