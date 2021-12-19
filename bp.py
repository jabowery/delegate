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

# Usage:
# import bp
# bp.bp()
#
# This is useful for debugging ngrok/flask apps
# It enables breakpoints _only_ on the first thread/task to execute it.
# The file it creates must be deleted by the startup script.

import logging
def bp():
    with open('nowdebugging','w') as f:
        print(' ',file=f)
    breakpoint()

