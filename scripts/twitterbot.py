import os
import re
import tweepy
import pandas as pd
import time
from datetime import datetime
from termcolor import colored
from web3 import Web3

LOCATION = "data/"

# Load infura rpc endpoint url
with open("key/infura.txt", "r") as f:
    RPC_ENDPOINT = f.read().strip()

# Validator list
validator_list = [
    1372330, 1372331, 1372332, 1372333, 1372334, 1465979, 1465980, 1465981, 
    1465982, 1465983, 1465984, 1465985, 1465986, 1465987, 1465988, 1465989, 
    1465990, 1466419, 1466420, 1466421, 1489959, 1489960, 1489961, 1489962, 
    1489963, 1489964, 1489965, 1489966, 1489967, 1489968, 1489969, 1490094, 
    1490095, 1490096, 1490097, 1490098, 1490099, 1490100, 1490101, 1490102, 
    1539382, 1540907, 1540908, 1540909, 1540910, 1540911, 1540912, 1540913, 
    1540914, 1540915, 1540916, 1540917, 1540918, 1540919, 1541009, 1541010, 
    1541011, 1541012, 1541013, 1541014
]

fb_b = ["0xa1dead01e65f0a0eee7b5170223f20c8f0cbf122eac3324d61afbdb33a8885ff8cab2ef514ac2c7698ae0d6289ef27fc",
        "0x81beef03aafd3dd33ffd7deb337407142c80fea2690e5b3190cfc01bde5753f28982a7857c96172a75a234cb7bcb994f",
        "0x81babeec8c9f2bb9c329fd8a3b176032fe0ab5f3b92a3f44d4575a231c7bd9c31d10b6328ef68ed1e8c02a3dbc8e80f9",
        "0xa1defa73d675983a6972e8686360022c1ebc73395067dd1908f7ac76a526a19ac75e4f03ccab6788c54fdb81ff84fc1b"]

ed_b = ["0xa5eec32c40cc3737d643c24982c7f097354150aac1612d4089e2e8af44dbeefaec08a11c76bd57e7d58697ad8b2bbef5"]

bx_b = ["0x80c7311597316f871363f8395b6a8d056071d90d8eb27defd14759e8522786061b13728623452740ba05055f5ba9d3d5",
        "0x8b8edce58fafe098763e4fabdeb318d347f9238845f22c507e813186ea7d44adecd3028f9288048f9ad3bc7c7c735fba",
        "0x95701d3f0c49d7501b7494a7a4a08ce66aa9cc1f139dbd3eec409b9893ea213e01681e6b76f031122c6663b7d72a331b",
        "0xb086acdd8da6a11c973b4b26d8c955addbae4506c78defbeb5d4e00c1266b802ff86ec7457c4c3c7c573fa1e64f7e9e0",
        "0xaa1488eae4b06a1fff840a2b6db167afc520758dc2c8af0dfb57037954df3431b747e2f900fe8805f05d635e9a29717b",
        "0x94aa4ee318f39b56547a253700917982f4b737a49fc3f99ce08fa715e488e673d88a60f7d2cf9145a05127f17dcb7c67",
        "0xb9b50821ec5f01bb19ec75e0f22264fa9369436544b65c7cf653109dd26ef1f65c4fcaf1b1bcd2a7278afc34455d3da6"]

ma_b = ["0xa25f5d5bd4f1956971bbd6e5a19e59c9b1422ca253587bbbb644645bd2067cc08fb854a231061f8c91f110254664e943"]

bn_b = ["0x9000009807ed12c1f08bf4e81c6da3ba8e3fc3d953898ce0102433094e5f22f21102ec057841fcb81978ed1ea0fa8246"]

bu_z = ["0xb194b2b8ec91a71c18f8483825234679299d146495a08db3bf3fb955e1d85a5fca77e88de93a74f4e32320fc922d3027"]

def get_builder_label(a):
    if a in fb_b:
        return "(Flashbots)"
    elif a in ed_b:
        return "(Eden)"
    elif a in bx_b:
         return "(Bloxroute)"
    elif a in ma_b:
         return "(Manifold)"
    elif a in bn_b:
        return "(Blocknative)"
    elif a in bu_z:
        return "(Builder 0x69)"
    return "(anon)"

def get_twitter_handle(a):
    if a in fb_b or a == "flashbots":
        return "Flashbots"
    elif a in ed_b or a == "eden":
        return "@EdenNetwork"
    elif a in bx_b or "bloxroute" in a:
         return "@bloXrouteLabs"
    elif a in ma_b or a == "manifold":
         return "@foldfinance"
    elif a in bn_b or a == "blocknative":
        return "@blocknative"
    elif a in bu_z:
        return "@builder0x69"
    return a

w3 = Web3(Web3.HTTPProvider(RPC_ENDPOINT))
assert w3.isConnected()

# Twitter API KEY
with open("key/twitterkey.txt", "r") as f:
    consumer_key, consumer_secret, bearer, access_token, access_token_secret = f.read().strip().split(",")
    
client = tweepy.Client(
    consumer_key=consumer_key, consumer_secret=consumer_secret,
    access_token=access_token, access_token_secret=access_token_secret
)

# Use either beaconscan or beaconcha.in
URL = "https://beaconscan.com/slot/{}"
URL2 = "https://beaconcha.in/slot/{}"

# Tweet templates
TWEET = "High Proposer Payment Alert! 💸 \nValidator received {:,.3f} ETH\nBuilder: {}.\n" \
        + "Slot: {:,.0f}.\nReceived through the {} relay.\n" + URL

TWEET_2 = "High Proposer Payment Alert! 💸 \nValidator {} received {:,.2f} ETH\nBuilder: {} ({}).\n" \
          + "Slot: {:,.0f}.\nReceived through the {} relay.\n" + URL

TWEET_3 = "High Proposer Payment Alert! 💸 \nValidator {} received {:,.2f} ETH\nBlock built by a {} builder ({}) 👷‍.\n" \
          + "Slot: {:,.0f}.\nReceived through the {} relay.\n" + URL

def get_last_file(off=0):
    # Get latest mevboost.csv file
    maxfilenr = []
    for file in os.listdir(LOCATION):
        if file.startswith("mevboost_") and file.endswith(".csv"):
            nr = re.findall("[0-9]+", file)
            nr = [int(n) for n in nr]
            if len(nr) == 0:
                nr = 0
            else:
                nr = max(nr)
            maxfilenr.append(nr) 
    max_file = str(max(maxfilenr)+off)
    maxfilenr.remove(int(max_file))
    second_max = str(max(maxfilenr)+off)
    
    return LOCATION + "mevboost_" +  max_file + ".csv", LOCATION + "mevboost_" + second_max + ".csv"

def check_threshold(proposer_payment):
    return proposer_payment > 0.01  # 0.01 ETH filtresi

def process_data(df):
    for idx, row in df.iterrows():
        if not check_threshold(row['Proposer Payment (ETH)']):
            continue

        builder_label = get_builder_label(row['Builder Pubkey'])
        if int(row['Validator Index']) in validator_list:
            handle = get_twitter_handle(row['Builder Pubkey'])
            tweet_text = TWEET_2.format(row['Validator Index'], row['Proposer Payment (ETH)'], 
                                        builder_label, handle, row['Slot'], row['Relay'])
        else:
            tweet_text = TWEET_3.format(row['Validator Index'], row['Proposer Payment (ETH)'], 
                                        builder_label, row['Builder Pubkey'], row['Slot'], row['Relay'])
        
        print(colored(f"{datetime.now()}: Sending tweet: {tweet_text}", "green"))
        # client.create_tweet(text=tweet_text)
        time.sleep(1)

def main():
    while True:
        try:
            df = pd.read_csv(get_last_file()[0])
            process_data(df)
        except Exception as e:
            print(colored(f"Error: {str(e)}", "red"))
        time.sleep(60)

if __name__ == "__main__":
    main()
