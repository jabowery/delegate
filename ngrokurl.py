###
##
# Copyright (C) 2021 James A. Bowery
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see: <http://www.gnu.org/licenses/>.
##
###

# This is called by run_delegate_network to provide the app's public URL to forwardngrokcontrolappurl
import requests
import json
import sys
path = sys.argv[1] if len(sys.argv)>1 else ''
r = requests.get('http://localhost:4040/api/tunnels')
root =  json.loads(r.content)
print('{}/{}'.format(root['tunnels'][0]['public_url'],path))
