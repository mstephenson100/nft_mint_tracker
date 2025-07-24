#!/bin/bash

pkill -ef mintbot.py

echo
sleep 1

cd /home/nft_mint_tracker

screen -dmS mintbot -L -Logfile /home/nft_mint_tracker/logs/mintbot_screen.log /usr/bin/python3 /home/tracker/nft_mint_tracker/mintbot/mintbot.py

echo "Restarted mintbot"

