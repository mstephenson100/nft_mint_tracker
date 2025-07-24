#!/bin/bash

restart_script="/home/nft_mint_tracker/restart_mint_metadata.sh"

count=`pgrep -f mint_metadata.py | wc -l`
if [ $count -eq 0 ]
then
	echo "Restarting mint_metadata.py"
	${restart_script}
fi
