""" Commons """
import os.path
import sys

def resolve_route(rute,relative = '.'): # Resolve the route of a file
    """resolve_route"""
    if hasattr(sys,'_MEIPASS'): # Check if the file is a compiled executable
        return os.path.join(sys._MEIPASS,rute) # Return the route of the file
    return os.path.join(os.path.abspath(relative),rute) # Return the route of the file

ROUTE = lambda route: os.path.join(os.path.abspath("."), route) # Set the route of the file
