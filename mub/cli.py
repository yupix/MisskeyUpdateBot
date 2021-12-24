import asyncio
import argparse
import configparser
from mub.bot import MUB

from mub.exception import ArgumentError

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config')
    args = parser.parse_args()
    
    if args.config is None:
        raise ArgumentError('--config引数は必須です')
    config = configparser.ConfigParser()
    config.read(args.config)
    bot = MUB(config=config)
    asyncio.run(bot.start(config['BOT']['url'], config['BOT']['token']))
        
    