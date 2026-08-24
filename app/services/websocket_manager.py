
from fastapi import WebSocket # type: ignore


class ConnectionManager:

    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(
        self,
        user_id: int,
        websocket: WebSocket
    ):
        await websocket.accept()

        self.active_connections[user_id] = websocket

        print(
            f"WebSocket connected for user {user_id}"
        )

    def disconnect(
        self,
        user_id: int
    ):
        self.active_connections.pop(
            user_id,
            None
        )

        print(
            f"WebSocket disconnected for user {user_id}"
        )

    async def send_to_user(
        self,
        user_id: int,
        message: dict
    ):
        websocket = self.active_connections.get(
            user_id
        )

        if websocket:

            try:

                await websocket.send_json(
                    message
                )

            except Exception as exc:

                print(
                    "WebSocket send error:",
                    repr(exc)
                )

                self.disconnect(user_id)


manager = ConnectionManager()

