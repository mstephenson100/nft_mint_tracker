#!/usr/bin/python3

import requests
import os
import configparser
import time
import requests
import urllib3
import json
import pymysql
import warnings
import traceback
import asyncio
import sys
import re
from web3 import Web3, HTTPProvider
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def mysqlCon(user, password, db):

    con = pymysql.connect("192.168.100.2", user, password, db)
    return con

def getTxns(con):

    txns = []
    try:
        sql="SELECT txn_id, contract_address, mints, average_price, ethervalue, txn_fee, contract_type, minter_address FROM mint_tracker_txns WHERE status = 0 ORDER BY DATE ASC LIMIT 50"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

        with con:

            cur = con.cursor()
            tic = time.time()
            cur.execute("%s" % sql)
            toc = time.time()
            rows = cur.fetchall()

            for row in rows:

                txns.append({"txn_id": row[0], "contract_address": row[1], "mints": row[2], "average_price": row[3], "ethervalue": row[4], "txn_fee": row[5], "contract_type": row[6], "minter_address": row[7]})

    except:
        print(traceback.format_exc())

    return txns


def getNftMetadata(con, contract_address):

    contract_name = None
    image = None
    nft_json = None
    token_uri = None
    nft_type = None
    metadata_type = None
    contract_owner = None
    owner_count = None
    slug = None
    opensea_image_url = None

    try:
        sql=("SELECT contract_name, image, token_uri, nft_type, metadata_type, contract_owner, owner_count, slug, opensea_image_url FROM mint_tracker_contracts WHERE contract_address = '%s'" % contract_address)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

        with con:

            cur = con.cursor()
            tic = time.time()
            cur.execute("%s" % sql)
            toc = time.time()
            rows = cur.fetchall()

            for row in rows:

                contract_name = row[0]
                image = row[1]
                token_uri = row[2]
                nft_type = row[3]
                metadata_type = row[4]
                contract_owner = row[5]
                owner_count = row[6]
                slug = row[7]
                opensea_image_url = row[8]

    except:
        print(traceback.format_exc())

    return contract_name, image, token_uri, nft_type, metadata_type, contract_owner, owner_count, slug, opensea_image_url


def getAlertMetrics(con, contract_address):

    contract_name = None
    image = None
    nft_json = None
    token_uri = None
    nft_type = None
    metadata_type = None
    contract_owner = None
    owner_count = None
    slug = None
    opensea_image_url = None

    try:
        sql=("SELECT contract_name, image, token_uri, metadata_type, contract_owner, owner_count, slug, opensea_image_url, current_mint, current_wallets, average_price FROM mint_tracker_alerts WHERE contract_address = '%s'" % contract_address)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

        with con:

            cur = con.cursor()
            tic = time.time()
            cur.execute("%s" % sql)
            toc = time.time()
            rows = cur.fetchall()

            for row in rows:

                contract_name = row[0]
                image = row[1]
                token_uri = row[2]
                metadata_type = row[3]
                contract_owner = row[4]
                owner_count = row[5]
                slug = row[6]
                opensea_image_url = row[7]
                current_mint = row[8]
                current_wallets = row[9]
                average_price = row[10]

    except:
        print(traceback.format_exc())

    return contract_name, image, token_uri, nft_type, metadata_type, contract_owner, owner_count, slug, opensea_image_url, current_mint, current_wallets, average_price


def lookupThumbnail(slug):

    url=('https://api.opensea.io/api/v2/collections/' + slug)
    print("curl --request GET --url \'%s\' --header 'Accept: application/json' --header 'X-API-KEY: %s\'" % (url, api_key))
    parsed = callOpenseaApi(url, api_key)
    if parsed is not None:
        print("parsed is not none for %s" % slug)
        if "errors" in parsed:
            thumbnail = None
        else:
            thumbnail = parsed['image_url']

    return thumbnail


def tryOpensea(con, api_key, contract_address):

    image_url = None
    slug = None

    url=('https://api.opensea.io/api/v2/chain/ethereum/contract/' + contract_address)
    print("curl --request GET --url \'%s\' --header 'Accept: application/json' --header 'X-API-KEY: %s\'" % (url, api_key))
    time.sleep(1)
    parsed = callOpenseaApi(url, api_key)
    print(parsed)
    if parsed is not None:

        print("parsed is not none for %s" % contract_address)
        if "errors" in parsed:
            print("opensea failed")
        else:
            if "collection" in parsed:
                slug = parsed['collection']
                image_url = lookupThumbnail(slug)

    return slug, image_url


def callOpenseaApi(url, api_key):

    headers = {
        "Accept": "application/json",
        "X-API-KEY": api_key
    }

    time.sleep(0.25)
    opensea_tries = 5
    while True:
        try:
            response = requests.request("GET", url, headers=headers)
            parsed = json.loads(response.text)

            rate_retries = 5
            while True:
                for element in parsed:
                    if element == "detail":
                        print("ERROR: %s" % url)
                        rate_retries -= 1
                        time.sleep(1)
                        if rate_tries:
                            continue
                        else:
                            print("opensea call was a total failure")
                            return None
                    else:
                        return parsed

        except:
            print("failed to call opensea %s" % url)
            print("sleeping 1 seconds before trying again")
            opensea_tries -= 1
            time.sleep(1)
            if opensea_tries:
                continue
            else:
                print("opensea call was a total failure")
                return None
        else:
            return None


def updateMintTrackerSlug(con, contract_address, slug, image_url):

    sql=("UPDATE mint_tracker_contracts SET slug = '%s', opensea_image_url = '%s', opensea_retries = 0, opensea_updated = (SELECT NOW()) WHERE contract_address = '%s'" % (slug, image_url, contract_address))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)


def countTrendingMints(con, trending_mints_threshold):

    trending_mints = []
    sql="SELECT contract_address, count(*) FROM mint_tracker_alertlog WHERE last_updated > (now() - INTERVAL 4 MINUTE) AND bot_mint = 1 AND reported = 0 GROUP BY contract_address"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

    with con:

        cur = con.cursor()
        tic = time.time()
        cur.execute("%s" % sql)
        toc = time.time()
        rows = cur.fetchall()

        for row in rows:

            if row[1] >= trending_mints_threshold:
                trending_mints.append({"contract_address": row[0], "mint_alerts": row[1]})

    return trending_mints



def countTrendingWallets(con, trending_wallets_threhsold):

    trending_wallets = []
    sql="SELECT contract_address, count(*) FROM mint_tracker_alertlog WHERE last_updated > (now() - INTERVAL 3 MINUTE) AND bot_wallet = 1 AND reported = 0 GROUP BY contract_address"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

    with con:

        cur = con.cursor()
        tic = time.time()
        cur.execute("%s" % sql)
        toc = time.time()
        rows = cur.fetchall()

        for row in rows:

            if row[1] >= trending_wallets_threhsold:
                trending_wallets.append({"contract_address": row[0], "mint_alerts": row[1]})

    return trending_wallets



def countMints(con, api_key, contract_list, contract_metadata, processed_txns, mint_alert_threshold, unique_mints_list, wallet_alert_threshold):

    for key, value in contract_list.items():

        contract_address = key
        bot=0
        bot_mint=0
        bot_wallet=0

        for contract in contract_metadata:
            if contract_address in contract['contract_address']:
                print(contract)
                contract_name=contract['contract_name']
                image=contract['image']
                token_uri=contract['token_uri']
                average_price=contract['average_price']
                txn_fee=contract['txn_fee']
                contract_type=contract['contract_type']
                minter_address=contract['minter_address']
                metadata_type=contract['metadata_type']
                contract_owner=contract['contract_owner']
                owner_count=contract['owner_count']
                slug=contract['slug']
                opensea_image_url=contract['opensea_image_url']

        # garbage mint counter math
        new_mints = value
        new_delta_mints=0
        previous_mints=getPreviousMints(con, contract_address)
        old_previous_mints=previous_mints
        current_mints = (new_mints + previous_mints)
        delta_mints=getDeltaMints(con, contract_address)
        new_delta_mints=(delta_mints + (current_mints - previous_mints))

        # its possible to have value token_uri but no metadata_type with older contracts so try to force a refresh in mint_metadata
        if metadata_type is None and current_mints > 3:
            resetUriRetries(con, contract_address)

        if metadata_type is None:
            metadata_type = 'UNKNOWN'

        if slug is None:
            slug, opensea_image_url = tryOpensea(con, api_key, contract_address)

            if slug is not None:
                updateMintTrackerSlug(con, contract_address, slug, opensea_image_url)

        if (new_delta_mints >= mint_alert_threshold):
            bot_mint=1
            print("new_delta_mints %s is greater than mint_alert_threshold %s" % (new_delta_mints, mint_alert_threshold))

        # garbage wallet counter math
        unique_wallets=0
        new_delta_wallets=0
        delta_wallets=0
        unique_wallets=getUniqueWallets(con, contract_address)
        previous_wallets=getPreviousWallets(con, contract_address)
        old_previous_wallets=unique_wallets

        if unique_wallets > previous_wallets:
            new_delta_wallets = (unique_wallets - previous_wallets)
            old_delta_wallets=getDeltaWallets(con, contract_address)
            delta_wallets = new_delta_wallets + old_delta_wallets

        current_wallets = unique_wallets

        # garbage mint to wallet ratio math
        mint_to_wallet_ratio=0
        mint_to_wallet_ratio=(current_mints / current_wallets)
        mint_to_wallet_ratio=round(mint_to_wallet_ratio)

        if (delta_wallets >= wallet_alert_threshold):
            # bot_wallet status 1 = contract_address reached wallet_alert_threshold and bot should alert
            bot_wallet=1
            print("new_delta_wallets %s is greater than or equal to wallet_alert_threshold %s" % (new_delta_wallets, wallet_alert_threshold))

        updateMints(con, contract_address, contract_name, contract_owner, owner_count, contract_type, current_mints, new_delta_mints, old_previous_mints, current_wallets, delta_wallets, old_previous_wallets, mint_to_wallet_ratio, image, token_uri, average_price, txn_fee, metadata_type, bot_mint, bot_wallet, bot, slug, opensea_image_url)

    for txn in processed_txns:
        # update txns that have now been processed
        updateTxns(con, txn, "nft")


def updateTxns(con, txn, contract_type):
    if contract_type == "nft":
        sql = ("UPDATE mint_tracker_txns SET status = 9 WHERE txn_id = '%s'" % (txn))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
        with con:
            cur = con.cursor()
            cur.execute("%s" % sql)
    else:
        sql = ("UPDATE mint_tracker_txns SET status = 8 WHERE txn_id = '%s'" % (txn))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
        with con:
            cur = con.cursor()
            cur.execute("%s" % sql)


def resetUriRetries(con, contract_address):
    sql=("UPDATE mint_tracker_contracts SET uri_retries = 0 WHERE contract_address = '%s' AND uri_retries >= 5" % contract_address)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)

    sql2=("UPDATE mint_tracker_contracts SET retry_metadata_type = 1 WHERE contract_address = '%s' AND token_uri IS NOT NULL" % contract_address)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql2)


def resetSlugRetries(con, contract_address):
    sql=("UPDATE mint_tracker_contracts SET opensea_retries = 0 WHERE contract_address = '%s' AND opensea_retries >= 5" % contract_address)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
    with con:
        cur = con.cursor()
        cur.execute("%s" % sql)


def updateMints(con, contract_address, contract_name, contract_owner, owner_count, contract_type, current_mints, delta_mints, old_previous_mints, current_wallets, delta_wallets, old_previous_wallets, mint_to_wallet_ratio, image, token_uri, average_price, txn_fee, metadata_type, bot_mint, bot_wallet, bot, slug, opensea_image_url):

    try:
        sql=("SELECT COUNT(*) FROM mint_tracker_alerts WHERE contract_address = '%s'" % contract_address)
        cur = con.cursor()
        cur.execute("%s" % sql)
        result = cur.fetchone()
        count=int(result[0])

        # contract_address is already in mint_tracker_alerts so update in place
        if count > 0:
            sql2=("UPDATE mint_tracker_alerts SET previous_mint = %s, current_mint = %s, delta_mint = %s, old_previous_mint = %s, image = '%s', token_uri = '%s', average_price = %s, txn_fee = %s, bot_mint = %s, bot_wallet = %s, bot = %s, contract_name = '%s', contract_type = '%s', metadata_type = '%s', previous_wallets = %s, current_wallets = %s, delta_wallets = %s, old_previous_wallets = %s, slug = '%s', opensea_image_url = '%s' WHERE contract_address = '%s'" % (current_mints, current_mints, delta_mints, old_previous_mints, image, token_uri, average_price, txn_fee, bot_mint, bot_wallet, bot, contract_name, contract_type, metadata_type, current_wallets, current_wallets, delta_wallets, old_previous_wallets, slug, opensea_image_url, contract_address))
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
            with con:
                cur = con.cursor()
                cur.execute("%s" % sql2)

        else:
            # contract_address is not yet tracked in mint_tracker_alerts so insert
            sql3=("INSERT IGNORE INTO mint_tracker_alerts (contract_address, contract_name, contract_owner, owner_count, contract_type, current_mint, previous_mint, delta_mint, old_previous_mint, image, token_uri, average_price, txn_fee, metadata_type, current_wallets, previous_wallets, delta_wallets, old_previous_wallets, last_updated, bot_mint, bot_wallet, bot, slug, opensea_image_url) VALUES ('%s', '%s', '%s', %s, '%s', %s, %s, %s, %s, '%s', '%s', %s, %s, '%s', %s, %s, %s, %s, (SELECT NOW()), %s, %s, %s, '%s', '%s')" % (contract_address, contract_name, contract_owner, owner_count, contract_type, current_mints, current_mints, delta_mints, old_previous_mints, image, token_uri, average_price, txn_fee, metadata_type, current_wallets, current_wallets, delta_wallets, old_previous_wallets, bot_mint, bot_wallet, bot, slug, opensea_image_url))
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
            with con:
                cur = con.cursor()
                cur.execute("%s" % sql3)

    except:
        print(traceback.format_exc())


def getConsolidatedMetrics(con, contract_address, metric_type):

    
    if metric_type == "mint":
        sql=("SELECT current_mint FROM mint_tracker_alerts WHERE contract_address = '%s'" % contract_address)
    else:
        sql=("SELECT current_wallets FROM mint_tracker_alerts WHERE contract_address = '%s'" % contract_address)

    cur = con.cursor()
    cur.execute("%s" % sql)
    result = cur.fetchone()
    if result is None:
        metric_count=0
    else:
        metric_count=int(result[0])

    return metric_count


def getPrice(con, contract_address):

    sql=("SELECT average_price FROM mint_tracker_alerts WHERE contract_address = '%s'" % contract_address)
    cur = con.cursor()
    cur.execute("%s" % sql)
    result = cur.fetchone()
    if result is None:
        average_price=0
    else:
        average_price = result[0]

    return average_price


def updateTrendingMint(con, trending_mints_threshold):

    contracts=[]
    sql="SELECT contract_address, count(*) FROM mint_tracker_alertlog WHERE last_updated > (now() - INTERVAL 3 MINUTE) AND bot_mint = 1 AND reported = 0 GROUP BY contract_address"
    cur = con.cursor()
    cur.execute("%s" % sql)
    rows = cur.fetchall()
    for row in rows:
            contracts.append({"contract_address": row[0], "alerts": int(row[1])})

    if len(contracts) > 0:

        for row in contracts:
            if row['alerts'] >= trending_mints_threshold:
                contract_address = row['contract_address']
                alerts = row['alerts']
                contract_name, image, token_uri, nft_type, metadata_type, contract_owner, owner_count, slug, opensea_image_url = getNftMetadata(con, contract_address)
                total_mints = getConsolidatedMetrics(con, contract_address, "mint")
                total_wallets = getConsolidatedMetrics(con, contract_address, "wallet")
                average_price = getPrice(con, contract_address)

                sql2=("INSERT INTO mint_tracker_trending (contract_address, contract_name, contract_owner, owner_count, total_mints, total_wallets, image, token_uri, average_price, metadata_type, bot_mint, slug, opensea_image_url, last_updated) VALUES ('%s', '%s', '%s', %s, %s, %s, '%s', '%s', %s, '%s', 1, '%s', '%s', (SELECT NOW()))" % (contract_address, contract_name, contract_owner, owner_count, total_mints, total_wallets, image, token_uri, average_price, metadata_type, slug, opensea_image_url))

                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                with con:
                    cur = con.cursor()
                    cur.execute("%s" % sql2)

                sql3=("UPDATE mint_tracker_alertlog SET reported = 1 WHERE contract_address = '%s' AND bot_mint = 1" % contract_address)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                with con:
                    cur = con.cursor()
                    cur.execute("%s" % sql3)


def updateTrendingWallets(con, trending_wallets_threshold):

    contracts=[]
    sql="SELECT contract_address, count(*) FROM mint_tracker_alertlog WHERE last_updated > (now() - INTERVAL 3 MINUTE) AND bot_wallet = 1 AND reported = 0 GROUP BY contract_address"
    cur = con.cursor()
    cur.execute("%s" % sql)
    rows = cur.fetchall()
    for row in rows:
            contracts.append({"contract_address": row[0], "alerts": int(row[1])})

    if len(contracts) > 0:

        for row in contracts:
            if row['alerts'] >= trending_wallets_threshold:
                contract_address = row['contract_address']
                alerts = row['alerts']
                contract_name, image, token_uri, nft_type, metadata_type, contract_owner, owner_count, slug, opensea_image_url = getNftMetadata(con, contract_address)
                total_mints = getConsolidatedMetrics(con, contract_address, "mint")
                total_wallets = getConsolidatedMetrics(con, contract_address, "wallet")
                average_price = getPrice(con, contract_address)

                sql2=("INSERT INTO mint_tracker_trending (contract_address, contract_name, contract_owner, owner_count, total_mints, total_wallets, image, token_uri, average_price, metadata_type, bot_wallet, slug, opensea_image_url, last_updated) VALUES ('%s', '%s', '%s', %s, %s, %s, '%s', '%s', %s, '%s', 1, '%s', '%s', (SELECT NOW()))" % (contract_address, contract_name, contract_owner, owner_count, total_mints, total_wallets, image, token_uri, average_price, metadata_type, slug, opensea_image_url))

                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                with con:
                    cur = con.cursor()
                    cur.execute("%s" % sql2)

                sql3=("UPDATE mint_tracker_alertlog SET reported = 1 WHERE contract_address = '%s' AND bot_wallet = 1" % contract_address)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                with con:
                    cur = con.cursor()
                    cur.execute("%s" % sql3)


def getPreviousMints(con, contract_address):

    mints = 0
    sql = ("SELECT previous_mint FROM mint_tracker_alerts WHERE contract_address = '%s'" % contract_address)
    with con:

        cur = con.cursor()
        cur.execute("%s" % sql)
        result = cur.fetchone()
        if result is None:
            mints=0
        else:
            mints=int(result[0])

    return mints


def getPreviousWallets(con, contract_address):

    previous_wallets = 0
    sql = ("SELECT previous_wallets FROM mint_tracker_alerts WHERE contract_address = '%s'" % contract_address)
    with con:

        cur = con.cursor()
        cur.execute("%s" % sql)
        result = cur.fetchone()
        if result is None:
            previous_wallets=0
        else:
            previous_wallets=int(result[0])

    return previous_wallets


def getUniqueWallets(con, contract_address):

    unique_wallets = 0
    sql = ("SELECT COUNT(DISTINCT(minter_address)) FROM mint_tracker_txns WHERE contract_address = '%s'" % contract_address)
    with con:

        cur = con.cursor()
        cur.execute("%s" % sql)
        result = cur.fetchone()
        if result is None:
            unique_wallets=0
        else:
            unique_wallets=int(result[0])

    return unique_wallets


def getDeltaMints(con, contract_address):

    delta_mints = 0
    sql = ("SELECT delta_mint FROM mint_tracker_alerts WHERE contract_address = '%s'" % contract_address)

    with con:

        cur = con.cursor()
        cur.execute("%s" % sql)
        result = cur.fetchone()
        if result is None:
            delta_mints=0
        else:
            delta_mints=int(result[0])

    return delta_mints


def getDeltaWallets(con, contract_address):

    delta_wallets = 0
    sql = ("SELECT delta_wallets FROM mint_tracker_alerts WHERE contract_address = '%s'" % contract_address)

    with con:

        cur = con.cursor()
        cur.execute("%s" % sql)
        result = cur.fetchone()
        if result is None:
            delta_wallets=0
        else:
            delta_wallets=int(result[0])

    return delta_wallets


async def log_loop(con, api_key, mint_alert_threshold, poll_interval, trending_mints_threshold, trending_wallets_threshold, wallet_alert_threshold):

    while True:

        contract_list = {}
        minter_list = {}
        unique_mints_list = {}
        contract_metadata = []
        processed_txns = []
        txns = getTxns(con)

        if len(txns) > 0:
            for _dict in txns:

                txn_id = _dict['txn_id']
                contract_address = _dict['contract_address']
                mints = _dict['mints']
                average_price = _dict['average_price']
                ethervalue = _dict['ethervalue']
                txn_fee = _dict['txn_fee']
                contract_type = _dict['contract_type']
                minter_address = _dict['minter_address']

                # nuke txns with unknown contract type
                if contract_type == "UNKNOWN":
                    print("Nuking %s because contract_type is UNKNOWN" % txn_id)
                    updateTxns(con, txn_id, contract_type)

                else:

                    if contract_address in contract_list:
                        #print("Adding %s to contract_list" % contract_address)
                        contract_list[contract_address]+=mints
                        if minter_address in minter_list:
                            if contract_address == minter_list[minter_address]:
                                unique_mints_list[contract_address]+=1
                    else:
                        # add contract to nft_list
                        contract_list.update({contract_address: mints})
                        minter_list.update({minter_address: contract_address})
                        unique_mints_list.update({contract_address: 1})
                        contract_name, image, token_uri, nft_type, metadata_type, contract_owner, owner_count, slug, opensea_image_url = getNftMetadata(con, contract_address)
                        print("txn_id: %s, contract_name: %s, image: %s, token_uri: %s, contract_address: %s, nft_type: %s, minter_address: %s, metadata_type: %s, contract_owner: %s, owner_count: %s, slug: %s, opensea_image_url: %s" % (txn_id, contract_name, image, token_uri, contract_address, nft_type, minter_address, metadata_type, contract_owner, owner_count, slug, opensea_image_url))
                        contract_metadata.append({"contract_address": contract_address, "average_price": average_price, "txn_fee": txn_fee, "contract_name": contract_name, "image": image, "token_uri": token_uri, "contract_type": contract_type, "minter_address": minter_address, "metadata_type": metadata_type, "contract_owner": contract_owner, "owner_count": owner_count, "slug": slug, "opensea_image_url": opensea_image_url})

                    # make a list of processed txns to mark them done later
                    processed_txns.append(txn_id)

        countMints(con, api_key, contract_list, contract_metadata, processed_txns, mint_alert_threshold, unique_mints_list, wallet_alert_threshold)

        #trending_mints_threshold=5
        updateTrendingMint(con, trending_mints_threshold)

        #trending_wallets_threshold=3
        updateTrendingWallets(con, trending_wallets_threshold)

        await asyncio.sleep(poll_interval)


def main():

    global db_user
    global db_password
    global db
    global con
    global sales_threshold
    global offers_threshold
    global creates_threshold
    global listings_threshold
    global api_key

    # load config options and secrets
    config_file="/home/nft_mint_tracker/scanner.conf"
    if os.path.exists(config_file):
        config = configparser.ConfigParser()
        config.read(config_file)
        db_user = config.get('credentials', 'db_user')
        db_password = config.get('credentials', 'db_password')
        db = config.get('credentials', 'db')
        api_key = config.get('opensea', 'api_key')

    else:
        raise Exception(config_file)

    con=mysqlCon(db_user, db_password, db)

    mint_alert_threshold=30
    trending_mints_threshold=2

    wallet_alert_threshold = 15
    trending_wallets_threshold=3

    poll_interval=1
    loop = asyncio.get_event_loop()
    try:
        print("*** Starting mint counter")
        loop.run_until_complete(
            asyncio.gather(
                log_loop(con, api_key, mint_alert_threshold, poll_interval, trending_mints_threshold, trending_wallets_threshold, wallet_alert_threshold)))
    finally:
        loop.close()


if __name__ == "__main__" : main()
