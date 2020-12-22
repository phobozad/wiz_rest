import asyncio
import concurrent

import bottle
import pywizlight as wiz
import netaddr

# Hue API Error Types
#const ERROR_TYPES = {
#  1: 'unauthorized user',
#  2: 'body contains invalid JSON',
#  3: 'resource not found',
#  4: 'method not available for resource',
#  5: 'missing paramters in body',
#  6: 'parameter not available',
#  7: 'invalid value for parameter',
#  8: 'parameter not modifiable',
#  11: 'too many items in list',
#  12: 'portal connection is required',
#  901: 'bridge internal error',
#}

class App:
    def __init__(self, domain_name=None):
        
        self.domain_name = domain_name

        self.Server = bottle.Bottle()
        self._setup_routes()

    def _setup_routes(self):
        route_map = [
                {"method": "GET", "path": "/", "handler": self._index_page},
                {"method": "POST", "path": "/api/lights/<light_id>/state", "handler": self._state_command_handler}
        ]

        for route in route_map:
            self.Server.route(route['path'], method=route['method'], callback=route['handler'])

    def _index_page(self):
        return("Hi :) \n Wiz Light API")

    def _generate_dns_fqdn(self, shortname: str):
        if self.domain_name is None:
            return shortname
        else:
            return f"{shortname}.{self.domain_name}"

    def _generate_light_connectionstring(self, light_id: str):
        # Handle FQDN vs shortname vs IP address, etc for light ID
        # and map to a string that can be passed to pywizlight for connection setup

        # Check if this is an IP address
        if netaddr.valid_ipv4(light_id) or netaddr.valid_ipv6(light_id):
            # Valid IP can be directly used - return as-is
            return light_id

        # TODO: add check if its a numeric ID or something that the Wiz App uses

        if light_id.endswith(f".{self.domain_name}"):
            # FQDN is in the light string - return as-is
            return light_id

        # Finally, assume its a DNS shortname and generate an FQDN (assuming domain was provided)
        return self._generate_dns_fqdn(light_id)


    def _state_command_handler(self, light_id: str):

        # Parse input
        data = bottle.request.json

        if data is None:
            bottle.response.status = 400
            bottle.response.content_type = "application/json"
            return "{'error': 'Invalid JSON Payload'}\n"


        bulb_changes = {}

        try:
            # If we got a light state, handle that
            if "on" in data:
                # Make sure data is valid boolean value
                if data['on'] == True or data['on'] == False:
                    bulb_changes['on'] = data['on']
                else:
                    raise KeyError


        except KeyError:
            bottle.response.status = 400
            bottle.response.content_type = "application/json"
            return "{'error': 'Missing key fields in request'}\n"


        response_dict = {}
        response_dict['success'] = {}

        # Execute changes if there were any provided
        if bulb_changes:

            # Setup light object
            light = wiz.wizlight(self._generate_light_connectionstring(light_id))

            if "on" in bulb_changes:
                try:
                    if bulb_changes['on']:
                        asyncio.run(asyncio.wait_for(light.turn_on(), timeout=5))
                    else:
                        asyncio.run(asyncio.wait_for(light.turn_off(), timeout=5))

                    asyncio.run(asyncio.wait_for(light.updateState(), timeout=5))
                    response_dict['success'][f'/lights/{light_id}/state/on'] = light.state.get_state()

                except concurrent.futures._base.TimeoutError:
                    # Light commands timed out
                    bottle.response.status = 503
                    bottle.response.content_type = "application/json"
                    return "{'error': 'Timeout while attempting to communicate with light.'}\n"



        else:
            # No bulb changes - tell the user they're a dumb dumb
            bottle.response.status = 400
            bottle.response.content_type = "application/json"
            return "{'error': 'No state changes provided'}\n"

        # Include current state in response?
        bottle.response.status = 200
        return response_dict
