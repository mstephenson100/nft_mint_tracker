#!/bin/bash

restart_script="/home/nft_mint_tracker/restart_mint_counter.sh"

count=`pgrep -f mint_counter.py | wc -l`
if [ $count -eq 0 ]
then
	echo "Restarting mint_counter.py"
	${restart_script}
fi
