"""Server TCP connection"""
import socket
import struct
from typing import Tuple, List, Union
from battle_tanks.commons.package import Struct

from queue import SimpleQueue

class NetworkComponent:
    """ Client TCP connection """

    SEND_Q = SimpleQueue() # Queue to send events from client to server
    UPDATE_Q = SimpleQueue() # Queue to update events from server to client

    def __init__(self, addr: Tuple[str, int], name: str = "John", tank_color: int = 0): # Initialize the network component
        print(f"Connecting to {addr}, Player: {name}") # Print the address and name
        self.name = name # Name of the player
        self.addr = addr # Address of the server
        self.tank_color = tank_color # Color of the tank
        self.lvl_map: str = "" # Level map

        self._socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Create a socket
        self._socket_tcp.connect(addr) # Connect to the server
        self._socket_tcp.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1) # Set socket options

        self.game_state: bytes = b"" # Game state
        self._player_data: Union[dict, bytes] = self.load_data() # Load player data


    def load_data(self) -> Union[dict, bytes]: # Load player data
        """ Load player data INIT """
        ok = self._socket_tcp.recv(Struct.BUFFER_SIZE_EVENT) # Receive player data
        if ok == Struct.OK_MESSAGE: # Check if the player data is OK
            name_data = self.name.encode('utf-8') # Encode the player name
            if len(name_data) < Struct.BUFFER_SIZE_NAME: # Check if the player name is less than the buffer size
                name_data = name_data + b'\x00' * (Struct.BUFFER_SIZE_NAME - len(name_data))
            else: # Otherwise
                name_data = name_data[:Struct.BUFFER_SIZE_NAME]
            
            color_data = struct.pack('B', int(self.tank_color)) # Pack the tank color
            self._socket_tcp.send(name_data + color_data) # Send the player name and tank color
            lvl_map = self._socket_tcp.recv(Struct.BUFFER_SIZE_LVL_MAP) # Receive the level map
            if lvl_map == Struct.USER_NOT_AVAILABLE: # Check if the user is not available
                return Struct.USER_NOT_AVAILABLE

            self.lvl_map = Struct.unpack(lvl_map) # Unpack the level map

            data = self._socket_tcp.recv(Struct.SIZE_PLAYER) # Receive the player data
            data_player = Struct.unpack_player(data) # Unpack the player data
            size_map = Struct.unpack_single_data(self._socket_tcp.recv(Struct.BUFFER_SIZE_EVENT)) # Unpack the map size

            for i in range(size_map[0]): # Loop through the map size
                split_map = self._socket_tcp.recv(Struct.BUFFER_SPLIT_MAP) # Receive the map split
                self.game_state += split_map # Add the map split to the game state

            return {
                "position": data_player[1], # Position of the player
                "x": data_player[2], # X coordinate of the player
                "y": data_player[3], # Y coordinate of the player
                "angle": data_player[4], # Angle of the player
                "angle_cannon": data_player[5], # Angle of the cannon
                "tank_color": data_player[7] if len(data_player) > 7 else 0 # Color of the tank
            }

    @staticmethod
    def _modify_data(data_arr: list) -> dict: # Modify player and events data
        """ MODIFY PLAYER AND EVENTS """
        if data_arr[0] in Struct.STATUS_PLAYER: # Check if the data is player data
            return {
                "status": data_arr[0], # Status of the player
                "position": data_arr[1], # Position of the player
                "x": data_arr[2], # X coordinate of the player
                "y": data_arr[3], # Y coordinate of the player
                "angle": data_arr[4], # Angle of the player
                "angle_cannon": data_arr[5], # Angle of the cannon
                "damage_indicator": data_arr[6], # Damage indicator of the player
                "tank_color": data_arr[7] if len(data_arr) > 7 else 0 # Color of the tank
            }

        elif data_arr[0] == Struct.BROKE_BRICK: # Check if the data is a broken brick
            return { # Return the broken brick data
                "status": data_arr[0], # Status of the brick
                "x": data_arr[1], # X coordinate of the brick
                "y": data_arr[2], # Y coordinate of the brick
                "w": data_arr[3], # Width of the brick
                "h": data_arr[4], # Height of the brick
            }


    def recv_move_player(self) -> List[dict]:
        """ get data player and states game"""
        try:
            data = self._socket_tcp.recv(120)
            if data == b'': # Check if the data is empty
                import time
                time.sleep(0.1) # Wait for 0.1 seconds
                return [] # Return an empty list
            data_set = Struct.unpack_all_data(data) # Unpack the data
            return list(map(NetworkComponent._modify_data, data_set)) # Map the data to the modified data
        except BlockingIOError as e: # BlockingIOError as e
            # print(f"BLOCKING AS: {e}")
            pass
        except socket.error as e: # Socket error
            import time
            time.sleep(0.1) # Wait for 0.1 seconds
            pass

        return []

    def send_move_tcp(self, move: bytes): # Send move to server
        try:
            self._socket_tcp.send(move) # Send the move to the server
        except socket.error as e: # Socket error
            self._socket_tcp.close() # Close the socket

    @property
    def player_data(self) -> Union[dict, bytes]: # Get player data
        """ get number of player """
        return self._player_data

    @property
    def player_number(self) -> int: # Get player number
        """ get number of player """
        if self._player_data == Struct.USER_NOT_AVAILABLE: # Check if the player data is not available
            return 0

        return self._player_data["position"] # Get player position


    @property
    def socket_tcp(self) -> socket.socket: # Get socket tcp
        return self._socket_tcp


    @staticmethod
    def check_name(addr: tuple, name: str) -> Union[bool, socket.error]: # Check name
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Create socket
            sock.settimeout(0.1) # Set timeout
            sock.connect(addr) # Connect to server

            if sock.recv(Struct.BUFFER_SIZE_EVENT) == Struct.OK_MESSAGE: # Check if the data is OK
                check_name = (name + "-c").encode('utf-8') # Encode the player name
                if len(check_name) < Struct.BUFFER_SIZE_NAME: # Check if the player name is less than the buffer size
                    check_name = check_name + b'\x00' * (Struct.BUFFER_SIZE_NAME - len(check_name))
                else: # Otherwise
                    check_name = check_name[:Struct.BUFFER_SIZE_NAME]
                check_name = check_name + struct.pack('B', 0) # Pack the player name
                sock.send(check_name) # Send the player name
                res = sock.recv(1) == Struct.OK_MESSAGE # Check if the data is OK
                try:
                    sock.close()
                except Exception: # Exception
                    pass
                return res

        except socket.error as e: # Socket error
            return e

        return False


    def get_events_to_game_state(self):
        """
        Extracts and returns the events from the current game state.

        This method uses the Struct class to unpack events from the 
        game_state attribute of the instance.

        Returns:
            list: A list of events extracted from the game state.
        """
        return Struct.unpack_events(self.game_state)

    @classmethod
    def send_keys(cls, keys: List[bytes]) -> None: # Send keys
        for action in keys: # Loop through the keys
            cls.SEND_Q.put(action) # Put the keys in the queue

    @classmethod
    def recv_to_queue(cls) -> bytes: # Receive to queue
        data = []
        while cls.UPDATE_Q.empty() is False: # Check if the queue is not empty
            data.extend(cls.UPDATE_Q.get()) # Add the data to the queue
    
        return data