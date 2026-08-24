
from fastapi import APIRouter, WebSocket, WebSocketDisconnect # type: ignore

from app.services.websocket_manager import manager


router = APIRouter(
    tags=["WebSocket"]
)


# ============================================================
# USER WEBSOCKET CONNECTION
# ============================================================

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: int
):

    await manager.connect(
        user_id,
        websocket
    )

    try:

        while True:

            data = await websocket.receive_text()

            print(
                f"WebSocket message from user {user_id}:",
                data
            )

    except WebSocketDisconnect:

        manager.disconnect(
            user_id
        )

    except Exception as exc:

        print(
            "WebSocket error:",
            repr(exc)
        )

        manager.disconnect(
            user_id
        )
