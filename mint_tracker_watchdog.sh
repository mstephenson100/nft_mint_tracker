#!/bin/bash

restart_script="/home/nft_mint_tracker/restart_mint_tracker.sh"

count=`pgrep -f mint_tracker.py | wc -l`
if [ $count -eq 0 ]
then
	echo "Restarting mint_tracker.py"
	${restart_script}
fi
