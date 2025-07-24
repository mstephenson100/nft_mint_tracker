## nft_mint_tracker
### Overview
Nft_mint_tracker is a set of python scripts which watch confirmed transactions for every block on the Ethereum L1 block chain. It only watches transactions associated with erc721 and erc1155 smart contracts. When any new action is detected then data is written to a mysql database. When enough actions have occurred in a certain amount of time then a discord bot posts data to a discord channel. This is a very basic description of what this code actually does. I will provide more insight into each script that's part of this repo.

### Requirements
 - MySQL 8.0
 - Full ethereum node
 - IPFS gateway
 - Etherscan API key
 - Opensea API key

#### mint_tracker.py
mint_tracker.py checks every block in the ethereum full node for confirmed transactions. If the smart contract address was not previously identified based on a query to the MySQL database then it is checked to see if it supports either the erc721 or erc1155 interface. If the contract passes that check then it's marked as an NFT contract.

Each transaction from an erc721 or erc1155 contract is then checked to see if the mint write function was called. For each mint function called then the number of tokens minted in that transaction are counted and written to the database.

There is some additional checks to see if a to_addr matches a list of addresses which I called whale addresses but it's not the most useful unless you have addresses you want to watch.

#### mint_metadata.py
mint_metadata.py polls the database for erc721 and erc1155 contracts that are missing some data attributes that have not yet been identified. When a contract is found in the database missing any of the following attributes then this script attempts to find that missing data:

 - contract owner count
 - NFT metadata type (ipfs, hosted, arweave, onchain)
 - missing NFT metadata

##### contract owner count
Assuming the contract owner was identified in mint_tracker.py then mint_metadata.py then checks the database for other contracts that were also deployed by the same contract owner. If this number is large then we can consider this a red flag that the contract owner might be a scammer and that would be a warning to avoid this particular contract.

##### NFT metadata type
NFT metadata type is the format of the metadata returned by the tokenURI function. The most decentralized type of metadata is stored directly onchain. The more common type of metadata is hosted in IPFS or possibly also hosted by some other webserver. The NFT metadata type might be useful to people interested in minting from this contract.

##### missing NFT metadata
All erc721 or erc1155 contracts will have a function allowing anybody to read the metadata. This metadata is usually in JSON format and includes relevant data like a link to a sample of the artwork associated with each token id. I'm collecting a sample image for each smart contract here which is then shown to discord users to help them decide on if they want to mint or not.

#### mint_counter.py
mint_counter.py counts the number of mints written to the database for all contracts that had mints in n amount of time. If enough mints are identified in n amount of time then it writes to another database table to tell the discord bot to trigger an alert. 

If many mints are counted for a single contract in a very short amount of time then that indicates that a contract is trending and is very popular. 

If a new erc721 or erc1155 contract is found with a single mint then that also can have value to people who are looking for new NFT collections. 

mint_counter.py manages counting for all of these scenarios and triggers alerts based on configurable thresholds.

#### mintbot.py
mintbot.py is a discord bot that sends alerts to a discord channel based on the the previous 3 scripts reviewed above. It also allows users to send commands requesting data about contracts or contract owner addresses. Here is a brief list on the alerting that's currently configured:

 - New contract is found
 - First mint for a contract is found
 - Number of wallets holding NFT's from a contract increases passed an alert threshold
 - Number of mints from a contract increases passed an alert threshold

Mintbot also supports the following commands:
##### ~owner
Shows contracts deployed by this address
##### ~listing
Shows listing for this contract
##### ~metadata
Shows metadata for this contract
##### ~stats
Shows mint and holder stats for this contract
##### ~whatsminting
Shows other contracts that have mints in the last n blocks
