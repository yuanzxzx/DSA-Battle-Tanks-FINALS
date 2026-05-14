import math
import pickle
import struct
from typing import Union, Dict, List, Tuple, Any, Optional

from battle_tanks.components.collision import Collision
from battle_tanks.sprites.player import Player

# Manage data serialization and deserialization for client-server communication
class Struct:
    
    # Establish byte boundaries and capacity limits for network synchronization
    SIZE_PLAYER: int = 13
    MAX_PLAYERS: int = 4
    BUFFER_SIZE_PLAYER: int = 100
    BUFFER_SIZE_EVENT_RESPONSE: int = 11
    BUFFER_SPLIT_MAP: int = 88
    BUFFER_SIZE_LVL_MAP: int = 40
    BUFFER_SIZE_INIT_PLAYER: int = 4
    BUFFER_SIZE_EVENT: int = 32  # Increased from 1 to handle multi-byte events (LASER_OFF_EVENT=5, damage packets=3)
    BUFFER_SIZE_NAME: int = 32
    
    # Pre-define connection status codes to streamline server responses
    OK_MESSAGE: bytes = b'\x01'
    JOIN_MESSAGE: bytes = b'\x02'
    USER_NOT_AVAILABLE: bytes = b'\x09'
    CLOSE_CONN: bytes = b'\x10'

    # Map directional actions to byte signatures to minimize payload footprint
    LEFT_EVENT_PLAYER: bytes = b'\x03'
    RIGHT_EVENT_PLAYER: bytes = b'\x04'
    UP_EVENT_PLAYER: bytes = b'\x05'
    DOWN_EVENT_PLAYER: bytes = b'\x06'
    SHOOT_EVENT_PLAYER: bytes = b'\x06'

    # Map turret rotation actions to bytes
    LEFT_ANGLE_EVENT_PLAYER: bytes = b'\x07'
    RIGHT_ANGLE_EVENT_PLAYER: bytes = b'\x08'

    # Map weapon-specific firing actions to bytes
    FIRE_EVENT_PLAYER: bytes = b'\x11'
    SHOTGUN_EVENT_PLAYER: bytes = b'\x12'

    # Toggle events for specific entity states
    LASER_ON_EVENT: bytes = b"L_ON"
    LASER_OFF_EVENT: bytes = b"L_OFF"

    # Define integers representing player states for state machines
    UPDATE_PLAYER: int = 1
    NEW_PLAYER: int = 2
    OLD_PLAYER: int = 3
    BROKE_BRICK: int = 4
    BRICK: int = 5
    BLOCK: int = 6
    PLAYER_SHOT: int = 7
    PLAYER_FIRED: int = 8
    PLAYER_SHOTGUN: int = 9

    # Aggregate valid status codes to validate network payloads
    STATUS_PLAYER: List[int] = [
        UPDATE_PLAYER, NEW_PLAYER, OLD_PLAYER, PLAYER_SHOT, PLAYER_FIRED, PLAYER_SHOTGUN
    ]

    # Aggregate valid movement commands to filter incoming data bytes
    MOVES: List[bytes] = [
        LEFT_EVENT_PLAYER, RIGHT_EVENT_PLAYER, UP_EVENT_PLAYER, DOWN_EVENT_PLAYER,
        LEFT_ANGLE_EVENT_PLAYER, RIGHT_ANGLE_EVENT_PLAYER
    ]

    # Decode a single byte into a usable python structure
    @staticmethod
    def unpack_single_data(data: bytes) -> Tuple[Any, ...]:
        return struct.unpack('B', data)

    # Encode generic single data items for minimal transmission
    @staticmethod
    def pack_single_data(data: int) -> bytes:
        return struct.pack('B', data)

    # Decode a 13-byte array into a player object, ignoring the size byte
    @staticmethod
    def unpack_player(data: bytes) -> Tuple[Any, ...]:
        return struct.unpack('BBhhhhbB', data[1:])

    # Handle rotational mutations based on specific input commands
    @staticmethod
    def _apply_rotation(player_data: Dict[str, Any], data: bytes) -> None:
        
        # Determine rotation path based on network command to align visual assets
        if data == Struct.RIGHT_EVENT_PLAYER:
            
            # Rotate both hull and turret together for consistent turning
            player_data["angle"] += Player.ANGLE * Player.ANGLE_RIGHT
            player_data["angle_cannon"] += Player.ANGLE * Player.ANGLE_RIGHT
            
        elif data == Struct.LEFT_EVENT_PLAYER:
            
            # Shift hull left and turret right to simulate counter-steer
            player_data["angle"] -= Player.ANGLE * Player.ANGLE_RIGHT
            player_data["angle_cannon"] += Player.ANGLE * Player.ANGLE_LEFT
            
        elif data == Struct.LEFT_ANGLE_EVENT_PLAYER:
            
            # Isolate turret rotation to allow aiming independently of movement
            player_data["angle_cannon"] += Player.ANGLE * Player.ANGLE_LEFT
            
        elif data == Struct.RIGHT_ANGLE_EVENT_PLAYER:
            
            # Pivot turret rightward independently
            player_data["angle_cannon"] += Player.ANGLE * Player.ANGLE_RIGHT

    # Handle velocity mutations and object collisions based on directional input
    @staticmethod
    def _apply_translation(player_data: Dict[str, Any], data: bytes) -> None:
        
        # Convert degrees to radians to compute trigonometric velocities
        radians: float = math.radians(player_data["angle"])
        
        # Calculate X velocity vector using sine to simulate tank forward momentum
        vlx: float = Player.SPEED * -math.sin(radians)
        
        # Calculate Y velocity vector using cosine to map vertical momentum
        vly: float = Player.SPEED * -math.cos(radians)

        # Apply vectors positively or negatively depending on forward/backward inputs
        if data == Struct.UP_EVENT_PLAYER:
            
            # Advance coordinates forward along the current vector
            player_data["y"] += vly
            player_data["x"] += vlx
            
        elif data == Struct.DOWN_EVENT_PLAYER:
            
            # Reverse coordinates backward against the vector
            player_data["y"] -= vly
            player_data["x"] -= vlx

        # Enforce boundary and object restrictions after calculating the new position
        Collision.collide_with_objects(player_data)

    # Conditionally mutate the player dictionary using command bytes
    @staticmethod
    def _apply_movement_logic(player_data: Dict[str, Any], data: bytes) -> None:
        
        # Evaluate movement command to route to the correct physics handler
        if data in [Struct.LEFT_EVENT_PLAYER, Struct.RIGHT_EVENT_PLAYER, Struct.LEFT_ANGLE_EVENT_PLAYER, Struct.RIGHT_ANGLE_EVENT_PLAYER]:
            Struct._apply_rotation(player_data, data)
            
        elif data in [Struct.UP_EVENT_PLAYER, Struct.DOWN_EVENT_PLAYER]:
            Struct._apply_translation(player_data, data)

    # Package all vital player properties into a standardized byte format for transmission
    @staticmethod
    def pack_player(data: Optional[bytes], player_data: Dict[str, Any], status: Optional[int] = None) -> bytes:
        
        # Validate and apply physics if a movement command is provided
        if data in Struct.MOVES:
            Struct._apply_movement_logic(player_data, data)

        # Normalize degree values to prevent overflow errors in rendering logic
        player_data["angle"] = player_data["angle"] % 360
        player_data["angle_cannon"] = player_data["angle_cannon"] % 360

        # Compile final byte string mapping properties to binary format
        return Struct.pack_single_data(Struct.SIZE_PLAYER) + struct.pack(
            'BBhhhhbB',
            status if status is not None else Struct.UPDATE_PLAYER,
            player_data["position"],
            int(player_data["x"]),
            int(player_data["y"]),
            int(player_data["angle"]),
            int(player_data["angle_cannon"]),
            int(player_data["damage_indicator"]),
            int(player_data.get("tank_color", 0))
        )

    # Decode mixed data streams into discrete player or event objects by inspecting header bytes
    @staticmethod
    def unpack_all_data(data: bytes) -> List[Tuple[Any, ...]]:
        index: int = 0
        step: int = 0
        data_wrapped: List[Tuple[Any, ...]] = []

        # Iterate over the byte stream to extract all encapsulated records
        while index < len(data):
            
            # Identify player data chunks via standard size header
            if data[index] == Struct.SIZE_PLAYER:
                
                # Shift step forward to slice the designated chunk size
                step += Struct.SIZE_PLAYER
                
                # Extract the chunk exactly matching the expected boundary
                if len(data[index:step]) == Struct.SIZE_PLAYER:
                    data_wrapped.append(Struct.unpack_player(data[index:step]))
                
                # Advance index to continue scanning stream
                index = step

            # Identify event data chunks via predefined response size
            elif data[index] == Struct.BUFFER_SIZE_EVENT_RESPONSE:
                
                # Shift step forward to slice the designated event size
                step += Struct.BUFFER_SIZE_EVENT_RESPONSE
                
                # Validate the chunk length prior to unpacking
                if len(data[index:step]) == Struct.BUFFER_SIZE_EVENT_RESPONSE:
                    data_wrapped.append(Struct.unpack_event(data[index:step]))

                # Advance index to process remaining stream
                index = step
                
            else:
                
                # Traverse sequentially to find the next valid header byte
                index += 1
                step += 1

        return data_wrapped

    # Extract all serialized player arrays from bulk data transmissions
    @staticmethod
    def unpack_players(data: bytes) -> List[Tuple[Any, ...]]:
        players: List[Tuple[Any, ...]] = []
        
        # Branch parsing strategy based on chunk size expectations
        if len(data) > Struct.BUFFER_SIZE_PLAYER:
            
            # Slice stream by interval to isolate each individual entity
            for i in range(0, len(data), Struct.BUFFER_SIZE_PLAYER):
                players.append(Struct.unpack_player(data[i + 1:i + Struct.BUFFER_SIZE_PLAYER]))
                
        else:
            
            # Fall back to single decode if stream contains only one entity
            if len(data) > 0:
                players.append(Struct.unpack_player(data))

        return players

    # Flatten multiple player dictionaries into a cohesive binary chunk
    @staticmethod
    def pack_players(data: Dict[int, Dict[str, Any]], status: Optional[int] = None) -> bytes:
        
        # Serialize each nested dict sequentially to build the final buffer
        return b"".join([Struct.pack_player(None, item, status) for _, item in data.items()])

    # Encode map elements into minimal byte representations to reduce map transfer sizes
    @staticmethod
    def pack_tile(data: Dict[str, Any]) -> bytes:
        
        # Concatenate headers and parameters into a strict sequence
        return Struct.pack_single_data(Struct.BUFFER_SIZE_EVENT_RESPONSE) + struct.pack(
            "bhhhh", data["type"], data["x"], data["y"], data["w"], data["h"]
        )

    # Fire bullet physics logic and encode the event payload simultaneously
    @staticmethod
    def pack_event(player_data: Dict[str, Any]) -> bytes:
        
        # Dispatch weapon mechanics inside physics system before serializing state
        Collision.add_bullet(player_data, 30)
        return Struct.pack_player(None, player_data, Struct.PLAYER_FIRED)

    # Decode event payload disregarding size headers
    @staticmethod
    def unpack_event(data: bytes) -> Tuple[Any, ...]:
        return struct.unpack('bhhhh', data[1:])

    # Process batch event arrays from continuous network streams
    @staticmethod
    def unpack_events(data: bytes) -> List[Tuple[Any, ...]]:
        events: List[Tuple[Any, ...]] = []

        # Choose extraction strategy depending on batch dimensions
        if len(data) > Struct.BUFFER_SIZE_EVENT_RESPONSE:
            
            # Step through memory block to gather multiple event footprints
            for i in range(0, len(data), Struct.BUFFER_SIZE_EVENT_RESPONSE):
                events.append(Struct.unpack_event(data[i:i + Struct.BUFFER_SIZE_EVENT_RESPONSE]))
                
        else:
            
            # Handle isolated event packets using direct extraction
            if len(data) > 0:
                events.append(Struct.unpack_event(data))

        return events

    # Provide generic serialization fallback for untyped arbitrary payloads
    @staticmethod
    def pack(data: Union[str, Dict[str, Any]]) -> bytes:
        try:
            
            # Leverage pickle for complex dictionary objects
            return pickle.dumps(data)
            
        except pickle.PicklingError:
            
            # Fallback to UTF-8 for string data types
            return data.encode('utf-8')

    # De-serialize mixed-format payloads returning pure python data
    @staticmethod
    def unpack(data: bytes) -> Any:
        try:
            
            # Treat payload as python object graph natively
            return pickle.loads(data)
            
        except pickle.UnpicklingError:
            
            # Revert to standard string extraction for text formats
            return data.decode('utf-8')
