# The Delegate Network

## Overview

The delegate network is a completely transparent, easy-to-use and understand version of what is sometimes called [liquid democracy](https://en.wikipedia.org/wiki/Liquid_democracy).

Imagine a phone number answered by an instance of the Delegate Network.  You, as a registered voter, call that number.  Say "John Doe of Centerville" and hang up.  Later, the registered voter, John Doe of Centerville calls the Delegate Network and votes on bills before the US House of Representatives, but his count as _TWO_ votes:  His and yours.  He's your "delegate".  More people delegate to him.  His power grows.  But John Doe of Centerville is only human.  You call the Delegate Network and say "audit".  The Delegate Network reports how your voting power has been used on a bill you deeply care about.  Power corrupted him.  You say "recall".  Instantly, he wields one less vote against people like you.  You know others that trust him.  You call to warn them.  Even after discussions, some disagree with your opinion.  Others agree.  He loses more power.  Since the Delegate Network is publicly auditable at all times, news of his betrayal spreads to most everyone that trusted him.  All have an incentive to communicate in more depth than a Facebook post or Tweet.  Power hierarchies evolve toward greater trust. 

Now, imagine a candidate campaigns for a seat in the US House of Representatives with one promise:

"I will vote the way the delegate network for my Congressional district tells me to vote and refer all political negotiations to them."

Voter authentication is based on:

1. [FCC-mandated SHAKEN/STIR](https://www.fcc.gov/call-authentication) authentication of caller IDs that has been in effect since June of 2021.
2. Phone numbers appearing in the Secretary of State voter registration records.

Another feature is "delegate money":  a [demurrage currency](https://en.wikipedia.org/wiki/Demurrage_(currency)) system to incentivise participation.  Philosophically speaking, politics and money are the two primary abstractions of government's monopoly on force.  Reforming politics alone is impractical.  To quote the founder of the Rothschild banking dynasty:  "Give me control of a nation’s money supply, and I care not who makes its laws." While there have been, will continue to be, ideas held as passionately as they are divergent about how to wrangle the abstraction of force called "fiat money", the delegate money system is a pragmatic degeneration -- targeting political command and control hierarchies -- of what the author has called "[property money](https://jimbowery.blogspot.com/2020/01/property-money.html)".  In the general form of "property money", fiat money is backed by the value of enforced property rights in what might be called "civilization as a service" -- a service provided by "[those who place their flesh, blood and bone between chaos and civilization](https://youtu.be/pobG397KwDw)".  They are called "Soverigns" in the terminology of "property money".  In the interim, delegate money pragmatically degenerates property money as follows: 

1. Treat those who verify their phone numbers in their voter registrations with their Secretary of State, and who then use those phone numbers to participate in the delegate network, as though they were placing their flesh, blood and bone between chaos and civilization.  They are the recipients of demurrage fees, equally apportioned among them.
2. The money supply is based on an estimate of the property value required to support all governmental personnel.
3. The initial money supply is "minted" so as to make the delegate network go viral:  incentivise early participation thereby creating a critical mass of participants to reach [network effect](https://en.wikipedia.org/wiki/Network_effect) tipping point.

## Installation

1. Obtain a [Telnyx phone number](https://portal.telnyx.com/#/app/numbers/my-numbers) with a [call control app id](https://portal.telnyx.com/#/app/call-control/applications).
2. In this directory create a file named .env for environment variables, with a development environment exemplified in README.resources/home/delegate/.env

	```
	DEBUG_LEVEL = 1
	TELNYX_PUBLIC_KEY=
	TELNYX_API_KEY=
	TELNYX_APP_CONNECTION_ID=
	```
	Note: The TELNYX_APP_CONNECTION_ID is the same as what is sometimes called TELNYX_CALL_CONTROL_APP_ID
	
	To make use of the anonymized test dataset in this repository, set these environment variables:
	```
	STATE_OR_PROVINCE = 'iowa'
	```
	For authentication of call-ins by sovereigns (unrestricted ability to mint Delegate money), specify their caller IDs:
	```
	SOVEREIGN_PHONES = ['712-123-9876','712-125-7890']
	```
	
	Provide a path for the publicly accessible audit log.  In this example a symbolic link has been created to a website directory:
	```
	AUDIT_LOG=public_html/audit_log.txt
	```
	
	Estimate the delegate money supply (ms) and then solve for x where ms = x*(x+1)/2.
	That solution is: x = (sqrt(8*ms+1)+1)/2
	Define NUMBER_OF_ACTIVATIONS_TO_REWARD to be x.  In the case of Iowa, x turns out to be about 2^16 or 65536.
	```
	NUMBER_OF_ACTIVATIONS_TO_REWARD=65536
	```

	The `redis` installation instructions below require the definition of a unix socket:
	```
	REDIS_SOCKET=/var/run/redis-delegate-private/redis-server.sock
	```
	
	To run a development environment and production environment on the same `redis` server, the database numbers must not overlap.
	Therefore, one of the environments must set these environment variables to not conflict with the default (0,1,2,3):
	```
	REDIS_TRANSACTIONS_DB=4
	REDIS_SESSIONS_DB=5
	REDIS_VOTERS_DB=6
	REDIS_PROPERTIES_DB=7
	```

3. [Install ngrok](https://ngrok.com/) so that it is executable from this directory.
4. [Install redis](https://redis.io/) with example configurations in these files:
	```
	README.resources/lib/systemd/system/redis-server@.service	# systemd template (unmodified location and contents from the Ubuntu 20.04 distribution) 
	README.resources/etc/systemd/system/redis-server@.service.d/override.conf # installation override of the systemd template
	README.resources/etc/redis/create-delegate-public.conf.sh	# script to generate the public-facing redis server's configuration
	README.resources/etc/redis/bak/redis.conf			# source configuration for configuration generation edited from original /etc/redis/redis.conf according to the "suggested modification for" below
	README.resources/etc/redis/create-delegate-private.conf.sh	# script to generate the private redis server's configuration
	README.resources/etc/redis/redis-delegate-private.conf.patch	# patch required by create-delegate-private.conf.sh
	README.resources/etc/redis/redis-delegate-public.conf.patch	# patch required by create-delegate-public.conf.sh
	```
	The following instructions work under a clean install of Ubuntu 20.04LTS, but may damage other systems:
	
	Disable the existing `redis` server instance:
	```
	systemctl stop redis-server
	systemctl disable redis-server
	```
	Copy the template override:
	```
	cp -r README.resources/etc/systemd/system/redis-server@.service.d /etc/systemd/system
	```
	Delete the existing `/etc/redis` directory:
	```
	rm -r /etc/redis
	```
	Copy the `README.resources/etc/redis` directory files to `/etc/redis`:
	```
	cp -r README.resources/etc/redis /etc
	```
	Generate the redis configuration files (which also enables and starts their corresponding server instances):
	```
	cd /etc/redis
	./create-delegate-transactions.conf.sh
	./create-delegate-private.conf.sh
	```
	At this point, the two `redis` server instances should be running and should start on reboot as well.

	
	For those not using these configuration generation scripts, here is the suggested modification for the default redis configuration under Linux, reflected in the above configuration generation shell scripts:
	```
	# Please check http://redis.io/topics/persistence for more information.

	appendonly yes

	# The name of the append only file (default: "appendonly.aof")

	appendfilename "appendonly.aof"

	# The fsync() call tells the Operating System to actually write data on disk
	# instead of waiting for more data in the output buffer. Some OS will really flush
	# data on disk, some other OS will just try to do it ASAP.
	#
	# Redis supports three different modes:
	#
	# no: don't fsync, just let the OS flush the data when it wants. Faster.
	# always: fsync after every write to the append only log. Slow, Safest.
	# everysec: fsync only one time every second. Compromise.
	#
	# The default is "everysec", as that's usually the right compromise between
	# speed and data safety. It's up to you to understand if you can relax this to
	# "no" that will let the operating system flush the output buffer when
	# it wants, for better performances (but if you can live with the idea of
	# some data loss consider the default persistence mode that's snapshotting),
	# or on the contrary, use "always" that's very slow but a bit safer than
	# everysec.
	#
	# More details please check the following article:
	# http://antirez.com/post/redis-persistence-demystified.html
	#
	# If unsure, use "everysec".

	appendfsync always
	#appendfsync everysec
	# appendfsync no
	```
5. [Install pipenv](https://pipenv.pypa.io/en/latest/).
6. While in this directory, execute the command:
	```
	pipenv --python 3.9
	pipenv shell
	pip install -r requirements.txt
	```
7. While in this directory, execute the command:
	```
	./run_delegate_network
	```

## Roadmap

1. Web interface:
	1. Public download an audit snapshot of the current database.
	1. Current delegate network tally of votes on those bills.
		1. Lower priority: Queries to identify top influencers on specific bills.
1. Call-back authentication in lieu of SHAKEN/STIR APIs.
1. Re-factor to abstract jurisdiction-specific parameters and put them in the .env configuration.
	1. This may involve creating a modularized extension API inheriting from an Abstract Base Class.
1. Regression testing framework.
	1. A set of MP3s to stimulate the transcription service, with expected results based on the anonymized voters sample data provided with the repository.
1. Document lobotomized redis with invocation: runuser -g redis -u redis redis-server redis-delegate-public.conf
1. Authentication using SHAKEN/STIR attestation.
	1. This may entail getting off the Telynx platform, which would raise the priority of abstracting out the telecom service provider API.
1. Better-abstraction of the telecom service provider API.
	1. Again, a modularized extension API inheriting from ABC is probably necessary.
1. Replace all those print statements with a logger and read any non-default level from .env.
1. SIP level processing of speech packets for real-time custom transcription.
	1. Improve accuracy (telnyx transcripts must be converted back to phonemes for the delegate network's approximate proper name matching).
	1. Decreased costs (telnyx charges $0.05/minute of connect time to the delegate network systems).
1. Flesh out the "Property Money" implementation.
	1. Allow people to opt-in to receive text notifications when they receive property money.
	1. Get the phone numbers (caller IDs) of all sovereigns in the Congressional district.
	1. Locate those sovereigns in the voters registrations and update the associated tentative data in redis to contain those phone numbers.
	1. In the interim (before incorporation of property taxes), a web interface suffices for property owners to register their properties in delegate money.
		1. Prioritize counties where sovereigns have an existing program to give toys to impoverished children.
		1. Contact businesses that have excess inventory they are willing to sell for play money heading toward Christmas.
		1. Ensure their phone numbers are registered as are the phone numbers of the sovereigns.
		1. Provide businesses and sovereigns with The Delegate Networks phone number and instructions.
		1. Provide a web interface at delegate.network for businesses and property owners to register the amount of Delegate Money they're willing to accept and for what in exchange.
			1. The implementation should model the ultimate implementation's reliance on declaration of property value assessing demurrage charges.
		1. This registration puts their account in the red while dividing the corresponding amount in equal transfers to the sovereigns.
		1. Sovereigns, Business and property owners receive a text message informing them ($,from whom) they receive money.
	1. This ultimately (incorporating property taxes) requires a county-assessors data-importation extension API for property databases.
		1. Include in the repository sample data from county assessors.  Currently included are:
			1. Page County, Iowa
			1. Polk County, Iowa
		1. Escrowed bids for each property.
		1. Assessment of demurrage charged to the owner based on the high bid.
		1. Assessment of demurrage charged to the owner of property money _except_ for high bids in escrow.

