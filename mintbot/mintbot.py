#!/usr/bin/python3

import sys
import os
import os.path
import configparser
import discord
import asyncio
import logging
import requests
import traceback
import time
import validators
from datetime import datetime
from decimal import Decimal

sys.path.insert(0,'/home/nft_mint_tracker/mintbot')
import reporting.db as mintbot_db

global session
session = requests.session()

intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.members = True

logging.basicConfig(level=logging.WARNING)

class MyDiscordClient(discord.Client):

    urls = {
        "etherscan_address": "https://etherscan.io/address/",
        "etherscan_txn": "https://etherscan.io/tx/"
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bg_task = self.loop.create_task(self.main_loop())
        self.bg_task = self.loop.create_task(self.background_tasks())

    async def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('--- MINTBOT ENGAGED ---')

        members = await self.guilds[0].fetch_members().flatten()
        for member in members:
            if len(member.roles) == 1:
                continue
            for role in member.roles:
                if role.name.lower() == "group_one":
                    vip_members.append(member.id)
                if role.name.lower() == "group_two":
                    if not member.id in vip_members:
                        vip_members.append(member.id)

    async def main_loop(self):
        await self.wait_until_ready()
        while True:
            try:

                await self.check_for_first_mints()
                await asyncio.sleep(1)

                await self.check_for_mint_increase()
                await asyncio.sleep(1)

                await self.check_for_wallet_increase()
                await asyncio.sleep(1)

                await self.check_for_new_contracts()
                await asyncio.sleep(1)

                await self.check_for_mint_trending()
                await asyncio.sleep(1)

            except:
                print(traceback.format_exc())


    async def background_tasks(self):
        await self.wait_until_ready()
        while True:
            try:
                await asyncio.sleep(180)

                await self.repopulate_vip_members()
                await asyncio.sleep(2)

            except:
                print(traceback.format_exc())



    async def check_for_first_mints(self):
        mints = mintbot_db.getFirstMint()
        if len(mints) == 0 or mints is None:
            return

        print(mints)

        for mint in mints:

            await self.send_first_mint_to_channel(mint)
            mintbot_db.stopFirstMint(mint['contract_address'])


    async def check_for_mint_increase(self):
        mints = mintbot_db.getMintIncrease()

        if len(mints) == 0 or mints is None:
            return

        print(mints)
        for mint in mints:

            await self.send_mint_increase_to_channel(mint)
            mintbot_db.stopMintAlert(mint['contract_address'])


    async def check_for_wallet_increase(self):
        mints = mintbot_db.getWalletsIncrease()

        if len(mints) == 0 or mints is None:
            return

        print(mints)
        for mint in mints:

            await self.send_wallet_increase_to_channel(mint)
            mintbot_db.stopWalletAlert(mint['contract_address'])


    async def check_for_mint_trending(self):
        mints = mintbot_db.getMintTrending()
        contracts = []

        if len(mints) == 0 or mints is None:
            return

        print(mints)
        for mint in mints:

            if mint['contract_address'] not in contracts:

                await self.send_mint_trending_to_channel(mint)
                mintbot_db.stopMintTrending(mint['contract_address'])
                contracts.append(mint['contract_address'])


    async def check_for_wallet_trending(self):
        mints = mintbot_db.getWalletTrending()
        contracts = []

        if len(mints) == 0 or mints is None:
            return
    
        print(mints)
        for mint in mints:

            if mint['contract_address'] not in contracts:

                await self.send_wallet_trending_to_channel(mint)
                mintbot_db.stopWalletTrending(mint['contract_address'])
                contracts.append(mint['contract_address'])


    async def check_for_new_contracts(self):

        new_contracts = mintbot_db.getContractsToAnnounce()
        if not new_contracts:
            return None

        for contract in new_contracts:

            print(datetime.now().strftime("%d/%m/%Y %H:%M:%S") + ": New NFT contract found" + str(contract))

            if contract['baseuri'] is None:
                contract['baseuri'] = "NULL"

            if contract['owner_address'] == "NULL":
                owner = ":white_small_square: Owner: Not Found \n"
            else:
                owner = ":white_small_square: Owner: <" + self.urls['etherscan_address'] + contract['owner_address'] + ">\n"

            name = contract['contract_name']
            address = ":white_small_square: Address: <" + self.urls['etherscan_address'] + contract['contract_address'] + ">\n"
            baseuri = ":white_small_square: Baseuri: <" + contract['baseuri'] + ">\n"
            opensea = ":white_small_square: Opensea: <" + 'https://opensea.io/assets?search[query]=' + contract['contract_address'] + ">\n"
            header = ":sparkles: New NFT Contract: **" + name + "**\n"

            if contract['baseuri'] == "NULL":
                send_text = (header + address + owner + opensea + "\n")
            else:
                send_text = (header + address + owner + opensea + baseuri + "\n")

            channel = self.get_channel(self.nft_contracts_channel)
            await self.send_contract_to_channel(channel, send_text)
            mintbot_db.markAnnouncementDone(contract['contract_address'])


    async def command_owner(self, message, contract_address):

        special_characters = '!@#$%^&*()+?=,<>/"'
        if any(c in special_characters for c in contract_address):
            await message.channel.send('owner supports only alphanumeric characters')
            return

        owner_address, owner_results = mintbot_db.getOwner(contract_address)
        print(len(owner_results))
        
        if (owner_address is None) or (owner_results is None):
            send_text = "Owner not found\n"

        else:

            if len(owner_results) > 0:
                print("owner_results length: %s" % len(owner_results))
                send_text = "**" + contract_address + " owner address:**\n" + "<" + self.urls['etherscan_address'] +  owner_address + ">\nHas also deployed:\n"
                for contract in owner_results:
                    average_price = Decimal(contract['average_price']).normalize()
                    send_text = send_text + str(contract['date']) + " **" + contract['contract_name'] + "** " + "<" + self.urls['etherscan_address'] + contract['contract_address'] + "> **Mints**:" + str(contract['current_mint']) + " **Wallets**: " + str(contract['current_wallets']) + " **Price**: " + str(average_price) + "\n"
            else:
                send_text = "Owner not found" + "\n"

        await message.channel.send(send_text[:2000])


    async def command_stats(self, message, contract_address):

        special_characters = '!@#$%^&*()+?=,<>/"'
        if any(c in special_characters for c in contract_address):
            await message.channel.send('stat supports only alphanumeric characters')
            return

        stats = mintbot_db.getStats(contract_address)
        print(len(stats))
        if stats is None:
            send_text = "Nothing found"
        else:
            if stats['metadata_type'] == "arweave":
                metadata_emoji = ":dna:"
            elif stats['metadata_type'] == "base64":
                metadata_emoji = ":chains:"
            elif stats['metadata_type'] == "ipfs":
                metadata_emoji = ":ringed_planet:"
            elif stats['metadata_type'] == "hosted":
                metadata_emoji = ":ghost:"
            elif stats['metadata_type'] == "utf8":
                metadata_emoji = ":8ball:"
            else:
                metadata_emoji = ":skull_crossbones:"

            if stats['verified'] is False:
                verified = " | <:BYTECODE:834146570298589194> Unverified"
            else:
                verified = ""

            current_mint = stats['current_mint']
            current_wallets = stats['current_wallets']
            mints_per_wallet = str(round((current_mint / current_wallets)))

            average_price = Decimal(stats['average_price']).normalize()
            send_text = "**" + stats['contract_name'] + "** " + metadata_emoji + "| Mints: " + str(current_mint) + " | Wallets: " + str(current_wallets) + " | Wallet Avg: " + mints_per_wallet + " | Avg Price: " + str(average_price) + verified + "\n"

        await message.channel.send(send_text)


    async def command_metadata(self, message, contract_address):

        special_characters = '!@#$%^&*()+?=,<>/"'
        if any(c in special_characters for c in contract_address):
            await message.channel.send('metadata supports only alphanumeric characters')
            return

        metadata = mintbot_db.getMetadata(contract_address)
        print(len(metadata))
        if metadata is None:
            send_text = "No metadata found"
        else:
	
            header = "Metadata info: **" + str(metadata['contract_name']) + "** | " + metadata['contract_address'] + "\n"

            token_uri = ""
            image = ""
            if metadata['metadata_type'] == "hosted" or metadata['metadata_type'] == "ipfs" or metadata['metadata_type'] == "arweave":
                token_uri = ":white_small_square: Metadata: <" + metadata['token_uri'] + ">\n"

                if metadata['image'] is not None:
                    image = ":white_small_square: Art: <" + metadata['image'] + ">\n"

            if metadata['metadata_type'] is None:
                metadata_type = ""
            else:
                metadata_type = ":white_small_square: Metadata Type: " + metadata['metadata_type'] + "\n"

            contract_url = ":white_small_square: Contract: <" + self.urls['etherscan_address'] + metadata['contract_address'] + ">\n"

            if metadata['verified'] is False:
                verified = ":white_small_square: <:BYTECODE:834146570298589194> Unverified"
            else:
                verified = ""

            if metadata['slug'] != "None" and metadata['slug'] is not None:
                opensea = ":white_small_square: Opensea: <" + 'https://opensea.io/collection/' + metadata['slug'] + ">\n"
            else:
                opensea = ":white_small_square: Opensea: <" + 'https://opensea.io/assets?search[query]=' + metadata['contract_address'] + ">\n"

            send_text = header + metadata_type + token_uri + image + contract_url + opensea + verified

        await message.channel.send(send_text) 


    async def command_whats_minting(self, message, search_params):

        try:
            blocks = int(search_params)
        except:
            blocks = 1

        if blocks > 5:
            blocks = 5

        last_blocks_str, sorted_dict = mintbot_db.whatsMinting(blocks)
        header = "**Currently minting in blocks " + last_blocks_str + ":**\n"
        send_text = header

        for row in sorted_dict:
            contract_address = row['contract_address']
            contract_name = row['contract_name']
            fees = row['fees']
            mints = row['mints']
            txn_count = row['txn_count']
            send_text = send_text + "**Txns:** " + str(txn_count) + " | **Fees:** " + str(fees) + " | **Contract:** " + contract_address + " | **Name:** " + contract_name + "\n"

        await message.channel.send(send_text)


    async def command_listing(self, message, contract_address):

        special_characters = '!@#$%^&*()+?=,<>/"'
        if any(c in special_characters for c in contract_address):
            await message.channel.send('owner supports only alphanumeric characters')
            return

        mint = mintbot_db.getContract(contract_address)
        print(mint)

        if mint['metadata_type'] == "arweave":
            metadata_emoji = ":dna:"
        elif mint['metadata_type'] == "base64":
            metadata_emoji = ":chains:"
        elif mint['metadata_type'] == "ipfs":
            metadata_emoji = ":ringed_planet:"
        elif mint['metadata_type'] == "hosted":
            metadata_emoji = ":ghost:"
        elif mint['metadata_type'] == "utf8":
            metadata_emoji = ":8ball:"
        else:
            metadata_emoji = ":skull_crossbones:"

        if mint['verified'] is False:
            verified = " | <:BYTECODE:834146570298589194> Unverified"
        else:
            verified = ""

        print("token_uri len: %s" % (len(mint['token_uri'])))

        if (mint['contract_name'] is not None) or (mint['contract_nama'] != "UNKNOWN"):
            contract_name = mint['contract_name']

        header = "Listing info: **" + contract_name + "**: " + metadata_emoji + " " + mint['contract_address'] + verified + "\n"
        token_uri = ":white_small_square: Metadata: <" + mint['token_uri'] + ">\n"
        metadata_type = ":white_small_square: Metadata Type: " + str(mint['metadata_type']) + "\n"
        contract_url = ":white_small_square: Contract: <" + self.urls['etherscan_address'] + mint['contract_address'] + ">\n"
        creation_date = ":white_small_square: Date: " + str(mint['creation_date']) + "\n"
        image_url = ":white_small_square: Art: <" + mint['image'] + ">\n"
        opensea = ":white_small_square: Opensea: <" + 'https://opensea.io/assets?search[query]=' + mint['contract_address'] + ">\n"

        if mint['slug'] != "None" and mint['slug'] is not None:
            opensea = ":white_small_square: Opensea: <" + 'https://opensea.io/collection/' + mint['slug'] + ">\n"
        else:
            opensea = ":white_small_square: Opensea: <" + 'https://opensea.io/assets?search[query]=' + mint['contract_address'] + ">\n"

        if mint['contract_owner'] != "None":
            if mint['owner_count'] > 1:
                contract_owner = ":white_small_square: Owner: <" + self.urls['etherscan_address'] + mint['contract_owner'] + ">\n" + ":white_small_square: Contracts by owner: " + str(mint['owner_count']) + "\n" + creation_date
            else:
                contract_owner = ":white_small_square: Owner: <" + self.urls['etherscan_address'] + mint['contract_owner'] + ">\n" + creation_date 

        if mint['metadata_type'] is not None and mint['metadata_type'] != "UNKNOWN" and mint['metadata_type'] != "None":
            if mint['metadata_type'] == "base64" or mint['metadata_type'] == "utf8" or mint['metadata_type'] == "text/plain" or mint['metadata_type'] == "arweave":
                send_text = (header + contract_url + opensea + metadata_type)
            elif mint['metadata_type'] is None:
                send_text = (header + contract_url + opensea)
            else:
                send_text = (header + contract_url + opensea + token_uri + metadata_type)

            if mint['image'] != 'None':
                send_text = (send_text + image_url)
        else:
            send_text = ("\n" + header + contract_url + opensea)

        if mint['contract_owner'] != "None":
            send_text = send_text + contract_owner

        await message.channel.send(send_text)


    async def command_help(self, message):

        if message:
            help_text = "**~owner <contract_address>** *Show contracts deployed by this address*\n" \
            + "**~listing <contract_address>** *Show listing for this contract*\n" \
            + "**~metadata <contract_address>** *Show metadata type for this contract*\n" \
            + "**~stats <contract_address>** *Show wallet and mint stats for this contract*\n" \
            + "**~whatsminting (<number of blocks with max of 3>)** *Show metrics on minting in the last few blocks*\n"

        await message.channel.send(help_text)



    async def send_first_mint_to_channel(self, mint):

        if (mint['contract_name'] is not None) or (mint['contract_nama'] != "UNKNOWN"):
            contract_name = mint['contract_name']

        if mint['verified'] is False:
            verified = " | <:BYTECODE:111146570298589194> Unverified"
        else:
            verified =""

        header = ":dizzy: **First mint for " + contract_name + "**" + verified + "\n"

        token_uri = ":white_small_square: Metadata: <" + mint['token_uri'] + ">\n"

        metadata_type = ":white_small_square: Metadata Type: " + str(mint['metadata_type']) + "\n"

        contract_url = ":white_small_square: Contract: <" + self.urls['etherscan_address'] + mint['contract_address'] + ">\n"

        current_holders = ":white_small_square: Holders: " + str(mint['current_wallets']) + "\n"

        current_mints = ":white_small_square: Mints: " + str(mint['current_mints']) + "\n"

        creation_date = ":white_small_square: Date: " + str(mint['creation_date']) + "\n"

        art = ""
        if mint['slug'] != "None" and mint['slug'] is not None:
            opensea = ":white_small_square: Opensea: " + 'https://opensea.io/collection/' + mint['slug'] + "\n"
        else:
            opensea = ":white_small_square: Opensea: <" + 'https://opensea.io/assets?search[query]=' + mint['contract_address'] + ">\n"


        if mint['contract_owner'] != "None":
            if mint['owner_count'] > 1:
                contract_owner = ":white_small_square: Owner: <" + self.urls['etherscan_address'] + mint['contract_owner'] + ">\n" + ":white_small_square: Contracts by owner: " + str(mint['owner_count']) + "\n" + current_holders + current_mints
            else:
                contract_owner = ":white_small_square: Owner: <" + self.urls['etherscan_address'] + mint['contract_owner'] + ">\n" + current_holders + current_mints

        print(mint)
        if mint['metadata_type'] is not None and mint['metadata_type'] != "UNKNOWN" and mint['metadata_type'] != "None" and mint['metadata_type'] != "invalid":
            if mint['metadata_type'] == "base64" or mint['metadata_type'] == "utf8" or mint['metadata_type'] == "text/plain" or mint['metadata_type'] == "arweave":
                send_text = (header + contract_url + opensea + metadata_type)
            elif mint['metadata_type'] is None:
                send_text = (header + contract_url + opensea)
            else:
                send_text = (header + contract_url + opensea + token_uri)
        else:
            send_text = ("\n" + header + contract_url + opensea)

        if mint['contract_owner'] != "None":
            send_text = send_text + contract_owner

        send_text = "--------------------------------------------------\n" + send_text

        print("Channel send_text:  " + send_text)

        channel = self.get_channel(self.public_channel)
        await channel.send(send_text)


    async def send_mint_increase_to_channel(self, mint):

        print(mint)

        if (mint['contract_name'] is not None) or (mint['contract_nama'] != "UNKNOWN"):
            contract_name = mint['contract_name']
        else:
            contract_name = "Null"

        if mint['average_price'] == 0:
            price = " :free: "
        else:
            average_price = Decimal(mint['average_price']).normalize()
            price = "| **Price:** " + str(average_price)

        mint_alert_count = mint['mint_alert_count']
        current_wallets = mint['current_wallets']
        current_mint = mint['current_mint']
        mints_per_wallet = str(round((current_mint / current_wallets)))

        if mint['metadata_type'] == "arweave":
            metadata_emoji = ":dna:"
        elif mint['metadata_type'] == "base64":
            metadata_emoji = ":chains:"
        elif mint['metadata_type'] == "ipfs":
            metadata_emoji = ":ringed_planet:"
        elif mint['metadata_type'] == "hosted":
            metadata_emoji = ":ghost:"
        elif mint['metadata_type'] == "utf8":
            metadata_emoji = ":8ball:"
        else:
            metadata_emoji = ":skull_crossbones:"

        if mint['verified'] is False:
            verified = " | <:BYTECODE:111146570298589194> Unverified"
        else:
            verified=""

        send_text = "<:nft:1118481343606177802> **Mints (" + contract_name + "):** " + price + "| **New:** " + str(mint['delta_mint']) + " | **Total:** " + str(current_mint) + " | **Wallet Avg:** " + mints_per_wallet + " | **Alert Count:** " + str(mint_alert_count) + " | " + mint['contract_address'] + " " + metadata_emoji + verified + "\n"
        print(send_text)
        mintbot_db.updateAlertLog(mint['contract_address'], mint['contract_name'], mint['current_mint'], mint['average_price'], mint['metadata_type'], mint['current_wallets'], 1, 0, 1)

        channel = self.get_channel(self.nft_war_room_channel)
        await channel.send(send_text)


    async def send_wallet_increase_to_channel(self, mint):

        print(mint)

        if (mint['contract_name'] is not None) or (mint['contract_nama'] != "UNKNOWN"):
            contract_name = mint['contract_name']
        else:
            contract_name = "Null"

        if mint['average_price'] == 0:
            price = " :free: "
        else:
            average_price = Decimal(mint['average_price']).normalize()
            price = "| **Price:** " + str(average_price)

        wallet_alert_count = mint['wallet_alert_count']
        current_wallets = mint['current_wallets']
        current_mint = mint['current_mint']
        mints_per_wallet = str(round((current_mint / current_wallets)))

        if mint['metadata_type'] == "arweave":
            metadata_emoji = ":dna:"
        elif mint['metadata_type'] == "base64":
            metadata_emoji = ":chains:"
        elif mint['metadata_type'] == "ipfs":
            metadata_emoji = ":ringed_planet:"
        elif mint['metadata_type'] == "hosted":
            metadata_emoji = ":ghost:"
        elif mint['metadata_type'] == "utf8":
            metadata_emoji = ":8ball:"
        else:
            metadata_emoji = ":skull_crossbones:"

        if mint['verified'] is False:
            verified = " | <:BYTECODE:111146570298589194> Unverified"
        else:
            verified=""

        send_text = ":shopping_bags: **Wallets (" + contract_name + "):** " + price + "| **New:** " + str(mint['delta_wallets']) + " | **Total:** " + str(mint['current_wallets']) + " | **Wallet Avg:** " + mints_per_wallet + " | **Alert Count:** " + str(wallet_alert_count) + " | " + mint['contract_address'] + " " + metadata_emoji + verified + "\n"
        print(send_text)
        mintbot_db.updateAlertLog(mint['contract_address'], mint['contract_name'], mint['current_mint'], mint['average_price'], mint['metadata_type'], mint['current_wallets'], 0, 1, 1)

        channel = self.get_channel(self.nft_war_room_channel)
        await channel.send(send_text)


    async def send_wallet_trending_to_channel(self, mint):

        print(mint)

        if (mint['contract_name'] is not None) or (mint['contract_nama'] != "UNKNOWN"):
            contract_name = mint['contract_name']
        else:
            contract_name = "Null"

        if mint['average_price'] == 0:
            price = " :free: "
        else:
            average_price = Decimal(mint['average_price']).normalize()
            price = "| **Price:** " + str(average_price)

        total_mints = mint['total_mints']
        total_wallets = mint['total_wallets']
        mints_per_wallet = str(round((total_mints / total_wallets)))
        wallet_alert_count = mint['wallet_alert_count']

        if mint['metadata_type'] == "arweave":
            metadata_emoji = ":dna:"
        elif mint['metadata_type'] == "base64":
            metadata_emoji = ":chains:"
        elif mint['metadata_type'] == "ipfs":
            metadata_emoji = ":ringed_planet:"
        elif mint['metadata_type'] == "hosted":
            metadata_emoji = ":ghost:"
        elif mint['metadata_type'] == "utf8":
            metadata_emoji = ":8ball:"
        else:
            metadata_emoji = ":skull_crossbones:"

        etherscan_url = self.urls['etherscan_address'] + mint['contract_address']

        if mint['slug'] != "None" and mint['slug'] is not None:
            opensea = 'https://opensea.io/collection/' + mint['slug']
        else:
            opensea = 'https://opensea.io/assets?search[query]=' + mint['contract_address']

        embed = None
        send_text = None
        
        if wallet_alert_count == 1:
            send_text = "**First trending wallet alert for " + mint['contract_address'] + "**\n"
            embed=discord.Embed(title=(contract_name + "** | First trending wallet alert \#" + str(wallet_alert_count) + "**"), url=opensea, description=mint['contract_address'], color=0xff0000)
        elif wallet_alert_count == 2:
            embed=discord.Embed(title=(contract_name + "** | Trending wallet alert \#" + str(wallet_alert_count) + "**"), url=opensea, description=mint['contract_address'], color=0x003cff)
        else:
            embed=discord.Embed(title=(contract_name + "** | Trending wallet alert \#" + str(wallet_alert_count) + "**"), description=mint['contract_address'], url=opensea, color=0x109319)

        thumbnail = None
        if mint['opensea_image_url'] is not None and mint['opensea_image_url'] != "none" and mint['opensea_image_url'] != "None":
            thumbnail = mint['opensea_image_url']
            embed.set_thumbnail(url=mint['opensea_image_url'])

        if thumbnail is None:
            if mint['image'] != 'None':
                thumbnail = mint['image']

        if thumbnail is not None:
            embed.set_thumbnail(url=thumbnail)

        embed.add_field(name="Price", value=price, inline=True)
        embed.add_field(name="Wallets", value=mint['total_wallets'], inline=True)
        embed.add_field(name="Per Wallet", value=mints_per_wallet, inline=True)
        embed.add_field(name="Etherscan", value=etherscan_url, inline=False)

        print(send_text)


    async def send_mint_trending_to_channel(self, mint):

        print(mint)

        if (mint['contract_name'] is not None) or (mint['contract_nama'] != "UNKNOWN"):
            contract_name = mint['contract_name']
        else:
            contract_name = "Null"

        if contract_name == "Null":
            contract_name = mint['slug']

        if mint['average_price'] == 0:
            price = " :free: "
        else:
            average_price = Decimal(mint['average_price']).normalize()
            price = str(average_price)

        total_mints = mint['total_mints']
        total_wallets = mint['total_wallets']
        mints_per_wallet = str(round((total_mints / total_wallets)))
        mint_alert_count = mint['alert_count']

        if mint['metadata_type'] == "arweave":
            metadata_emoji = ":dna:"
        elif mint['metadata_type'] == "base64":
            metadata_emoji = ":chains:"
        elif mint['metadata_type'] == "ipfs":
            metadata_emoji = ":ringed_planet:"
        elif mint['metadata_type'] == "hosted":
            metadata_emoji = ":ghost:"
        elif mint['metadata_type'] == "utf8":
            metadata_emoji = ":8ball:"
        else:
            metadata_emoji = ":skull_crossbones:"

        etherscan_url = self.urls['etherscan_address'] + mint['contract_address']

        if mint['slug'] != "None" and mint['slug'] is not None:
            opensea = 'https://opensea.io/collection/' + mint['slug']
        else:
            opensea = 'https://opensea.io/assets?search[query]=' + mint['contract_address']

        embed = None
        send_text = None
        if mint_alert_count == 1:
            send_text = "**First trending mint alert for " + mint['contract_address'] + "**\n"
            embed=discord.Embed(title=(contract_name + "** | First trending mint alert \#" + str(mint_alert_count) + "**"), url=opensea, description=mint['contract_address'], color=0xff0000)
        elif mint_alert_count == 2:
            embed=discord.Embed(title=(contract_name + "** | Trending mint alert \#" + str(mint_alert_count) + "**"), url=opensea, description=mint['contract_address'], color=0x003cff)
        else:
            embed=discord.Embed(title=(contract_name + "** | Trending mint alert \#" + str(mint_alert_count) + "**"), description=mint['contract_address'], url=opensea, color=0x109319)

        thumbnail = None
        if mint['opensea_image_url'] is not None and mint['opensea_image_url'] != "none" and mint['opensea_image_url'] != "None":
            thumbnail = mint['opensea_image_url']
            embed.set_thumbnail(url=mint['opensea_image_url'])

        if thumbnail is None:
            if mint['image'] != 'None':
                thumbnail = mint['image']

        if thumbnail is not None and thumbnail != 'NULL' and validators.url(thumbnail):
            embed.set_thumbnail(url=thumbnail)

        embed.add_field(name="Price", value=price, inline=True)
        embed.add_field(name="Mints", value=mint['total_mints'], inline=True)
        embed.add_field(name="Per Wallet", value=mints_per_wallet, inline=True)

        if mint['owner_count'] > 1:
            embed.add_field(name="Owner", value=mint['owner_count'], inline=True)

        embed.add_field(name="Etherscan", value=etherscan_url, inline=False)

        print(send_text)
        channel = self.get_channel(self.nft_war_room_channel)
        await channel.send(embed=embed)

        embed.add_field(name="Mint.fun", value=('https://mint.fun/' + mint['contract_address']), inline=False)
        channel = self.get_channel(self.nft_war_room_channel)
        if send_text is not None:
            await channel.send(send_text)
        await channel.send(embed=embed)


    async def send_contract_to_channel(self, channel, send_text):

        # Send to channel
        try:
            await channel.send(send_text)

        except:
            print(traceback.format_exc())


    async def repopulate_vip_members(self):

        vip = []
        for member in self.guilds[0].members:
            if len(member.roles) == 1:
                continue
            for role in member.roles:
                if role.name.lower() == "group_one":
                    vip.append(member.id)
                if role.name.lower() == "group_two":
                    if not member.id in vip:
                        vip.append(member.id)
        global vip_members
        vip_members = vip


    async def on_message(self, message):

        try:
            # Prevent bot from reacting to it's own messages
            if message.author == self.user: return

            if not message.content.lower().startswith('~'): return

            if message.guild:
                print(datetime.now().strftime("%d/%m/%Y %H:%M:%S") + " *** BOT COMMAND: " + str(message.author.id) + " - " + message.author.name + " - Message: " + message.content)

            if not message.guild: # This is a DM
                print(datetime.now().strftime("%d/%m/%Y %H:%M:%S") + " *** BOT DM: " + str(message.author.id)  + " - " + message.author.name + " - Message: " + message.content)
                vip = False
                if message.author.id in vip_members:
                    vip = True
                if vip == False:
                    await message.channel.send('Bot commands require VIP.')
                    return

            if not message.author.id in vip_members:
                return

            if message.content.lower().startswith('~owner '):
                contract_address = message.content.replace('~owner ','').strip()
                await self.command_owner(message, contract_address)
                return

            if message.content.lower().startswith('~listing '):
                contract_address = message.content.replace('~listing ','').strip()
                await self.command_listing(message, contract_address)
                return

            if message.content.lower().startswith('~stats '):
                contract_address = message.content.replace('~stats ','').strip()
                await self.command_stats(message, contract_address)
                return

            if message.content.lower().startswith('~metadata '):
                contract_address = message.content.replace('~metadata ','').strip()
                await self.command_metadata(message, contract_address)
                return

            if message.content.lower().startswith('~whatsminting'):
                blocks = message.content.replace('~whatsminting ','').strip()
                await self.command_whats_minting(message, blocks)
                return

            if message.content.lower().startswith('~help'):
                await self.command_help(message)
                return


        except:
            print(traceback.format_exc())


def main():

        global discord_token
        global mintDiscordClient
        global nft_war_room_channel
        global nft_contracts_channel
        global public_channel

        global admin_members
        admin_members = []

        global vip_members
        vip_members = []

        # load config options and secrets
        config_file="/home/nft_mint_tracker/mintbot/mintbot.conf"
        if os.path.exists(config_file):
                config = configparser.ConfigParser()
                config.read(config_file)
                discord_token = config.get('mintbot', 'token')
                nft_war_room_channel = config.get('mintbot', 'nft_war_room_channel')
                nft_contracts_channel = config.get('mintbot', 'nft_contracts_channel')
                public_channel = config.get('mintbot', 'public_channel')

        else:
                raise Exception(config_file)

        mintDiscordClient=MyDiscordClient(intents=intents)
        mintDiscordClient.run(discord_token)

if __name__ == "__main__" : main()
