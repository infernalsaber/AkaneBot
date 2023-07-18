

# Akane Bot


<div align="center"> 

<img src="https://cdn.discordapp.com/attachments/980479966389096460/1130626054302744688/akanebotround.png" width="250" />

[![Python 3.10](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3100/)
 [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

An discord bot for animanga related search and feed functions

Written in Python 3.10 in the [hikari](https://github.com/hikari-py/hikari) microframework,
using [hikari-lightbulb](https://github.com/tandemdude/hikari-lightbulb) and [hikari-miru](https://github.com/HyperGH/hikari-miru) to extend functionality.

</div>

## Navigation

1. [Features](#features)  
1. [Add to your Server](#adding-the-bot)
1. [Running it Locally](#run-locally)  
1. [Credits](#credits)  


## Adding the bot

As of present, the bot is not public.  
Please contact `fenix.er` on Discord should you want to add it to your server.

## Features

* Search for animanga 
* Make cool comparitive charts 
* Find the source (sauce)
* Anime update feeds

More coming soon...


## Run Locally


### Prerequisites
Before you start, you'll need to have [Python](https://www.python.org/downloads/) and [create a Discord app](https://discord.com/developers/applications) with the proper permissions:
- `applications.commands`
- `bot` (with Send Messages enabled)


Configuring the app is covered in detail in the [getting started guide](https://discord.com/developers/docs/getting-started).

Note: Remember to enable the text messages intent to enable prefix commands

### Setup project

First clone the project:
```
$ git clone https://github.com/infernalsaber/AkaneBot.git
```

Open the directory and run
```
$ mv .example.env .env
```

Now put your Discord Bot Token and [SauceNAO Token](https://saucenao.com/) in the `.env` file

### Install dependencies

Do
```
pip install -r requirements.txt
```
To install the dependencies

If you're an active python developer, might want to create a [virtual environment first](https://www.freecodecamp.org/news/how-to-setup-virtual-environments-in-python/)


### Run the app

You're all set up now.

Run the following to get the bot running
```
python -OO bot.py
```


Note: If you're running off a VM running
```
nohup python -OO bot.py &
```
might be a better option since your bot wouldn't get killed when the terminal is closed


Btw:
i. replacing the owner id with your own would be a good idea
ii. the emotes will break on your instance, so do replace them with equivalent ones

<!-- ## Credits

**NOTE**: This bot bears no affiliation to Akane, the character from the Oshi no Ko series -->
