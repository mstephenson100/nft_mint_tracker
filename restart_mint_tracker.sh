#!/bin/bash

pkill -ef mint_tracker.py

echo
sleep 1

cd /home/nft_mint_tracker

screen -dmS mint_tracker -L -Logfile /home/nft_mint_tracker/logs/mint_tracker_screen.log /usr/bin/python3 /home/nft_mint_tracker/mint_tracker.py

echo "Restarted mint_tracker"

