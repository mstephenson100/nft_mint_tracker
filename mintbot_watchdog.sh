#!/bin/bash

restart_script="/home/nft_mint_tracker/restart_mintbot.sh"

count=`pgrep -f mintbot.py | wc -l`
if [ $count -eq 0 ]
then
	echo "Restarting mintbot.py"
	${restart_script}
fi
