#!/bin/bash

pkill -ef mint_counter.py

echo
sleep 1

cd /home/nft_mint_tracker

screen -dmS mint_counter -L -Logfile /home/nft_mint_tracker/logs/mint_counter_screen.log /usr/bin/python3 /home/nft_mint_tracker/mint_counter.py

echo "Restarted mint_counter"

