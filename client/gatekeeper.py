"""
Gatekeeper

Represents a node where authentication is needed to provide access. Something like an door 
lock controlled by RFID card. Gatekeeper is a client of MSYS that primarily relies on the 
server for making authentication decisions. However sometimes the server may be unavailable
and just like a friendly castle guard, will be able to remember people that have been seen before.

Gatekeeper will cache the results of the recent authentications.
"""

class Gatekeeper():
    """
    The Gatekeeper object is an interface to an MSYS server for authentication of IDs
    """
    
    def __init__(self, server_url):
        self.url = server_url


    def authenticate(self, rfid):
        """
        Authenticate an ID
        
        Returns True if the server allows access for the ID or if the server is unavailable,
        will return True if the cache indicates the ID had recent access
        """
        pass
