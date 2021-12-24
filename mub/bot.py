import os
import re
import asyncio
import aiohttp

from mi.ext import commands
from mi import Router
from mi.note import Note, Reaction

from mub.exception import InstallDepenciesError, MisskeyBuildError


class InstanceManager:
    def __init__(self, bot: commands.Bot, config):
        self.bot = bot
        self.config = config
        self.upgratable:bool = False

    async def get_current_version(self) -> str:
        """
        現在のMisskeyInstanceが利用しているバージョン(ブランチ)を取得します
        """

        proc = await asyncio.create_subprocess_exec(*['git', 'branch'], cwd=self.config['Misskey']['path'], stdout=asyncio.subprocess.PIPE)
        proc_stdout = await proc.communicate()
        version = re.findall(r'(\(HEAD detached at (.*)\)| \* (.*))', str(proc_stdout[0].decode('utf-8')))
        return [i for i in version[0] if 'HEAD' not in i and len(i) > 0][0]

    async def get_repository(self):
        proc = await asyncio.create_subprocess_exec(*['git', 'config', '--get', 'remote.origin.url'], cwd=self.config['Misskey']['path'], stdout=asyncio.subprocess.PIPE)
        proc_stdout = await proc.communicate()
        return proc_stdout[0].decode('utf-8').replace('git@', '').replace('github.com/', '').replace('.git', '').replace('https://', '')

    async def get_remote_tags(self, repository: str):
        async with aiohttp.ClientSession() as session:
            res = await session.get(f'https://api.github.com/repos/{repository}/tags')
            return await res.json()

    async def get_latest(self, repository) -> str:
        async with aiohttp.ClientSession() as session:
            print(f'https://github.com/{repository}/releases/latest')
            res = await session.get(f'https://github.com/{repository}/releases/latest')
            return str(res.url)

    async def check(self, request_version: str, current_version: str):
        # '/releases/latest'
        repository = await self.get_repository()
        if request_version in 'latest':
            _new_version = await self.get_latest(repository)
            new_version = re.findall(r'releases/tag/(.*)', str(_new_version))[0]
        else:
            tags = await self.get_remote_tags(repository)
            for i in tags:
                if request_version in i['name']:
                    new_version = i['name']
                    break
        if 'new_version' not in locals():
            print('存在しないバージョンです')
        print(f'new: {new_version}\ncurrent: {current_version}')
        if new_version == current_version:
            return False, new_version
        else:
            return True, new_version

    async def check_update(self, version: str, mention:Note):
        current_version = await self.get_current_version()
        check_update, new_version = await self.check(request_version=version, current_version=current_version)
        if check_update:
            self.upgratable = True
            res = await mention.reply(f'アップグレードが利用可能です\nアップデートする場合は👍をつけてください\ncurrent: {current_version}\nnew: {new_version}')
            self.note_id = res.id
            self.new_version = new_version
        else:
            await self.bot.post_note('アップグレードする必要はなさそうです')

    async def checkout(self):
        print(['git', 'checkout', f'{self.new_version}'])
        proc = await asyncio.create_subprocess_exec(*['git', 'checkout', f'{self.new_version}'], cwd=self.config['Misskey']['path'], stdout=asyncio.subprocess.PIPE)
        proc_stdout = await proc.communicate()
        if proc_stdout[0].decode('utf-8') in 'HEAD is now at':
            return True
        return False

    async def install_dependencies(self):
        proc = await asyncio.create_subprocess_exec(*['yarn'], cwd=self.config['Misskey']['path'], stdout=asyncio.subprocess.PIPE)
        await proc.communicate()
        return proc.returncode
        

    async def build(self):
        os.environ['NODE_ENV'] = 'production'
        proc = await asyncio.create_subprocess_exec(*['yarn', 'build'], cwd=self.config['Misskey']['path'], stdout=asyncio.subprocess.PIPE)
        await proc.communicate()
        return proc.returncode
    
    async def migrate(self):
        proc = await asyncio.create_subprocess_exec(*['yarn', 'migrate'], cwd=self.config['Misskey']['path'], stdout=asyncio.subprocess.PIPE)
        await proc.communicate()
        return proc.returncode

    async def upgrade(self):
        checkout_status = await self.checkout()
        if checkout_status:
            exit_code = await self.install_dependencies()
            if exit_code != 0:
                raise InstallDepenciesError('依存関係のインストールに失敗しました')
            exit_code = await self.build()
            if exit_code != 0:
                raise MisskeyBuildError()
            return await self.migrate()
            
        

class MUB(commands.Bot):
    def __init__(self, config):
        super().__init__('tu!tu!tu!')
        self.config = config
        self.instance_manager = InstanceManager(self, config=self.config)

    async def on_ready(self, ws):
        await Router(ws).connect_channel(['main'])

    async def on_reaction(self, reaction: Reaction):
        if self.instance_manager.upgratable:
            print(reaction.note.id, self.instance_manager.note_id)
            if reaction.note.id == self.instance_manager.note_id and reaction.reaction == '👍':
                await self.post_note('アップグレードを開始します')
                try:
                    exit_code = await self.instance_manager.upgrade()
                    if exit_code == 0:
                        await self.post_note('更新に成功しました')
                    else:
                        await self.post_note('更新に失敗しました\n原因: ビルドに失敗')
                        
                except InstallDepenciesError:
                    await self.post_note('更新に失敗しました\n原因: 依存関係のインストールに失敗')
                

    async def on_mention(self, mention: Note):
        update_text = re.findall(r'(v(.*)に|最新に|latestに)アップデート.*', str(mention.content))
        if update_text:
            await self.instance_manager.check_update(version=update_text[0][0].replace('最新', 'latest').replace('に', ''), mention=mention)
