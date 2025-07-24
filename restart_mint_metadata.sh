#!/bin/bash

pkill -ef mint_metadata.py

echo
sleep 1

cd /home/nft_mint_tracker

screen -dmS mint_metadata -L -Logfile /home/nft_mint_tracker/logs/mint_metadata_screen.log /usr/bin/python3 /home/nft_mint_tracker/mint_metadata.py

echo "Restarted mint_metadata"

